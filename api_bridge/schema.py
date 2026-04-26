"""
API request/response schemas.

Position fields are [row, col] on the engine grid (no transform).
All timing is engine turns; "epoch" = a configurable batch of turns
between BLUE decision points.
"""

from __future__ import annotations

from typing import Literal, Optional
from pydantic import BaseModel, Field


# ── Units & forces ────────────────────────────────────────────────────────────

class UnitOut(BaseModel):
    unit_id:    str
    side:       str                    # BLUE | RED
    unit_type:  str                    # MNV | FRS | ENB | UNK
    template_id:str
    position:   list[int]              # [row, col]
    strength:   float                  # 0.0–1.0
    readiness:  str
    posture:    str
    dug_in:     bool
    is_alive:   bool


class ForceOut(BaseModel):
    side:         str
    combat_power: float                # 0–100
    units:        list[UnitOut]


# ── Map & objectives ──────────────────────────────────────────────────────────

class TerrainCellOut(BaseModel):
    row:     int
    col:     int
    terrain: str                       # FOREST | WATER | URBAN | IMPASSABLE | ...


class MapOut(BaseModel):
    rows:        int
    cols:        int
    km_per_cell: float
    cells:       list[TerrainCellOut]  # sparse; OPEN omitted


class ObjectiveOut(BaseModel):
    id:            str
    name:          str
    position:      list[int]
    controlled_by: str                 # BLUE | RED | NEUTRAL
    weight:        float


# ── Orders (BLUE input) ───────────────────────────────────────────────────────
# Per-unit, mirrors the engine's native unit_decision_list shape.

ActionLiteral = Literal["WAIT", "ATTACK", "MOVE"]

class UnitOrderIn(BaseModel):
    unit_id:         str
    action:          ActionLiteral = "WAIT"
    target_id:       Optional[str] = None       # required for ATTACK
    target_position: Optional[list[int]] = None # required for MOVE


class OrdersIn(BaseModel):
    orders: list[UnitOrderIn]
    note:   str = ""


# ── Orders template (what BLUE can do this epoch) ─────────────────────────────

class UnitOrderOption(BaseModel):
    unit_id:           str
    can_wait:          bool = True
    can_attack:        bool
    can_move:          bool
    valid_attack_ids:  list[str] = Field(default_factory=list)
    # MOVE target enumeration deferred until engine exposes movement


class OrdersTemplateOut(BaseModel):
    epoch:        int
    turn:         int
    units:        list[UnitOrderOption]


# ── Turn log ──────────────────────────────────────────────────────────────────

class TurnRecordOut(BaseModel):
    turn:           int
    blue_action:    str                # short label, e.g. "ATTACK x3, WAIT x1"
    red_action:     str                # short label
    note:           str
    narrative:      str                # filled by adjudicator later
    doctrine_refs:  list[str]
    blue_cp_after:  float
    red_cp_after:   float
    destroyed:      list[str]          # unit_ids destroyed this turn
    skipped:        list[dict]         # [{unit_id, reason}, ...] — illegal/no-op orders
    unit_positions: dict[str, list[int]]


class EpochRecordOut(BaseModel):
    epoch:        int
    turn_start:   int
    turn_end:     int
    note:         str
    turns:        list[TurnRecordOut]


# ── Game state envelope ───────────────────────────────────────────────────────

GameStatus = Literal["awaiting_orders", "running", "ended"]

class GameStateOut(BaseModel):
    game_id:           str
    scenario:          str
    status:            GameStatus
    outcome:           str                       # running | blue_win | red_win
    turn:              int                       # current engine turn
    turns_total:       int
    epoch:             int                       # current epoch index
    epoch_size:        int                       # turns per epoch
    next_epoch_at_turn:int                       # bridge will pause here
    blue_force:        ForceOut
    red_force:         ForceOut
    objectives:        list[ObjectiveOut]
    map:               MapOut                    # static; same each call
    epoch_log:         list[EpochRecordOut]
    pending_orders:    Optional[OrdersTemplateOut]  # null when status != awaiting_orders


# ── AAR ───────────────────────────────────────────────────────────────────────

class AAROut(BaseModel):
    game_id:         str
    outcome:         str
    turns_played:    int
    epochs_played:   int
    blue_cp_final:   float
    red_cp_final:    float
    objectives_held: list[str]
    epoch_log:       list[EpochRecordOut]


# ── Game creation ─────────────────────────────────────────────────────────────

class CreateGameIn(BaseModel):
    scenario:    str = "latgale_2027"
    epoch_size:  int = Field(default=2, ge=1, le=20)   # engine turns per epoch
    turns_total: int = Field(default=10, ge=1, le=200)
    seed:        Optional[int] = None
