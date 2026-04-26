"""Coast 2027 scenario."""

from __future__ import annotations

from kriegsspiel.engine.enums import Affiliation, Posture, Readiness, Side
from kriegsspiel.engine.state import (
    ControlState, Objective, UnitState, WorldState,
)
from kriegsspiel.scenarios.base_scenario import BaseScenario


class CoastScenario(BaseScenario):
    scenario_id = "coast"

    def build_units(self) -> dict[str, UnitState]:
        lib = self.load_template_library()
        blue_pos, red_pos = self.sample_unit_positions(n_blue=6, n_red=6)

        units = [
            self.unit_from_template(lib["LI-005"], "BLUE-LI-005-A", Side.BLUE, blue_pos[0], Posture.DEFENSIVE, dug_in=True),
            self.unit_from_template(lib["LI-001"], "BLUE-LI-001-A", Side.BLUE, blue_pos[1], Posture.DEFENSIVE, dug_in=False),
            self.unit_from_template(lib["ARM-001"], "BLUE-ARM-001-A", Side.BLUE, blue_pos[2], Posture.DEFENSIVE, dug_in=True),
            self.unit_from_template(lib["ARM-004"], "BLUE-ARM-004-A", Side.BLUE, blue_pos[3], Posture.DEFENSIVE, dug_in=True),
            self.unit_from_template(lib["ART-001"], "BLUE-ART-001-A", Side.BLUE, blue_pos[4], Posture.DEFENSIVE),
            self.unit_from_template(lib["AD-001"],  "BLUE-AD-001-A",  Side.BLUE, blue_pos[5], Posture.SCREENING),

            self.unit_from_template(lib["LI-003"], "RED-LI-003-A",  Side.RED, red_pos[0], Posture.OFFENSIVE),
            self.unit_from_template(lib["LI-004"], "RED-LI-004-A",  Side.RED, red_pos[1], Posture.OFFENSIVE),
            self.unit_from_template(lib["ARM-003"], "RED-ARM-003-A", Side.RED, red_pos[2], Posture.OFFENSIVE),
            self.unit_from_template(lib["ARM-002"], "RED-ARM-002-A", Side.RED, red_pos[3], Posture.OFFENSIVE),
            self.unit_from_template(lib["ART-004"], "RED-ART-004-A", Side.RED, red_pos[4], Posture.OFFENSIVE),
            self.unit_from_template(lib["TRN-005"], "RED-TRN-005-A", Side.RED, red_pos[5], Posture.OFFENSIVE),
        ]
        return {u.unit_id: u for u in units}

    def build_objectives(self) -> dict[str, Objective]:
        objs = [
            Objective(objective_id="OBJ-DAUGAVPILS", cell=(10, 4), name="Daugavpils", weight=3.0, held_by=Side.BLUE, taken_at_turn=0),
            Objective(objective_id="OBJ-REZEKNE", cell=(5, 5), name="Rezekne", weight=2.0, held_by=Side.BLUE, taken_at_turn=0),
            Objective(objective_id="OBJ-KRASLAVA", cell=(12, 11), name="Kraslava", weight=1.5, held_by=Side.NEUTRAL),
        ]
        return {o.objective_id: o for o in objs}

    def build_control(self, height: int, width: int) -> dict[str, ControlState]:
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

    def side_postures(self) -> dict[Side, str]:
        return {Side.BLUE: "DEFEND_IN_DEPTH", Side.RED: "OFFENSIVE_DUAL_AXIS"}


def build_coast_world(*, run_id: str = "coast-demo-001", seed: int = 1729) -> WorldState:
    return CoastScenario().build_world(run_id=run_id, seed=seed)





