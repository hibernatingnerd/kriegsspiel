"""Latgale 2027 worked scenario for deterministic integration tests."""

from __future__ import annotations

from kriegsspiel.engine.enums import (
    Affiliation,
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
    WorldState,
    validate_world_invariants,
)


def _open() -> TerrainCell:
    return TerrainCell(base=TerrainBase.OPEN)


def _forest() -> TerrainCell:
    return TerrainCell(
        base=TerrainBase.FOREST,
        movement_cost_ground=1.6,
        cover_factor=0.6,
        visibility_factor=0.4,
        supply_throughput=0.7,
    )


def _water() -> TerrainCell:
    return TerrainCell(
        base=TerrainBase.WATER,
        movement_cost_ground=999.0,
        supply_throughput=0.0,
        visibility_factor=1.0,
    )


def _urban_dense(strategic_weight: float = 0.0, objective: bool = False) -> TerrainCell:
    feats: list[TerrainFeature] = [TerrainFeature.URBAN_DENSE, TerrainFeature.ROAD]
    if objective:
        feats.append(TerrainFeature.OBJECTIVE)
    return TerrainCell(
        base=TerrainBase.URBAN,
        features=tuple(feats),
        movement_cost_ground=2.0,
        cover_factor=0.7,
        visibility_factor=0.5,
        supply_throughput=1.2,
        strategic_weight=strategic_weight,
    )


def build_latgale_terrain() -> TerrainGrid:
    h, w = 16, 16
    grid: list[list[TerrainCell]] = [[_open() for _ in range(w)] for _ in range(h)]

    for r, c in [(1, 13), (1, 14), (2, 11), (2, 12), (2, 13), (2, 14), (3, 10), (3, 11)]:
        grid[r][c] = _forest()

    river_cells = [
        (9, 5), (9, 6), (9, 7), (9, 8), (9, 9), (9, 10), (9, 11), (9, 12),
        (10, 6), (10, 7), (10, 11), (10, 12), (10, 13), (11, 13), (12, 13), (13, 13),
    ]
    for r, c in river_cells:
        grid[r][c] = _water()

    grid[5][5] = _urban_dense(strategic_weight=2.0, objective=True)
    grid[5][6] = _urban_dense(strategic_weight=1.0)
    grid[6][5] = _urban_dense(strategic_weight=0.5)

    grid[10][4] = _urban_dense(strategic_weight=3.0, objective=True)
    grid[10][5] = _urban_dense(strategic_weight=1.5)
    grid[11][4] = _urban_dense(strategic_weight=1.0)
    grid[11][5] = _urban_dense(strategic_weight=1.0)

    grid[12][11] = _urban_dense(strategic_weight=1.5, objective=True)

    # Bridge cells
    grid[9][5] = TerrainCell(
        base=TerrainBase.OPEN,
        features=(TerrainFeature.BRIDGE, TerrainFeature.ROAD),
        movement_cost_ground=1.0,
        supply_throughput=1.5,
        strategic_weight=1.0,
    )
    grid[11][13] = TerrainCell(
        base=TerrainBase.OPEN,
        features=(TerrainFeature.BRIDGE, TerrainFeature.ROAD),
        movement_cost_ground=1.0,
        supply_throughput=1.5,
        strategic_weight=0.8,
    )

    crossings = [
        RiverCrossing(
            crossing_id="X-DAUGAVPILS",
            cell_a=(8, 5),
            cell_b=(9, 5),
            crossing_type="BRIDGE",
            capacity_per_turn=2,
            integrity="INTACT",
            controlled_by=Side.BLUE,
        ),
        RiverCrossing(
            crossing_id="X-DAUGAVPILS-S",
            cell_a=(9, 5),
            cell_b=(10, 5),
            crossing_type="BRIDGE",
            capacity_per_turn=2,
            integrity="INTACT",
            controlled_by=Side.BLUE,
        ),
        RiverCrossing(
            crossing_id="X-KRASLAVA-N",
            cell_a=(10, 13),
            cell_b=(11, 13),
            crossing_type="BRIDGE",
            capacity_per_turn=1,
            integrity="INTACT",
            controlled_by=Side.NEUTRAL,
        ),
        RiverCrossing(
            crossing_id="X-KRASLAVA-S",
            cell_a=(11, 13),
            cell_b=(12, 13),
            crossing_type="BRIDGE",
            capacity_per_turn=1,
            integrity="INTACT",
            controlled_by=Side.NEUTRAL,
        ),
    ]

    return TerrainGrid(height=h, width=w, cells=grid, crossings=crossings)


