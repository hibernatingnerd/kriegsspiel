"""
Pydantic schemas for all API request/response bodies.

UnitOut.position and TurnRecordOut.unit_positions carry [row, col]
coordinates so the frontend can render the 2D map without any
extra transformation.
"""

from typing import Optional
from pydantic import BaseModel


# ── Unit & force ──────────────────────────────────────────────────────────────

class UnitOut(BaseModel):
    unit_id:   str
    side:      str              # "BLUE" | "RED"
    unit_type: str              # "MNV" | "FRS" | "ENB"
    position:  list[int]       # [row, col] — primary 2D map input
    strength:  float            # 0.0–1.0
    readiness: str              # FULLY_OPERATIONAL | DEGRADED | SUPPRESSED | DESTROYED
    posture:   str
    dug_in:    bool

class ForceOut(BaseModel):
    side:         str
    combat_power: float         # 0–100, derived from mean unit strength
    units:        list[UnitOut]


# ── Map ───────────────────────────────────────────────────────────────────────

class TerrainCellOut(BaseModel):
    row:     int
    col:     int
    terrain: str    # OPEN | FOREST | WATER | URBAN | IMPASSABLE

class MapOut(BaseModel):
    rows:        int
    cols:        int
    km_per_cell: float
    cells:       list[TerrainCellOut]   # sparse — OPEN cells omitted


# ── Objectives ────────────────────────────────────────────────────────────────

class ObjectiveOut(BaseModel):
    id:            str
    name:          str
    position:      list[int]    # [row, col] — for map markers
    controlled_by: str          # "BLUE" | "RED" | "NEUTRAL"
    weight:        float


# ── Decisions ─────────────────────────────────────────────────────────────────

class DecisionOptionOut(BaseModel):
    key:              str
    label:            str
    consequence_hint: str

class PendingDecisionOut(BaseModel):
    turn:    int
    context: str
    options: list[DecisionOptionOut]


# ── Turn log ──────────────────────────────────────────────────────────────────

class TurnRecordOut(BaseModel):
    turn:           int
    blue_action:    str
    red_action:     str
    narrative:      str
    doctrine_refs:  list[str]
    blue_cp_after:  float
    red_cp_after:   float
    unit_positions: dict[str, list[int]]    # {unit_id: [row, col]} — map replay


# ── Game state ────────────────────────────────────────────────────────────────

class GameStateOut(BaseModel):
    game_id:          str
    scenario:         str
    status:           str   # running | blue_win | red_win
    turn:             int
    turns_total:      int
    blue_force:       ForceOut
    red_force:        ForceOut
    objectives:       list[ObjectiveOut]
    map:              MapOut
    turn_log:         list[TurnRecordOut]
    pending_decision: Optional[PendingDecisionOut]


# ── AAR ───────────────────────────────────────────────────────────────────────

class AAROut(BaseModel):
    game_id:         str
    outcome:         str
    turns_played:    int
    blue_cp_final:   float
    red_cp_final:    float
    objectives_held: list[str]      # objective IDs held by BLUE at end
    turn_log:        list[TurnRecordOut]


# ── Requests ──────────────────────────────────────────────────────────────────

class StartIn(BaseModel):
    scenario: str = "latgale_2027"

class ActionIn(BaseModel):
    decision_key: str
    note: str = ""
