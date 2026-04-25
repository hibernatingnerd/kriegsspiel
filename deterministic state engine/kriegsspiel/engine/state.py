"""World-state models and invariants for deterministic simulation."""

from __future__ import annotations

import math
from typing import Any, Iterable, Iterator, Optional

import numpy as np
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .enums import (
    Affiliation,
    Category,
    Domain,
    Posture,
    Readiness,
    Side,
    TerrainBase,
    TerrainFeature,
)

Coord = tuple[int, int]


class WorldStateError(ValueError):
    """Raised by world-level invariant checks."""

    def __init__(self, message: str, *, code: str = "WS_INVARIANT", details: dict | None = None):
        super().__init__(message)
        self.code = code
        self.details = details or {}


class TerrainCell(BaseModel):
    model_config = ConfigDict(frozen=True)

    base: TerrainBase
    features: tuple[TerrainFeature, ...] = ()
    altitude_m: float = 0.0
    slope_deg: float = Field(default=0.0, ge=0.0, le=90.0)
    cover_factor: float = Field(default=0.0, ge=0.0, le=1.0)
    visibility_factor: float = Field(default=1.0, ge=0.0, le=1.0)
    movement_cost_ground: float = Field(default=1.0, ge=0.0)
    supply_throughput: float = Field(default=1.0, ge=0.0, le=10.0)
    strategic_weight: float = Field(default=0.0, ge=0.0)

    @model_validator(mode="after")
    def _check_feature_base_coherence(self) -> TerrainCell:
        urban_only = {TerrainFeature.URBAN_DENSE, TerrainFeature.URBAN_SPARSE}
        if any(f in urban_only for f in self.features) and self.base != TerrainBase.URBAN:
            raise ValueError(
                "URBAN_DENSE/URBAN_SPARSE features require base=URBAN; "
                f"got base={self.base.value}"
            )
        if TerrainFeature.OBJECTIVE in self.features and self.strategic_weight <= 0.0:
            raise ValueError("TerrainCell with OBJECTIVE feature must have strategic_weight > 0")
        if self.base == TerrainBase.IMPASSABLE and self.movement_cost_ground < 999.0:
            raise ValueError("TerrainBase.IMPASSABLE requires movement_cost_ground >= 999.0")
        return self


class RiverCrossing(BaseModel):
    model_config = ConfigDict(frozen=False)

    crossing_id: str
    cell_a: Coord
    cell_b: Coord
    crossing_type: str = Field(pattern="^(BRIDGE|FORD|FERRY|ENGINEER_TEMP)$")
    capacity_per_turn: int = Field(default=1, ge=0)
    integrity: str = Field(default="INTACT", pattern="^(INTACT|DAMAGED|DESTROYED)$")
    controlled_by: Side = Side.NEUTRAL

    @model_validator(mode="after")
    def _cells_must_be_adjacent(self) -> RiverCrossing:
        if self.cell_a == self.cell_b:
            raise ValueError(f"crossing {self.crossing_id} connects a cell to itself")
        dr = abs(self.cell_a[0] - self.cell_b[0])
        dc = abs(self.cell_a[1] - self.cell_b[1])
        if max(dr, dc) != 1:
            raise ValueError(
                f"crossing {self.crossing_id}: cells {self.cell_a} and "
                f"{self.cell_b} are not adjacent (Chebyshev distance {max(dr, dc)})"
            )
        return self


