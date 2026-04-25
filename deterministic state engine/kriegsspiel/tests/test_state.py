"""Tests for state.py — each test is also documentation.

Every model invariant gets a positive test (it accepts valid input) and
a negative test (it rejects the specific kind of bad input it's supposed
to catch). Read top-to-bottom for a tour of what the schema enforces.

Run with:  pytest tests/test_state.py -v
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from kriegsspiel.engine.enums import (
    Affiliation,
    Category,
    Domain,
    Posture,
    Readiness,
    Side,
    TerrainBase,
    TerrainFeature,
)
from kriegsspiel.engine.state import (
    ControlState,
    Objective,
    RiverCrossing,
    RunIdentity,
    TerrainCell,
    TerrainGrid,
    UnitState,
    UnitTemplate,
    WorldState,
    WorldStateError,
    chebyshev_distance,
    euclidean_distance,
    validate_world_invariants,
)


# ============================================================================
# TerrainCell invariants
# ============================================================================


class TestTerrainCellModelInvariants:
    """Per-cell invariants — fired at construction time by Pydantic."""

    def test_open_cell_minimal_valid(self):
        c = TerrainCell(base=TerrainBase.OPEN)
        assert c.base == TerrainBase.OPEN
        assert c.cover_factor == 0.0
        assert c.movement_cost_ground == 1.0

    def test_cover_factor_above_one_rejected(self):
        with pytest.raises(ValidationError):
            TerrainCell(base=TerrainBase.OPEN, cover_factor=1.5)

    def test_negative_movement_cost_rejected(self):
        with pytest.raises(ValidationError):
            TerrainCell(base=TerrainBase.OPEN, movement_cost_ground=-1.0)

    def test_urban_density_feature_requires_urban_base(self):
        # OPEN base + URBAN_DENSE feature is incoherent.
        with pytest.raises(ValidationError, match="URBAN_DENSE"):
            TerrainCell(
                base=TerrainBase.OPEN,
                features=(TerrainFeature.URBAN_DENSE,),
            )

    def test_urban_density_feature_on_urban_base_ok(self):
        c = TerrainCell(
            base=TerrainBase.URBAN,
            features=(TerrainFeature.URBAN_DENSE,),
            movement_cost_ground=2.0,
        )
        assert TerrainFeature.URBAN_DENSE in c.features

    def test_objective_feature_requires_strategic_weight(self):
        # OBJECTIVE feature + zero weight is incoherent: an objective must
        # actually be worth something.
        with pytest.raises(ValidationError, match="strategic_weight"):
            TerrainCell(
                base=TerrainBase.OPEN,
                features=(TerrainFeature.OBJECTIVE,),
                strategic_weight=0.0,
            )

    def test_objective_feature_with_weight_ok(self):
        c = TerrainCell(
            base=TerrainBase.URBAN,
            features=(TerrainFeature.OBJECTIVE,),
            strategic_weight=2.5,
        )
        assert c.strategic_weight == 2.5

    def test_impassable_requires_high_cost(self):
        # IMPASSABLE base must have movement cost >= 999.
        with pytest.raises(ValidationError, match="IMPASSABLE"):
            TerrainCell(base=TerrainBase.IMPASSABLE, movement_cost_ground=5.0)

    def test_impassable_with_high_cost_ok(self):
        c = TerrainCell(base=TerrainBase.IMPASSABLE, movement_cost_ground=999.0)
        assert c.base == TerrainBase.IMPASSABLE


# ============================================================================
# RiverCrossing invariants
# ============================================================================


class TestRiverCrossing:

    def test_valid_bridge(self):
        x = RiverCrossing(
            crossing_id="X-1",
            cell_a=(5, 5),
            cell_b=(5, 6),
            crossing_type="BRIDGE",
        )
        assert x.integrity == "INTACT"

    def test_self_loop_rejected(self):
        with pytest.raises(ValidationError, match="cell to itself"):
            RiverCrossing(
                crossing_id="X-bad",
                cell_a=(5, 5),
                cell_b=(5, 5),
                crossing_type="BRIDGE",
            )

    def test_non_adjacent_cells_rejected(self):
        with pytest.raises(ValidationError, match="not adjacent"):
            RiverCrossing(
                crossing_id="X-far",
                cell_a=(0, 0),
                cell_b=(5, 5),
                crossing_type="BRIDGE",
            )

    def test_diagonal_adjacency_allowed(self):
        # 8-neighbor adjacency: diagonals are adjacent.
        x = RiverCrossing(
            crossing_id="X-diag",
            cell_a=(0, 0),
            cell_b=(1, 1),
            crossing_type="FORD",
        )
        assert x.crossing_type == "FORD"

    def test_invalid_crossing_type_rejected(self):
        with pytest.raises(ValidationError):
            RiverCrossing(
                crossing_id="X",
                cell_a=(0, 0), cell_b=(0, 1),
                crossing_type="HOVERCRAFT",  # not in enum
            )

    def test_invalid_integrity_rejected(self):
        with pytest.raises(ValidationError):
            RiverCrossing(
                crossing_id="X",
                cell_a=(0, 0), cell_b=(0, 1),
                crossing_type="BRIDGE",
                integrity="ON_FIRE",  # not in enum
            )


# ============================================================================
# TerrainGrid construction
# ============================================================================


class TestTerrainGrid:

    def _open_grid(self, h: int, w: int) -> TerrainGrid:
        cells = [[TerrainCell(base=TerrainBase.OPEN) for _ in range(w)] for _ in range(h)]
        return TerrainGrid(height=h, width=w, cells=cells)

    def test_build_open_grid(self):
        g = self._open_grid(3, 4)
        assert g.height == 3 and g.width == 4
        assert g._movement_cost_ground.shape == (3, 4)
        assert g.is_passable_ground((1, 2))

    def test_non_rectangular_rejected(self):
        cells = [
            [TerrainCell(base=TerrainBase.OPEN), TerrainCell(base=TerrainBase.OPEN)],
            [TerrainCell(base=TerrainBase.OPEN)],  # short row
        ]
        with pytest.raises(ValidationError, match="width"):
            TerrainGrid(height=2, width=2, cells=cells)

    def test_declared_shape_mismatch_rejected(self):
        cells = [[TerrainCell(base=TerrainBase.OPEN)]]
        with pytest.raises(ValueError, match="does not match declared"):
            TerrainGrid(height=5, width=5, cells=cells)

    def test_water_cell_not_passable_ground(self):
        cells = [[TerrainCell(base=TerrainBase.WATER, movement_cost_ground=999.0)]]
        g = TerrainGrid(height=1, width=1, cells=cells)
        assert not g.is_passable_ground((0, 0))

    def test_in_bounds(self):
        g = self._open_grid(3, 3)
        assert g.in_bounds((0, 0))
        assert g.in_bounds((2, 2))
        assert not g.in_bounds((-1, 0))
        assert not g.in_bounds((3, 0))
        assert not g.in_bounds((0, 3))

    def test_neighbors_8_corner(self):
        g = self._open_grid(3, 3)
        # Corner has 3 neighbors.
        assert set(g.neighbors_8((0, 0))) == {(0, 1), (1, 0), (1, 1)}

    def test_neighbors_8_center(self):
        g = self._open_grid(3, 3)
        # Center has 8 neighbors.
        assert len(list(g.neighbors_8((1, 1)))) == 8

    def test_crossing_out_of_bounds_rejected(self):
        cells = [[TerrainCell(base=TerrainBase.OPEN) for _ in range(2)] for _ in range(2)]
        bad_crossing = RiverCrossing(
            crossing_id="X-oob",
            cell_a=(0, 0),
            cell_b=(0, 1),
            crossing_type="BRIDGE",
        )
        # Construct fine within grid, but if we use a 2x2 grid with a crossing
        # to (5, 5), it would fail. Use a crossing that's adjacent (legal at
        # crossing-construction time) but out of bounds for this grid:
        # (0,1) -> (0,2) is adjacent but col 2 is out of bounds for width=2.
        oob_crossing = RiverCrossing(
            crossing_id="X-oob",
            cell_a=(0, 1),
            cell_b=(0, 2),  # out of bounds for width=2
            crossing_type="BRIDGE",
        )
        with pytest.raises(ValueError, match="out-of-bounds"):
            TerrainGrid(height=2, width=2, cells=cells, crossings=[oob_crossing])


# ============================================================================
# UnitState cross-field invariants
# ============================================================================


class TestUnitState:

    def _base_unit_kwargs(self, **overrides):
        defaults = dict(
            unit_id="U-001",
            template_id="MNV-001",
            side=Side.BLUE,
            affiliation=Affiliation.BLUE,
            position=(5, 5),
        )
        defaults.update(overrides)
        return defaults

    def test_minimal_valid(self):
        u = UnitState(**self._base_unit_kwargs())
        assert u.is_alive
        assert u.effective_combat_factor == 1.0  # full strength, FULLY_OPERATIONAL

    def test_destroyed_must_have_zero_strength(self):
        with pytest.raises(ValidationError, match="DESTROYED"):
            UnitState(
                **self._base_unit_kwargs(
                    readiness=Readiness.DESTROYED,
                    strength=0.5,
                )
            )

    def test_destroyed_with_zero_strength_ok(self):
        u = UnitState(
            **self._base_unit_kwargs(
                readiness=Readiness.DESTROYED,
                strength=0.0,
            )
        )
        assert not u.is_alive
        assert u.effective_combat_factor == 0.0

    def test_negative_supply_rejected(self):
        with pytest.raises(ValidationError, match="supply_days_remaining"):
            UnitState(**self._base_unit_kwargs(supply_days_remaining=-0.5))

    def test_unlimited_supply_ok(self):
        u = UnitState(**self._base_unit_kwargs(supply_days_remaining=None))
        assert u.supply_days_remaining is None

    def test_dug_in_while_moving_rejected(self):
        with pytest.raises(ValidationError, match="dug_in.*MOVING"):
            UnitState(
                **self._base_unit_kwargs(dug_in=True, posture=Posture.MOVING)
            )

    def test_blue_side_red_affiliation_rejected(self):
        with pytest.raises(ValidationError, match="BLUE.*affiliation"):
            UnitState(
                **self._base_unit_kwargs(
                    side=Side.BLUE,
                    affiliation=Affiliation.RED_RU,
                )
            )

    def test_red_side_blue_affiliation_rejected(self):
        with pytest.raises(ValidationError, match="RED"):
            UnitState(
                **self._base_unit_kwargs(
                    side=Side.RED,
                    affiliation=Affiliation.BLUE,
                )
            )

    def test_red_with_red_ru_ok(self):
        u = UnitState(
            **self._base_unit_kwargs(
                side=Side.RED,
                affiliation=Affiliation.RED_RU,
            )
        )
        assert u.side == Side.RED

    def test_red_with_opfor_ok(self):
        u = UnitState(
            **self._base_unit_kwargs(
                side=Side.RED,
                affiliation=Affiliation.OPFOR,
            )
        )
        assert u.affiliation == Affiliation.OPFOR

    def test_strength_above_one_rejected(self):
        with pytest.raises(ValidationError):
            UnitState(**self._base_unit_kwargs(strength=1.2))

    def test_effective_combat_factor_degraded(self):
        u = UnitState(
            **self._base_unit_kwargs(
                strength=0.8,
                readiness=Readiness.DEGRADED,
            )
        )
        assert abs(u.effective_combat_factor - 0.8 * 0.7) < 1e-6


# ============================================================================
# UnitTemplate invariants
# ============================================================================


class TestUnitTemplate:

    def _kwargs(self, **overrides):
        defaults = dict(
            template_id="MNV-001",
            name="Test BCT",
            type="Infantry Brigade",
            category=Category.MANEUVER,
            domain=Domain.GROUND,
            affiliation=Affiliation.BLUE,
            echelon_canonical="BRIGADE",
            base_personnel=4500,
            base_combat_power=72,
            offensive_rating=68,
            defensive_rating=76,
            speed_road=40, speed_offroad=20,
            operational_radius_km=150,
            base_supply_days=3,
            signature="HIGH",
        )
        defaults.update(overrides)
        return defaults

    def test_offensive_zero_must_set_can_assault_false(self):
        # ADF-style unit: offensive_rating=0, but can_assault left True => reject.
        with pytest.raises(ValidationError, match="can_assault"):
            UnitTemplate(
                **self._kwargs(
                    template_id="ADF-001",
                    category=Category.AIR_DEFENSE,
                    offensive_rating=0,
                    defensive_rating=84,
                    can_assault=True,  # WRONG given offensive_rating=0
                )
            )

    def test_air_defense_with_can_assault_false_ok(self):
        t = UnitTemplate(
            **self._kwargs(
                template_id="ADF-001",
                category=Category.AIR_DEFENSE,
                offensive_rating=0,
                defensive_rating=84,
                can_assault=False,
            )
        )
        assert not t.can_assault

    def test_resupply_only_for_sustainment(self):
        with pytest.raises(ValidationError, match="SUSTAINMENT"):
            UnitTemplate(
                **self._kwargs(
                    category=Category.MANEUVER,
                    can_resupply_others=True,
                )
            )

    def test_sustainment_can_resupply(self):
        t = UnitTemplate(
            **self._kwargs(
                template_id="SUS-001",
                category=Category.SUSTAINMENT,
                offensive_rating=0,
                defensive_rating=10,
                can_assault=False,
                can_defend=True,
                can_resupply_others=True,
            )
        )
        assert t.can_resupply_others


# ============================================================================
# Distance helpers
# ============================================================================


class TestDistances:

    def test_chebyshev_diagonal(self):
        # Diagonals: max(|dr|, |dc|) -- (0,0) -> (3,3) is 3 king moves.
        assert chebyshev_distance((0, 0), (3, 3)) == 3
        assert chebyshev_distance((0, 0), (0, 5)) == 5
        assert chebyshev_distance((2, 7), (5, 3)) == 4

    def test_euclidean(self):
        assert euclidean_distance((0, 0), (3, 4)) == 5.0


# ============================================================================
# WorldState world-level invariants
# ============================================================================


class TestWorldStateInvariants:

    def _minimal_world(self) -> WorldState:
        cells = [[TerrainCell(base=TerrainBase.OPEN) for _ in range(3)] for _ in range(3)]
        terrain = TerrainGrid(height=3, width=3, cells=cells)
        ident = RunIdentity(
            run_id="t-001", scenario_id="toy", rulepack_id="krg_v0_1",
            engine_version="0.1.0",
        )
        return WorldState(
            identity=ident,
            terrain=terrain,
            units={},
            control={},
            objectives={},
        )

    def test_minimal_world_passes_invariants(self):
        w = self._minimal_world()
        validate_world_invariants(w)  # should not raise

    def test_unit_out_of_bounds_caught(self):
        w = self._minimal_world()
        # Bypass per-model checks by inserting a unit at an out-of-bounds
        # position. Pydantic UnitState doesn't know the grid size, so it
        # accepts any tuple — the world-level checker is the gate.
        u = UnitState(
            unit_id="U-x", template_id="T",
            side=Side.BLUE, affiliation=Affiliation.BLUE,
            position=(10, 10),  # out of bounds for the 3x3 world
        )
        w.units["U-x"] = u
        with pytest.raises(WorldStateError, match="out-of-bounds"):
            validate_world_invariants(w)

    def test_stacking_violation_caught(self):
        w = self._minimal_world()
        u1 = UnitState(unit_id="U1", template_id="T", side=Side.BLUE,
                       affiliation=Affiliation.BLUE, position=(1, 1))
        u2 = UnitState(unit_id="U2", template_id="T", side=Side.BLUE,
                       affiliation=Affiliation.BLUE, position=(1, 1))
        w.units["U1"] = u1
        w.units["U2"] = u2
        with pytest.raises(WorldStateError, match="stacking"):
            validate_world_invariants(w)

    def test_opposing_sides_same_cell_allowed(self):
        # Co-located opposing units are LEGAL (combat will resolve them) —
        # the one-stack rule is per-side.
        w = self._minimal_world()
        u_blue = UnitState(unit_id="UB", template_id="T", side=Side.BLUE,
                           affiliation=Affiliation.BLUE, position=(1, 1))
        u_red = UnitState(unit_id="UR", template_id="T", side=Side.RED,
                          affiliation=Affiliation.RED_RU, position=(1, 1))
        w.units["UB"] = u_blue
        w.units["UR"] = u_red
        validate_world_invariants(w)  # passes

    def test_unit_dict_key_mismatch_caught(self):
        w = self._minimal_world()
        u = UnitState(unit_id="U-real", template_id="T", side=Side.BLUE,
                      affiliation=Affiliation.BLUE, position=(0, 0))
        w.units["U-wrong-key"] = u  # key doesn't match unit_id
        with pytest.raises(WorldStateError, match="does not match unit_id"):
            validate_world_invariants(w)

    def test_objective_on_impassable_caught(self):
        cells = [[TerrainCell(base=TerrainBase.OPEN) for _ in range(3)] for _ in range(3)]
        cells[1][1] = TerrainCell(
            base=TerrainBase.IMPASSABLE,
            movement_cost_ground=999.0,
        )
        terrain = TerrainGrid(height=3, width=3, cells=cells)
        ident = RunIdentity(run_id="t", scenario_id="toy",
                            rulepack_id="krg_v0_1", engine_version="0.1.0")
        obj = Objective(objective_id="OBJ-1", cell=(1, 1), name="Bad")
        w = WorldState(
            identity=ident, terrain=terrain,
            units={}, control={},
            objectives={"OBJ-1": obj},
        )
        with pytest.raises(WorldStateError, match="IMPASSABLE"):
            validate_world_invariants(w)

    def test_time_regression_caught(self):
        w = self._minimal_world()
        # Manually corrupt: turn=2, minutes_per_turn=60 implies time>=120;
        # set timestamp_minutes=30 to force a regression.
        # Pydantic v2 doesn't re-run model_validator on direct assignment
        # by default, so this corrupts the state for our test.
        w.turn = 2
        w.timestamp_minutes = 30
        with pytest.raises(WorldStateError, match="time went backwards"):
            validate_world_invariants(w)


# ============================================================================
# Latgale scenario integration test
# ============================================================================


class TestLatgaleScenario:
    """The worked scenario — its very compilation is the strongest assertion
    that the schema describes something real."""

    def test_latgale_world_builds(self):
        from kriegsspiel.scenarios.latgale_2027 import build_latgale_world
        w = build_latgale_world()
        assert w.identity.scenario_id == "latgale_2027"
        assert len(w.alive_units()) == 8
        assert len(w.alive_units_of_side(Side.BLUE)) == 4
        assert len(w.alive_units_of_side(Side.RED)) == 4

    def test_latgale_objectives(self):
        from kriegsspiel.scenarios.latgale_2027 import build_latgale_world
        w = build_latgale_world()
        assert "OBJ-DAUGAVPILS" in w.objectives
        assert w.objectives["OBJ-DAUGAVPILS"].held_by == Side.BLUE
        assert w.objectives["OBJ-KRASLAVA"].held_by == Side.NEUTRAL

    def test_latgale_river_crossings(self):
        from kriegsspiel.scenarios.latgale_2027 import build_latgale_world
        w = build_latgale_world()
        assert len(w.terrain.crossings) == 4
        # Daugavpils bridge should be BLUE-controlled at start.
        daug = next(x for x in w.terrain.crossings if x.crossing_id == "X-DAUGAVPILS")
        assert daug.controlled_by == Side.BLUE

    def test_latgale_passes_world_invariants(self):
        # build_latgale_world calls validate_world_invariants internally;
        # if it raises, the world is broken.
        from kriegsspiel.scenarios.latgale_2027 import build_latgale_world
        w = build_latgale_world()
        validate_world_invariants(w)

    def test_latgale_query_helpers(self):
        from kriegsspiel.scenarios.latgale_2027 import build_latgale_world
        w = build_latgale_world()
        # The BLUE ABCT in Daugavpils should have RED enemies somewhere
        # east, but not adjacent (RED is at col 14, BLUE ABCT at col 4).
        abct = w.units["BLUE-MNV-002-A"]
        adj_enemies = w.enemies_adjacent_to(abct)
        assert adj_enemies == []  # too far apart at scenario start
        # The opposing side helper.
        assert w.opposing_side(Side.BLUE) == Side.RED


# ============================================================================
# Serialization round-trip
# ============================================================================


class TestSerialization:

    def test_world_dumps_to_json(self):
        from kriegsspiel.scenarios.latgale_2027 import build_latgale_world
        w = build_latgale_world()
        # Should not raise; produces a JSON-compatible dict.
        dumped = w.model_dump(mode="json")
        assert dumped["identity"]["scenario_id"] == "latgale_2027"
        assert dumped["turn"] == 0
        # Units are a dict keyed by unit_id.
        assert "BLUE-MNV-001-A" in dumped["units"]
