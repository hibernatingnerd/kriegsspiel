from __future__ import annotations

"""
Kriegsspiel backend API.

This module currently exposes two adjudication contracts:
1. `/api/adjudicate` keeps the existing thin `UnitSnapshot[]` payload for the
   dashboard scaffold.
2. `/api/adjudicate/world` defines the richer backend-owned contract where the
   deterministic engine's `WorldState` is the source of truth for each turn.
"""

import json
import math
import os
import random
import sys
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

load_dotenv()

ENGINE_ROOT = Path(__file__).resolve().parents[1] / "deterministic state engine"
if str(ENGINE_ROOT) not in sys.path:
    sys.path.insert(0, str(ENGINE_ROOT))

from kriegsspiel.engine.enums import (  # noqa: E402
    EventType,
    Posture,
    Readiness,
    ReasonCode,
    Side,
    TerrainFeature,
)
from kriegsspiel.engine.state import (  # noqa: E402
    WorldState,
    chebyshev_distance,
    validate_world_invariants,
)

try:
    from google import genai  # type: ignore
except ImportError:
    genai = None


def build_llm_client() -> Any | None:
    api_key = os.environ.get("GEMINI_API_KEY")
    if genai is None or not api_key:
        return None
    try:
        return genai.Client(api_key=api_key)
    except Exception:
        return None


llm_client = build_llm_client()

app = FastAPI(title="Kriegsspiel LLM API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class UnitSnapshot(BaseModel):
    unit_id: str
    side: str
    designation: str
    category: str
    position: list[int]
    readiness: str
    strength: float
    supply_days_remaining: Optional[float] = None
    posture: str


class BattleIterationRequest(BaseModel):
    run_id: str
    turn: int
    blue_order_key: str
    blue_order_label: str
    commander_note: str
    units: list[UnitSnapshot]
    scenario_summary: str
    blue_cp: float
    red_cp: float
    max_penetration_km: float


class UnitMove(BaseModel):
    unit_id: str
    from_position: list[int]
    to_position: list[int]
    action: str
    readiness_after: str
    strength_after: float


class BattleIterationResponse(BaseModel):
    turn: int
    narrative: str
    red_response_label: str
    unit_moves: list[UnitMove]
    blue_cp_after: float
    red_cp_after: float
    penetration_km_after: float
    audit_entries: list[dict[str, Any]]
    doctrine_refs: list[str]
    game_over: bool
    outcome: Optional[str] = None


class StateDeltaEvent(BaseModel):
    event_type: str
    reason_code: Optional[str] = None
    unit_id: Optional[str] = None
    from_position: Optional[list[int]] = None
    to_position: Optional[list[int]] = None
    summary: str
    payload: dict[str, Any] = Field(default_factory=dict)


class WorldStateBattleIterationRequest(BaseModel):
    run_id: str
    turn: int
    blue_order_key: str
    blue_order_label: str
    commander_note: str = ""
    scenario_summary: str
    world_state: WorldState


class WorldStateBattleIterationResponse(BaseModel):
    turn: int
    narrative: str
    red_response_label: str
    world_state_before: WorldState
    world_state_after: WorldState
    unit_moves: list[UnitMove]
    events: list[StateDeltaEvent]
    doctrine_refs: list[str]
    game_over: bool
    outcome: Optional[str] = None


ADJUDICATION_SYSTEM = """You are the adjudicator for a Kriegsspiel wargame simulation.
Your job is to:
1. Interpret the BLUE commander's order
2. Generate a realistic RED force response
3. Adjudicate the combat outcome
4. Move units on the grid accordingly
5. Write a clear, concise battle narrative

Always respond with valid JSON only.

The grid uses [row, col] coordinates. Units can move 1-3 cells per turn.
Readiness levels: FULLY_OPERATIONAL > DEGRADED > SUPPRESSED > DESTROYED
Postures: OFFENSIVE, DEFENSIVE, MOVING, SCREENING, RESUPPLYING

Return this exact JSON structure:
{
  "narrative": "...",
  "red_response_label": "...",
  "unit_moves": [
    {
      "unit_id": "...",
      "from_position": [r, c],
      "to_position": [r, c],
      "action": "MOVE|ASSAULT|HOLD|WITHDRAW",
      "readiness_after": "FULLY_OPERATIONAL|DEGRADED|SUPPRESSED|DESTROYED",
      "strength_after": 0.0
    }
  ],
  "blue_cp_after": 0.0,
  "red_cp_after": 0.0,
  "penetration_km_after": 0.0,
  "doctrine_refs": ["..."],
  "game_over": false,
  "outcome": null
}"""


def build_adjudication_prompt(req: BattleIterationRequest) -> str:
    unit_summary = "\n".join(
        f"  [{u.side}] {u.unit_id} ({u.designation}) @ {u.position} "
        f"readiness={u.readiness} strength={u.strength:.2f} posture={u.posture}"
        for u in req.units
        if u.readiness != "DESTROYED"
    )

    return f"""SCENARIO: {req.scenario_summary}

TURN {req.turn} SITUATION:
- BLUE Combat Power: {req.blue_cp:.0f}%
- RED Combat Power:  {req.red_cp:.0f}%
- Max Penetration:   {req.max_penetration_km:.1f} km

CURRENT UNIT POSITIONS:
{unit_summary}

BLUE COMMANDER'S ORDER: {req.blue_order_label}
Commander's Note: "{req.commander_note or 'None'}"

Adjudicate this turn. Move units realistically. Generate the RED response.
Return JSON only."""


def call_llm_adjudicate(req: BattleIterationRequest) -> dict[str, Any]:
    if llm_client is None:
        raise RuntimeError("LLM client not configured")

    prompt = ADJUDICATION_SYSTEM + "\n\n" + build_adjudication_prompt(req)
    response = llm_client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt,
    )

    raw = response.text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw)


