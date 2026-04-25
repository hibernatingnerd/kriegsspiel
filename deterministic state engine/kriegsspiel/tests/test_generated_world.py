from __future__ import annotations

from kriegsspiel.engine.enums import Side, TerrainBase
from kriegsspiel.scenarios.generated_world import build_world_from_npz


def test_build_world_from_npz_has_units_and_valid_positions():
    world = build_world_from_npz(r"D:\hackathon\kriegsspiel\backend\test_grid.npz")

    assert world.identity.scenario_id == "generated_npz_world"
    assert len(world.alive_units_of_side(Side.BLUE)) == 4
    assert len(world.alive_units_of_side(Side.RED)) == 4

    for unit in world.alive_units():
        cell = world.terrain.cell_at(unit.position)
        assert cell.base not in {TerrainBase.WATER, TerrainBase.IMPASSABLE}
