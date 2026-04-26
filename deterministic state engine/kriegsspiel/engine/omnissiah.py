"""
The Omnissiah — deterministic tactical resolver.

                    ┌──────────────┐
   [LLM issues] ──▶ │ MissionOrders│
                    └──────┬───────┘
                           │  group-level intent
                    ┌──────▼───────┐
                    │  Omnissiah   │  ← math gods
                    └──────┬───────┘
                           │  (new WorldState, [EngineEvent])
                    ┌──────▼───────┐
                    │   VectorDB   │  ← snapshot for next LLM turn
                    └──────────────┘

Pipeline per timestep
─────────────────────
  1. validate_orders   – reject unknown / dead / unowned units
  2. movement_phase    – A* pathfind all groups simultaneously
  3. combat_phase      – adjacent fights + suppression fires
  4. control_update    – presence → cell ownership shift
  5. objective_update  – check capture / loss
  6. supply_phase      – burn supply days; mark isolated
  7. advance_time      – increment turn + timestamp

The LLM must never specify individual unit coordinates.
It issues a MissionOrder per group; this module does all the geometry.
"""

from __future__ import annotations

import copy
import heapq
import math
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from .enums import (
    EventType,
    Posture,
    Readiness,
    ReasonCode,
    Side,
    TerrainBase,
    TerrainFeature,
)
from .orders import MissionOrder, MissionType
from .state import (
    Coord,
    ControlState,
    Objective,
    TerrainGrid,
    UnitState,
    UnitTemplate,
    WorldState,
    chebyshev_distance,
    validate_world_invariants,
)


# ---------------------------------------------------------------------------
# Engine event
# ---------------------------------------------------------------------------

class EngineEvent(BaseModel):
    model_config = ConfigDict(frozen=True)

    event_type: EventType
    turn: int
    unit_id: Optional[str] = None
    from_coord: Optional[Coord] = None
    to_coord: Optional[Coord] = None
    reason: ReasonCode
    narrative: str
    detail: dict = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Terrain modifiers
# ---------------------------------------------------------------------------

_TERRAIN_DEFENSE_MOD: dict[TerrainBase, float] = {
    TerrainBase.OPEN:       1.0,
    TerrainBase.FOREST:     1.4,
    TerrainBase.URBAN:      1.6,
    TerrainBase.MOUNTAIN:   1.5,
    TerrainBase.SWAMP:      1.2,
    TerrainBase.WATER:      1.0,
    TerrainBase.IMPASSABLE: 1.0,
}

_DUG_IN_MOD        = 1.3
_FORTIFIED_MOD     = 1.5
_SUPPLY_LOW_ATK    = 0.7   # attacker penalty when unsupplied

# Odds thresholds (attacker_power / defender_power)
_ODDS_WIN          = 3.0
_ODDS_WIN_CLEAR    = 5.0
_ODDS_STALEMATE    = 1.5

# Strength deltas per engagement
_DMG_WIN_LOSER     = 0.35
_DMG_WIN_WINNER    = 0.08
_DMG_STALEMATE     = 0.15

# Suppression fire per suppressor
_SUPPRESS_STR_HIT  = 0.05


# ---------------------------------------------------------------------------
# A* pathfinder
# ---------------------------------------------------------------------------

def _astar(
    grid: TerrainGrid,
    start: Coord,
    goal: Coord,
    blocked: set[Coord],
) -> list[Coord]:
    """Return path start→goal inclusive, or [] if unreachable.

    `blocked` contains friendly-occupied cells that cannot be destinations,
    but units may pass through enemy-occupied cells en route.
    """
    if not grid.is_passable_ground(goal) or goal in blocked:
        return []
    if start == goal:
        return [start]

    open_heap: list[tuple[float, Coord]] = [(0.0, start)]
    came_from: dict[Coord, Coord] = {}
    g: dict[Coord, float] = {start: 0.0}

    while open_heap:
        _, current = heapq.heappop(open_heap)
        if current == goal:
            path: list[Coord] = []
            node = goal
            while node != start:
                path.append(node)
                node = came_from[node]
            path.append(start)
            path.reverse()
            return path

        for nb in grid.neighbors_8(current):
            if not grid.is_passable_ground(nb):
                continue
            tentative_g = g[current] + grid.movement_cost(nb)
            if tentative_g < g.get(nb, math.inf):
                came_from[nb] = current
                g[nb] = tentative_g
                f = tentative_g + chebyshev_distance(nb, goal)
                heapq.heappush(open_heap, (f, nb))

    return []