def fallback_adjudicate(req: BattleIterationRequest) -> dict[str, Any]:
    moves = []
    for u in req.units:
        if u.readiness == "DESTROYED":
            continue
        dr = random.randint(-1, 1)
        dc = random.randint(-1, 1)
        new_pos = [u.position[0] + dr, u.position[1] + dc]
        moves.append(
            {
                "unit_id": u.unit_id,
                "from_position": u.position,
                "to_position": new_pos,
                "action": "MOVE" if u.side == req.blue_order_key else "HOLD",
                "readiness_after": u.readiness,
                "strength_after": max(0.0, u.strength - random.uniform(0, 0.05)),
            }
        )

    blue_delta = random.uniform(-5, 5)
    red_delta = random.uniform(-8, 3)

    return {
        "narrative": (
            f"Turn {req.turn}: Blue executed {req.blue_order_label}. "
            "Red responded with a probing counterattack. Inconclusive."
        ),
        "red_response_label": "PROBE",
        "unit_moves": moves,
        "blue_cp_after": max(0, min(100, req.blue_cp + blue_delta)),
        "red_cp_after": max(0, min(100, req.red_cp + red_delta)),
        "penetration_km_after": req.max_penetration_km + random.uniform(0, 2),
        "doctrine_refs": ["FM 3-0 §4.2"],
        "game_over": False,
        "outcome": None,
    }


def build_audit_entries(req: BattleIterationRequest, result: dict[str, Any]) -> list[dict[str, Any]]:
    base_h = (req.turn - 1) * 6
    entries = [
        {
            "time": f"T+{base_h:02d}:00",
            "category": "C2",
            "text": f"BLUE order confirmed: {req.blue_order_label}",
        },
        {
            "time": f"T+{base_h:02d}:15",
            "category": "INTEL",
            "text": f"RED response detected: {result['red_response_label']}",
        },
    ]

    for move in result.get("unit_moves", []):
        if move["from_position"] != move["to_position"]:
            entries.append(
                {
                    "time": f"T+{base_h:02d}:30",
                    "category": "MOVEMENT",
                    "text": (
                        f"{move['unit_id']} {move['action']} "
                        f"{move['from_position']} -> {move['to_position']} "
                        f"[{move['readiness_after']} str={move['strength_after']:.2f}]"
                    ),
                }
            )

    entries.append(
        {
            "time": f"T+{base_h + 6:02d}:00",
            "category": "ASSESSMENT",
            "text": (
                f"CP BLUE {result['blue_cp_after']:.0f}% | RED {result['red_cp_after']:.0f}% | "
                f"Penetration {result['penetration_km_after']:.1f} km"
            ),
        }
    )
    return entries


