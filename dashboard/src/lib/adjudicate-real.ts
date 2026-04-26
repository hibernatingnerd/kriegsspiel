import type { GameState, DecisionKey, TurnRecord, PendingDecision, Scenario } from './schema'
import { synthesizeAAR } from './aar-stub'
import type {
  BoardUnit,
  ControlStateSnapshot,
  ObjectiveSnapshot,
  TerrainCellSnapshot,
  UnitMove,
  WorldStateBattleIterationRequest,
  WorldStateBattleIterationResponse,
  WorldStateSnapshot,
} from './battle-types'
import { adjudicateWorldTurn } from './api-client'
import { GREY_HORIZON_DECISIONS } from './mock-data'

const GRID_ROWS = 20
const GRID_COLS = 24
const OBJECTIVE_CELLS = new Set(['5,5', '10,4', '12,11'])
const OBJECTIVES: ObjectiveSnapshot[] = [
  {
    objective_id: 'OBJ-REZEKNE',
    cell: [5, 5],
    name: 'Rezekne',
    weight: 2,
    held_by: 'BLUE',
    taken_at_turn: 0,
  },
  {
    objective_id: 'OBJ-DAUGAVPILS',
    cell: [10, 4],
    name: 'Daugavpils',
    weight: 3,
    held_by: 'BLUE',
    taken_at_turn: 0,
  },
  {
    objective_id: 'OBJ-KRASLAVA',
    cell: [12, 11],
    name: 'Kraslava',
    weight: 1.5,
    held_by: 'NEUTRAL',
    taken_at_turn: null,
  },
]

export function applyUnitMoves(
  units: BoardUnit[],
  moves: UnitMove[],
): BoardUnit[] {
  const moveMap = new Map(moves.map((move) => [move.unit_id, move]))

  return units.map((unit) => {
    const move = moveMap.get(unit.unit_id)
    if (!move) return unit
    return {
      ...unit,
      position: move.to_position,
      readiness: move.readiness_after,
      strength: move.strength_after,
    }
  })
}

function nextDecision(turn: number): PendingDecision | null {
  return GREY_HORIZON_DECISIONS[turn + 1] ?? null
}

function fallbackDecision(turn: number): PendingDecision {
  const template =
    GREY_HORIZON_DECISIONS[turn] ??
    GREY_HORIZON_DECISIONS[Math.min(turn, 10)] ??
    GREY_HORIZON_DECISIONS[10]

  return {
    turn,
    context: template?.context ?? 'Situation update pending from backend adjudication.',
    options: template?.options ?? [],
  }
}

function buildTurnRecord(
  turn: number,
  orderLabel: string,
  note: string,
  narrative: string,
  redResponseLabel: string,
  blueCpAfter: number,
  redCpAfter: number,
  penetrationKmAfter: number,
  doctrineRefs: string[],
): TurnRecord {
  return {
    turn,
    elapsed_hours: turn * 6,
    blue_action_key: orderLabel,
    blue_action_label: orderLabel,
    blue_note: note,
    red_action_label: redResponseLabel,
    narrative,
    blue_cp_after: blueCpAfter,
    red_cp_after: redCpAfter,
    penetration_km_after: penetrationKmAfter,
    doctrine_refs: doctrineRefs,
  }
}

function buildOpenCell(features: TerrainCellSnapshot['features'] = []): TerrainCellSnapshot {
  return {
    base: 'OPEN',
    features,
    altitude_m: 0,
    slope_deg: 0,
    cover_factor: 0.1,
    visibility_factor: 1,
    movement_cost_ground: 1,
    supply_throughput: 1,
    strategic_weight: features.includes('OBJECTIVE') ? 1 : 0,
  }
}

function inferAffiliation(unit: BoardUnit): 'BLUE' | 'RED_RU' {
  return unit.side === 'BLUE' ? 'BLUE' : 'RED_RU'
}