def _cells_per_turn(
    unit: UnitState,
    template: UnitTemplate,
    grid: TerrainGrid,
    km_per_cell: float,
) -> int:
    """Movement allowance for this unit this turn, in cells."""
    on_road = grid.has_feature(unit.position, TerrainFeature.ROAD)
    speed_km = template.speed_road if on_road else template.speed_offroad
    return max(1, int(speed_km / km_per_cell))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _enemy_centroid(world: WorldState, side: Side) -> Optional[Coord]:
    enemies = world.alive_units_of_side(world.opposing_side(side))
    if not enemies:
        return None
    r = sum(u.position[0] for u in enemies) / len(enemies)
    c = sum(u.position[1] for u in enemies) / len(enemies)
    return (int(round(r)), int(round(c)))


def _farthest_passable_from(
    grid: TerrainGrid,
    origin: Coord,
    away_from: Coord,
    *,
    radius: int = 10,
) -> Coord:
    """Return the passable cell within radius that maximises distance from away_from."""
    best = origin
    best_dist = chebyshev_distance(origin, away_from)
    for dr in range(-radius, radius + 1):
        for dc in range(-radius, radius + 1):
            cand = (origin[0] + dr, origin[1] + dc)
            if grid.in_bounds(cand) and grid.is_passable_ground(cand):
                d = chebyshev_distance(cand, away_from)
                if d > best_dist:
                    best_dist = d
                    best = cand
    return best


def _update_readiness(unit: UnitState) -> None:
    """Recalculate readiness from current strength."""
    if unit.strength <= 0.0:
        unit.strength = 0.0
        unit.readiness = Readiness.DESTROYED
    elif unit.strength < 0.3 and unit.readiness == Readiness.FULLY_OPERATIONAL:
        unit.readiness = Readiness.DEGRADED


# ---------------------------------------------------------------------------
# Mission → target cell
# ---------------------------------------------------------------------------

def _resolve_target(
    world: WorldState,
    unit: UnitState,
    order: MissionOrder,
) -> Optional[Coord]:
    mission = order.mission

    if mission in (MissionType.HOLD, MissionType.SUPPRESS):
        return None  # No movement

    if order.target_coord is not None:
        if mission == MissionType.WITHDRAW:
            return _farthest_passable_from(
                world.terrain, unit.position, order.target_coord
            )
        return order.target_coord

    # Heuristic: no explicit target given
    centroid = _enemy_centroid(world, unit.side)

    if mission in (MissionType.ADVANCE, MissionType.ASSAULT, MissionType.RECON):
        return centroid

    if mission == MissionType.WITHDRAW:
        if centroid is None:
            return None
        return _farthest_passable_from(world.terrain, unit.position, centroid)

    return None


# ---------------------------------------------------------------------------
# Phase 1 — validate orders
# ---------------------------------------------------------------------------

def _validate_orders(
    world: WorldState,
    orders: list[MissionOrder],
    events: list[EngineEvent],
) -> list[MissionOrder]:
    valid: list[MissionOrder] = []
    for order in orders:
        ok = True
        for uid in order.unit_ids:
            u = world.units.get(uid)
            if u is None:
                events.append(EngineEvent(
                    event_type=EventType.INVARIANT_VIOLATION, turn=world.turn,
                    unit_id=uid, reason=ReasonCode.VAL_UNIT_NOT_FOUND,
                    narrative=f"Order {order.order_id}: unit {uid} not found.",
                ))
                ok = False
            elif not u.is_alive:
                events.append(EngineEvent(
                    event_type=EventType.INVARIANT_VIOLATION, turn=world.turn,
                    unit_id=uid, reason=ReasonCode.VAL_UNIT_DESTROYED,
                    narrative=f"Order {order.order_id}: unit {uid} is destroyed.",
                ))
                ok = False
            elif u.side != order.side:
                events.append(EngineEvent(
                    event_type=EventType.INVARIANT_VIOLATION, turn=world.turn,
                    unit_id=uid, reason=ReasonCode.VAL_UNIT_NOT_OWNED,
                    narrative=f"Order {order.order_id}: unit {uid} belongs to {u.side.value}, not {order.side.value}.",
                ))
                ok = False
        if ok:
            valid.append(order)
    return valid


