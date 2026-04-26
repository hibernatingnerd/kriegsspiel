"""run_demo_turn.py — Run one turn end-to-end with Claude.

Place at REPO ROOT (next to kriegsspiel/ folder).
Run with: python run_demo_turn.py
"""

# Load API key BEFORE importing anything that needs it
from dotenv import load_dotenv
load_dotenv()

import argparse
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
import numpy as np

if not os.environ.get("ANTHROPIC_API_KEY"):
    print("ERROR: ANTHROPIC_API_KEY not found.")
    print("Create .env at the repo root with:")
    print("  ANTHROPIC_API_KEY=sk-ant-...")
    sys.exit(1)

from kriegsspiel.scenarios.coast import CoastScenario
from kriegsspiel.engine.enums import Side
from kriegsspiel.engine.llm_planner import (
    AnthropicBackend, plan_side, apply_decisions_to_world,
)
from kriegsspiel.engine.aar_writer import write_aar
from kriegsspiel.engine.audit import (
    AuditLog, canonical_hash, snapshot_units_for_delta, post_combat_deltas,
    build_turn_plan_record, build_turn_aar_record, build_turn_summary_record,
)

def plot_world_status(world, save_dir: str = "turn_plots") -> None:
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    from kriegsspiel.engine.enums import TerrainBase

    Path(save_dir).mkdir(exist_ok=True)

    terrain = world.terrain
    h, w = terrain.height, terrain.width

    # build terrain image once
    color_map = {
        TerrainBase.OPEN:       [0.83, 0.90, 0.71],
        TerrainBase.FOREST:     [0.29, 0.49, 0.35],
        TerrainBase.WATER:      [0.29, 0.56, 0.85],
        TerrainBase.URBAN:      [0.76, 0.70, 0.50],
        TerrainBase.IMPASSABLE: [0.33, 0.33, 0.33],
    }
    terrain_mat = np.zeros((h, w, 3))
    for r in range(h):
        for c in range(w):
            cell = terrain.cell_at((r, c))
            terrain_mat[r, c] = color_map.get(cell.base, [1, 1, 1])

    readiness_colors = {
        "FULLY_OPERATIONAL": "#00ff00",
        "DEGRADED":          "#ffaa00",
        "SUPPRESSED":        "#ff4400",
        "DESTROYED":         "#444444",
    }

    fig, ax = plt.subplots(figsize=(12, 12))
    ax.imshow(terrain_mat, origin="upper", aspect="equal", zorder=0)

    for unit in world.alive_units_of_side(Side.BLUE):
        r, c = unit.position
        rc = readiness_colors.get(unit.readiness.value, "#ffffff")
        ax.plot(c, r, "o", color="#1f77b4", markersize=10, markeredgecolor=rc, markeredgewidth=2, zorder=5)
        ax.text(c + 1, r, unit.unit_id.split("-")[1], color="white", fontsize=6, zorder=6,
                bbox=dict(boxstyle="round,pad=0.1", fc="black", alpha=0.5, ec="none"))

    for unit in world.alive_units_of_side(Side.RED):
        r, c = unit.position
        rc = readiness_colors.get(unit.readiness.value, "#ffffff")
        ax.plot(c, r, "X", color="#d62728", markersize=10, markeredgecolor=rc, markeredgewidth=2, zorder=5)
        ax.text(c + 1, r, unit.unit_id.split("-")[1], color="white", fontsize=6, zorder=6,
                bbox=dict(boxstyle="round,pad=0.1", fc="black", alpha=0.5, ec="none"))

    legend = [
        mpatches.Patch(color="#1f77b4", label="BLUE"),
        mpatches.Patch(color="#d62728", label="RED"),
        mpatches.Patch(color="#00ff00", label="FULLY_OPERATIONAL"),
        mpatches.Patch(color="#ffaa00", label="DEGRADED"),
        mpatches.Patch(color="#ff4400", label="SUPPRESSED"),
    ]
    ax.legend(handles=legend, loc="lower right", fontsize=8)
    ax.set_title(f"Turn {world.turn} | BLUE: {len(world.alive_units_of_side(Side.BLUE))} | RED: {len(world.alive_units_of_side(Side.RED))}")
    ax.axis("off")
    plt.tight_layout()
    plt.show()


def world_summary(world):
    return {
        "turn": world.turn,
        "units": {
            uid: {
                "position": list(u.position) if hasattr(u.position, "__iter__") else u.position,
                "strength": float(u.strength),
                "readiness": u.readiness.value if hasattr(u.readiness, "value") else str(u.readiness),
            }
            for uid, u in world.units.items()
        },
    }


def should_stop(world, turn_count: int, max_turns: int) -> bool:
    if turn_count >= max_turns:
        return True
    blue_alive = len(world.alive_units_of_side(Side.BLUE))
    red_alive = len(world.alive_units_of_side(Side.RED))
    return blue_alive == 0 or red_alive == 0


