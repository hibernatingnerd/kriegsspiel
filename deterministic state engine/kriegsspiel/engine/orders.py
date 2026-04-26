"""Mission orders and unit groups.

The interface between the LLM (intent) and the Omnissiah (execution).
The LLM never moves individual units; it issues MissionOrders to groups.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from .enums import Side
from .state import Coord


class MissionType(str, Enum):
    ADVANCE  = "ADVANCE"   # Move toward target; engage enemies en route
    ASSAULT  = "ASSAULT"   # Close with and destroy a specific enemy position
    SUPPRESS = "SUPPRESS"  # Pin enemy with fires; hold ground
    WITHDRAW = "WITHDRAW"  # Break contact; move to rear
    HOLD     = "HOLD"      # Defend current position; dig in
    RECON    = "RECON"     # Observe and report; avoid decisive engagement


class MissionOrder(BaseModel):
    """A single LLM directive — group-level intent, not a unit move.

    The Omnissiah expands this into per-unit actions.
    """
    model_config = ConfigDict(frozen=True)

    order_id: str
    side: Side
    group_id: str
    unit_ids: tuple[str, ...]          # units assigned to this order
    mission: MissionType
    target_coord: Optional[Coord] = None  # objective cell; None → heuristic
    priority: int = Field(default=0, ge=0)  # higher resolved first


class UnitGroup(BaseModel):
    """Named grouping for display and tracking purposes."""
    model_config = ConfigDict(frozen=True)

    group_id: str
    side: Side
    label: str                    # e.g. "Northern Battlegroup"
    unit_ids: tuple[str, ...]