# ---------------------------------------------------------------------------
# Phase 2 — movement
# ---------------------------------------------------------------------------

def _movement_phase(
    world: WorldState,
    units: dict[str, UnitState],
    templates: dict[str, UnitTemplate],
    orders: list[MissionOrder],
    claimed: dict[Side, set[Coord]],
    km_per_cell: float,
    events: list[EngineEvent],
) -> None:
    for order in orders:
        for uid in order.unit_ids:
            u = units.get(uid)
            if u is None or not u.is_alive:
                continue

            tmpl = templates.get(u.template_id)
            if tmpl is None:
                events.append(EngineEvent(
                    event_type=EventType.UNIT_MOVE_BLOCKED, turn=world.turn,
                    unit_id=uid, from_coord=u.position,
                    reason=ReasonCode.VAL_UNIT_NOT_FOUND,
                    narrative=f"{uid}: template {u.template_id!r} missing; unit holds.",
                ))
                u.posture = Posture.DEFENSIVE
                claimed[u.side].add(u.position)
                continue

            if order.mission == MissionType.HOLD:
                u.dug_in = True
                u.posture = Posture.DEFENSIVE
                claimed[u.side].add(u.position)
                continue

            if order.mission == MissionType.SUPPRESS:
                u.posture = Posture.SCREENING
                claimed[u.side].add(u.position)
                continue

            target = _resolve_target(world, u, order)
            if target is None:
                _emit_fallback_hold(u, order, world.turn, events)
                claimed[u.side].add(u.position)
                continue

            path = _astar(world.terrain, u.position, target, claimed[u.side])

            if not path or len(path) <= 1:
                events.append(EngineEvent(
                    event_type=EventType.UNIT_MOVE_BLOCKED, turn=world.turn,
                    unit_id=uid, from_coord=u.position, to_coord=target,
                    reason=ReasonCode.MOV_NO_PATH,
                    narrative=f"{uid}: no path to {target}; holding.",
                ))
                _emit_fallback_hold(u, order, world.turn, events)
                claimed[u.side].add(u.position)
                continue

            steps = _cells_per_turn(u, tmpl, world.terrain, km_per_cell)
            dest_idx = min(steps, len(path) - 1)
            dest = path[dest_idx]

            # Back off from friendly-occupied destinations
            while dest != u.position and dest in claimed[u.side]:
                dest_idx -= 1
                dest = path[dest_idx]

            # ZOC / contact rule:
            #   ADVANCE  → halt the step *before* entering an enemy's ZOC (Chebyshev ≤ 1)
            #   ASSAULT  → advance *to* the first enemy cell encountered (Chebyshev = 0),
            #              so close combat resolves at distance 0 without overshooting.
            is_assault = order.mission is MissionType.ASSAULT
            stop_dist  = 0 if is_assault else 1
            enemy_posns = frozenset(
                eu.position for eu in units.values()
                if eu.is_alive and eu.side != u.side
            )
            if enemy_posns:
                for zoc_idx in range(1, dest_idx + 1):
                    if any(chebyshev_distance(path[zoc_idx], ep) <= stop_dist for ep in enemy_posns):
                        dest_idx = zoc_idx if is_assault else max(0, zoc_idx - 1)
                        break
                dest = path[dest_idx]
                # Fallback cell may coincide with a friendly — re-check stacking
                while dest != u.position and dest in claimed[u.side]:
                    dest_idx -= 1
                    dest = path[dest_idx]

            # Final stacking guard — belt-and-suspenders before committing the move
            while dest != u.position and dest in claimed[u.side]:
                dest_idx -= 1
                dest = path[dest_idx]

            old_pos = u.position
            u.position = dest
            u.dug_in = False

            if order.mission == MissionType.WITHDRAW:
                u.posture = Posture.MOVING
            elif order.mission in (MissionType.ADVANCE, MissionType.ASSAULT):
                u.posture = Posture.OFFENSIVE
            elif order.mission == MissionType.RECON:
                u.posture = Posture.MOVING

            if dest != old_pos:
                claimed[u.side].discard(old_pos)  # vacated
            claimed[u.side].add(dest)

            if dest != old_pos:
                events.append(EngineEvent(
                    event_type=EventType.UNIT_MOVED, turn=world.turn,
                    unit_id=uid, from_coord=old_pos, to_coord=dest,
                    reason=ReasonCode.MOV_OK,
                    narrative=f"{uid} moved {old_pos} → {dest}.",
                ))