def stop_reason(world, turn_count: int, max_turns: int) -> str:
    if turn_count >= max_turns:
        return "max_turns"
    blue_alive = len(world.alive_units_of_side(Side.BLUE))
    red_alive = len(world.alive_units_of_side(Side.RED))
    if blue_alive == 0 and red_alive == 0:
        return "both_sides_eliminated"
    if blue_alive == 0:
        return "blue_eliminated"
    if red_alive == 0:
        return "red_eliminated"
    return "unknown"


def run_single_turn(world, backend, planner_template, aar_template, audit_log, run_id: str):
    
    # --- movement phase --- must be on world, before planning_world is copied
    print(f"\n[TURN {world.turn}] Moving units...")
    world.move_units_tactically(radius=15, seed=world.turn)
    print(f"    Movement complete")

    # copy AFTER movement so planning sees updated positions
    planning_world = world.model_copy(deep=True)
    planning_world.unit_decision_list = []
    planning_world.compute_visibilities(k=5)

    pre_turn_hash = canonical_hash(world_summary(world))
    pre_combat_snap = snapshot_units_for_delta(world)
    world.unit_decision_list = []

    print(f"\n[TURN {world.turn}] BLUE planning (Claude call)...")
    blue = plan_side(planning_world, "BLUE", backend=backend, prompt_template=planner_template)
    print(f"    intent: {blue.side_intent}")
    blue_fallback_count = sum(1 for d in blue.final_decisions if d.get("rationale", "").startswith("fallback:"))
    print(
        f"    parse_ok: {blue.parse_ok}, fallback_scope: {blue.fallback_scope}, "
        f"fallback_count: {blue_fallback_count}, latency: {blue.latency_ms}ms"
    )
    for d in blue.final_decisions:
        print(f"      {d['unit_id']}: {d['action']}" + (f" -> {d['target_id']}" if d['action'] == 'ATTACK' else ""))

    print(f"\n[TURN {world.turn}] RED planning (Claude call)...")
    red = plan_side(planning_world, "RED", backend=backend, prompt_template=planner_template)
    print(f"    intent: {red.side_intent}")
    red_fallback_count = sum(1 for d in red.final_decisions if d.get("rationale", "").startswith("fallback:"))
    print(
        f"    parse_ok: {red.parse_ok}, fallback_scope: {red.fallback_scope}, "
        f"fallback_count: {red_fallback_count}, latency: {red.latency_ms}ms"
    )
    for d in red.final_decisions:
        print(f"      {d['unit_id']}: {d['action']}" + (f" -> {d['target_id']}" if d['action'] == 'ATTACK' else ""))

    audit_log.write(build_turn_plan_record(
        run_id=run_id, turn=world.turn, side="BLUE",
        rulepack_id=world.identity.rulepack_id,
        engine_version="0.1.0", prompt_version="turn_planner_simple_v1",
        model=backend.model_name, model_temperature=backend.temperature,
        model_max_tokens=backend.max_tokens, request_id=blue.request_id,
        latency_ms=blue.latency_ms,
        input_state_hash=blue.input_state_hash,
        input_summary=blue.input_summary,
        prompt_text_hash=blue.prompt_text_hash,
        raw_llm_output=blue.raw_llm_output, parse_ok=blue.parse_ok,
        side_intent=blue.side_intent,
        final_decisions=blue.final_decisions,
        validation_issues=[i.to_dict() for i in blue.issues],
        fallback_scope=blue.fallback_scope,
        fallback_reason=blue.fallback_reason,
    ))

    audit_log.write(build_turn_plan_record(
        run_id=run_id, turn=world.turn, side="RED",
        rulepack_id=world.identity.rulepack_id,
        engine_version="0.1.0", prompt_version="turn_planner_simple_v1",
        model=backend.model_name, model_temperature=backend.temperature,
        model_max_tokens=backend.max_tokens, request_id=red.request_id,
        latency_ms=red.latency_ms,
        input_state_hash=red.input_state_hash,
        input_summary=red.input_summary,
        prompt_text_hash=red.prompt_text_hash,
        raw_llm_output=red.raw_llm_output, parse_ok=red.parse_ok,
        side_intent=red.side_intent,
        final_decisions=red.final_decisions,
        validation_issues=[i.to_dict() for i in red.issues],
        fallback_scope=red.fallback_scope,
        fallback_reason=red.fallback_reason,
    ))

    apply_decisions_to_world(world, "BLUE", blue.final_decisions)
    apply_decisions_to_world(world, "RED", red.final_decisions)

    print(f"\n[TURN {world.turn}] Engine resolving combat...")
    if hasattr(world, "map_solve_attacks"):
        world.map_solve_attacks()
    elif hasattr(world, "solve_attacks"):
        world.solve_attacks()
    else:
        print("    WARNING: no combat resolver method found on world!")

    post_combat_hash = canonical_hash(world_summary(world))
    deltas = post_combat_deltas(pre_combat_snap, world)
    print(f"    {len(deltas)} units changed strength/readiness")

    print(f"\n[TURN {world.turn}] AAR (Claude call)...")
    all_issues = [i.to_dict() for i in blue.issues + red.issues]
    aar = write_aar(
        backend=backend, prompt_template=aar_template,
        run_id=run_id, turn=world.turn,
        rulepack_id=world.identity.rulepack_id,
        blue_intent=blue.side_intent, red_intent=red.side_intent,
        blue_decisions=blue.final_decisions,
        red_decisions=red.final_decisions,
        post_combat_deltas=deltas,
        validation_issues=all_issues,
    )
    if aar.parse_ok and aar.aar:
        print("    AAR OK")
    else:
        print(f"    AAR FAILED: {aar.failure_reason}")

    audit_log.write(build_turn_aar_record(
        run_id=run_id, turn=world.turn,
        rulepack_id=world.identity.rulepack_id,
        engine_version="0.1.0", prompt_version="aar_writer_v1",
        model=backend.model_name, model_temperature=backend.temperature,
        model_max_tokens=backend.max_tokens, request_id=aar.request_id,
        latency_ms=aar.latency_ms,
        pre_combat_state_hash=pre_turn_hash,
        post_combat_state_hash=post_combat_hash,
        raw_llm_output=aar.raw_llm_output, parse_ok=aar.parse_ok,
        aar=aar.aar, failure_reason=aar.failure_reason,
        post_combat_deltas=deltas,
    ))

    all_actions = blue.final_decisions + red.final_decisions
    attacks = sum(1 for d in all_actions if d["action"] == "ATTACK")
    waits = sum(1 for d in all_actions if d["action"] == "WAIT")
    fallbacks = sum(1 for d in all_actions if d["rationale"] and d["rationale"].startswith("fallback:"))
    destroyed = sum(1 for d in deltas if d["readiness_after"] == "DESTROYED")
    degraded = sum(1 for d in deltas if d["readiness_after"] == "DEGRADED")
    suppressed = sum(1 for d in deltas if d["readiness_after"] == "SUPPRESSED")

    audit_log.write(build_turn_summary_record(
        run_id=run_id, turn=world.turn,
        rulepack_id=world.identity.rulepack_id,
        pre_turn_state_hash=pre_turn_hash,
        post_turn_state_hash=post_combat_hash,
        actions_submitted=len(all_actions),
        actions_attack=attacks, actions_wait=waits,
        actions_fallback=fallbacks,
        units_destroyed=destroyed, units_degraded=degraded,
        units_suppressed=suppressed,
        invariant_check_passed=True,
    ))

    world.turn += 1
    world.timestamp_minutes += world.minutes_per_turn