# def build_latgale_units() -> dict[str, UnitState]:
#     units = [
#         UnitState(unit_id="BLUE-MNV-001-A", template_id="MNV-001", side=Side.BLUE, affiliation=Affiliation.BLUE, position=(5, 4), strength=1.0, readiness=Readiness.FULLY_OPERATIONAL, supply_days_remaining=3.0, posture=Posture.DEFENSIVE, dug_in=True),
#         UnitState(unit_id="BLUE-MNV-002-A", template_id="MNV-002", side=Side.BLUE, affiliation=Affiliation.BLUE, position=(10, 4), strength=1.0, readiness=Readiness.FULLY_OPERATIONAL, supply_days_remaining=2.0, posture=Posture.DEFENSIVE, dug_in=True),
#         UnitState(unit_id="BLUE-FRS-001-A", template_id="FRS-001", side=Side.BLUE, affiliation=Affiliation.BLUE, position=(8, 3), strength=1.0, readiness=Readiness.FULLY_OPERATIONAL, supply_days_remaining=4.0, posture=Posture.DEFENSIVE, dug_in=False),
#         UnitState(unit_id="BLUE-ENB-001-A", template_id="ENB-001", side=Side.BLUE, affiliation=Affiliation.BLUE, position=(3, 2), strength=1.0, readiness=Readiness.FULLY_OPERATIONAL, supply_days_remaining=None, posture=Posture.SCREENING, dug_in=False),
#         UnitState(unit_id="RED-MNV-006-A", template_id="MNV-006", side=Side.RED, affiliation=Affiliation.RED_RU, position=(5, 14), strength=1.0, readiness=Readiness.FULLY_OPERATIONAL, supply_days_remaining=2.0, posture=Posture.OFFENSIVE, dug_in=False),
#         UnitState(unit_id="RED-MNV-005-A", template_id="MNV-005", side=Side.RED, affiliation=Affiliation.RED_RU, position=(10, 14), strength=0.9, readiness=Readiness.FULLY_OPERATIONAL, supply_days_remaining=1.5, posture=Posture.OFFENSIVE, dug_in=False),
#         UnitState(unit_id="RED-FRS-007-A", template_id="FRS-007", side=Side.RED, affiliation=Affiliation.RED_RU, position=(8, 15), strength=1.0, readiness=Readiness.FULLY_OPERATIONAL, supply_days_remaining=3.0, posture=Posture.DEFENSIVE, dug_in=False),
#         UnitState(unit_id="RED-ENB-009-A", template_id="ENB-009", side=Side.RED, affiliation=Affiliation.RED_RU, position=(3, 15), strength=1.0, readiness=Readiness.FULLY_OPERATIONAL, supply_days_remaining=None, posture=Posture.SCREENING, dug_in=False),
#     ]
#     return {u.unit_id: u for u in units}


# def build_latgale_control(height: int, width: int) -> dict[str, ControlState]:
#     control: dict[str, ControlState] = {}
#     for r in range(height):
#         for c in range(width):
#             coord = (r, c)
#             key = WorldState.cell_key(coord)
#             if c <= 7:
#                 control[key] = ControlState(cell=coord, controlled_by=Side.BLUE, persistence_turns=999)
#             elif c >= 13:
#                 control[key] = ControlState(cell=coord, controlled_by=Side.RED, persistence_turns=999)
#             else:
#                 control[key] = ControlState(cell=coord, controlled_by=Side.NEUTRAL, persistence_turns=0)
#     return control


# def build_latgale_objectives() -> dict[str, Objective]:
#     objs = [
#         Objective(objective_id="OBJ-DAUGAVPILS", cell=(10, 4), name="Daugavpils", weight=3.0, held_by=Side.BLUE, taken_at_turn=0),
#         Objective(objective_id="OBJ-REZEKNE", cell=(5, 5), name="Rezekne", weight=2.0, held_by=Side.BLUE, taken_at_turn=0),
#         Objective(objective_id="OBJ-KRASLAVA", cell=(12, 11), name="Kraslava", weight=1.5, held_by=Side.NEUTRAL),
#     ]
#     return {o.objective_id: o for o in objs}