def _emit_fallback_hold(
    unit: UnitState,
    order: MissionOrder,
    turn: int,
    events: list[EngineEvent],
) -> None:
    unit.posture = Posture.DEFENSIVE
    events.append(EngineEvent(
        event_type=EventType.UNIT_MOVE_BLOCKED, turn=turn,
        unit_id=unit.unit_id, from_coord=unit.position,
        reason=ReasonCode.SYS_FALLBACK_HOLD,
        narrative=f"{unit.unit_id}: {order.mission.value} failed; holding.",
    ))


# ---------------------------------------------------------------------------
# Phase 3 — combat
# ---------------------------------------------------------------------------

def _combat_phase(
    world: WorldState,
    units: dict[str, UnitState],
    templates: dict[str, UnitTemplate],
    orders: list[MissionOrder],
    km_per_cell: float,
    events: list[EngineEvent],
) -> None:
    unit_mission: dict[str, MissionType] = {
        uid: o.mission for o in orders for uid in o.unit_ids
    }

    # --- Suppression fires ---
    for order in orders:
        if order.mission != MissionType.SUPPRESS:
            continue
        for uid in order.unit_ids:
            u = units.get(uid)
            if u is None or not u.is_alive:
                continue
            tmpl = templates.get(u.template_id)
            if tmpl is None or tmpl.fires_range_km <= 0:
                continue

            range_cells = max(1, int(tmpl.fires_range_km / km_per_cell))
            enemy_side = world.opposing_side(u.side)
            hits: list[str] = []

            for enemy in [units[e.unit_id] for e in world.alive_units_of_side(enemy_side) if e.unit_id in units]:
                if chebyshev_distance(u.position, enemy.position) <= range_cells:
                    enemy.strength = max(0.0, enemy.strength - _SUPPRESS_STR_HIT)
                    if enemy.readiness == Readiness.FULLY_OPERATIONAL:
                        enemy.readiness = Readiness.SUPPRESSED
                    _update_readiness(enemy)
                    hits.append(enemy.unit_id)

            if hits:
                events.append(EngineEvent(
                    event_type=EventType.UNIT_SUPPRESSED, turn=world.turn,
                    unit_id=uid, from_coord=u.position,
                    reason=ReasonCode.CMB_FIRES_SUPPORT_APPLIED,
                    narrative=f"{uid} suppression fires hit: {hits}.",
                    detail={"targets": hits, "str_hit": _SUPPRESS_STR_HIT},
                ))

    # --- Adjacent / co-located close combat ---
    # Use the snapshot (post-move positions) to find contacts at distance <= 1.
    resolved: set[frozenset[str]] = set()

    alive_snapshot = [u for u in units.values() if u.is_alive]

    for u in alive_snapshot:
        enemy_side = world.opposing_side(u.side)
        contacts = [
            e for e in alive_snapshot
            if e.side == enemy_side and chebyshev_distance(u.position, e.position) <= 1
        ]
        for e in contacts:
            e = units.get(e.unit_id)
            if e is None or not e.is_alive:
                continue

            pair = frozenset([u.unit_id, e.unit_id])
            if pair in resolved:
                continue
            resolved.add(pair)

            u_mission = unit_mission.get(u.unit_id, MissionType.HOLD)
            e_mission = unit_mission.get(e.unit_id, MissionType.HOLD)
            offensive = {MissionType.ADVANCE, MissionType.ASSAULT}

            u_attacks = u_mission in offensive
            e_attacks = e_mission in offensive

            if u_attacks and not e_attacks:
                attacker, defender = u, e
            elif e_attacks and not u_attacks:
                attacker, defender = e, u
            else:
                # Both or neither attacking — higher offensive power goes first
                tmpl_u = templates.get(u.template_id)
                tmpl_e = templates.get(e.template_id)
                u_off = (tmpl_u.offensive_rating if tmpl_u else 0) * u.effective_combat_factor
                e_off = (tmpl_e.offensive_rating if tmpl_e else 0) * e.effective_combat_factor
                attacker, defender = (u, e) if u_off >= e_off else (e, u)

            _resolve_combat(world, units, attacker, defender, templates, events)