function buildWorldStateSnapshot(
  gameState: GameState,
  units: BoardUnit[],
): WorldStateSnapshot {
  const cells = Array.from({ length: GRID_ROWS }, (_, row) =>
    Array.from({ length: GRID_COLS }, (_, col) =>
      buildOpenCell(OBJECTIVE_CELLS.has(`${row},${col}`) ? ['OBJECTIVE'] : []),
    ),
  )

  const unitMap = Object.fromEntries(
    units.map((unit) => [
      unit.unit_id,
      {
        unit_id: unit.unit_id,
        template_id: unit.category,
        side: unit.side,
        affiliation: inferAffiliation(unit),
        position: unit.position,
        strength: unit.strength,
        readiness: unit.readiness,
        supply_days_remaining: unit.supply_days_remaining,
        posture: unit.posture,
        dug_in: false,
        turns_isolated: 0,
        notes: '',
      },
    ]),
  )

  const control: Record<string, ControlStateSnapshot> = {}
  for (let row = 0; row < GRID_ROWS; row++) {
    for (let col = 0; col < GRID_COLS; col++) {
      const key = `${row},${col}`
      const occupant = units.find((unit) => unit.position[0] === row && unit.position[1] === col)
      control[key] = {
        cell: [row, col],
        controlled_by: occupant?.side ?? 'NEUTRAL',
        persistence_turns: occupant ? 1 : 0,
        contender: null,
      }
    }
  }

  const objectives = Object.fromEntries(
    OBJECTIVES.map((objective) => {
      const occupant = units.find(
        (unit) =>
          unit.position[0] === objective.cell[0] &&
          unit.position[1] === objective.cell[1],
      )
      const heldBy = occupant?.side ?? objective.held_by
      return [
        objective.objective_id,
        {
          ...objective,
          held_by: heldBy,
          taken_at_turn: heldBy === 'NEUTRAL' ? null : objective.taken_at_turn,
        },
      ]
    }),
  )

  return {
    identity: {
      run_id: gameState.run_id,
      scenario_id: gameState.scenario_id,
      rulepack_id: 'krg_v0_1',
      engine_version: '0.1.0',
      seed: 1729,
      noise_enabled: false,
    },
    turn: gameState.current_turn - 1,
    minutes_per_turn: 60,
    timestamp_minutes: (gameState.current_turn - 1) * 60,
    terrain: {
      height: GRID_ROWS,
      width: GRID_COLS,
      cells,
      crossings: [],
    },
    units: unitMap,
    control,
    objectives,
    side_posture: {
      BLUE: 'STANDARD',
      RED: 'STANDARD',
      NEUTRAL: 'STANDARD',
    },
    unit_decision_list: [],
  }
}

function computeCp(units: WorldStateBattleIterationResponse['world_state_after']['units'], side: 'BLUE' | 'RED'): number {
  const sideUnits = Object.values(units).filter((unit) => unit.side === side)
  if (sideUnits.length === 0) return 0
  return Math.round((sideUnits.reduce((sum, unit) => sum + unit.strength, 0) / sideUnits.length) * 100)
}

function computePenetrationKm(units: WorldStateBattleIterationResponse['world_state_after']['units']): number {
  const redUnits = Object.values(units).filter((unit) => unit.side === 'RED')
  if (redUnits.length === 0) return 0
  return Math.max(0, (GRID_COLS - 2 - Math.min(...redUnits.map((unit) => unit.position[1]))) * 2.5)
}

export interface AdjudicateResult {
  gameState: GameState
  units: BoardUnit[]
  moves: UnitMove[]
}

export async function adjudicateWithLLM(
  gameState: GameState,
  units: BoardUnit[],
  key: DecisionKey,
  note: string,
  scenario: Scenario,
): Promise<AdjudicateResult> {
  const req: WorldStateBattleIterationRequest = {
    run_id: gameState.run_id,
    turn: gameState.current_turn,
    blue_order_key: key,
    blue_order_label: key,
    commander_note: note,
    scenario_summary: scenario.summary,
    world_state: buildWorldStateSnapshot(gameState, units),
  }

  const res = await adjudicateWorldTurn(req)
  const updatedUnits = applyUnitMoves(units, res.unit_moves)
  const blueCpAfter = computeCp(res.world_state_after.units, 'BLUE')
  const redCpAfter = computeCp(res.world_state_after.units, 'RED')
  const penetrationKmAfter = computePenetrationKm(res.world_state_after.units)
  const record = buildTurnRecord(
    gameState.current_turn,
    key,
    note,
    res.narrative,
    res.red_response_label,
    blueCpAfter,
    redCpAfter,
    penetrationKmAfter,
    res.doctrine_refs,
  )

  const hasTerminalOutcome = res.game_over && res.outcome !== null
  const isEnded = hasTerminalOutcome
  const interimGS: GameState = {
    ...gameState,
    status: isEnded ? 'ended' : 'running',
    current_turn: gameState.current_turn + 1,
    blue_force: { ...gameState.blue_force, combat_power: blueCpAfter },
    red_force: { ...gameState.red_force, combat_power: redCpAfter },
    max_penetration_km: penetrationKmAfter,
    turn_log: [...gameState.turn_log, record],
    pending_decision: isEnded
      ? null
      : nextDecision(gameState.current_turn) ?? fallbackDecision(gameState.current_turn + 1),
    aar: null,
  }

  // STUB: synthesize AAR locally on the frontend until the backend exposes
  // /api/aar. Remove this block when the real endpoint lands.
  const nextGS: GameState = isEnded && res.outcome
    ? { ...interimGS, aar: synthesizeAAR(interimGS, scenario, res.outcome) }
    : interimGS

  return { gameState: nextGS, units: updatedUnits, moves: res.unit_moves }
}