def sign(v: int) -> int:
    if v > 0:
        return 1
    if v < 0:
        return -1
    return 0


def compute_side_cp(world: WorldState, side: Side) -> float:
    units = world.units_of_side(side)
    if not units:
        return 0.0
    total = sum(u.effective_combat_factor for u in units)
    return round(100.0 * total / len(units), 1)


def compute_penetration_km(world: WorldState) -> float:
    red_alive = world.alive_units_of_side(Side.RED)
    if not red_alive:
        return 0.0
    baseline_col = world.terrain.width - 2
    westernmost_red = min(u.position[1] for u in red_alive)
    return round(max(0.0, float(baseline_col - westernmost_red)) * 2.5, 1)


def make_move(
    unit_id: str,
    from_pos: tuple[int, int],
    to_pos: tuple[int, int],
    action: str,
    readiness: Readiness,
    strength: float,
) -> UnitMove:
    return UnitMove(
        unit_id=unit_id,
        from_position=[from_pos[0], from_pos[1]],
        to_position=[to_pos[0], to_pos[1]],
        action=action,
        readiness_after=readiness.value,
        strength_after=round(strength, 3),
    )


def movement_mode_for_side(side: Side, blue_order_key: str) -> str:
    key = blue_order_key.lower()
    if side == Side.BLUE:
        if key == "withdraw":
            return "withdraw"
        if key in {"advance", "escalate"}:
            return "advance"
        if key == "commit_reserve":
            return "reinforce"
        if key == "strike":
            return "probe"
        return "hold"

    if key == "withdraw":
        return "exploit"
    if key in {"advance", "escalate", "strike"}:
        return "counter"
    if key == "commit_reserve":
        return "pressure"
    return "pressure"


def red_response_label(blue_order_key: str) -> str:
    return {
        "hold": "PRESS_FORWARD",
        "reorient_fires": "TACTICAL_PAUSE",
        "commit_reserve": "FLANK_ATTEMPT",
        "withdraw": "EXPLOITATION",
        "advance": "COUNTER_ATTACK",
        "escalate": "EW_INTENSIFICATION",
        "hold_cyber": "INFORMATION_STRIKE",
        "strike": "DISPERSE_EVADE",
    }.get(blue_order_key.lower(), "PRESS_FORWARD")


def nearest_enemy_position(world: WorldState, unit_id: str) -> tuple[int, int] | None:
    unit = world.units[unit_id]
    enemies = world.alive_units_of_side(world.opposing_side(unit.side))
    if not enemies:
        return None
    target = min(enemies, key=lambda enemy: chebyshev_distance(unit.position, enemy.position))
    return target.position


def desired_vector(
    world: WorldState,
    unit_id: str,
    mode: str,
) -> tuple[int, int]:
    unit = world.units[unit_id]
    enemy_pos = nearest_enemy_position(world, unit_id)
    if enemy_pos is None:
        return (0, 0)

    dr_to_enemy = sign(enemy_pos[0] - unit.position[0])
    dc_to_enemy = sign(enemy_pos[1] - unit.position[1])

    if mode in {"advance", "pressure", "exploit", "counter", "probe"}:
        return (dr_to_enemy, dc_to_enemy)
    if mode == "withdraw":
        return (-dr_to_enemy, -dc_to_enemy)
    if mode == "reinforce":
        if unit.side == Side.BLUE:
            blue_objectives = [obj for obj in world.objectives.values() if obj.held_by == Side.BLUE]
            if blue_objectives:
                threatened = min(
                    blue_objectives,
                    key=lambda obj: min(
                        chebyshev_distance(obj.cell, enemy.position)
                        for enemy in world.alive_units_of_side(Side.RED)
                    ),
                )
                return (
                    sign(threatened.cell[0] - unit.position[0]),
                    sign(threatened.cell[1] - unit.position[1]),
                )
        return (dr_to_enemy, dc_to_enemy)
    return (0, 0)