def _resolve_combat(
    world: WorldState,
    units: dict[str, UnitState],
    attacker: UnitState,
    defender: UnitState,
    templates: dict[str, UnitTemplate],
    events: list[EngineEvent],
) -> None:
    atk_tmpl = templates.get(attacker.template_id)
    def_tmpl = templates.get(defender.template_id)

    if atk_tmpl is None or not atk_tmpl.can_assault:
        return

    def_cell = world.terrain.cell_at(defender.position)

    supply_mod = _SUPPLY_LOW_ATK if not world.is_supplied(attacker) else 1.0
    atk_power = attacker.effective_combat_factor * atk_tmpl.offensive_rating * supply_mod

    def_rating = def_tmpl.defensive_rating if def_tmpl else 10
    terrain_mod = _TERRAIN_DEFENSE_MOD.get(def_cell.base, 1.0)
    if world.terrain.has_feature(defender.position, TerrainFeature.FORTIFIED):
        terrain_mod *= _FORTIFIED_MOD
    if defender.dug_in:
        terrain_mod *= _DUG_IN_MOD
    def_power = defender.effective_combat_factor * def_rating * terrain_mod

    odds = atk_power / max(def_power, 0.01)

    if odds >= _ODDS_WIN:
        multiplier = 1.4 if odds >= _ODDS_WIN_CLEAR else 1.0
        str_loss_def = _DMG_WIN_LOSER * multiplier
        str_loss_atk = _DMG_WIN_WINNER
        reason = ReasonCode.CMB_ATTACKER_WIN
        result = "attacker wins"
    elif odds >= _ODDS_STALEMATE:
        str_loss_def = _DMG_STALEMATE
        str_loss_atk = _DMG_STALEMATE
        reason = ReasonCode.CMB_STALEMATE
        result = "stalemate"
    else:
        str_loss_atk = _DMG_WIN_LOSER
        str_loss_def = _DMG_WIN_WINNER
        reason = ReasonCode.CMB_DEFENDER_WIN
        result = "defender wins"

    prev_atk = attacker.strength
    prev_def = defender.strength

    attacker.strength = max(0.0, attacker.strength - str_loss_atk)
    defender.strength = max(0.0, defender.strength - str_loss_def)
    _update_readiness(attacker)
    _update_readiness(defender)

    for unit in (attacker, defender):
        if unit.readiness == Readiness.DESTROYED:
            events.append(EngineEvent(
                event_type=EventType.UNIT_DESTROYED, turn=world.turn,
                unit_id=unit.unit_id, from_coord=unit.position,
                reason=reason,
                narrative=f"{unit.unit_id} destroyed at {unit.position}.",
            ))

    events.append(EngineEvent(
        event_type=EventType.COMBAT_RESOLVED, turn=world.turn,
        unit_id=attacker.unit_id,
        from_coord=attacker.position,
        to_coord=defender.position,
        reason=reason,
        narrative=(
            f"{attacker.unit_id} vs {defender.unit_id} at {defender.position}: "
            f"odds={odds:.2f} → {result}. "
            f"ATK {prev_atk:.2f}→{attacker.strength:.2f}, "
            f"DEF {prev_def:.2f}→{defender.strength:.2f}."
        ),
        detail={
            "attacker_id": attacker.unit_id,
            "defender_id": defender.unit_id,
            "odds": round(odds, 3),
            "atk_power": round(atk_power, 2),
            "def_power": round(def_power, 2),
            "str_loss_atk": round(str_loss_atk, 3),
            "str_loss_def": round(str_loss_def, 3),
            "terrain_mod": round(terrain_mod, 2),
        },
    ))


# ---------------------------------------------------------------------------
# Phase 4 — control update
# ---------------------------------------------------------------------------

