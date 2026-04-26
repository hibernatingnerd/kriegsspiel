"""
HTTP route handlers — thin wrappers over session.py.
"""

import uuid
from fastapi import APIRouter, HTTPException

from . import session
from .schema import (
    AAROut, CreateGameIn, GameStateOut, OrdersIn, OrdersTemplateOut,
)

router = APIRouter()


# ── Liveness ──────────────────────────────────────────────────────────────────

@router.get("/health")
def health():
    return {
        "status":     "ok",
        "sessions":   session.count(),
        "session_ids": session.all_session_ids(),
    }


# ── Game lifecycle ────────────────────────────────────────────────────────────

@router.post("/games", response_model=GameStateOut, status_code=201)
def create_game(body: CreateGameIn):
    game_id = uuid.uuid4().hex[:8]
    try:
        sess = session.create(
            game_id=game_id,
            scenario=body.scenario,
            epoch_size=body.epoch_size,
            turns_total=body.turns_total,
            seed=body.seed,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return session.to_game_state(sess)


@router.get("/games/{game_id}", response_model=GameStateOut)
def get_game(game_id: str):
    if not session.exists(game_id):
        raise HTTPException(status_code=404, detail="Game not found")
    return session.to_game_state(session.get(game_id))


@router.get("/games/{game_id}/orders/template", response_model=OrdersTemplateOut)
def get_orders_template(game_id: str):
    if not session.exists(game_id):
        raise HTTPException(status_code=404, detail="Game not found")
    sess = session.get(game_id)
    if sess.status != "awaiting_orders":
        raise HTTPException(
            status_code=409,
            detail=f"Cannot fetch orders template; game status={sess.status}",
        )
    return session.orders_template(sess)


@router.post("/games/{game_id}/orders", response_model=GameStateOut)
def submit_orders(game_id: str, body: OrdersIn):
    if not session.exists(game_id):
        raise HTTPException(status_code=404, detail="Game not found")
    sess = session.get(game_id)
    if sess.status == "ended":
        raise HTTPException(status_code=409, detail="Game already ended")
    if sess.status != "awaiting_orders":
        raise HTTPException(
            status_code=409,
            detail=f"Cannot submit orders; game status={sess.status}",
        )

    blue_unit_ids = {
        u.unit_id for u in sess.world.units.values() if u.side.value == "BLUE"
    }
    foreign = [o.unit_id for o in body.orders if o.unit_id not in blue_unit_ids]
    if foreign:
        raise HTTPException(
            status_code=400,
            detail=f"Orders contain non-BLUE or unknown unit_ids: {foreign}",
        )

    try:
        session.advance_one_epoch(sess, body.orders, body.note)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return session.to_game_state(sess)


@router.get("/games/{game_id}/aar", response_model=AAROut)
def get_aar(game_id: str):
    if not session.exists(game_id):
        raise HTTPException(status_code=404, detail="Game not found")
    return session.to_aar(session.get(game_id))