def candidate_cells(world: WorldState, unit_id: str) -> list[tuple[int, int]]:
    unit = world.units[unit_id]
    return [unit.position, *list(world.terrain.neighbors_8(unit.position))]


def can_enter(
    world: WorldState,
    unit_id: str,
    dest: tuple[int, int],
    reserved: set[tuple[int, int]],
) -> tuple[bool, ReasonCode | None]:
    unit = world.units[unit_id]
    if not world.terrain.in_bounds(dest):
        return False, ReasonCode.MOV_NO_PATH
    if dest != unit.position and not world.terrain.is_passable_ground(dest):
        return False, ReasonCode.MOV_TERRAIN_IMPASSABLE
    if dest in reserved:
        return False, ReasonCode.MOV_INSUFFICIENT_ALLOWANCE
    for other in world.alive_units_of_side(unit.side):
        if other.unit_id != unit_id and other.position == dest:
            return False, ReasonCode.MOV_INSUFFICIENT_ALLOWANCE
    for other in world.alive_units_of_side(world.opposing_side(unit.side)):
        if other.position == dest:
            return False, ReasonCode.MOV_BLOCKED_BY_ENEMY
    return True, None


def score_cell(
    world: WorldState,
    unit_id: str,
    dest: tuple[int, int],
    mode: str,
) -> float:
    unit = world.units[unit_id]
    desired_dr, desired_dc = desired_vector(world, unit_id, mode)
    delta_r = sign(dest[0] - unit.position[0])
    delta_c = sign(dest[1] - unit.position[1])
    score = 0.0

    if (delta_r, delta_c) == (desired_dr, desired_dc):
        score += 3.0
    if mode == "hold" and dest == unit.position:
        score += 2.5
    if mode == "withdraw" and dest != unit.position:
        score += 1.5

    cell = world.terrain.cell_at(dest)
    score += cell.strategic_weight
    if TerrainFeature.ROAD in cell.features:
        score += 0.4
    score -= max(0.0, cell.movement_cost_ground - 1.0)

    enemy_dist = min(
        (
            chebyshev_distance(dest, enemy.position)
            for enemy in world.alive_units_of_side(world.opposing_side(unit.side))
        ),
        default=99,
    )
    if mode in {"advance", "pressure", "exploit", "counter", "probe"}:
        score += max(0.0, 4.0 - enemy_dist)
    elif mode == "withdraw":
        score += enemy_dist * 0.5
    else:
        score += min(enemy_dist, 3) * 0.3

    if unit.readiness == Readiness.SUPPRESSED and dest != unit.position:
        score -= 2.0

    return score


def update_readiness(unit) -> Readiness:
    if unit.strength <= 0.0:
        unit.strength = 0.0
        unit.readiness = Readiness.DESTROYED
    elif unit.strength < 0.3:
        unit.readiness = Readiness.SUPPRESSED
    elif unit.strength < 0.6:
        unit.readiness = Readiness.DEGRADED
    else:
        unit.readiness = Readiness.FULLY_OPERATIONAL
    return unit.readiness


