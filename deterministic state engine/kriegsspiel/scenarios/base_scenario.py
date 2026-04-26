from __future__ import annotations
from abc import ABC, abstractmethod
from kriegsspiel.engine.state import (
    ControlState, Objective, RunIdentity, TerrainGrid,
    UnitState, WorldState, validate_world_invariants,
)
from kriegsspiel.engine.enums import TerrainBase, TerrainFeature
from kriegsspiel.engine.state import TerrainCell
from kriegsspiel.engine.enums import Side
import numpy as np
from pathlib import Path

# kriegsspiel/scenarios/template_loader.py

import json
import re
from pathlib import Path
from kriegsspiel.engine.state import UnitTemplate

_LIBRARY_PATH = (
    Path(__file__).parent.parent.parent.parent
    / "backend"
    / "wargame_unit_library_v3.json"
)


TERRAIN_MAP: dict[int, TerrainCell] = {
    0: TerrainCell(base=TerrainBase.OPEN),
    1: TerrainCell(base=TerrainBase.FOREST, movement_cost_ground=1.6, cover_factor=0.6, visibility_factor=0.4, supply_throughput=0.7),
    2: TerrainCell(base=TerrainBase.URBAN, features=(TerrainFeature.URBAN_DENSE, TerrainFeature.ROAD), movement_cost_ground=2.0, cover_factor=0.7, visibility_factor=0.5, supply_throughput=1.2),
    3: TerrainCell(base=TerrainBase.WATER, movement_cost_ground=999.0, supply_throughput=0.0, visibility_factor=1.0),
    4: TerrainCell(base=TerrainBase.WATER, features=(TerrainFeature.WATER_DEEP,), movement_cost_ground=999.0, supply_throughput=0.0, visibility_factor=1.0),
}

class BaseScenario(ABC):

    scenario_id: str
    rulepack_id: str = "krg_v0_1"
    engine_version: str = "0.1.0"
    minutes_per_turn: int = 60

    def build_terrain(self) -> TerrainGrid:
        map_path = (
            Path(__file__).parent.parent.parent.parent
            / "backend"
            / f"{self.scenario_id}.npz"
        )
        base_mat = np.load(map_path)["terrain"]
        h, w = base_mat.shape[:2]
        terrain_2d = np.zeros((h, w), dtype=np.int32)  # default: OPEN = 0

        for r in range(h):
            for c in range(w):
                if base_mat[r, c, 3] == 2.0:
                    terrain_2d[r, c] = 4  # deep water
                elif base_mat[r, c, 3] == 1.0:
                    terrain_2d[r, c] = 3  # shallow water
                elif base_mat[r, c, 1] > 0:
                    terrain_2d[r, c] = 2  # urban
                elif base_mat[r, c, 0] > 0:
                    terrain_2d[r, c] = 1  # forest
                # roads and open both stay 0 for now

        grid = [[TERRAIN_MAP[terrain_2d[r, c]] for c in range(w)] for r in range(h)]
        return TerrainGrid(height=h, width=w, cells=grid, crossings=[])
    
    def _strip_comments(self, text: str) -> str:
        return re.sub(r"//.*", "", text)


    def load_template_library(self, path: Path = _LIBRARY_PATH) -> dict[str, UnitTemplate]:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(self._strip_comments(raw))
        templates = {}
        for unit in data["units"]:
            t = UnitTemplate.model_validate(unit)
            templates[t.template_id] = t
        return templates
    
    def unit_from_template(self,
        template: UnitTemplate,
        unit_id: str,
        side: Side,
        position: Coord,
        posture: Posture = Posture.DEFENSIVE,
        dug_in: bool = False,
    ) -> UnitState:
        return UnitState(
            unit_id=unit_id,
            template_id=template.template_id,
            side=side,
            affiliation=template.affiliation,  # comes from template
            position=position,
            strength=1.0,
            readiness=Readiness.FULLY_OPERATIONAL,
            supply_days_remaining=None if template.supply_unlimited else float(template.base_supply_days),
            posture=posture,
            dug_in=dug_in,
        )
    
    def sample_unit_positions(
        self,
        n_blue: int,
        n_red: int,
        seed: int = 1729,
    ) -> tuple[list[tuple[int, int]], list[tuple[int, int]]]:
        map_path = (
            Path(__file__).parent.parent.parent.parent
            / "backend"
            / f"{self.scenario_id}.npz"
        )
        raw = np.load(map_path)["terrain"]
        is_water = raw[:, :, 3] > 0
        is_land = ~is_water

        land_coords = np.argwhere(is_land)
        cols = land_coords[:, 1]
        midpoint = (cols.max() + cols.min()) / 2

        blue_coords = land_coords[cols <= midpoint]
        red_coords = land_coords[cols > midpoint]

        def center_biased_probs(coords: np.ndarray) -> np.ndarray:
            center = coords.mean(axis=0)
            dists = np.linalg.norm(coords - center, axis=1)
            weights = np.exp(-dists / dists.std())
            return weights / weights.sum()

        rng = np.random.default_rng(seed)
        blue_idxs = rng.choice(len(blue_coords), size=n_blue, replace=False, p=center_biased_probs(blue_coords))
        red_idxs = rng.choice(len(red_coords), size=n_red, replace=False, p=center_biased_probs(red_coords))

        return [tuple(blue_coords[i]) for i in blue_idxs], [tuple(red_coords[i]) for i in red_idxs]

    @abstractmethod
    def build_units(self) -> dict[str, UnitState]:
        ...

    @abstractmethod
    def build_objectives(self) -> dict[str, Objective]:
        ...

    @abstractmethod
    def build_control(self, height: int, width: int) -> dict[str, ControlState]:
        ...

    @abstractmethod
    def side_postures(self) -> dict[Side, str]:
        ...

    def build_world(self, *, run_id: str | None = None, seed: int = 1729) -> WorldState:
        terrain = self.build_terrain()
        units = self.build_units()
        objectives = self.build_objectives()
        control = self.build_control(terrain.height, terrain.width)
        templates = load_template_library()

        identity = RunIdentity(
            run_id=run_id or f"{self.scenario_id}-001",
            scenario_id=self.scenario_id,
            rulepack_id=self.rulepack_id,
            engine_version=self.engine_version,
            seed=seed,
            noise_enabled=False,
        )

        world = WorldState(
            identity=identity,
            turn=0,
            minutes_per_turn=self.minutes_per_turn,
            timestamp_minutes=0,
            terrain=terrain,
            units=units,
            control=control,
            templates=templates,
            objectives=objectives,
            side_posture=self.side_postures(),
        )
        validate_world_invariants(world)
        return world