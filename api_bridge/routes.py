"""
Route handlers — thin wrappers over session.py.
Import order: schema → session → routes → main.
"""

import uuid
from fastapi import APIRouter, HTTPException

from .schema import StartIn, ActionIn, GameStateOut, AAROut
from . import session

router = APIRouter()


@router.get("/health")
def health():
    return {"status": "ok", "sessions": session.count()}


@router.post("/game/start", response_model=GameStateOut)
def start_game(body: StartIn):
    game_id = str(uuid.uuid4())[:8]
    session.create(game_id)
    return session.to_game_state(game_id)


@router.get("/game/{game_id}", response_model=GameStateOut)
def get_game(game_id: str):
    if not session.exists(game_id):
        raise HTTPException(status_code=404, detail="Game not found")
    return session.to_game_state(game_id)


@router.post("/game/{game_id}/action", response_model=GameStateOut)
def take_action(game_id: str, body: ActionIn):
    if not session.exists(game_id):
        raise HTTPException(status_code=404, detail="Game not found")
    if body.decision_key not in session.DECISIONS:
        raise HTTPException(status_code=400, detail=f"Unknown decision_key: {body.decision_key}")

    world = session.get_world(game_id)
    if world.turn > session.TURNS_TOTAL:
        raise HTTPException(status_code=409, detail="Game already ended")

    session.resolve_action(game_id, body.decision_key, body.note)
    return session.to_game_state(game_id)


@router.get("/game/{game_id}/report", response_model=AAROut)
def get_report(game_id: str):
    if not session.exists(game_id):
        raise HTTPException(status_code=404, detail="Game not found")
    return session.to_aar(game_id)