def _control_update(
    world: WorldState,
    units: dict[str, UnitState],
    control: dict[str, ControlState],
    turn: int,
    events: list[EngineEvent],
) -> None:
    alive = [u for u in units.values() if u.is_alive]

    for r in range(world.terrain.height):
        for c in range(world.terrain.width):
            coord = (r, c)
            cell_key = WorldState.cell_key(coord)

            blue_here = any(u.side == Side.BLUE and u.position == coord for u in alive)
            red_here  = any(u.side == Side.RED  and u.position == coord for u in alive)

            if not (blue_here or red_here):
                continue

            if blue_here and red_here:
                # Contested — reset persistence
                ctl = control.get(cell_key)
                if ctl is not None:
                    ctl.persistence_turns = 0
                    # opposing_side(NEUTRAL) returns NEUTRAL, which would equal
                    # controlled_by and fail the ControlState invariant.
                    opposing = world.opposing_side(ctl.controlled_by)
                    ctl.contender = opposing if opposing != ctl.controlled_by else None
                events.append(EngineEvent(
                    event_type=EventType.CONTROL_CHANGED, turn=turn,
                    from_coord=coord, reason=ReasonCode.CTL_CONTESTED,
                    narrative=f"Cell {coord} contested.",
                ))
                continue

            presser = Side.BLUE if blue_here else Side.RED

            ctl = control.get(cell_key)
            if ctl is None:
                control[cell_key] = ControlState(
                    cell=coord, controlled_by=presser, persistence_turns=1
                )
            elif ctl.controlled_by == presser:
                ctl.persistence_turns += 1
            else:
                ctl.persistence_turns += 1
                if ctl.persistence_turns >= 2:
                    old = ctl.controlled_by
                    ctl.controlled_by = presser
                    ctl.persistence_turns = 0
                    ctl.contender = None
                    dom_reason = (
                        ReasonCode.CTL_DOMINANCE_BLUE
                        if presser == Side.BLUE
                        else ReasonCode.CTL_DOMINANCE_RED
                    )
                    events.append(EngineEvent(
                        event_type=EventType.CONTROL_CHANGED, turn=turn,
                        from_coord=coord, reason=dom_reason,
                        narrative=f"Cell {coord} flipped {old.value} → {presser.value}.",
                    ))


# ---------------------------------------------------------------------------
# Phase 5 — objective update
# ---------------------------------------------------------------------------

def _objective_update(
    world: WorldState,
    units: dict[str, UnitState],
    objectives: dict[str, Objective],
    turn: int,
    events: list[EngineEvent],
) -> None:
    alive = [u for u in units.values() if u.is_alive]

    for obj in objectives.values():
        present = [u for u in alive if u.position == obj.cell]
        if not present:
            continue
        sides = {u.side for u in present}
        if len(sides) != 1:
            continue  # Contested

        holder = next(iter(sides))
        if obj.held_by != holder:
            obj.held_by = holder
            obj.taken_at_turn = turn
            dom_reason = (
                ReasonCode.CTL_DOMINANCE_BLUE
                if holder == Side.BLUE
                else ReasonCode.CTL_DOMINANCE_RED
            )
            events.append(EngineEvent(
                event_type=EventType.OBJECTIVE_TAKEN, turn=turn,
                from_coord=obj.cell, reason=dom_reason,
                narrative=f"Objective '{obj.name}' at {obj.cell} taken by {holder.value}.",
                detail={"objective_id": obj.objective_id, "weight": obj.weight},
            ))


# ---------------------------------------------------------------------------
# Phase 6 — supply
# ---------------------------------------------------------------------------