def build_latgale_units() -> dict[str, UnitState]:
    units = [
        UnitState(unit_id="BLUE-MNV-001-A", template_id="MNV-001", side=Side.BLUE, affiliation=Affiliation.BLUE, position=(5, 4), strength=1.0, readiness=Readiness.FULLY_OPERATIONAL, supply_days_remaining=3.0, posture=Posture.DEFENSIVE, dug_in=True),
        UnitState(unit_id="BLUE-MNV-002-A", template_id="MNV-002", side=Side.BLUE, affiliation=Affiliation.BLUE, position=(10, 4), strength=1.0, readiness=Readiness.FULLY_OPERATIONAL, supply_days_remaining=2.0, posture=Posture.DEFENSIVE, dug_in=True),
        UnitState(unit_id="BLUE-FRS-001-A", template_id="FRS-001", side=Side.BLUE, affiliation=Affiliation.BLUE, position=(8, 3), strength=1.0, readiness=Readiness.FULLY_OPERATIONAL, supply_days_remaining=4.0, posture=Posture.DEFENSIVE, dug_in=False),
        UnitState(unit_id="BLUE-ENB-001-A", template_id="ENB-001", side=Side.BLUE, affiliation=Affiliation.BLUE, position=(3, 2), strength=1.0, readiness=Readiness.FULLY_OPERATIONAL, supply_days_remaining=None, posture=Posture.SCREENING, dug_in=False),
        UnitState(unit_id="RED-MNV-006-A", template_id="MNV-006", side=Side.RED, affiliation=Affiliation.RED_RU, position=(5, 14), strength=1.0, readiness=Readiness.FULLY_OPERATIONAL, supply_days_remaining=2.0, posture=Posture.OFFENSIVE, dug_in=False),
        UnitState(unit_id="RED-MNV-005-A", template_id="MNV-005", side=Side.RED, affiliation=Affiliation.RED_RU, position=(10, 14), strength=0.9, readiness=Readiness.FULLY_OPERATIONAL, supply_days_remaining=1.5, posture=Posture.OFFENSIVE, dug_in=False),
        UnitState(unit_id="RED-FRS-007-A", template_id="FRS-007", side=Side.RED, affiliation=Affiliation.RED_RU, position=(8, 15), strength=1.0, readiness=Readiness.FULLY_OPERATIONAL, supply_days_remaining=3.0, posture=Posture.DEFENSIVE, dug_in=False),
        UnitState(unit_id="RED-ENB-009-A", template_id="ENB-009", side=Side.RED, affiliation=Affiliation.RED_RU, position=(3, 15), strength=1.0, readiness=Readiness.FULLY_OPERATIONAL, supply_days_remaining=None, posture=Posture.SCREENING, dug_in=False),
    ]
    return {u.unit_id: u for u in units}


def build_latgale_control(height: int, width: int) -> dict[str, ControlState]:
    control: dict[str, ControlState] = {}
    for r in range(height):
        for c in range(width):
            coord = (r, c)
            key = WorldState.cell_key(coord)
            if c <= 7:
                control[key] = ControlState(cell=coord, controlled_by=Side.BLUE, persistence_turns=999)
            elif c >= 13:
                control[key] = ControlState(cell=coord, controlled_by=Side.RED, persistence_turns=999)
            else:
                control[key] = ControlState(cell=coord, controlled_by=Side.NEUTRAL, persistence_turns=0)
    return control