def resolve_side_movement(
    world: WorldState,
    side: Side,
    mode: str,
    unit_moves: list[UnitMove],
    events: list[StateDeltaEvent],
) -> None:
    reserved: set[tuple[int, int]] = set()
    units = sorted(world.alive_units_of_side(side), key=lambda u: (u.position[1], u.position[0], u.unit_id))
    if side == Side.RED:
        units = list(reversed(units))

    for unit in units:
        start = unit.position
        best = start
        best_score = -math.inf
        best_reason: ReasonCode | None = None

        for dest in candidate_cells(world, unit.unit_id):
            allowed, reason = can_enter(world, unit.unit_id, dest, reserved)
            if not allowed:
                continue
            score = score_cell(world, unit.unit_id, dest, mode)
            if score > best_score:
                best_score = score
                best = dest
                best_reason = ReasonCode.MOV_OK if dest != start else ReasonCode.SYS_FALLBACK_HOLD

        if best != start:
            unit.position = best
            unit.posture = Posture.MOVING
            reserved.add(best)
            unit_moves.append(make_move(unit.unit_id, start, best, "MOVE", unit.readiness, unit.strength))
            events.append(
                StateDeltaEvent(
                    event_type=EventType.UNIT_MOVED.value,
                    reason_code=(best_reason or ReasonCode.MOV_OK).value,
                    unit_id=unit.unit_id,
                    from_position=[start[0], start[1]],
                    to_position=[best[0], best[1]],
                    summary=f"{unit.unit_id} moved from {start} to {best}.",
                    payload={"side": side.value, "mode": mode},
                )
            )
            crossing = world.terrain.crossing_between(start, best)
            if crossing is not None:
                events.append(
                    StateDeltaEvent(
                        event_type=EventType.CROSSING_USED.value,
                        reason_code=ReasonCode.MOV_OK.value,
                        unit_id=unit.unit_id,
                        from_position=[start[0], start[1]],
                        to_position=[best[0], best[1]],
                        summary=f"{unit.unit_id} used crossing {crossing.crossing_id}.",
                        payload={"crossing_id": crossing.crossing_id},
                    )
                )
        else:
            unit.posture = Posture.DEFENSIVE if mode in {"hold", "withdraw", "reinforce"} else Posture.OFFENSIVE
            events.append(
                StateDeltaEvent(
                    event_type=EventType.UNIT_MOVE_BLOCKED.value,
                    reason_code=(best_reason or ReasonCode.SYS_FALLBACK_HOLD).value,
                    unit_id=unit.unit_id,
                    from_position=[start[0], start[1]],
                    to_position=[start[0], start[1]],
                    summary=f"{unit.unit_id} held position at {start}.",
                    payload={"side": side.value, "mode": mode},
                )
            )


def attack_targets(world: WorldState, side: Side) -> dict[str, str]:
    targets: dict[str, str] = {}
    for unit in world.alive_units_of_side(side):
        adjacent = world.enemies_adjacent_to(unit)
        if not adjacent:
            continue
        target = min(adjacent, key=lambda enemy: (enemy.effective_combat_factor, enemy.unit_id))
        targets[unit.unit_id] = target.unit_id
    return targets


def apply_attrition(unit, world: WorldState) -> None:
    if unit.supply_days_remaining is not None:
        cell = world.terrain.cell_at(unit.position)
        unit.supply_days_remaining = max(0.0, unit.supply_days_remaining - max(0.2, 1.0 / max(cell.supply_throughput, 0.5)))
        if unit.supply_days_remaining <= 0.0:
            unit.turns_isolated += 1
            unit.strength = max(0.0, unit.strength - 0.05)
    update_readiness(unit)