class TerrainGrid(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    height: int = Field(ge=1)
    width: int = Field(ge=1)
    cells: list[list[TerrainCell]]
    crossings: list[RiverCrossing] = Field(default_factory=list)

    _movement_cost_ground: np.ndarray = None  # type: ignore[assignment]
    _passable_ground: np.ndarray = None  # type: ignore[assignment]
    _crossing_lookup: dict[tuple[Coord, Coord], RiverCrossing] = None  # type: ignore[assignment]

    @field_validator("cells")
    @classmethod
    def _check_rectangular(cls, v: list[list[TerrainCell]]) -> list[list[TerrainCell]]:
        if not v:
            raise ValueError("terrain grid must have at least one row")
        w = len(v[0])
        for i, row in enumerate(v):
            if len(row) != w:
                raise ValueError(f"row {i} has width {len(row)}, expected {w}")
        return v

    def model_post_init(self, __context) -> None:
        h, w = self.height, self.width
        if len(self.cells) != h or len(self.cells[0]) != w:
            raise ValueError(
                f"cells shape {(len(self.cells), len(self.cells[0]))} "
                f"does not match declared ({h}, {w})"
            )

        self._movement_cost_ground = np.array(
            [[c.movement_cost_ground for c in row] for row in self.cells],
            dtype=np.float32,
        )
        impassable_bases = {TerrainBase.WATER, TerrainBase.IMPASSABLE}
        self._passable_ground = np.array(
            [[(c.base not in impassable_bases) and (c.movement_cost_ground < 999.0) for c in row] for row in self.cells],
            dtype=bool,
        )

        self._crossing_lookup = {}
        for x in self.crossings:
            for cell in (x.cell_a, x.cell_b):
                if not self.in_bounds(cell):
                    raise ValueError(
                        f"crossing {x.crossing_id} references out-of-bounds cell {cell} "
                        f"(grid is {h}x{w})"
                    )
            self._crossing_lookup[(x.cell_a, x.cell_b)] = x
            self._crossing_lookup[(x.cell_b, x.cell_a)] = x

    def in_bounds(self, coord: Coord) -> bool:
        r, c = coord
        return 0 <= r < self.height and 0 <= c < self.width

    def cell_at(self, coord: Coord) -> TerrainCell:
        r, c = coord
        return self.cells[r][c]

    def is_passable_ground(self, coord: Coord) -> bool:
        r, c = coord
        return bool(self._passable_ground[r, c])

    def movement_cost(self, coord: Coord) -> float:
        r, c = coord
        return float(self._movement_cost_ground[r, c])

    def has_feature(self, coord: Coord, feature: TerrainFeature) -> bool:
        return feature in self.cell_at(coord).features

    def crossing_between(self, a: Coord, b: Coord) -> Optional[RiverCrossing]:
        return self._crossing_lookup.get((a, b))

    def neighbors_8(self, coord: Coord) -> Iterator[Coord]:
        r, c = coord
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                n = (r + dr, c + dc)
                if self.in_bounds(n):
                    yield n


def chebyshev_distance(a: Coord, b: Coord) -> int:
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def euclidean_distance(a: Coord, b: Coord) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _map_v3_category_to_legacy(cat: Category) -> Category:
    """Fallback canonical bucketing for legacy engine checks."""
    if cat in {Category.SUSTAINMENT, Category.TRANSPORT, Category.MARITIME_CARGO}:
        return Category.SUSTAINMENT
    if cat in {Category.AIR_DEFENSE}:
        return Category.AIR_DEFENSE
    if cat in {Category.ENABLER, Category.SPECIAL}:
        return Category.ENABLER
    if cat in {Category.FIRES, Category.ARTILLERY}:
        return Category.FIRES
    return Category.MANEUVER


class UnitTemplate(BaseModel):
    """Template compatible with both legacy and V3 unit-library schema."""

    model_config = ConfigDict(frozen=True)

    template_id: str
    name: str
    type: str
    category: Category
    domain: Domain
    affiliation: Affiliation
    echelon_canonical: str
    base_personnel: int = Field(ge=1)
    base_combat_power: int = Field(ge=0, le=100)
    offensive_rating: int = Field(ge=0, le=100)
    defensive_rating: int = Field(ge=0, le=100)
    speed_road: float = Field(ge=0)
    speed_offroad: float = Field(ge=0)
    operational_radius_km: float = Field(ge=0)
    fires_range_km: float = Field(default=0.0, ge=0)
    sensor_range_km: float = Field(default=0.0, ge=0)
    base_supply_days: int = Field(ge=0)
    supply_unlimited: bool = False
    signature: str
    can_assault: bool = True
    can_defend: bool = True
    can_resupply_others: bool = False
    # Keep V3 raw components for economics/gameplay layer.
    cost: dict[str, Any] | None = None
    maneuver: dict[str, Any] | None = None
    attack: dict[str, Any] | None = None
    detect: dict[str, Any] | None = None
    health: dict[str, Any] | None = None
    special_effect: dict[str, Any] | None = None

    @model_validator(mode="before")
    @classmethod
    def _normalize_v3_payload(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        # If this already looks like normalized engine schema, leave it.
        if "template_id" in data and "category" in data and "domain" in data:
            return data

        # V3 schema normalization.
        v = dict(data)
        maneuver = v.get("maneuver") or {}
        attack = v.get("attack") or {}
        detect = v.get("detect") or {}
        health = v.get("health") or {}
        cat_raw = v.get("category", "MANEUVER")
        dom_raw = maneuver.get("type", "LAND")

        v.setdefault("template_id", v.get("id", "UNKNOWN"))
        v.setdefault("type", v.get("category", "GENERIC"))
        v.setdefault("category", cat_raw)
        v.setdefault("domain", dom_raw)
        v.setdefault("echelon_canonical", "UNIT")
        v.setdefault("base_personnel", 1)
        v.setdefault("base_combat_power", int(attack.get("power", 0)))
        v.setdefault("offensive_rating", int(attack.get("power", 0)))
        v.setdefault("defensive_rating", int(health.get("armor", 0)))
        speed = float(maneuver.get("speed_per_turn_km", 0))
        v.setdefault("speed_road", speed)
        v.setdefault("speed_offroad", speed)
        v.setdefault("operational_radius_km", float(maneuver.get("operational_radius_km", 0)))
        v.setdefault("fires_range_km", float(attack.get("range_km", 0)))
        v.setdefault("sensor_range_km", float(detect.get("sensor_range_km", 0)))
        v.setdefault("base_supply_days", 0)
        v.setdefault("supply_unlimited", False)
        v.setdefault("signature", str(health.get("signature", "MEDIUM")))
        v.setdefault("can_assault", int(attack.get("power", 0)) > 0)
        v.setdefault("can_defend", int(health.get("armor", 0)) > 0)
        v.setdefault(
            "can_resupply_others",
            cat_raw in {"SUSTAINMENT", "TRANSPORT", "MARITIME_CARGO"},
        )
        return v

    @model_validator(mode="after")
    def _capability_coherence(self) -> UnitTemplate:
        if self.offensive_rating == 0 and self.can_assault:
            raise ValueError(
                f"template {self.template_id}: offensive_rating=0 implies can_assault=False"
            )
        if self.defensive_rating == 0 and self.can_defend:
            raise ValueError(
                f"template {self.template_id}: defensive_rating=0 implies can_defend=False"
            )
        legacy_bucket = _map_v3_category_to_legacy(self.category)
        if self.can_resupply_others and legacy_bucket != Category.SUSTAINMENT:
            raise ValueError(
                f"template {self.template_id}: can_resupply_others=True "
                f"requires SUSTAINMENT-style category (got {self.category.value})"
            )
        return self


class UnitState(BaseModel):
    model_config = ConfigDict(frozen=False)

    unit_id: str
    template_id: str
    side: Side
    affiliation: Affiliation
    position: Coord
    strength: float = Field(default=1.0, ge=0.0, le=1.0)
    readiness: Readiness = Readiness.FULLY_OPERATIONAL
    supply_days_remaining: Optional[float] = Field(default=None)
    posture: Posture = Posture.DEFENSIVE
    dug_in: bool = False
    turns_isolated: int = Field(default=0, ge=0)
    notes: str = ""

    @field_validator("supply_days_remaining")
    @classmethod
    def _supply_nonneg(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v < 0:
            raise ValueError(f"supply_days_remaining must be >= 0 or None, got {v}")
        return v

    @model_validator(mode="after")
    def _coherence(self) -> UnitState:
        if self.readiness == Readiness.DESTROYED and self.strength > 0.0:
            raise ValueError(
                f"unit {self.unit_id}: readiness=DESTROYED requires strength=0.0 "
                f"(got {self.strength})"
            )
        if self.dug_in and self.posture == Posture.MOVING:
            raise ValueError(
                f"unit {self.unit_id}: cannot be dug_in while MOVING"
            )
        if self.side == Side.BLUE and self.affiliation != Affiliation.BLUE:
            raise ValueError(
                f"unit {self.unit_id}: side=BLUE requires affiliation=BLUE "
                f"(got {self.affiliation.value})"
            )
        red_affiliations = {
            Affiliation.RED_RU,
            Affiliation.RED_CN,
            Affiliation.RED_IRR,
            Affiliation.OPFOR,
        }
        if self.side == Side.RED and self.affiliation not in red_affiliations:
            raise ValueError(
                f"unit {self.unit_id}: side=RED requires affiliation in "
                f"{{RED_RU, RED_CN, RED_IRR, OPFOR}} (got {self.affiliation.value})"
            )
        return self

    @property
    def is_alive(self) -> bool:
        return self.readiness != Readiness.DESTROYED

    @property
    def effective_combat_factor(self) -> float:
        readiness_mult = {
            Readiness.FULLY_OPERATIONAL: 1.0,
            Readiness.DEGRADED: 0.7,
            Readiness.SUPPRESSED: 0.4,
            Readiness.DESTROYED: 0.0,
        }[self.readiness]
        return self.strength * readiness_mult


class ControlState(BaseModel):
    model_config = ConfigDict(frozen=False)

    cell: Coord
    controlled_by: Side = Side.NEUTRAL
    persistence_turns: int = Field(default=0, ge=0)
    contender: Optional[Side] = None

    @model_validator(mode="after")
    def _contender_coherence(self) -> ControlState:
        if self.contender is not None and self.contender == self.controlled_by:
            raise ValueError(
                f"cell {self.cell}: contender ({self.contender.value}) "
                f"cannot equal controlled_by ({self.controlled_by.value})"
            )
        return self


class Objective(BaseModel):
    model_config = ConfigDict(frozen=False)

    objective_id: str
    cell: Coord
    name: str
    weight: float = Field(default=1.0, ge=0.0)
    held_by: Side = Side.NEUTRAL
    taken_at_turn: Optional[int] = Field(default=None)

    @model_validator(mode="after")
    def _taken_at_coherence(self) -> Objective:
        if self.held_by == Side.NEUTRAL and self.taken_at_turn is not None:
            raise ValueError(
                f"objective {self.objective_id}: held_by=NEUTRAL but "
                f"taken_at_turn={self.taken_at_turn}"
            )
        if self.held_by != Side.NEUTRAL and self.taken_at_turn is None:
            raise ValueError(
                f"objective {self.objective_id}: held_by={self.held_by.value} "
                "but taken_at_turn is None"
            )
        return self


class RunIdentity(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_id: str
    scenario_id: str
    rulepack_id: str
    engine_version: str
    seed: int = 0
    noise_enabled: bool = False


class WorldState(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    identity: RunIdentity
    turn: int = Field(default=0, ge=0)
    minutes_per_turn: int = Field(default=60, ge=1)
    timestamp_minutes: int = Field(default=0, ge=0)
    terrain: TerrainGrid
    units: dict[str, UnitState]
    control: dict[str, ControlState]
    objectives: dict[str, Objective]
    side_posture: dict[Side, str] = Field(
        default_factory=lambda: {Side.BLUE: "STANDARD", Side.RED: "STANDARD"}
    )

    @staticmethod
    def cell_key(coord: Coord) -> str:
        return f"{coord[0]},{coord[1]}"

    @staticmethod
    def parse_cell_key(key: str) -> Coord:
        r, c = key.split(",")
        return (int(r), int(c))

    def units_at(self, coord: Coord) -> list[UnitState]:
        return [u for u in self.units.values() if u.position == coord]

    def units_of_side(self, side: Side) -> list[UnitState]:
        return [u for u in self.units.values() if u.side == side]

    def alive_units(self) -> list[UnitState]:
        return [u for u in self.units.values() if u.is_alive]

    def alive_units_of_side(self, side: Side) -> list[UnitState]:
        return [u for u in self.alive_units() if u.side == side]

    def control_of(self, coord: Coord) -> Side:
        ctl = self.control.get(self.cell_key(coord))
        return ctl.controlled_by if ctl else Side.NEUTRAL

    def opposing_side(self, side: Side) -> Side:
        if side == Side.BLUE:
            return Side.RED
        if side == Side.RED:
            return Side.BLUE
        return Side.NEUTRAL

    def enemies_adjacent_to(self, unit: UnitState) -> list[UnitState]:
        enemy = self.opposing_side(unit.side)
        adj_cells = set(self.terrain.neighbors_8(unit.position))
        return [
            u for u in self.alive_units()
            if u.side == enemy and u.position in adj_cells
        ]

    def units_within_chebyshev(self, coord: Coord, radius: int) -> list[UnitState]:
        return [
            u for u in self.alive_units()
            if chebyshev_distance(u.position, coord) <= radius
        ]

    def is_supplied(self, unit: UnitState, *, threshold: float = 0.5) -> bool:
        if unit.supply_days_remaining is None:
            return True
        return unit.supply_days_remaining > threshold

    def find_objective_at(self, coord: Coord) -> Optional[Objective]:
        for obj in self.objectives.values():
            if obj.cell == coord:
                return obj
        return None

    def iter_all_cell_keys(self) -> Iterable[str]:
        for r in range(self.terrain.height):
            for c in range(self.terrain.width):
                yield self.cell_key((r, c))


def validate_world_invariants(world: WorldState) -> None:
    terrain = world.terrain

    for u in world.units.values():
        if not terrain.in_bounds(u.position):
            raise WorldStateError(
                f"unit {u.unit_id} at out-of-bounds position {u.position} "
                f"(grid is {terrain.height}x{terrain.width})",
                code="WS_UNIT_OUT_OF_BOUNDS",
                details={"unit_id": u.unit_id, "position": u.position},
            )

    occupancy: dict[tuple[Coord, Side], list[str]] = {}
    for u in world.alive_units():
        key = (u.position, u.side)
        occupancy.setdefault(key, []).append(u.unit_id)
    for (coord, side), unit_ids in occupancy.items():
        if len(unit_ids) > 1:
            raise WorldStateError(
                f"cell {coord} has {len(unit_ids)} {side.value} units "
                f"({unit_ids}); stacking rule violated",
                code="WS_STACKING_VIOLATION",
                details={"cell": coord, "side": side.value, "unit_ids": unit_ids},
            )

    for obj in world.objectives.values():
        if not terrain.in_bounds(obj.cell):
            raise WorldStateError(
                f"objective {obj.objective_id} at out-of-bounds cell {obj.cell}",
                code="WS_OBJECTIVE_OUT_OF_BOUNDS",
                details={"objective_id": obj.objective_id, "cell": obj.cell},
            )
        cell = terrain.cell_at(obj.cell)
        if cell.base == TerrainBase.IMPASSABLE:
            raise WorldStateError(
                f"objective {obj.objective_id} placed on IMPASSABLE cell {obj.cell}",
                code="WS_OBJECTIVE_ON_IMPASSABLE",
                details={"objective_id": obj.objective_id, "cell": obj.cell},
            )

    for key, ctl in world.control.items():
        coord = WorldState.parse_cell_key(key)
        if not terrain.in_bounds(coord):
            raise WorldStateError(
                f"control entry {key} references out-of-bounds cell {coord}",
                code="WS_CONTROL_OUT_OF_BOUNDS",
                details={"cell_key": key, "cell": coord},
            )
        if ctl.cell != coord:
            raise WorldStateError(
                f"control entry key {key} does not match cell field {ctl.cell}",
                code="WS_CONTROL_KEY_MISMATCH",
                details={"cell_key": key, "ctl_cell": ctl.cell},
            )

    for key, u in world.units.items():
        if u.unit_id != key:
            raise WorldStateError(
                f"unit dict key {key!r} does not match unit_id {u.unit_id!r}",
                code="WS_UNIT_KEY_MISMATCH",
                details={"dict_key": key, "unit_id": u.unit_id},
            )

    expected_min = world.turn * world.minutes_per_turn
    if world.timestamp_minutes < expected_min:
        raise WorldStateError(
            f"timestamp_minutes={world.timestamp_minutes} but "
            f"turn*minutes_per_turn={expected_min}; time went backwards",
            code="WS_TIME_REGRESSION",
            details={
                "turn": world.turn,
                "minutes_per_turn": world.minutes_per_turn,
                "timestamp_minutes": world.timestamp_minutes,
            },
        )

    for x in terrain.crossings:
        for cell in (x.cell_a, x.cell_b):
            if not terrain.in_bounds(cell):
                raise WorldStateError(
                    f"crossing {x.crossing_id} references out-of-bounds cell {cell}",
                    code="WS_CROSSING_OUT_OF_BOUNDS",
                    details={"crossing_id": x.crossing_id, "cell": cell},
                )
"""World-state models and invariants for deterministic simulation."""