def build_latgale_objectives() -> dict[str, Objective]:
    objs = [
        Objective(objective_id="OBJ-DAUGAVPILS", cell=(10, 4), name="Daugavpils", weight=3.0, held_by=Side.BLUE, taken_at_turn=0),
        Objective(objective_id="OBJ-REZEKNE", cell=(5, 5), name="Rezekne", weight=2.0, held_by=Side.BLUE, taken_at_turn=0),
        Objective(objective_id="OBJ-KRASLAVA", cell=(12, 11), name="Kraslava", weight=1.5, held_by=Side.NEUTRAL),
    ]
    return {o.objective_id: o for o in objs}


def build_latgale_world(*, run_id: str = "latgale-demo-001", seed: int = 1729) -> WorldState:
    terrain = build_latgale_terrain()
    units = build_latgale_units()
    control = build_latgale_control(terrain.height, terrain.width)
    objectives = build_latgale_objectives()

    identity = RunIdentity(
        run_id=run_id,
        scenario_id="latgale_2027",
        rulepack_id="krg_v0_1",
        engine_version="0.1.0",
        seed=seed,
        noise_enabled=False,
    )

    world = WorldState(
        identity=identity,
        turn=0,
        minutes_per_turn=60,
        timestamp_minutes=0,
        terrain=terrain,
        units=units,
        control=control,
        objectives=objectives,
        side_posture={Side.BLUE: "DEFEND_IN_DEPTH", Side.RED: "OFFENSIVE_DUAL_AXIS"},
    )
    validate_world_invariants(world)
    return world


def summarize(world: WorldState) -> dict:
    """Compact scenario snapshot for demo output."""
    return {
        "scenario": world.identity.scenario_id,
        "turn": world.turn,
        "time_min": world.timestamp_minutes,
        "grid": (world.terrain.height, world.terrain.width),
        "units_total": len(world.units),
        "units_alive": len(world.alive_units()),
        "blue_alive": len(world.alive_units_of_side(Side.BLUE)),
        "red_alive": len(world.alive_units_of_side(Side.RED)),
        "objectives": [
            {
                "id": obj.objective_id,
                "name": obj.name,
                "held_by": obj.held_by.value,
                "weight": obj.weight,
            }
            for obj in world.objectives.values()
        ],
        "crossings": [
            {
                "id": x.crossing_id,
                "a": x.cell_a,
                "b": x.cell_b,
                "integrity": x.integrity,
                "controlled_by": x.controlled_by.value,
            }
            for x in world.terrain.crossings
        ],
    }


def detailed_status(world: WorldState) -> None:
    """Human-readable situation report for terminal/demo."""
    print(f"=== {world.identity.scenario_id} | Turn {world.turn} ===")
    print(f"Time (min): {world.timestamp_minutes}")
    print(f"Grid: {world.terrain.height} x {world.terrain.width}")
    print(
        "Alive units: "
        f"BLUE={len(world.alive_units_of_side(Side.BLUE))} | "
        f"RED={len(world.alive_units_of_side(Side.RED))}"
    )

    print("\nOBJECTIVES:")
    for obj in world.objectives.values():
        print(
            f"  - {obj.name:12s} ({obj.objective_id}) at {obj.cell} | "
            f"held_by={obj.held_by.value} | weight={obj.weight}"
        )

    print("\nBLUE FORCES:")
    for u in world.alive_units_of_side(Side.BLUE):
        supply = "UNLIMITED" if u.supply_days_remaining is None else f"{u.supply_days_remaining:.1f}d"
        print(
            f"  - {u.unit_id:16s} pos={u.position} str={u.strength:.2f} "
            f"posture={u.posture.value} supply={supply}"
        )

    print("\nRED FORCES:")
    for u in world.alive_units_of_side(Side.RED):
        supply = "UNLIMITED" if u.supply_days_remaining is None else f"{u.supply_days_remaining:.1f}d"
        print(
            f"  - {u.unit_id:16s} pos={u.position} str={u.strength:.2f} "
            f"posture={u.posture.value} supply={supply}"
        )

    print("\nRIVER CROSSINGS:")
    for x in world.terrain.crossings:
        print(
            f"  - {x.crossing_id:16s} {x.cell_a} <-> {x.cell_b} | "
            f"{x.integrity} | controlled_by={x.controlled_by.value}"
        )
