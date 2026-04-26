"""
Single boundary between api_bridge and the deterministic engine.

Every place api_bridge touches the engine goes through this file. When
the backend team adds new methods (step(), visible_to(), victory_status(),
etc. — see ASK_BACKEND.md) the change lands here only.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

# ── Make the engine importable ────────────────────────────────────────────────
_ENGINE_ROOT = Path(__file__).parent.parent / "deterministic state engine"
if str(_ENGINE_ROOT) not in sys.path:
    sys.path.insert(0, str(_ENGINE_ROOT))

from kriegsspiel.engine.state import WorldState, UnitState           # noqa: E402
from kriegsspiel.engine.enums import Side, Posture, Readiness        # noqa: E402
from kriegsspiel.scenarios.latgale_2027 import build_latgale_world   # noqa: E402

Coord = tuple[int, int]

# ── Scenario registry ─────────────────────────────────────────────────────────
# Add new scenarios here as backend team ships them.
SCENARIOS: dict[str, callable] = {
    "latgale_2027": build_latgale_world,
}

DEFAULT_SCENARIO = "latgale_2027"


def build_world(scenario_id: str, seed: int | None = None) -> WorldState:
    if scenario_id not in SCENARIOS:
        raise ValueError(f"Unknown scenario: {scenario_id}")
    factory = SCENARIOS[scenario_id]
    if seed is not None:
        return factory(seed=seed)
    return factory()


# ── Tick one engine turn given a per-unit decision list ───────────────────────
# The engine currently exposes only attack resolution. MOVE actions are
# accepted in the decision schema but not yet applied — see ASK_BACKEND.md
# item "Movement resolution".
def tick_one_turn(world: WorldState, decisions: list[dict]) -> dict:
    """
    Apply one engine turn. Returns a per-turn delta:
        {
          "applied": [...decisions actually applied...],
          "skipped": [...{unit_id, reason}...],
          "destroyed": [unit_id, ...],
        }
    """
    applied: list[dict] = []
    skipped: list[dict] = []
    pre_alive = {uid for uid, u in world.units.items() if u.is_alive}

    safe_decisions: list[dict] = []
    for d in decisions:
        uid = d.get("unit_id")
        action = d.get("action", "WAIT")
        unit = world.units.get(uid)
        if unit is None:
            skipped.append({"unit_id": uid, "reason": "unknown_unit"})
            continue
        if not unit.is_alive:
            skipped.append({"unit_id": uid, "reason": "destroyed"})
            continue

        if action == "ATTACK":
            target_id = d.get("target_id")
            target = world.units.get(target_id)
            if target is None or not target.is_alive:
                skipped.append({"unit_id": uid, "reason": "invalid_target"})
                continue
            safe_decisions.append({
                "unit_id": uid,
                "action": "ATTACK",
                "target_id": target_id,
                "target_position": None,
            })
            applied.append(d)
        elif action == "MOVE":
            # TODO[ASK_BACKEND]: engine.apply_move(unit, target_position)
            skipped.append({"unit_id": uid, "reason": "move_not_implemented"})
        else:
            applied.append({"unit_id": uid, "action": "WAIT"})

    attack_map = world._build_attack_map(safe_decisions)
    world._resolve_attacks(attack_map)
    world.turn += 1
    world.timestamp_minutes = world.turn * world.minutes_per_turn

    post_alive = {uid for uid, u in world.units.items() if u.is_alive}
    destroyed = sorted(pre_alive - post_alive)

    return {"applied": applied, "skipped": skipped, "destroyed": destroyed}


# ── Visibility ────────────────────────────────────────────────────────────────
# Design choice: god's-eye view. Both sides see everything on the 2D map.
# No fog-of-war for v0.x. If we ever want it, add the filter here.
def units_visible_to(world: WorldState, side: Side) -> list[UnitState]:
    return list(world.units.values())


# ── Victory / outcome ─────────────────────────────────────────────────────────
# TODO[ASK_BACKEND]: replace with engine.victory_status(world) returning
# {"status": "running"|"blue_win"|"red_win"|"draw", "reason": "..."}.
def outcome(world: WorldState, total_turns: int) -> str:
    if world.turn < total_turns:
        return "running"
    blue_held = sum(1 for o in world.objectives.values() if o.held_by == Side.BLUE)
    return "blue_win" if blue_held >= 2 else "red_win"


# ── Helpers used by projection layer ──────────────────────────────────────────
def combat_power(world: WorldState, side: Side) -> float:
    """0–100, mean unit strength × 100, alive units only."""
    alive = [u for u in world.units.values() if u.side == side and u.is_alive]
    if not alive:
        return 0.0
    return round(sum(u.strength for u in alive) / len(alive) * 100, 1)


def serialize_terrain(world: WorldState) -> list[dict]:
    """Sparse non-OPEN cells: [{row, col, terrain}, ...]."""
    out = []
    for r in range(world.terrain.height):
        for c in range(world.terrain.width):
            base = world.terrain.cell_at((r, c)).base.name
            if base != "OPEN":
                out.append({"row": r, "col": c, "terrain": base})
    return out


__all__ = [
    "Side", "Posture", "Readiness", "WorldState", "UnitState",
    "build_world", "tick_one_turn", "units_visible_to", "outcome",
    "combat_power", "serialize_terrain", "SCENARIOS", "DEFAULT_SCENARIO",
]
