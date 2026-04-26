// adjudicate-real.ts
// Replace dashboard/src/lib/adjudicate.ts with this file (or merge).
//
// Key difference from the mock version:
// - Calls the FastAPI backend which calls Claude
// - Applies UnitMove[] from the response to update BoardUnit positions
// - Returns the updated GameState + updated BoardUnit list

import type { GameState, DecisionKey, TurnRecord, PendingDecision } from './schema'
import type {
  BoardUnit,
  BattleIterationRequest,
  BattleIterationResponse,
  UnitMove,
} from './battle-types'
import { adjudicateTurn } from './api-client'
import { GREY_HORIZON_DECISIONS } from './mock-data'  // keep existing decision options

// ── Apply unit moves to the board ─────────────────────────────────────────

export function applyUnitMoves(
  units: BoardUnit[],
  moves: UnitMove[],
): BoardUnit[] {
  const moveMap = new Map(moves.map(m => [m.unit_id, m]))

  return units.map(unit => {
    const move = moveMap.get(unit.unit_id)
    if (!move) return unit
    return {
      ...unit,
      position:  move.to_position   as [number, number],
      readiness: move.readiness_after,
      strength:  move.strength_after,
    }
  })
}

// ── Build the next TurnRecord from the LLM response ───────────────────────

function buildTurnRecord(
  turn: number,
  orderLabel: string,
  note: string,
  res: BattleIterationResponse,
): TurnRecord {
  return {
    turn,
    elapsed_hours:         turn * 6,
    blue_action_key:       orderLabel,
    blue_action_label:     orderLabel,
    blue_note:             note,
    red_action_label:      res.red_response_label,
    narrative:             res.narrative,
    blue_cp_after:         res.blue_cp_after,
    red_cp_after:          res.red_cp_after,
    penetration_km_after:  res.penetration_km_after,
    doctrine_refs:         res.doctrine_refs,
  }
}

// ── Pick the next pending decision ───────────────────────────────────────

function nextDecision(turn: number): PendingDecision | null {
  return GREY_HORIZON_DECISIONS[turn + 1] ?? null
}

// ── Main exported function ────────────────────────────────────────────────

export interface AdjudicateResult {
  gameState: GameState
  units: BoardUnit[]          // updated board positions
}

export async function adjudicateWithLLM(
  gameState: GameState,
  units: BoardUnit[],
  key: DecisionKey,
  note: string,
  scenario_summary: string,
): Promise<AdjudicateResult> {

  const req: BattleIterationRequest = {
    run_id:            gameState.run_id,
    turn:              gameState.current_turn,
    blue_order_key:    key,
    blue_order_label:  key,
    commander_note:    note,
    units,
    scenario_summary,
    blue_cp:           gameState.blue_force.combat_power,
    red_cp:            gameState.red_force.combat_power,
    max_penetration_km: gameState.max_penetration_km,
  }

  const res: BattleIterationResponse = await adjudicateTurn(req)

  // Apply moves to unit positions
  const updatedUnits = applyUnitMoves(units, res.unit_moves)

  // Build turn record
  const record = buildTurnRecord(gameState.current_turn, key, note, res)

  const isEnded = res.game_over || gameState.current_turn >= (gameState.turn_log.length + 8)

  const nextGS: GameState = {
    ...gameState,
    status:              isEnded ? 'ended' : 'running',
    current_turn:        gameState.current_turn + 1,
    blue_force:          { ...gameState.blue_force,  combat_power: res.blue_cp_after },
    red_force:           { ...gameState.red_force,   combat_power: res.red_cp_after  },
    max_penetration_km:  res.penetration_km_after,
    turn_log:            [...gameState.turn_log, record],
    pending_decision:    isEnded ? null : nextDecision(gameState.current_turn),
    aar:                 isEnded ? gameState.aar : null,
  }

  return { gameState: nextGS, units: updatedUnits }
}