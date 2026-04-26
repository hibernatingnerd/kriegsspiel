"""
Session store + epoch state machine.

A Session wraps one WorldState. State machine:

    [created] ──▶ awaiting_orders ──┬─▶ (BLUE submits orders)
                                    │     advance_one_epoch()
                                    │     turn += epoch_size
                                    └─▶ awaiting_orders | ended

Bridge ticks turns synchronously inside POST /games/{id}/orders. No
threads, no background loop — keeps things deterministic and easy to
reason about. If we later want long-running games the loop becomes a
background task; the public surface stays the same.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from . import engine_facade as ef
from .red_ai import red_orders_for_turn
from .schema import (
    AAROut, EpochRecordOut, ForceOut, GameStateOut, MapOut, ObjectiveOut,
    OrdersTemplateOut, TerrainCellOut, TurnRecordOut, UnitOrderIn,
    UnitOrderOption, UnitOut,
)


# ── Session container ─────────────────────────────────────────────────────────

@dataclass
class Session:
    game_id:     str
    scenario:    str
    epoch_size:  int
    turns_total: int
    world:       ef.WorldState
    epoch:       int = 0
    epoch_log:   list[EpochRecordOut] = field(default_factory=list)
    status:      str = "awaiting_orders"   # awaiting_orders | running | ended

    @property
    def next_epoch_at_turn(self) -> int:
        return min(self.world.turn + self.epoch_size, self.turns_total)


_sessions: dict[str, Session] = {}


def all_session_ids() -> list[str]:
    return list(_sessions.keys())

def count() -> int:
    return len(_sessions)

def exists(game_id: str) -> bool:
    return game_id in _sessions

def get(game_id: str) -> Session:
    return _sessions[game_id]


# ── Lifecycle ─────────────────────────────────────────────────────────────────

def create(
    game_id: str,
    scenario: str,
    epoch_size: int,
    turns_total: int,
    seed: Optional[int],
) -> Session:
    world = ef.build_world(scenario, seed=seed)
    sess = Session(
        game_id=game_id,
        scenario=scenario,
        epoch_size=epoch_size,
        turns_total=turns_total,
        world=world,
    )
    _sessions[game_id] = sess
    return sess


# ── Advance one epoch (driven by POST /orders) ────────────────────────────────

def advance_one_epoch(sess: Session, blue_orders: list[UnitOrderIn], note: str) -> EpochRecordOut:
    if sess.status != "awaiting_orders":
        raise ValueError(f"cannot advance: status={sess.status}")

    sess.status = "running"
    sess.epoch += 1
    blue_orders_dict = [o.model_dump() for o in blue_orders]
    turn_records: list[TurnRecordOut] = []
    turn_start = sess.world.turn

    for tick in range(sess.epoch_size):
        if sess.world.turn >= sess.turns_total:
            break

        # BLUE orders are reused unchanged across ticks within the same
        # epoch — that's what "epoch" means: BLUE commits a posture for
        # epoch_size turns, RED reacts each turn.
        red = red_orders_for_turn(sess.world)
        decisions = blue_orders_dict + red

        delta = ef.tick_one_turn(sess.world, decisions)
        turn_records.append(_record_turn(sess, delta, blue_orders_dict, red, note))

    epoch_record = EpochRecordOut(
        epoch=sess.epoch,
        turn_start=turn_start,
        turn_end=sess.world.turn,
        note=note,
        turns=turn_records,
    )
    sess.epoch_log.append(epoch_record)

    sess.status = "ended" if ef.outcome(sess.world, sess.turns_total) != "running" \
                  else "awaiting_orders"
    return epoch_record


def _record_turn(
    sess: Session,
    delta: dict,
    blue_orders: list[dict],
    red_orders: list[dict],
    note: str,
) -> TurnRecordOut:
    return TurnRecordOut(
        turn=sess.world.turn,
        blue_action=_summarize_orders(blue_orders),
        red_action=_summarize_orders(red_orders),
        note=note,
        narrative="",                     # filled by llm_adjudicator (other team)
        doctrine_refs=[],                 # filled by llm_adjudicator
        blue_cp_after=ef.combat_power(sess.world, ef.Side.BLUE),
        red_cp_after=ef.combat_power(sess.world, ef.Side.RED),
        destroyed=delta["destroyed"],
        skipped=delta["skipped"],
        unit_positions={uid: list(u.position) for uid, u in sess.world.units.items()},
    )


def _summarize_orders(orders: list[dict]) -> str:
    counts: dict[str, int] = {}
    for o in orders:
        counts[o["action"]] = counts.get(o["action"], 0) + 1
    return ", ".join(f"{a}×{n}" for a, n in sorted(counts.items())) or "none"


# ── Projections to API shapes ─────────────────────────────────────────────────

def to_game_state(sess: Session) -> GameStateOut:
    return GameStateOut(
        game_id=sess.game_id,
        scenario=sess.scenario,
        status=sess.status,                     # type: ignore[arg-type]
        outcome=ef.outcome(sess.world, sess.turns_total),
        turn=sess.world.turn,
        turns_total=sess.turns_total,
        epoch=sess.epoch,
        epoch_size=sess.epoch_size,
        next_epoch_at_turn=sess.next_epoch_at_turn,
        blue_force=_force(sess, ef.Side.BLUE),
        red_force=_force(sess, ef.Side.RED),
        objectives=_objectives(sess),
        map=_map(sess),
        epoch_log=sess.epoch_log,
        pending_orders=orders_template(sess) if sess.status == "awaiting_orders" else None,
    )


def to_aar(sess: Session) -> AAROut:
    return AAROut(
        game_id=sess.game_id,
        outcome=ef.outcome(sess.world, sess.turns_total),
        turns_played=sess.world.turn,
        epochs_played=sess.epoch,
        blue_cp_final=ef.combat_power(sess.world, ef.Side.BLUE),
        red_cp_final=ef.combat_power(sess.world, ef.Side.RED),
        objectives_held=[
            o.objective_id for o in sess.world.objectives.values()
            if o.held_by == ef.Side.BLUE
        ],
        epoch_log=sess.epoch_log,
    )


def orders_template(sess: Session) -> OrdersTemplateOut:
    visible_red = [
        u for u in ef.units_visible_to(sess.world, ef.Side.BLUE)
        if u.side == ef.Side.RED and u.is_alive
    ]
    blue_alive = [u for u in sess.world.units.values()
                  if u.side == ef.Side.BLUE and u.is_alive]

    options = [
        UnitOrderOption(
            unit_id=u.unit_id,
            can_attack=bool(visible_red),
            can_move=False,                         # engine doesn't move yet
            valid_attack_ids=[r.unit_id for r in visible_red],
        )
        for u in blue_alive
    ]
    return OrdersTemplateOut(epoch=sess.epoch + 1, turn=sess.world.turn, units=options)


# ── Internal projection helpers ───────────────────────────────────────────────

def _unit_type(unit_id: str) -> str:
    for part in unit_id.split("-"):
        if part in ("MNV", "FRS", "ENB"):
            return part
    return "UNK"


def _unit_out(u: ef.UnitState) -> UnitOut:
    return UnitOut(
        unit_id=u.unit_id,
        side=u.side.value,
        unit_type=_unit_type(u.unit_id),
        template_id=u.template_id,
        position=list(u.position),
        strength=round(u.strength, 3),
        readiness=u.readiness.value,
        posture=u.posture.value,
        dug_in=u.dug_in,
        is_alive=u.is_alive,
    )


def _force(sess: Session, side: ef.Side) -> ForceOut:
    units = [
        _unit_out(u) for u in ef.units_visible_to(sess.world, ef.Side.BLUE)
        if u.side == side
    ]
    return ForceOut(
        side=side.value,
        combat_power=ef.combat_power(sess.world, side),
        units=units,
    )


def _objectives(sess: Session) -> list[ObjectiveOut]:
    return [
        ObjectiveOut(
            id=o.objective_id,
            name=o.name,
            position=list(o.cell),
            controlled_by=o.held_by.value,
            weight=o.weight,
        )
        for o in sess.world.objectives.values()
    ]


def _map(sess: Session) -> MapOut:
    cells = [TerrainCellOut(**c) for c in ef.serialize_terrain(sess.world)]
    return MapOut(
        rows=sess.world.terrain.height,
        cols=sess.world.terrain.width,
        km_per_cell=5.0,
        cells=cells,
    )
