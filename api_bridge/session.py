"""
In-memory session store and WorldState projection helpers.

Each game session is keyed by a short UUID.  Sessions are lost on
restart — no persistence layer yet.
"""

import sys
from pathlib import Path

from .schema import (
    UnitOut, ForceOut, ObjectiveOut, TerrainCellOut, MapOut,
    DecisionOptionOut, PendingDecisionOut, TurnRecordOut, GameStateOut, AAROut,
)

# ── Engine path ───────────────────────────────────────────────────────────────
_ENGINE = Path(__file__).parent.parent / "deterministic state engine"
sys.path.insert(0, str(_ENGINE))

from kriegsspiel.engine.state import WorldState          # noqa: E402
from kriegsspiel.engine.enums import Side                # noqa: E402
from kriegsspiel.scenarios.latgale_2027 import build_latgale_world  # noqa: E402

# ── Store ─────────────────────────────────────────────────────────────────────
_worlds:     dict[str, WorldState] = {}
_turn_logs:  dict[str, list[TurnRecordOut]] = {}

TURNS_TOTAL = 10

# ── Decision catalogue ────────────────────────────────────────────────────────
DECISIONS: dict[str, tuple[str, str]] = {
    "hold":           ("HOLD FORWARD",    "Preserves terrain, accepts attrition"),
    "reorient_fires": ("REORIENT FIRES",  "Disrupts RED tempo on confirmed axis"),
    "commit_reserve": ("COMMIT RESERVE",  "Gains ground, exposes flank"),
    "elastic_defense":("ELASTIC DEFENSE", "Preserves CP, trades terrain deliberately"),
    "counter_battery":("COUNTER-BATTERY", "Degrades RED fires, combined arms push"),
    "mass_fires_deep":("STRIKE DEEP",     "Disrupts RED support, no BLUE maneuver"),
    "ew_suppress":    ("EW SUPPRESS",     "Neutralises RED fires this turn"),
    "cyber_strike":   ("CYBER STRIKE",    "Lasting RED FRS strength hit"),
    "consolidate":    ("CONSOLIDATE",     "Restores BLUE MNV strength, no terrain gain"),
    "withdraw":       ("WITHDRAW LOCALLY","Preserves combat power, cedes terrain"),
}

ATTACKING_KEYS = {"commit_reserve", "counter_battery", "mass_fires_deep", "reorient_fires"}

# ── CRUD ──────────────────────────────────────────────────────────────────────

def create(game_id: str) -> None:
    _worlds[game_id]    = build_latgale_world()
    _turn_logs[game_id] = []

def exists(game_id: str) -> bool:
    return game_id in _worlds

def get_world(game_id: str) -> WorldState:
    return _worlds[game_id]

def get_logs(game_id: str) -> list[TurnRecordOut]:
    return _turn_logs[game_id]

def count() -> int:
    return len(_worlds)

# ── Projection helpers ────────────────────────────────────────────────────────

def _unit_type(unit_id: str) -> str:
    for part in unit_id.split("-"):
        if part in ("MNV", "FRS", "ENB"):
            return part
    return "UNK"

def _cp(world: WorldState, side: Side) -> float:
    units = [u for u in world.units.values() if u.side == side]
    return round(sum(u.strength for u in units) / len(units) * 100, 1) if units else 0.0

def _force(world: WorldState, side: Side) -> ForceOut:
    units = [
        UnitOut(
            unit_id=u.unit_id,
            side=u.side.value,
            unit_type=_unit_type(u.unit_id),
            position=list(u.position),
            strength=round(u.strength, 3),
            readiness=u.readiness.value,
            posture=u.posture.value,
            dug_in=u.dug_in,
        )
        for u in world.units.values() if u.side == side
    ]
    return ForceOut(side=side.value, combat_power=_cp(world, side), units=units)

def _objectives(world: WorldState) -> list[ObjectiveOut]:
    return [
        ObjectiveOut(
            id=o.objective_id,
            name=o.name,
            position=list(o.cell),
            controlled_by=o.held_by.value,
            weight=o.weight,
        )
        for o in world.objectives.values()
    ]