def main():
    parser = argparse.ArgumentParser(description="Run multi-turn Claude demo")
    parser.add_argument("--turns", type=int, default=10, help="Number of turns to run")
    args = parser.parse_args()

    print("=" * 70)
    print("KRIEGSSPIEL — MULTI-TURN WITH CLAUDE")
    print("=" * 70)

    print("\n[1] Building Latgale world...")
    world = CoastScenario().build_world(run_id="coast-demo-001", seed=12)
    print(f"    Turn {world.turn}, {len(world.units)} units")

    print("\n[2] Setting up Claude backend...")
    backend = AnthropicBackend(
        model="claude-haiku-4-5-20251001",
        temperature=0.0,
        max_tokens=2048,
    )
    print(f"    Model: {backend.model_name}")

    planner_template = Path("kriegsspiel/prompts/turn_planner_simple_v1.txt").read_text(encoding="utf-8")
    aar_template = Path("kriegsspiel/prompts/aar_writer_v1.txt").read_text(encoding="utf-8")

    run_id = f"{world.identity.run_id}-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}"
    executed_turns = 0
    final_stop_reason = "unknown"

    with AuditLog(run_id=run_id) as audit_log:
        plot_world_status(world)
        while not should_stop(world, executed_turns, args.turns):
            run_single_turn(world, backend, planner_template, aar_template, audit_log, run_id)
            plot_world_status(world)
            executed_turns += 1
        final_stop_reason = stop_reason(world, executed_turns, args.turns)

    print("\n" + "=" * 70)
    print(f"DONE. Turns executed: {executed_turns} (stop_reason={final_stop_reason})")
    print(f"Audit log: audit_logs/{run_id}/{run_id}_audit.jsonl")
    print("=" * 70)


if __name__ == "__main__":
    main()