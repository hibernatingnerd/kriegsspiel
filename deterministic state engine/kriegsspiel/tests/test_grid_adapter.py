from __future__ import annotations

import numpy as np

from kriegsspiel.engine.enums import TerrainBase, TerrainFeature
from kriegsspiel.engine.grid_adapter import terrain_layers_to_grid


def test_terrain_layers_to_grid_basic_mapping():
    # [forest, urban, road, water]
    terrain = np.array(
        [
            [[0, 0, 0, 0], [1, 0, 0, 0]],
            [[0, 1, 1, 0], [0, 0, 0, 2]],
        ],
        dtype=np.float32,
    )
    altitude = np.array(
        [
            [0.1, 0.2],
            [0.3, 0.4],
        ],
        dtype=np.float32,
    )

    grid = terrain_layers_to_grid(terrain, altitude)
    assert grid.height == 2
    assert grid.width == 2

    assert grid.cell_at((0, 0)).base == TerrainBase.OPEN
    assert grid.cell_at((0, 1)).base == TerrainBase.FOREST
    assert grid.cell_at((1, 0)).base == TerrainBase.URBAN
    assert TerrainFeature.ROAD in grid.cell_at((1, 0)).features
    assert grid.cell_at((1, 1)).base == TerrainBase.WATER
    assert TerrainFeature.WATER_DEEP in grid.cell_at((1, 1)).features
    assert not grid.is_passable_ground((1, 1))