def _map(world: WorldState) -> MapOut:
    cells = [
        TerrainCellOut(row=r, col=c, terrain=world.terrain.cell_at((r, c)).base.name)
        for r in range(world.terrain.height)
        for c in range(world.terrain.width)
        if world.terrain.cell_at((r, c)).base.name != "OPEN"
    ]
    return MapOut(rows=world.terrain.height, cols=world.terrain.width, km_per_cell=5.0, cells=cells)

def _pending(turn: int) -> PendingDecisionOut:
    options = [DecisionOptionOut(key=k, label=v[0], consequence_hint=v[1]) for k, v in DECISIONS.items()]
    return PendingDecisionOut(
        turn=turn,
        context=f"Turn {turn}. Evaluate RED disposition and choose BLUE posture for the next 6-hour window.",
        options=options,
    )

def _outcome(world: WorldState) -> str:
    if world.turn <= TURNS_TOTAL:
        return "running"
    blue_held = sum(1 for o in world.objectives.values() if o.held_by == Side.BLUE)
    return "blue_win" if blue_held >= 2 else "red_win"

# ── Public projectors ─────────────────────────────────────────────────────────

def to_game_state(game_id: str) -> GameStateOut:
    world = _worlds[game_id]
    logs  = _turn_logs[game_id]
    oc    = _outcome(world)
    return GameStateOut(
        game_id=game_id,
        scenario="latgale_2027",
        status=oc,
        turn=world.turn,
        turns_total=TURNS_TOTAL,
        blue_force=_force(world, Side.BLUE),
        red_force=_force(world, Side.RED),
        objectives=_objectives(world),
        map=_map(world),
        turn_log=logs,
        pending_decision=_pending(world.turn) if oc == "running" else None,
    )

def to_aar(game_id: str) -> AAROut:
    world = _worlds[game_id]
    logs  = _turn_logs[game_id]
    return AAROut(
        game_id=game_id,
        outcome=_outcome(world),
        turns_played=len(logs),
        blue_cp_final=_cp(world, Side.BLUE),
        red_cp_final=_cp(world, Side.RED),
        objectives_held=[o.objective_id for o in world.objectives.values() if o.held_by == Side.BLUE],
        turn_log=logs,
    )

# ── Resolve one turn ──────────────────────────────────────────────────────────

def resolve_action(game_id: str, decision_key: str, note: str) -> None:
    """
    Apply BLUE's decision, run combat resolution, advance the turn counter,
    and append a TurnRecord.  Movement and supply are wired in next (omnissiah).
    """
    world = _worlds[game_id]
    logs  = _turn_logs[game_id]
    current_turn = world.turn

    blue_units = [u for u in world.units.values() if u.side == Side.BLUE]
    red_units  = [u for u in world.units.values() if u.side == Side.RED]

    decision_list = []
    for u in blue_units:
        if decision_key in ATTACKING_KEYS and red_units:
            target = min(red_units, key=lambda r: abs(r.position[0]-u.position[0]) + abs(r.position[1]-u.position[1]))
            decision_list.append({"unit_id": u.unit_id, "action": "ATTACK", "target_id": target.unit_id, "target_position": None})
        else:
            decision_list.append({"unit_id": u.unit_id, "action": "WAIT", "target_id": None, "target_position": None})
    for u in red_units:
        if blue_units:
            target = min(blue_units, key=lambda b: abs(b.position[0]-u.position[0]) + abs(b.position[1]-u.position[1]))
            decision_list.append({"unit_id": u.unit_id, "action": "ATTACK", "target_id": target.unit_id, "target_position": None})

    attack_map = world._build_attack_map(decision_list)
    world._resolve_attacks(attack_map)
    world.turn += 1

    label = DECISIONS.get(decision_key, (decision_key, ""))[0]
    logs.append(TurnRecordOut(
        turn=current_turn,
        blue_action=label,
        red_action="ADVANCE",           # TODO: derive from omnissiah RED orders
        narrative=f"Turn {current_turn} resolved. BLUE: {label}.",
        doctrine_refs=[],               # TODO: wired in by llm_adjudicator
        blue_cp_after=_cp(world, Side.BLUE),
        red_cp_after=_cp(world, Side.RED),
        unit_positions={uid: list(u.position) for uid, u in world.units.items()},
    ))