def resolve_combat(
    world: WorldState,
    unit_moves: list[UnitMove],
    events: list[StateDeltaEvent],
) -> None:
    targets = {}
    targets.update(attack_targets(world, Side.BLUE))
    targets.update(attack_targets(world, Side.RED))

    for attacker_id, target_id in targets.items():
        attacker = world.units[attacker_id]
        defender = world.units[target_id]
        if not attacker.is_alive or not defender.is_alive:
            continue
        if chebyshev_distance(attacker.position, defender.position) > 1:
            continue

        defender_before_strength = defender.strength
        defender_before_readiness = defender.readiness
        support = sum(
            0.08
            for ally in world.alive_units_of_side(attacker.side)
            if ally.unit_id != attacker.unit_id and chebyshev_distance(ally.position, defender.position) <= 1
        )
        attack_power = attacker.effective_combat_factor * (1.15 if attacker.posture == Posture.OFFENSIVE else 1.0) + support
        defense_power = defender.effective_combat_factor
        if defender.dug_in:
            defense_power *= 1.2
        defense_power *= 1.0 + world.terrain.cell_at(defender.position).cover_factor
        if attacker.supply_days_remaining is not None and attacker.supply_days_remaining < 0.5:
            attack_power *= 0.8

        damage = max(0.04, min(0.35, 0.18 * attack_power / max(0.2, attack_power + defense_power)))
        defender.strength = max(0.0, defender.strength - damage)
        update_readiness(defender)

        unit_moves.append(
            make_move(
                defender.unit_id,
                defender.position,
                defender.position,
                "ASSAULT",
                defender.readiness,
                defender.strength,
            )
        )
        events.append(
            StateDeltaEvent(
                event_type=EventType.COMBAT_RESOLVED.value,
                reason_code=(
                    ReasonCode.CMB_ATTACKER_WIN.value
                    if defender.strength < defender_before_strength
                    else ReasonCode.CMB_STALEMATE.value
                ),
                unit_id=defender.unit_id,
                from_position=[defender.position[0], defender.position[1]],
                to_position=[defender.position[0], defender.position[1]],
                summary=(
                    f"{attacker.unit_id} engaged {defender.unit_id}; "
                    f"strength {defender_before_strength:.2f}->{defender.strength:.2f}."
                ),
                payload={"attacker_id": attacker.unit_id, "target_id": defender.unit_id},
            )
        )

        if defender.readiness != defender_before_readiness:
            mapped = {
                Readiness.DEGRADED: EventType.UNIT_DEGRADED,
                Readiness.SUPPRESSED: EventType.UNIT_SUPPRESSED,
                Readiness.DESTROYED: EventType.UNIT_DESTROYED,
            }.get(defender.readiness)
            if mapped is not None:
                events.append(
                    StateDeltaEvent(
                        event_type=mapped.value,
                        reason_code=ReasonCode.CMB_ATTACKER_WIN.value,
                        unit_id=defender.unit_id,
                        from_position=[defender.position[0], defender.position[1]],
                        to_position=[defender.position[0], defender.position[1]],
                        summary=f"{defender.unit_id} readiness changed to {defender.readiness.value}.",
                        payload={"attacker_id": attacker.unit_id},
                    )
                )


def update_control_and_objectives(world: WorldState, events: list[StateDeltaEvent]) -> None:
    occupied: dict[tuple[int, int], set[Side]] = {}
    for unit in world.alive_units():
        occupied.setdefault(unit.position, set()).add(unit.side)

    for key, control in world.control.items():
        sides = occupied.get(control.cell, set())
        previous = control.controlled_by
        if len(sides) == 1:
            side = next(iter(sides))
            control.contender = None
            if control.controlled_by == side:
                control.persistence_turns += 1
            else:
                control.controlled_by = side
                control.persistence_turns = 1
        elif len(sides) > 1:
            control.contender = Side.NEUTRAL
            control.persistence_turns = 0

        if control.controlled_by != previous:
            events.append(
                StateDeltaEvent(
                    event_type=EventType.CONTROL_CHANGED.value,
                    reason_code=(
                        ReasonCode.CTL_DOMINANCE_BLUE.value
                        if control.controlled_by == Side.BLUE
                        else ReasonCode.CTL_DOMINANCE_RED.value
                    ),
                    summary=f"Control of {control.cell} changed from {previous.value} to {control.controlled_by.value}.",
                    payload={"cell": [control.cell[0], control.cell[1]]},
                )
            )

    for objective in world.objectives.values():
        sides = occupied.get(objective.cell, set())
        previous = objective.held_by
        if len(sides) == 1:
            holder = next(iter(sides))
            objective.held_by = holder
            if holder != Side.NEUTRAL:
                objective.taken_at_turn = world.turn
        if objective.held_by != previous:
            events.append(
                StateDeltaEvent(
                    event_type=EventType.OBJECTIVE_TAKEN.value,
                    reason_code=(
                        ReasonCode.CTL_DOMINANCE_BLUE.value
                        if objective.held_by == Side.BLUE
                        else ReasonCode.CTL_DOMINANCE_RED.value
                    ),
                    summary=f"Objective {objective.name} taken by {objective.held_by.value}.",
                    payload={"objective_id": objective.objective_id},
                )
            )