# def build_latgale_world(*, run_id: str = "latgale-demo-001", seed: int = 1729) -> WorldState:
#     terrain = build_latgale_terrain()
#     units = build_latgale_units()
#     control = build_latgale_control(terrain.height, terrain.width)
#     objectives = build_latgale_objectives()

#     identity = RunIdentity(
#         run_id=run_id,
#         scenario_id="latgale_2027",
#         rulepack_id="krg_v0_1",
#         engine_version="0.1.0",
#         seed=seed,
#         noise_enabled=False,
#     )

#     world = WorldState(
#         identity=identity,
#         turn=0,
#         minutes_per_turn=60,
#         timestamp_minutes=0,
#         terrain=terrain,
#         units=units,
#         control=control,
#         objectives=objectives,
#         side_posture={Side.BLUE: "DEFEND_IN_DEPTH", Side.RED: "OFFENSIVE_DUAL_AXIS"},
#     )
#     validate_world_invariants(world)
#     return world


# def summarize(world: WorldState) -> dict:
#     """Compact scenario snapshot for demo output."""
#     return {
#         "scenario": world.identity.scenario_id,
#         "turn": world.turn,
#         "time_min": world.timestamp_minutes,
#         "grid": (world.terrain.height, world.terrain.width),
#         "units_total": len(world.units),
#         "units_alive": len(world.alive_units()),
#         "blue_alive": len(world.alive_units_of_side(Side.BLUE)),
#         "red_alive": len(world.alive_units_of_side(Side.RED)),
#         "objectives": [
#             {
#                 "id": obj.objective_id,
#                 "name": obj.name,
#                 "held_by": obj.held_by.value,
#                 "weight": obj.weight,
#             }
#             for obj in world.objectives.values()
#         ],
#         "crossings": [
#             {
#                 "id": x.crossing_id,
#                 "a": x.cell_a,
#                 "b": x.cell_b,
#                 "integrity": x.integrity,
#                 "controlled_by": x.controlled_by.value,
#             }
#             for x in world.terrain.crossings
#         ],
#     }


# def detailed_status(world: WorldState) -> None:
#     """Human-readable situation report for terminal/demo."""
#     print(f"=== {world.identity.scenario_id} | Turn {world.turn} ===")
#     print(f"Time (min): {world.timestamp_minutes}")
#     print(f"Grid: {world.terrain.height} x {world.terrain.width}")
#     print(
#         "Alive units: "
#         f"BLUE={len(world.alive_units_of_side(Side.BLUE))} | "
#         f"RED={len(world.alive_units_of_side(Side.RED))}"
#     )

#     print("\nOBJECTIVES:")
#     for obj in world.objectives.values():
#         print(
#             f"  - {obj.name:12s} ({obj.objective_id}) at {obj.cell} | "
#             f"held_by={obj.held_by.value} | weight={obj.weight}"
#         )

#     print("\nBLUE FORCES:")
#     for u in world.alive_units_of_side(Side.BLUE):
#         supply = "UNLIMITED" if u.supply_days_remaining is None else f"{u.supply_days_remaining:.1f}d"
#         print(
#             f"  - {u.unit_id:16s} pos={u.position} str={u.strength:.2f} "
#             f"posture={u.posture.value} supply={supply}"
#         )

#     print("\nRED FORCES:")
#     for u in world.alive_units_of_side(Side.RED):
#         supply = "UNLIMITED" if u.supply_days_remaining is None else f"{u.supply_days_remaining:.1f}d"
#         print(
#             f"  - {u.unit_id:16s} pos={u.position} str={u.strength:.2f} "
#             f"posture={u.posture.value} supply={supply}"
#         )

#     print("\nRIVER CROSSINGS:")
#     for x in world.terrain.crossings:
#         print(
#             f"  - {x.crossing_id:16s} {x.cell_a} <-> {x.cell_b} | "
#             f"{x.integrity} | controlled_by={x.controlled_by.value}"
#         )