def _supply_phase(
    units: dict[str, UnitState],
    minutes_per_turn: int,
    turn: int,
    events: list[EngineEvent],
) -> None:
    cost = minutes_per_turn / (24 * 60)  # fraction of a day per turn

    for u in units.values():
        if not u.is_alive or u.supply_days_remaining is None:
            continue

        u.supply_days_remaining = max(0.0, u.supply_days_remaining - cost)

        if u.supply_days_remaining == 0.0:
            u.turns_isolated += 1
            if u.turns_isolated >= 3 and u.readiness == Readiness.FULLY_OPERATIONAL:
                u.readiness = Readiness.DEGRADED
            events.append(EngineEvent(
                event_type=EventType.UNIT_ISOLATED, turn=turn,
                unit_id=u.unit_id, from_coord=u.position,
                reason=ReasonCode.SUP_ISOLATED,
                narrative=f"{u.unit_id}: supply exhausted (isolated {u.turns_isolated} turns).",
                detail={"turns_isolated": u.turns_isolated},
            ))
        else:
            u.turns_isolated = 0
            if u.supply_days_remaining < 0.5:
                events.append(EngineEvent(
                    event_type=EventType.SUPPLY_CONSUMED, turn=turn,
                    unit_id=u.unit_id, from_coord=u.position,
                    reason=ReasonCode.SUP_LOW,
                    narrative=f"{u.unit_id}: supply low ({u.supply_days_remaining:.1f} days).",
                    detail={"supply_days_remaining": round(u.supply_days_remaining, 2)},
                ))


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def advance_timestep(
    world: WorldState,
    templates: dict[str, UnitTemplate],
    orders: list[MissionOrder],
    *,
    km_per_cell: float = 5.0,
) -> tuple[WorldState, list[EngineEvent]]:
    """Resolve one timestep.

    Returns a brand-new WorldState and the full event log for this turn.
    The caller (state_engine) is responsible for persisting both to VectorDB.

    Args:
        world:        Current world state (not mutated).
        templates:    Dict of template_id → UnitTemplate for all units.
        orders:       LLM-issued mission orders for this turn.
        km_per_cell:  Map scale; default 5 km per grid cell.

    Returns:
        (new_world, events)
    """
    events: list[EngineEvent] = []

    # 1. Validate
    valid_orders = _validate_orders(world, orders, events)
    valid_orders = sorted(valid_orders, key=lambda o: o.priority, reverse=True)

    # Work on mutable shallow copies of per-unit state
    units     = {k: v.model_copy(deep=True) for k, v in world.units.items()}
    control   = {k: v.model_copy(deep=True) for k, v in world.control.items()}
    objectives = {k: v.model_copy(deep=True) for k, v in world.objectives.items()}

    # Pre-claim every alive unit's starting position.
    # Ordered units release their start when they actually move, preventing two
    # units in the same order from both targeting a cell occupied by a peer.
    ordered_ids = {uid for o in valid_orders for uid in o.unit_ids}
    claimed: dict[Side, set[Coord]] = {Side.BLUE: set(), Side.RED: set()}
    for u in units.values():
        if u.is_alive:
            claimed[u.side].add(u.position)

    # 2. Movement
    _movement_phase(world, units, templates, valid_orders, claimed, km_per_cell, events)

    # 3. Combat — use original world geometry for adjacency queries; positions already updated
    # Build a transient world view with new positions for adjacency checks
    _combat_phase(
        _world_snapshot(world, units), units, templates, valid_orders, km_per_cell, events
    )

    # 4. Control
    _control_update(world, units, control, world.turn, events)

    # 5. Objectives
    _objective_update(world, units, objectives, world.turn, events)

    # 6. Supply
    _supply_phase(units, world.minutes_per_turn, world.turn, events)

    # 7. Build new WorldState — terrain is shared (immutable cells)
    new_world = WorldState(
        identity=world.identity,
        turn=world.turn + 1,
        minutes_per_turn=world.minutes_per_turn,
        timestamp_minutes=world.timestamp_minutes + world.minutes_per_turn,
        terrain=world.terrain,
        units=units,
        control=control,
        objectives=objectives,
        side_posture=dict(world.side_posture),
    )

    events.append(EngineEvent(
        event_type=EventType.TURN_ADVANCED,
        turn=new_world.turn,
        reason=ReasonCode.SYS_TURN_ADVANCED,
        narrative=f"Turn {new_world.turn} complete. Elapsed: {new_world.timestamp_minutes} min.",
    ))

    validate_world_invariants(new_world)
    return new_world, events


def _world_snapshot(base: WorldState, units: dict[str, UnitState]) -> WorldState:
    """Lightweight read-only view with updated unit positions for adjacency queries."""
    return WorldState(
        identity=base.identity,
        turn=base.turn,
        minutes_per_turn=base.minutes_per_turn,
        timestamp_minutes=base.timestamp_minutes,
        terrain=base.terrain,
        units=units,
        control=base.control,
        objectives=base.objectives,
        side_posture=dict(base.side_posture),
    )
