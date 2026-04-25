"""Build deterministic WorldState instances from generated NPZ terrain."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from kriegsspiel.engine.enums import Affiliation, Posture, Readiness, Side, TerrainBase
from kriegsspiel.engine.grid_adapter import load_npz_to_terrain_grid
from kriegsspiel.engine.state import RunIdentity, UnitState, WorldState, validate_world_invariants


def _deterministic_side_positions(world: WorldState, side: Side, count: int) -> list[tuple[int, int]]:
    """Pick deterministic passable positions for one side."""
    mid = world.terrain.width // 2
    candidates: list[tuple[int, int]] = []
    for r in range(world.terrain.height):
        for c in range(world.terrain.width):
            if side == Side.BLUE and c >= mid:
                continue
            if side == Side.RED and c < mid:
                continue
            cell = world.terrain.cell_at((r, c))
            if cell.base in {TerrainBase.WATER, TerrainBase.IMPASSABLE}:
                continue
            candidates.append((r, c))

    if not candidates:
        raise ValueError(f"No passable candidate cells found for side {side.value}")

    n = min(count, len(candidates))
    idxs = np.linspace(0, len(candidates) - 1, num=n, dtype=int)
    return [candidates[i] for i in idxs]


def build_world_from_npz(
    npz_path: str | Path,
    *,
    run_id: str = "generated-grid-001",
    seed: int = 1729,
    blue_count: int = 4,
    red_count: int = 4,
) -> WorldState:
    """Create deterministic world from NPZ terrain + deterministic unit placement."""
    terrain = load_npz_to_terrain_grid(npz_path)

    world = WorldState(
        identity=RunIdentity(
            run_id=run_id,
            scenario_id="generated_npz_world",
            rulepack_id="krg_v0_1",
            engine_version="0.1.0",
            seed=seed,
            noise_enabled=False,
        ),
        turn=0,
        minutes_per_turn=60,
        timestamp_minutes=0,
        terrain=terrain,
        units={},
        control={},
        objectives={},
        side_posture={Side.BLUE: "STANDARD", Side.RED: "STANDARD"},
    )

    units: dict[str, UnitState] = {}
    blue_positions = _deterministic_side_positions(world, Side.BLUE, blue_count)
    red_positions = _deterministic_side_positions(world, Side.RED, red_count)

    for i, pos in enumerate(blue_positions, start=1):
        unit_id = f"BLUE-GEN-{i:03d}"
        units[unit_id] = UnitState(
            unit_id=unit_id,
            template_id="GEN-MNV",
            side=Side.BLUE,
            affiliation=Affiliation.BLUE,
            position=pos,
            strength=1.0,
            readiness=Readiness.FULLY_OPERATIONAL,
            supply_days_remaining=2.0,
            posture=Posture.DEFENSIVE,
            dug_in=False,
            notes="Generated from NPZ terrain",
        )

    for i, pos in enumerate(red_positions, start=1):
        unit_id = f"RED-GEN-{i:03d}"
        units[unit_id] = UnitState(
            unit_id=unit_id,
            template_id="GEN-MNV",
            side=Side.RED,
            affiliation=Affiliation.RED_RU,
            position=pos,
            strength=1.0,
            readiness=Readiness.FULLY_OPERATIONAL,
            supply_days_remaining=2.0,
            posture=Posture.OFFENSIVE,
            dug_in=False,
            notes="Generated from NPZ terrain",
        )

    world.units = units
    validate_world_invariants(world)
    return world
