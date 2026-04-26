// battle-types.ts
// Extends schema.ts with the spatial/unit-position types needed for the
// LLM-powered battle iteration. Import these alongside the existing schema.

import type { DecisionKey } from './schema'

// ── Grid positions ────────────────────────────────────────────────────────

export type GridCoord = [number, number] // [row, col]

export type ReadinessLevel =
  | 'FULLY_OPERATIONAL'
  | 'DEGRADED'
  | 'SUPPRESSED'
  | 'DESTROYED'

export type PostureLabel =
  | 'OFFENSIVE'
  | 'DEFENSIVE'
  | 'MOVING'
  | 'SCREENING'
  | 'RESUPPLYING'

export type ActionType = 'MOVE' | 'ASSAULT' | 'HOLD' | 'WITHDRAW'

// ── Unit on the board ─────────────────────────────────────────────────────

export interface BoardUnit {
  unit_id: string
  side: 'BLUE' | 'RED'
  designation: string         // e.g. "1st Infantry Bn"
  category: string            // e.g. "ARMOR", "LIGHT_INFANTRY"
  position: GridCoord
  readiness: ReadinessLevel
  strength: number            // 0.0–1.0
  supply_days_remaining: number | null
  posture: PostureLabel
}

// ── What the frontend sends to /api/adjudicate ────────────────────────────

export interface BattleIterationRequest {
  run_id: string
  turn: number
  blue_order_key: DecisionKey
  blue_order_label: string
  commander_note: string
  units: BoardUnit[]
  scenario_summary: string
  blue_cp: number
  red_cp: number
  max_penetration_km: number
}

// ── What /api/adjudicate returns ──────────────────────────────────────────

export interface UnitMove {
  unit_id: string
  from_position: GridCoord
  to_position: GridCoord
  action: ActionType
  readiness_after: ReadinessLevel
  strength_after: number
}

export interface AuditEntry {
  time: string
  category: 'INTEL' | 'MOVEMENT' | 'FIRES' | 'CYBER' | 'EW' | 'C2' | 'ASSESSMENT' | 'SYSTEM'
  text: string
}

export interface BattleIterationResponse {
  turn: number
  narrative: string
  red_response_label: string
  unit_moves: UnitMove[]
  blue_cp_after: number
  red_cp_after: number
  penetration_km_after: number
  audit_entries: AuditEntry[]
  doctrine_refs: string[]
  game_over: boolean
  outcome: 'blue_win' | 'red_win' | 'draw' | null
}

// Backend-owned world-state contract. This mirrors the deterministic engine
// and is intended to replace the thin UnitSnapshot[] payload once the backend
// owns authoritative movement/combat resolution end-to-end.

export type SideLabel = 'BLUE' | 'RED' | 'NEUTRAL'

export type TerrainBase =
  | 'OPEN'
  | 'FOREST'
  | 'URBAN'
  | 'WATER'
  | 'MOUNTAIN'
  | 'SWAMP'
  | 'IMPASSABLE'

export type TerrainFeature =
  | 'RIVER'
  | 'WATER_DEEP'
  | 'BRIDGE'
  | 'FORD'
  | 'ROAD'
  | 'RAIL'
  | 'FORTIFIED'
  | 'URBAN_DENSE'
  | 'URBAN_SPARSE'
  | 'OBJECTIVE'

export type Affiliation =
  | 'BLUE'
  | 'RED_RU'
  | 'RED_CN'
  | 'RED_IRR'
  | 'OPFOR'

export type EventType =
  | 'UNIT_MOVED'
  | 'UNIT_MOVE_BLOCKED'
  | 'CROSSING_USED'
  | 'COMBAT_RESOLVED'
  | 'UNIT_DESTROYED'
  | 'UNIT_SUPPRESSED'
  | 'UNIT_DEGRADED'
  | 'SUPPLY_CONSUMED'
  | 'SUPPLY_DELIVERED'
  | 'UNIT_ISOLATED'
  | 'ATTRITION_APPLIED'
  | 'CONTROL_CHANGED'
  | 'OBJECTIVE_TAKEN'
  | 'TURN_ADVANCED'
  | 'INVARIANT_VIOLATION'

