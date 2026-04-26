"""Rural 2027 scenario."""

from __future__ import annotations

from kriegsspiel.engine.enums import Posture, Side
from kriegsspiel.engine.state import ControlState, Objective, UnitState, WorldState
from kriegsspiel.scenarios.base_scenario import BaseScenario


class RuralScenario(BaseScenario):
    scenario_id = "rural"

    def build_units(self) -> dict[str, UnitState]:
        lib = self.load_template_library()
        blue_pos, red_pos = self.sample_unit_positions(n_blue=6, n_red=6)

        units = [
            # BLUE - rangers, fast armor, mobile fires
            self.unit_from_template(lib["SPE-001"], "BLUE-SPE-001-A", Side.BLUE, blue_pos[0], Posture.SCREENING),
            self.unit_from_template(lib["SPE-001"], "BLUE-SPE-001-B", Side.BLUE, blue_pos[1], Posture.SCREENING),
            self.unit_from_template(lib["LI-001"],  "BLUE-LI-001-A",  Side.BLUE, blue_pos[2], Posture.OFFENSIVE),
            self.unit_from_template(lib["ARM-004"], "BLUE-ARM-004-A", Side.BLUE, blue_pos[3], Posture.OFFENSIVE),
            self.unit_from_template(lib["ART-001"], "BLUE-ART-001-A", Side.BLUE, blue_pos[4], Posture.OFFENSIVE),  # HIMARS shoot-and-displace
            self.unit_from_template(lib["ART-002"], "BLUE-ART-002-A", Side.BLUE, blue_pos[5], Posture.OFFENSIVE),

            # RED - spetsnaz, BTG, mobile artillery
            self.unit_from_template(lib["SPE-003"], "RED-SPE-003-A",  Side.RED, red_pos[0], Posture.SCREENING),
            self.unit_from_template(lib["SPE-003"], "RED-SPE-003-B",  Side.RED, red_pos[1], Posture.SCREENING),
            self.unit_from_template(lib["LI-004"],  "RED-LI-004-A",   Side.RED, red_pos[2], Posture.OFFENSIVE),
            self.unit_from_template(lib["ARM-002"], "RED-ARM-002-A",  Side.RED, red_pos[3], Posture.OFFENSIVE),  # BTG - faster than heavy armor
            self.unit_from_template(lib["ART-003"], "RED-ART-003-A",  Side.RED, red_pos[4], Posture.OFFENSIVE),  # Iskander - road mobile
            self.unit_from_template(lib["IRR-002"], "RED-IRR-002-A",  Side.RED, red_pos[5], Posture.SCREENING),  # IED network - terrain denial
        ]
        return {u.unit_id: u for u in units}

    def build_objectives(self) -> dict[str, Objective]:
        objs = [
            Objective(objective_id="OBJ-RURAL-A", cell=(50, 50), name="Crossroads Alpha", weight=3.0, held_by=Side.BLUE, taken_at_turn=0),
            Objective(objective_id="OBJ-RURAL-B", cell=(100, 100), name="Farmstead Beta", weight=2.0, held_by=Side.NEUTRAL),
            Objective(objective_id="OBJ-RURAL-C", cell=(150, 150), name="Ridge Charlie", weight=1.5, held_by=Side.NEUTRAL),
        ]
        return {o.objective_id: o for o in objs}

    def build_control(self, height: int, width: int) -> dict[str, ControlState]:
        control: dict[str, ControlState] = {}
        for r in range(height):
            for c in range(width):
                coord = (r, c)
                key = WorldState.cell_key(coord)
                if r >= height * 0.6:
                    control[key] = ControlState(cell=coord, controlled_by=Side.BLUE, persistence_turns=999)
                elif r <= height * 0.4:
                    control[key] = ControlState(cell=coord, controlled_by=Side.RED, persistence_turns=999)
                else:
                    control[key] = ControlState(cell=coord, controlled_by=Side.NEUTRAL, persistence_turns=0)
        return control

    def side_postures(self) -> dict[Side, str]:
        return {Side.BLUE: "DEFEND_IN_DEPTH", Side.RED: "OFFENSIVE_MAIN_EFFORT"}


def build_rural_world(*, run_id: str = "rural-demo-001", seed: int = 1729) -> WorldState:
    return RuralScenario().build_world(run_id=run_id, seed=seed)