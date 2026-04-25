"""Adapter from generated terrain layers to deterministic TerrainGrid."""

from __future__ import annotations

from pathlib import Path
from typing import Tuple

import numpy as np

from .enums import TerrainBase, TerrainFeature
from .state import TerrainCell, TerrainGrid


def _normalize_altitude(altitude: np.ndarray) -> np.ndarray:
    """Return altitude normalized to [0, 1]."""
    mn = float(altitude.min())
    mx = float(altitude.max())
    if mx - mn <= 1e-9:
        return np.zeros_like(altitude, dtype=np.float32)
    return ((altitude - mn) / (mx - mn)).astype(np.float32)


def _cell_from_layers(
    forest: float,
    urban: float,
    road: float,
    water: float,
    alt_norm: float,
) -> TerrainCell:
    """Map one generated-layer pixel to a TerrainCell."""
    features: list[TerrainFeature] = []

    if water > 0:
        # In the source generator: 1=shallow, 2=deep.
        base = TerrainBase.WATER
        if water >= 2:
            features.append(TerrainFeature.WATER_DEEP)
        movement = 999.0
        cover = 0.0
        visibility = 0.95 if water == 1 else 1.0
        supply = 0.0
    elif urban > 0:
        base = TerrainBase.URBAN
        features.append(TerrainFeature.URBAN_DENSE)
        movement = 2.0
        cover = 0.7
        visibility = 0.55
        supply = 1.2
    elif forest > 0:
        base = TerrainBase.FOREST
        movement = 1.6
        cover = 0.6
        visibility = 0.4
        supply = 0.7
    elif alt_norm >= 0.72:
        base = TerrainBase.MOUNTAIN
        movement = 2.8
        cover = 0.35
        visibility = 0.8
        supply = 0.45
    else:
        base = TerrainBase.OPEN
        movement = 1.0
        cover = 0.1
        visibility = 1.0
        supply = 1.0

    if road > 0 and water == 0:
        features.append(TerrainFeature.ROAD)
        movement = max(0.7, movement * 0.7)
        supply = min(2.0, supply + 0.3)

    return TerrainCell(
        base=base,
        features=tuple(features),
        altitude_m=float(alt_norm * 1200.0),
        slope_deg=float(min(45.0, max(0.0, alt_norm * 35.0))),
        cover_factor=float(min(1.0, max(0.0, cover))),
        visibility_factor=float(min(1.0, max(0.0, visibility))),
        movement_cost_ground=float(movement),
        supply_throughput=float(min(10.0, max(0.0, supply))),
        strategic_weight=0.0,
    )


def terrain_layers_to_grid(terrain: np.ndarray, altitude: np.ndarray) -> TerrainGrid:
    """Convert generator output into deterministic TerrainGrid.

    Expected terrain layout:
      - terrain[:, :, 0] = forest mask/intensity
      - terrain[:, :, 1] = urban mask/labels
      - terrain[:, :, 2] = road mask
      - terrain[:, :, 3] = water depth classes (0, 1, 2)
    """
    if terrain.ndim != 3 or terrain.shape[2] != 4:
        raise ValueError(
            f"terrain must have shape (H, W, 4), got {terrain.shape}"
        )
    if altitude.ndim != 2:
        raise ValueError(f"altitude must have shape (H, W), got {altitude.shape}")
    if terrain.shape[:2] != altitude.shape:
        raise ValueError(
            f"terrain spatial shape {terrain.shape[:2]} does not match altitude "
            f"shape {altitude.shape}"
        )

    h, w = altitude.shape
    alt_norm = _normalize_altitude(altitude)

    cells: list[list[TerrainCell]] = []
    for r in range(h):
        row: list[TerrainCell] = []
        for c in range(w):
            row.append(
                _cell_from_layers(
                    forest=float(terrain[r, c, 0]),
                    urban=float(terrain[r, c, 1]),
                    road=float(terrain[r, c, 2]),
                    water=float(terrain[r, c, 3]),
                    alt_norm=float(alt_norm[r, c]),
                )
            )
        cells.append(row)

    return TerrainGrid(height=h, width=w, cells=cells, crossings=[])


def load_npz_to_terrain_grid(npz_path: str | Path) -> TerrainGrid:
    """Load backend .npz output and convert to TerrainGrid."""
    p = Path(npz_path)
    data = np.load(p)
    if "terrain" not in data.files or "altitude" not in data.files:
        raise ValueError(
            f"{p} missing required arrays 'terrain' and 'altitude'; found {data.files}"
        )
    return terrain_layers_to_grid(data["terrain"], data["altitude"])


def summarize_grid(grid: TerrainGrid) -> dict[str, int]:
    """Return simple counts useful for demo verification."""
    counts = {
        "OPEN": 0,
        "FOREST": 0,
        "URBAN": 0,
        "WATER": 0,
        "MOUNTAIN": 0,
        "SWAMP": 0,
        "IMPASSABLE": 0,
        "ROAD_FEATURE_CELLS": 0,
        "WATER_DEEP_CELLS": 0,
    }
    for row in grid.cells:
        for cell in row:
            counts[cell.base.value] += 1
            if TerrainFeature.ROAD in cell.features:
                counts["ROAD_FEATURE_CELLS"] += 1
            if TerrainFeature.WATER_DEEP in cell.features:
                counts["WATER_DEEP_CELLS"] += 1
    return counts