def build_world_narrative(
    req: WorldStateBattleIterationRequest,
    world: WorldState,
    events: list[StateDeltaEvent],
) -> str:
    moved = sum(1 for e in events if e.event_type == EventType.UNIT_MOVED.value)
    combats = sum(1 for e in events if e.event_type == EventType.COMBAT_RESOLVED.value)
    blue_cp = compute_side_cp(world, Side.BLUE)
    red_cp = compute_side_cp(world, Side.RED)
    return (
        f"Turn {req.turn}: BLUE executed {req.blue_order_label}. "
        f"Backend resolved {moved} movements and {combats} combat engagements. "
        f"Combat power now BLUE {blue_cp:.1f}% and RED {red_cp:.1f}%."
    )


def determine_outcome(world: WorldState) -> tuple[bool, str | None]:
    blue_alive = len(world.alive_units_of_side(Side.BLUE))
    red_alive = len(world.alive_units_of_side(Side.RED))
    red_major_objectives = sum(1 for obj in world.objectives.values() if obj.held_by == Side.RED and obj.weight >= 2.0)
    penetration = compute_penetration_km(world)

    if blue_alive == 0:
        return True, "red_win"
    if red_alive == 0:
        return True, "blue_win"
    if red_major_objectives >= 2 or penetration >= 20.0:
        return True, "red_win"
    if world.turn >= 10:
        return True, "blue_win" if red_major_objectives == 0 and penetration < 12.5 else "draw"
    return False, None


def advance_world(req: WorldStateBattleIterationRequest) -> WorldStateBattleIterationResponse:
    before = req.world_state.model_copy(deep=True)
    validate_world_invariants(before)

    after = before.model_copy(deep=True)
    after.turn = before.turn + 1
    after.timestamp_minutes = before.timestamp_minutes + before.minutes_per_turn

    unit_moves: list[UnitMove] = []
    events: list[StateDeltaEvent] = [
        StateDeltaEvent(
            event_type=EventType.TURN_ADVANCED.value,
            reason_code=ReasonCode.SYS_TURN_ADVANCED.value,
            summary=f"World turn advanced from {before.turn} to {after.turn}.",
            payload={
                "blue_order_key": req.blue_order_key,
                "blue_order_label": req.blue_order_label,
                "commander_note": req.commander_note,
            },
        )
    ]

    resolve_side_movement(after, Side.BLUE, movement_mode_for_side(Side.BLUE, req.blue_order_key), unit_moves, events)
    resolve_side_movement(after, Side.RED, movement_mode_for_side(Side.RED, req.blue_order_key), unit_moves, events)

    for unit in after.alive_units():
        apply_attrition(unit, after)

    resolve_combat(after, unit_moves, events)
    update_control_and_objectives(after, events)
    validate_world_invariants(after)

    game_over, outcome = determine_outcome(after)

    return WorldStateBattleIterationResponse(
        turn=req.turn,
        narrative=build_world_narrative(req, after, events),
        red_response_label=red_response_label(req.blue_order_key),
        world_state_before=before,
        world_state_after=after,
        unit_moves=unit_moves,
        events=events,
        doctrine_refs=["FM 3-90 §3.4", "JP 3-0 §IV-12"],
        game_over=game_over,
        outcome=outcome,
    )


@app.post("/api/adjudicate", response_model=BattleIterationResponse)
async def adjudicate(req: BattleIterationRequest) -> BattleIterationResponse:
    try:
        result = call_llm_adjudicate(req)
    except Exception as exc:
        print(f"LLM call failed ({exc}), using fallback adjudicator")
        result = fallback_adjudicate(req)

    audit = build_audit_entries(req, result)

    return BattleIterationResponse(
        turn=req.turn,
        narrative=result["narrative"],
        red_response_label=result.get("red_response_label", "RESPOND"),
        unit_moves=[UnitMove(**m) for m in result.get("unit_moves", [])],
        blue_cp_after=result["blue_cp_after"],
        red_cp_after=result["red_cp_after"],
        penetration_km_after=result["penetration_km_after"],
        audit_entries=audit,
        doctrine_refs=result.get("doctrine_refs", []),
        game_over=result.get("game_over", False),
        outcome=result.get("outcome"),
    )


@app.post("/api/adjudicate/world", response_model=WorldStateBattleIterationResponse)
async def adjudicate_world(
    req: WorldStateBattleIterationRequest,
) -> WorldStateBattleIterationResponse:
    return advance_world(req)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
