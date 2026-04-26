"""
LLM order generation — WIP / NOT YET INTEGRATED

Claude-backed tactical planning as a drop-in replacement for the
deterministic heuristics in main.py.

Two entry points mirroring the current heuristics:

    llm_blue_orders(world, decision_key) -> list[MissionOrder]
    llm_red_orders(world)               -> list[MissionOrder]

Both return [] on any API failure so the caller can fall back automatically.

Set ANTHROPIC_API_KEY in the environment to enable; without it the module
is a silent no-op.

Architecture
────────────
  WorldState
    ↓ _board_summary()        compact text snapshot (units, objectives, turn)
    ↓ _doctrine_context()     passages from libs/*.json
    ↓ Claude API              claude-opus-4-7, JSON output
    ↓ _parse_orders()         JSON -> list[MissionOrder]
  → advance_timestep()

Integration plan (main.py)
──────────────────────────
  from backend.llm_orders import llm_blue_orders, llm_red_orders

  def _blue_orders(world, decision_key):
      orders = llm_blue_orders(world, decision_key)
      if orders:
          return orders
      # ... existing deterministic fallback ...

  def _red_orders(world):
      orders = llm_red_orders(world)
      if orders:
          return orders
      # ... existing deterministic fallback ...

TODO
────
  - Wire in VectorDB (Actian :50051) for turn-history retrieval
  - Add few-shot examples to system prompt
  - Tune doctrine passage selection (semantic search vs. static inclusion)
  - Validate parsed orders against live unit roster before returning
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

from kriegsspiel.engine.enums import Side
from kriegsspiel.engine.orders import MissionOrder, MissionType
from kriegsspiel.engine.state import WorldState

# ── Doctrine corpus ────────────────────────────────────────────────────────

_LIBS = Path(__file__).parent.parent / "libs"

def _load_doctrine() -> dict:
    corpus: dict = {}
    for fname in ("wargame_unit_library_v3.json", "ipb_terrain_schema.json", "modifiers.json"):
        p = _LIBS / fname
        if not p.exists():
            continue
        try:
            corpus[fname] = json.loads(p.read_text())
        except json.JSONDecodeError:
            # Some files use JS-style comments; skip rather than crash
            pass
    return corpus

_DOCTRINE = _load_doctrine()


# ── Board summary ──────────────────────────────────────────────────────────

def _board_summary(world: WorldState, pov_side: Side) -> str:
    """Compact natural-language snapshot fed to the LLM each turn."""
    lines: list[str] = [f"Turn {world.turn}. Grid 16×16, 5 km/cell."]

    friendly = world.alive_units_of_side(pov_side)
    enemy_side = world.opposing_side(pov_side)
    enemy = world.alive_units_of_side(enemy_side)

    def unit_line(u) -> str:
        return (f"  {u.unit_id} pos=({u.position[0]},{u.position[1]}) "
                f"str={u.strength:.0%} posture={u.posture.value}")

    lines.append(f"\n{pov_side.value} FORCES (friendly):")
    lines.extend(unit_line(u) for u in friendly)
    lines.append(f"\n{enemy_side.value} FORCES (enemy):")
    lines.extend(unit_line(u) for u in enemy)

    lines.append("\nOBJECTIVES:")
    for obj in world.objectives.values():
        lines.append(f"  {obj.name} ({obj.objective_id}) "
                     f"cell=({obj.cell[0]},{obj.cell[1]}) "
                     f"held_by={obj.held_by.value} weight={obj.weight}")

    return "\n".join(lines)


def _doctrine_context() -> str:
    """Distil a concise doctrine passage from the loaded corpus."""
    snippets: list[str] = []

    lib = _DOCTRINE.get("wargame_unit_library_v3.json", {})
    units = lib.get("units", [])[:3] if isinstance(lib, dict) else []
    if units:
        snippets.append("UNIT CAPABILITIES (excerpt):\n" +
                        "\n".join(f"  {u.get('id','?')}: {u.get('description','')}" for u in units))

    terrain = _DOCTRINE.get("ipb_terrain_schema.json", {})
    if terrain:
        tips = terrain.get("doctrinal_notes", terrain.get("guidance", ""))
        if tips:
            snippets.append(f"TERRAIN DOCTRINE:\n  {str(tips)[:400]}")

    mods = _DOCTRINE.get("modifiers.json", {})
    if isinstance(mods, dict):
        key_mods = list(mods.items())[:5]
        if key_mods:
            snippets.append("MODIFIERS:\n" +
                            "\n".join(f"  {k}: {v}" for k, v in key_mods))

    return "\n\n".join(snippets) or "(no doctrine loaded)"


# ── Output schema ──────────────────────────────────────────────────────────

_ORDER_SCHEMA = """
Respond with ONLY a JSON object — no prose, no markdown fences:
{"orders": [<order>, ...]}