export type ReasonCode =
  | 'MOV_OK'
  | 'MOV_TERRAIN_IMPASSABLE'
  | 'MOV_INSUFFICIENT_ALLOWANCE'
  | 'MOV_BLOCKED_BY_ENEMY'
  | 'MOV_NO_PATH'
  | 'MOV_CROSSING_REQUIRED'
  | 'MOV_CROSSING_DESTROYED'
  | 'CMB_ATTACKER_WIN'
  | 'CMB_DEFENDER_WIN'
  | 'CMB_STALEMATE'
  | 'CMB_DEFENDER_FORTIFIED'
  | 'CMB_TERRAIN_FAVORS_DEFENDER'
  | 'CMB_ATTACKER_LOW_SUPPLY'
  | 'CMB_FIRES_SUPPORT_APPLIED'
  | 'SUP_OK'
  | 'SUP_LOW'
  | 'SUP_CRITICAL'
  | 'SUP_ISOLATED'
  | 'SUP_RESUPPLY_DELIVERED'
  | 'CTL_DOMINANCE_BLUE'
  | 'CTL_DOMINANCE_RED'
  | 'CTL_CONTESTED'
  | 'CTL_PERSISTENCE_THRESHOLD'
  | 'VAL_UNIT_NOT_FOUND'
  | 'VAL_UNIT_NOT_OWNED'
  | 'VAL_UNIT_DESTROYED'
  | 'VAL_ACTION_ILLEGAL_FOR_UNIT'
  | 'VAL_TARGET_INVALID'
  | 'VAL_OUT_OF_RANGE'
  | 'VAL_UNIT_LACKS_OFFENSIVE_CAPABILITY'
  | 'SYS_TURN_ADVANCED'
  | 'SYS_FALLBACK_HOLD'

export interface TerrainCellSnapshot {
  base: TerrainBase
  features: TerrainFeature[]
  altitude_m: number
  slope_deg: number
  cover_factor: number
  visibility_factor: number
  movement_cost_ground: number
  supply_throughput: number
  strategic_weight: number
}

export interface RiverCrossingSnapshot {
  crossing_id: string
  cell_a: GridCoord
  cell_b: GridCoord
  crossing_type: 'BRIDGE' | 'FORD' | 'FERRY' | 'ENGINEER_TEMP'
  capacity_per_turn: number
  integrity: 'INTACT' | 'DAMAGED' | 'DESTROYED'
  controlled_by: SideLabel
}

export interface TerrainGridSnapshot {
  height: number
  width: number
  cells: TerrainCellSnapshot[][]
  crossings: RiverCrossingSnapshot[]
}

export interface UnitStateSnapshot {
  unit_id: string
  template_id: string
  side: SideLabel
  affiliation: Affiliation
  position: GridCoord
  strength: number
  readiness: ReadinessLevel
  supply_days_remaining: number | null
  posture: PostureLabel
  dug_in: boolean
  turns_isolated: number
  notes: string
}

export interface ControlStateSnapshot {
  cell: GridCoord
  controlled_by: SideLabel
  persistence_turns: number
  contender: SideLabel | null
}

export interface ObjectiveSnapshot {
  objective_id: string
  cell: GridCoord
  name: string
  weight: number
  held_by: SideLabel
  taken_at_turn: number | null
}

export interface RunIdentitySnapshot {
  run_id: string
  scenario_id: string
  rulepack_id: string
  engine_version: string
  seed: number
  noise_enabled: boolean
}

export interface WorldStateSnapshot {
  identity: RunIdentitySnapshot
  turn: number
  minutes_per_turn: number
  timestamp_minutes: number
  terrain: TerrainGridSnapshot
  units: Record<string, UnitStateSnapshot>
  control: Record<string, ControlStateSnapshot>
  objectives: Record<string, ObjectiveSnapshot>
  side_posture: Record<SideLabel, string>
  unit_decision_list: unknown[]
}

export interface StateDeltaEvent {
  event_type: EventType
  reason_code: ReasonCode | null
  unit_id: string | null
  from_position: GridCoord | null
  to_position: GridCoord | null
  summary: string
  payload: Record<string, unknown>
}

export interface WorldStateBattleIterationRequest {
  run_id: string
  turn: number
  blue_order_key: DecisionKey
  blue_order_label: string
  commander_note: string
  scenario_summary: string
  world_state: WorldStateSnapshot
}

export interface WorldStateBattleIterationResponse {
  turn: number
  narrative: string
  red_response_label: string
  world_state_before: WorldStateSnapshot
  world_state_after: WorldStateSnapshot
  unit_moves: UnitMove[]
  events: StateDeltaEvent[]
  doctrine_refs: string[]
  game_over: boolean
  outcome: 'blue_win' | 'red_win' | 'draw' | null
}
