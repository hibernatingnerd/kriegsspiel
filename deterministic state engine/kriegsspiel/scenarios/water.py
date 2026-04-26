"""Water 2027 scenario."""

from __future__ import annotations

from kriegsspiel.engine.enums import Posture, Side
from kriegsspiel.engine.state import ControlState, Objective, UnitState, WorldState
from kriegsspiel.scenarios.base_scenario import BaseScenario


class WaterScenario(BaseScenario):
    scenario_id = "water"

    def build_units(self) -> dict[str, UnitState]:
        lib = self.load_template_library()
        blue_pos, red_pos = self.sample_unit_positions(n_blue=6, n_red=6)

        units = [
            # BLUE - amphibious marines, coastal artillery, special forces
            self.unit_from_template(lib["LI-005"], "BLUE-LI-005-A", Side.BLUE, blue_pos[0], Posture.DEFENSIVE, dug_in=True),   # US Marine - amphibious
            self.unit_from_template(lib["LI-005"], "BLUE-LI-005-B", Side.BLUE, blue_pos[1], Posture.OFFENSIVE),                 # US Marine - assault element
            self.unit_from_template(lib["SPE-001"], "BLUE-SPE-001-A", Side.BLUE, blue_pos[2], Posture.SCREENING),               # Rangers - recon
            self.unit_from_template(lib["ART-001"], "BLUE-ART-001-A", Side.BLUE, blue_pos[3], Posture.DEFENSIVE),               # HIMARS - coastal fire support
            self.unit_from_template(lib["ARM-001"], "BLUE-ARM-001-A", Side.BLUE, blue_pos[4], Posture.DEFENSIVE, dug_in=True),  # Armor - beachhead holding
            self.unit_from_template(lib["AD-002"],  "BLUE-AD-002-A",  Side.BLUE, blue_pos[5], Posture.DEFENSIVE),               # Patriot - anti-missile cover

            # RED - PLA marines, amphibious assault follow-on
            self.unit_from_template(lib["LI-003"], "RED-LI-003-A",  Side.RED, red_pos[0], Posture.OFFENSIVE),                  # PLA Marine - amphibious
            self.unit_from_template(lib["LI-003"], "RED-LI-003-B",  Side.RED, red_pos[1], Posture.OFFENSIVE),                  # PLA Marine - second wave
            self.unit_from_template(lib["SPE-003"], "RED-SPE-003-A", Side.RED, red_pos[2], Posture.SCREENING),                 # Spetsnaz - recon/infiltration
            self.unit_from_template(lib["ARM-003"], "RED-ARM-003-A", Side.RED, red_pos[3], Posture.OFFENSIVE),                 # PLA armor - follow-on force
            self.unit_from_template(lib["ART-004"], "RED-ART-004-A", Side.RED, red_pos[4], Posture.OFFENSIVE),                 # PLA MLRS - fire support
            self.unit_from_template(lib["IRR-003"], "RED-IRR-003-A", Side.RED, red_pos[5], Posture.SCREENING),                 # Proxy militia - terrain hold
        ]
        return {u.unit_id: u for u in units}

    def build_objectives(self) -> dict[str, Objective]:
        objs = [
            Objective(objective_id="OBJ-WATER-A", cell=(50, 50),   name="Beachhead Alpha", weight=3.0, held_by=Side.BLUE, taken_at_turn=0),
            Objective(objective_id="OBJ-WATER-B", cell=(100, 100), name="Port Beta",       weight=2.0, held_by=Side.NEUTRAL),
            Objective(objective_id="OBJ-WATER-C", cell=(150, 150), name="Headland Charlie", weight=1.5, held_by=Side.NEUTRAL),
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
        return {Side.BLUE: "DEFEND_IN_DEPTH", Side.RED: "AMPHIBIOUS_ASSAULT"}


def build_water_world(*, run_id: str = "water-demo-001", seed: int = 1729) -> WorldState:
    return WaterScenario().build_world(run_id=run_id, seed=seed)