Each <order>:
{
  "order_id":    string,   // unique label, e.g. "B-HOLD-MNV"
  "group_id":    string,   // e.g. "BLUE-MNV"
  "mission":     "HOLD" | "ADVANCE" | "ASSAULT" | "SUPPRESS" | "WITHDRAW" | "RECON",
  "unit_ids":    [string, ...],  // must be unit_ids visible in the board summary
  "priority":    1-5,            // higher executes first
  "target_coord": [row, col] | null   // optional explicit target cell
}

Hard rules:
- Only order units listed under your side (friendly).
- FRS and ENB units cannot ASSAULT; use SUPPRESS or HOLD.
- One order per unit maximum; a unit in two orders is invalid.
- Prefer HOLD when unit strength < 0.30.
"""


# ── Claude API call ────────────────────────────────────────────────────────

def _call_claude(system: str, user: str) -> Optional[str]:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        msg = client.messages.create(
            model="claude-opus-4-7",
            max_tokens=1024,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return msg.content[0].text
    except Exception as exc:
        print(f"[llm_orders] Claude call failed: {exc}")
        return None


# ── Order parsing ──────────────────────────────────────────────────────────

_MISSION_MAP: dict[str, MissionType] = {m.value: m for m in MissionType}

def _parse_orders(raw: str, side: Side) -> list[MissionOrder]:
    try:
        text = raw.strip()
        # Strip markdown code fences if present
        if "```" in text:
            parts = text.split("```")
            text = parts[1] if len(parts) > 1 else text
            if text.startswith("json"):
                text = text[4:]
        data = json.loads(text.strip())
        orders: list[MissionOrder] = []
        seen_units: set[str] = set()
        for o in data.get("orders", []):
            mission = _MISSION_MAP.get(o.get("mission", ""))
            if mission is None:
                continue
            unit_ids = [uid for uid in o.get("unit_ids", []) if uid not in seen_units]
            if not unit_ids:
                continue
            seen_units.update(unit_ids)
            tc = o.get("target_coord")
            orders.append(MissionOrder(
                order_id=o.get("order_id", f"{side.value}-LLM-{len(orders)}"),
                side=side,
                group_id=o.get("group_id", f"{side.value}-LLM-GRP"),
                unit_ids=tuple(unit_ids),
                mission=mission,
                priority=max(1, min(5, int(o.get("priority", 1)))),
                target_coord=tuple(tc) if tc and len(tc) == 2 else None,
            ))
        return orders
    except Exception as exc:
        print(f"[llm_orders] Parse error: {exc}\nRaw snippet:\n{raw[:300]}")
        return []


# ── Public API ─────────────────────────────────────────────────────────────

def llm_blue_orders(world: WorldState, decision_key: str) -> list[MissionOrder]:
    """
    Generate BLUE orders from Claude given the human commander's intent.
    Returns [] when API unavailable; caller uses deterministic fallback.
    """
    system = "\n\n".join([
        "You are the BLUE tactical AI for a deterministic hex wargame.",
        "Translate the commander's intent into valid MissionOrders.",
        _ORDER_SCHEMA,
        "DOCTRINE:\n" + _doctrine_context(),
    ])
    user = "\n\n".join([
        _board_summary(world, Side.BLUE),
        f"Commander's intent: {decision_key.upper()}",
        "Issue BLUE orders that best execute this intent.",
    ])
    raw = _call_claude(system, user)
    return _parse_orders(raw, Side.BLUE) if raw else []


def llm_red_orders(world: WorldState) -> list[MissionOrder]:
    """
    Generate RED adversary orders from Claude (pure AI, no human intent).
    Returns [] when API unavailable; caller uses deterministic fallback.
    """
    system = "\n\n".join([
        "You are the RED tactical AI for a deterministic hex wargame.",
        "Objective: break through BLUE defences, capture Daugavpils, "
        "push westward (toward column 0) to maximise penetration.",
        _ORDER_SCHEMA,
        "DOCTRINE:\n" + _doctrine_context(),
    ])
    user = "\n\n".join([
        _board_summary(world, Side.RED),
        "Issue RED orders for this turn.",
    ])
    raw = _call_claude(system, user)
    return _parse_orders(raw, Side.RED) if raw else []
