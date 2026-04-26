"""
Kriegsspiel FastAPI backend.

No LLM layer — decisions are mapped deterministically to MissionOrders
and resolved by the Omnissiah engine.

Endpoints
─────────
GET  /health
GET  /scenarios
POST /game/start          body: ScenarioConfig
POST /game/{run_id}/decide body: DecideRequest
"""

from __future__ import annotations

import sys
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from statistics import mean
from typing import Any

# ── engine path ──────────────────────────────────────────────────────────
_ENGINE_DIR = Path(__file__).parent.parent / "deterministic state engine"
sys.path.insert(0, str(_ENGINE_DIR))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from kriegsspiel.engine.enums import Affiliation, Category, Domain, Side
from kriegsspiel.engine.omnissiah import advance_timestep
from kriegsspiel.engine.orders import MissionOrder, MissionType
from kriegsspiel.engine.state import (
    UnitState,
    UnitTemplate,
    WorldState,
    chebyshev_distance,
)
from kriegsspiel.scenarios.latgale_2027 import build_latgale_world

# ── app ───────────────────────────────────────────────────────────────────

app = FastAPI(title="Kriegsspiel Engine", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000", "http://127.0.0.1:3000",
        "http://localhost:3001", "http://127.0.0.1:3001",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── in-memory session store ───────────────────────────────────────────────

@dataclass
class Session:
    world: WorldState
    turn_log: list[dict] = field(default_factory=list)
    scenario_id: str = "latgale_2027"
    run_id: str = ""

_sessions: dict[str, Session] = {}

# ── unit templates ────────────────────────────────────────────────────────

def _mnv(tid: str, aff: Affiliation) -> UnitTemplate:
    return UnitTemplate(
        template_id=tid, name=tid, type="MANEUVER",
        category=Category.MANEUVER, domain=Domain.LAND, affiliation=aff,
        echelon_canonical="BATTALION", base_personnel=500, base_combat_power=65,
        offensive_rating=65, defensive_rating=55,
        speed_road=30.0, speed_offroad=15.0,
        operational_radius_km=100.0, fires_range_km=0.0, sensor_range_km=10.0,
        base_supply_days=3, supply_unlimited=False, signature="MEDIUM",
        can_assault=True, can_defend=True, can_resupply_others=False,
    )

def _frs(tid: str, aff: Affiliation) -> UnitTemplate:
    return UnitTemplate(
        template_id=tid, name=tid, type="FIRES",
        category=Category.FIRES, domain=Domain.LAND, affiliation=aff,
        echelon_canonical="BATTALION", base_personnel=200, base_combat_power=0,
        offensive_rating=0, defensive_rating=20,
        speed_road=20.0, speed_offroad=10.0,
        operational_radius_km=80.0, fires_range_km=40.0, sensor_range_km=20.0,
        base_supply_days=3, supply_unlimited=False, signature="MEDIUM",
        can_assault=False, can_defend=True, can_resupply_others=False,
    )

def _enb(tid: str, aff: Affiliation) -> UnitTemplate:
    return UnitTemplate(
        template_id=tid, name=tid, type="ENABLER",
        category=Category.ENABLER, domain=Domain.LAND, affiliation=aff,
        echelon_canonical="COMPANY", base_personnel=150, base_combat_power=10,
        offensive_rating=10, defensive_rating=30,
        speed_road=25.0, speed_offroad=10.0,
        operational_radius_km=60.0, fires_range_km=0.0, sensor_range_km=15.0,
        base_supply_days=3, supply_unlimited=False, signature="LOW",
        can_assault=False, can_defend=True, can_resupply_others=False,
    )

TEMPLATES: dict[str, UnitTemplate] = {
    "MNV-001": _mnv("MNV-001", Affiliation.BLUE),
    "MNV-002": _mnv("MNV-002", Affiliation.BLUE),
    "FRS-001": _frs("FRS-001", Affiliation.BLUE),
    "ENB-001": _enb("ENB-001", Affiliation.BLUE),
    "MNV-006": _mnv("MNV-006", Affiliation.RED_RU),
    "MNV-005": _mnv("MNV-005", Affiliation.RED_RU),
    "FRS-007": _frs("FRS-007", Affiliation.RED_RU),
    "ENB-009": _enb("ENB-009", Affiliation.RED_RU),
    # generic fallback used by generated worlds
    "GEN-MNV": _mnv("GEN-MNV", Affiliation.BLUE),
}

KM_PER_CELL = 5.0
TURNS_TOTAL = 10

# ── decision → MissionOrders ──────────────────────────────────────────────

_DECISION_LABELS = {
    "hold":           "HOLD FORWARD",
    "reorient_fires": "REORIENT FIRES",
    "commit_reserve": "COMMIT RESERVE",
    "withdraw":       "WITHDRAW LOCALLY",
    "advance":        "ADVANCE",
    "strike":         "STRIKE",
}

def _blue_orders(world: WorldState, decision_key: str) -> list[MissionOrder]:
    blue_units = world.alive_units_of_side(Side.BLUE)
    mnv_ids  = tuple(u.unit_id for u in blue_units if "MNV" in u.template_id)
    frs_ids  = tuple(u.unit_id for u in blue_units if "FRS" in u.template_id)
    all_ids  = tuple(u.unit_id for u in blue_units)

    orders: list[MissionOrder] = []

    if decision_key == "hold":
        if all_ids:
            orders.append(MissionOrder(
                order_id="B-HOLD", side=Side.BLUE, group_id="BLUE-ALL",
                unit_ids=all_ids, mission=MissionType.HOLD, priority=1,
            ))

    elif decision_key == "reorient_fires":
        if frs_ids:
            orders.append(MissionOrder(
                order_id="B-SUPPRESS", side=Side.BLUE, group_id="BLUE-FIRES",
                unit_ids=frs_ids, mission=MissionType.SUPPRESS, priority=2,
            ))
        if mnv_ids:
            orders.append(MissionOrder(
                order_id="B-HOLD-MNV", side=Side.BLUE, group_id="BLUE-MNV",
                unit_ids=mnv_ids, mission=MissionType.HOLD, priority=1,
            ))

    elif decision_key == "commit_reserve":
        if mnv_ids:
            orders.append(MissionOrder(
                order_id="B-ASSAULT", side=Side.BLUE, group_id="BLUE-MNV",
                unit_ids=mnv_ids, mission=MissionType.ASSAULT, priority=2,
            ))

    elif decision_key == "withdraw":
        if all_ids:
            orders.append(MissionOrder(
                order_id="B-WITHDRAW", side=Side.BLUE, group_id="BLUE-ALL",
                unit_ids=all_ids, mission=MissionType.WITHDRAW, priority=1,
            ))

    elif decision_key in ("advance", "strike"):
        if mnv_ids:
            orders.append(MissionOrder(
                order_id="B-ADVANCE", side=Side.BLUE, group_id="BLUE-MNV",
                unit_ids=mnv_ids, mission=MissionType.ADVANCE, priority=2,
            ))
        if frs_ids:
            orders.append(MissionOrder(
                order_id="B-SUPPRESS2", side=Side.BLUE, group_id="BLUE-FIRES",
                unit_ids=frs_ids, mission=MissionType.SUPPRESS, priority=1,
            ))

    return orders


def _red_orders(world: WorldState) -> list[MissionOrder]:
    """RED heuristic: advance to contact, then assault through BLUE positions."""
    red_units  = world.alive_units_of_side(Side.RED)
    blue_units = world.alive_units_of_side(Side.BLUE)
    mnv_units  = [u for u in red_units if "MNV" in u.template_id]
    frs_ids    = tuple(u.unit_id for u in red_units if "FRS" in u.template_id)

    def in_contact(u) -> bool:
        return any(chebyshev_distance(u.position, b.position) <= 3 for b in blue_units)

    assault_ids = tuple(u.unit_id for u in mnv_units if     in_contact(u))
    advance_ids = tuple(u.unit_id for u in mnv_units if not in_contact(u))

    orders: list[MissionOrder] = []
    if assault_ids:
        orders.append(MissionOrder(
            order_id="R-ASSAULT", side=Side.RED, group_id="RED-MNV",
            unit_ids=assault_ids, mission=MissionType.ASSAULT, priority=3,
        ))
    if advance_ids:
        orders.append(MissionOrder(
            order_id="R-ADVANCE", side=Side.RED, group_id="RED-MNV-ADV",
            unit_ids=advance_ids, mission=MissionType.ADVANCE, priority=2,
        ))
    if frs_ids:
        orders.append(MissionOrder(
            order_id="R-SUPPRESS", side=Side.RED, group_id="RED-FIRES",
            unit_ids=frs_ids, mission=MissionType.SUPPRESS, priority=1,
        ))
    return orders

# ── WorldState → frontend GameState ──────────────────────────────────────

_PENDING_OPTIONS = [
    {"key": "hold",           "label": "HOLD FORWARD",      "sub_label": "Maintain current positions",         "consequence_hint": "Preserves terrain, accepts attrition"},
    {"key": "reorient_fires", "label": "REORIENT FIRES",    "sub_label": "Mass fires at canalization point",    "consequence_hint": "Disrupts RED tempo on confirmed axis"},
    {"key": "commit_reserve", "label": "COMMIT RESERVE",    "sub_label": "Commit maneuver element forward",     "consequence_hint": "Gains ground, exposes flank"},
    {"key": "withdraw",       "label": "WITHDRAW LOCALLY",  "sub_label": "Fall back to prepared defensive line","consequence_hint": "Preserves combat power, cedes terrain"},
]

def _cp(units: list[UnitState]) -> int:
    """Combat power = average effective combat factor of maneuver units only.
    Returns 0 if no maneuver units remain (fires/recon in the rear don't count).
    """
    if not units:
        return 0
    mnv = [u for u in units if "MNV" in u.template_id]
    if not mnv:
        return 0
    return max(1, int(mean(u.strength for u in mnv) * 100))

def _penetration_km(world: WorldState) -> float:
    """How far RED's deepest MNV unit has pushed past the forward edge (col 6).

    Col 6 sits two cells in front of Daugavpils (col 4), so reaching the city
    registers as ~10 km and a true rear-area breakthrough registers as 20+ km.
    Using MNV units only — fires/recon stay in the rear and should not skew the metric.
    """
    red = world.alive_units_of_side(Side.RED)
    mnv = [u for u in red if "MNV" in u.template_id]
    units_to_measure = mnv if mnv else red
    if not units_to_measure:
        return 0.0
    min_col = min(u.position[1] for u in units_to_measure)
    return max(0.0, (6 - min_col) * KM_PER_CELL)

def _unit_to_dict(u: UnitState) -> dict:
    return {
        "designation": u.unit_id,
        "type": u.template_id,
        "equipment": u.readiness.value,
        "location": f"({u.position[0]},{u.position[1]})",
        "notes": f"str={u.strength:.2f}",
    }

def _narrative_from_events(events: list) -> str:
    lines = []
    for e in events:
        if hasattr(e, "narrative") and e.narrative:
            lines.append(e.narrative)
    if not lines:
        return "No significant activity this turn."
    # Keep the most interesting events — combat + moves, skip turn_advanced
    from kriegsspiel.engine.enums import EventType
    important = [e for e in events if e.event_type in (
        EventType.COMBAT_RESOLVED, EventType.UNIT_DESTROYED,
        EventType.OBJECTIVE_TAKEN, EventType.UNIT_SUPPRESSED,
        EventType.UNIT_MOVED,
    )]
    if not important:
        return lines[-1]
    return " | ".join(e.narrative for e in important[:4])

def _evaluate_outcome(
    world: WorldState, blue_cp: int, red_cp: int, pen_km: float
) -> tuple[str | None, bool]:
    """Return (outcome_label, game_ended).

    outcome_label is None while the game is still in progress.
    RED wins on any of its conditions being met mid-game; BLUE wins only at
    end-of-scenario if all holding conditions are satisfied.
    """
    daugavpils = world.objectives.get("OBJ-DAUGAVPILS")
    daugavpils_held_blue = daugavpils is not None and daugavpils.held_by == Side.BLUE

    # Immediate RED-win triggers
    if blue_cp <= 0:
        return "red_win", True
    if pen_km >= 20.0:
        return "red_win", True
    if daugavpils is not None and daugavpils.held_by == Side.RED:
        return "red_win", True

    # RED maneuver power exhausted — BLUE has successfully defended
    if red_cp <= 0:
        return "blue_win", True

    # End of scenario
    if world.turn >= TURNS_TOTAL:
        if daugavpils_held_blue and pen_km < 20.0 and blue_cp > 30:
            return "blue_win", True
        elif not daugavpils_held_blue or pen_km >= 20.0 or blue_cp <= 30:
            return "red_win", True
        else:
            return "draw", True

    return None, False


def _build_aar(blue_cp: int, red_cp: int, pen_km: float, turns: int, outcome: str) -> dict:
    _SUMMARIES = {
        "blue_win": f"Blue held. Penetration contained at {pen_km:.1f} km.",
        "red_win":  f"Red achieved penetration of {pen_km:.1f} km. Blue combat power degraded.",
        "draw":     f"Inconclusive. Penetration {pen_km:.1f} km. No side met full objectives.",
    }
    blue_conditions = 3 if outcome == "blue_win" else (2 if outcome == "draw" else 1)
    red_conditions  = 3 if outcome == "red_win"  else (2 if outcome == "draw" else 1)
    return {
        "outcome": {
            "label":              outcome,
            "summary":            _SUMMARIES.get(outcome, ""),
            "blue_cp_final":      blue_cp,
            "red_cp_final":       red_cp,
            "max_penetration_km": pen_km,
            "turns_played":       turns,
            "blue_conditions_met": blue_conditions,
            "red_conditions_met":  red_conditions,
            "conditions_total":    4,
        },
        "key_turns": list(range(max(1, turns - 2), turns + 1)),
        "lessons": [
            {"category": "tactical",    "text": "Terrain canalization proved decisive on primary axis."},
            {"category": "operational", "text": "Fires reorientation was the key inflection point."},
            {"category": "doctrinal",   "text": "Decision quality tracked FM 3-90 trade-space framework."},
        ],
        "recommendations": [
            {"text": "Re-run with RED reserves committed at T+0."},
            {"text": "Add alternate fires posture to stress-test BLUE combat power floor."},
        ],
        "doctrine_citations": [
            {"text": "Defending forces canalize the attacker into restrictive terrain.",
             "source": "FM 3-90 §3.4", "relevance": "primary lesson"},
        ],
        "generated_in_seconds": 0.1,
    }

def _world_to_game_state(session: Session) -> dict:
    world = session.world
    blue = world.alive_units_of_side(Side.BLUE)
    red  = world.alive_units_of_side(Side.RED)
    blue_cp = _cp(blue)
    red_cp  = _cp(red)
    pen_km  = _penetration_km(world)

    outcome, ended = _evaluate_outcome(world, blue_cp, red_cp, pen_km)

    return {
        "scenario_id":       session.scenario_id,
        "run_id":            session.run_id,
        "status":            "ended" if ended else "running",
        "outcome":           outcome,
        "current_turn":      world.turn,
        "next_checkin_iso":  None,
        "blue_force": {
            "side": "blue",
            "name": "NATO Task Force Baltic",
            "units": [_unit_to_dict(u) for u in blue],
            "combat_power": blue_cp,
        },
        "red_force": {
            "side": "red",
            "name": "RF 1st Guards Tank Army",
            "units": [_unit_to_dict(u) for u in red],
            "combat_power": red_cp,
        },
        "max_penetration_km": pen_km,
        "turn_log":          session.turn_log,
        "pending_decision": None if ended else {
            "turn":    world.turn + 1,
            "context": f"Turn {world.turn + 1} — BLUE CP: {blue_cp}  RED CP: {red_cp}  Penetration: {pen_km:.1f} km",
            "options": _PENDING_OPTIONS,
        },
        "aar": _build_aar(blue_cp, red_cp, pen_km, world.turn, outcome) if ended else None,
    }

# ── static scenario payload ───────────────────────────────────────────────

def _latgale_scenario(run_id: str = "latgale-static") -> dict:
    return {
        "id": "latgale_2027",
        "name": "IRON CORRIDOR — Latgale 2027",
        "classification": "UNCLASSIFIED // FOR TRAINING ONLY",
        "threat_tier": "peer",
        "scenario_type": "LAND",
        "strategic_objective": "RESOURCE_CONTROL",
        "summary": (
            "Russian forces mass on the Latvian border. "
            "NATO Task Force Baltic must hold the Daugavpils corridor and deny "
            "a fait accompli before Article 5 consultation completes."
        ),
        "timeline_hours": 60,
        "turns_total": TURNS_TOTAL,
        "location": {
            "name": "Latgale Region",
            "region": "Eastern Latvia",
            "country": "Latvia",
            "bbox": [26.5, 55.8, 28.2, 56.9],
            "key_routes": ["A6 Riga–Daugavpils", "E262 Rezekne axis"],
            "terrain_notes": "Forested lakeland with restrictive mobility corridors.",
            "pop_centers": ["Daugavpils", "Rezekne", "Kraslava"],
        },
        "nodes": {
            "blue_land_entry":  "RIGA CORRIDOR",
            "blue_sea_entry":   "GULF OF RIGA",
            "red_land_entry":   "PSKOV OBLAST",
            "red_sea_entry":    "NONE",
            "contested_nodes":  ["REZEKNE", "KRASLAVA"],
            "objective_node":   "DAUGAVPILS",
        },
        "blue_force": {
            "side": "blue",
            "name": "NATO Task Force Baltic",
            "units": [
                {"designation": "BLUE-MNV-001-A", "type": "Mechanised Bn",   "equipment": "CV90",         "location": "Rezekne",    "notes": "dug in"},
                {"designation": "BLUE-MNV-002-A", "type": "Armoured Bn",     "equipment": "Leopard 2A6",  "location": "Daugavpils", "notes": "dug in"},
                {"designation": "BLUE-FRS-001-A", "type": "Artillery Bn",    "equipment": "M109A7",       "location": "Fwd OP",     "notes": ""},
                {"designation": "BLUE-ENB-001-A", "type": "Recon Coy",       "equipment": "Mixed",        "location": "Screening",  "notes": "supply unlimited"},
            ],
            "combat_power": 100,
        },
        "red_force": {
            "side": "red",
            "name": "RF 1st Guards Tank Army",
            "units": [
                {"designation": "RED-MNV-006-A", "type": "Tank Bn",          "equipment": "T-90M",        "location": "Pskov axis", "notes": "offensive"},
                {"designation": "RED-MNV-005-A", "type": "Motor Rifle Bn",   "equipment": "BMP-3",        "location": "South axis", "notes": "offensive"},
                {"designation": "RED-FRS-007-A", "type": "MLRS Bn",          "equipment": "BM-21",        "location": "Rear OP",    "notes": ""},
                {"designation": "RED-ENB-009-A", "type": "Recon Coy",        "equipment": "Mixed",        "location": "Screening",  "notes": "supply unlimited"},
            ],
            "combat_power": 100,
        },
        "blue_resources": {
            "dollars_millions": 800, "income_per_turn_millions": 0,
            "supply_chain": 85, "stability": 90, "intel": 70,
        },
        "red_resources": {
            "dollars_millions": 1200, "income_per_turn_millions": 0,
            "supply_chain": 70, "stability": 75, "intel": 60,
        },
        "victory_conditions": {
            "blue": [
                "Daugavpils held at end of scenario",
                "RED penetration < 20 km",
                "BLUE combat power > 30% at end",
                "Article 5 consultation completes (turn 10)",
            ],
            "red": [
                "Daugavpils seized by turn 6",
                "RED penetration > 20 km",
                "BLUE combat power < 30% at any point",
                "Fait accompli before Article 5 trigger",
            ],
        },
        "available_modifiers": [],
        "active_modifier_keys": [],
        "budget": {"label": "NATO Defence Fund", "total": 800, "remaining": 800, "unit": "$M"},
        "seed_events": [
            {"date": "2027-02-14", "description": "RF force concentration detected near Pskov.", "source": "NATO SIGINT", "source_id": "NI-2027-0041"},
            {"date": "2027-02-28", "description": "Latvian government declares state of emergency.", "source": "LVA Govt", "source_id": "LVA-27-009"},
        ],
        "doctrine_citations": [
            {"text": "Defending forces canalize the attacker into restrictive terrain to mass fires at decisive points.", "source": "FM 3-90 §3.4", "relevance": "core defensive concept"},
        ],
        "generated_at": "2027-03-01T06:00:00Z",
        "generated_in_seconds": 0.1,
        "run_id": run_id,
    }

# ── request/response models ───────────────────────────────────────────────

class ScenarioConfig(BaseModel):
    base_scenario_id: str
    label_override: str = ""

class DecideRequest(BaseModel):
    decision_key: str
    note: str = ""

class SimulateRequest(BaseModel):
    turns: int = 5
    blue_strategy: str = "hold"   # any valid decision_key

# ── routes ────────────────────────────────────────────────────────────────

@app.get("/health")
def health() -> dict:
    return {"status": "ok", "engine": "omnissiah-v0.1"}


@app.get("/scenarios")
def list_scenarios() -> list[dict]:
    return [_latgale_scenario()]


@app.post("/game/start")
def start_game(config: ScenarioConfig) -> dict:
    run_id = str(uuid.uuid4())[:8].upper()
    world  = build_latgale_world(run_id=run_id)

    session = Session(world=world, run_id=run_id, scenario_id=config.base_scenario_id)
    _sessions[run_id] = session

    gs = _world_to_game_state(session)
    # Override name if label provided
    if config.label_override:
        gs["scenario_id"] = config.label_override
    return gs


@app.post("/game/{run_id}/decide")
def decide(run_id: str, body: DecideRequest) -> dict:
    session = _sessions.get(run_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Run {run_id!r} not found.")

    world = session.world
    if world.turn >= TURNS_TOTAL:
        raise HTTPException(status_code=400, detail="Game already ended.")

    # Build orders
    blue_orders = _blue_orders(world, body.decision_key)
    red_orders  = _red_orders(world)
    all_orders  = blue_orders + red_orders

    # Resolve
    new_world, events = advance_timestep(
        world, TEMPLATES, all_orders, km_per_cell=KM_PER_CELL
    )

    # Build turn record
    blue_after = _cp(new_world.alive_units_of_side(Side.BLUE))
    red_after  = _cp(new_world.alive_units_of_side(Side.RED))
    pen_after  = _penetration_km(new_world)

    red_label = "ADVANCE ON ALL AXES" if any(o.mission == MissionType.ADVANCE for o in red_orders) else "HOLD"

    turn_record = {
        "turn":                  world.turn + 1,
        "elapsed_hours":         (world.turn + 1) * 6,
        "blue_action_key":       body.decision_key,
        "blue_action_label":     _DECISION_LABELS.get(body.decision_key, body.decision_key.upper()),
        "blue_note":             body.note,
        "red_action_label":      red_label,
        "narrative":             _narrative_from_events(events),
        "blue_cp_after":         blue_after,
        "red_cp_after":          red_after,
        "penetration_km_after":  pen_after,
        "doctrine_refs":         [],
    }

    session.world = new_world
    session.turn_log.append(turn_record)

    return _world_to_game_state(session)


def _run_one_turn(session: Session, blue_decision: str) -> None:
    world = session.world
    blue_orders = _blue_orders(world, blue_decision)
    red_orders  = _red_orders(world)
    all_orders  = blue_orders + red_orders

    new_world, events = advance_timestep(
        world, TEMPLATES, all_orders, km_per_cell=KM_PER_CELL
    )

    blue_after = _cp(new_world.alive_units_of_side(Side.BLUE))
    red_after  = _cp(new_world.alive_units_of_side(Side.RED))
    pen_after  = _penetration_km(new_world)
    red_label  = "ADVANCE ON ALL AXES" if any(o.mission == MissionType.ADVANCE for o in red_orders) else "HOLD"

    session.turn_log.append({
        "turn":                  world.turn + 1,
        "elapsed_hours":         (world.turn + 1) * 6,
        "blue_action_key":       blue_decision,
        "blue_action_label":     _DECISION_LABELS.get(blue_decision, blue_decision.upper()) + " (AUTO)",
        "blue_note":             "auto-sim",
        "red_action_label":      red_label,
        "narrative":             _narrative_from_events(events),
        "blue_cp_after":         blue_after,
        "red_cp_after":          red_after,
        "penetration_km_after":  pen_after,
        "doctrine_refs":         [],
    })
    session.world = new_world


@app.post("/game/{run_id}/simulate")
def simulate(run_id: str, body: SimulateRequest) -> dict:
    """Run N turns on autopilot and return the resulting GameState."""
    session = _sessions.get(run_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Run {run_id!r} not found.")

    blue_decision = body.blue_strategy if body.blue_strategy in _DECISION_LABELS else "hold"
    turns_remaining = TURNS_TOTAL - session.world.turn
    turns_to_run = min(body.turns, turns_remaining)

    if turns_to_run <= 0:
        raise HTTPException(status_code=400, detail="Game already ended.")

    for _ in range(turns_to_run):
        world = session.world
        blue_cp = _cp(world.alive_units_of_side(Side.BLUE))
        red_cp  = _cp(world.alive_units_of_side(Side.RED))
        pen_km  = _penetration_km(world)
        _, already_ended = _evaluate_outcome(world, blue_cp, red_cp, pen_km)
        if already_ended:
            break
        _run_one_turn(session, blue_decision)

    return _world_to_game_state(session)
