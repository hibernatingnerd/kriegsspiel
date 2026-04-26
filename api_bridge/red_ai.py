"""
Deterministic stub RED orders.

Backend team will replace this with engine.generate_red_orders(world) once
the LLM/heuristic adjudicator lands (see ASK_BACKEND.md "RED order
generation"). Until then RED auto-attacks the nearest BLUE each turn.
"""

from __future__ import annotations

from .engine_facade import WorldState, Side


def red_orders_for_turn(world: WorldState) -> list[dict]:
    blue_units = [u for u in world.units.values() if u.side == Side.BLUE and u.is_alive]
    red_units  = [u for u in world.units.values() if u.side == Side.RED  and u.is_alive]

    orders: list[dict] = []
    for r in red_units:
        if not blue_units:
            orders.append({"unit_id": r.unit_id, "action": "WAIT"})
            continue
        target = min(
            blue_units,
            key=lambda b: abs(b.position[0] - r.position[0]) + abs(b.position[1] - r.position[1]),
        )
        orders.append({
            "unit_id": r.unit_id,
            "action": "ATTACK",
            "target_id": target.unit_id,
        })
    return orders
