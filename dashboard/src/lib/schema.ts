// schema.ts
// All fields use snake_case to mirror the Python backend dataclasses.
// Swap src/lib/mock-data.ts + API layer to connect a real backend — types stay stable.

export type ScenarioStatus = 'setup' | 'running' | 'ended'
export type SideLabel = 'blue' | 'red'
export type ThreatTier = 'peer' | 'near_peer' | 'hybrid' | 'asymmetric'
export type OutcomeLabel = 'blue_win' | 'red_win' | 'draw'
export type AppPhase = 'setup' | 'run' | 'debrief'

// Open string so backends can add domain-specific keys freely
export type DecisionKey = string

export interface Location {
  name: string
  region: string
  country: string
  bbox: [number, number, number, number] | null  // [west_lon, south_lat, east_lon, north_lat]
  key_routes: string[]
  terrain_notes: string
  pop_centers: string[]
}

export interface Unit {
  designation: string
  type: string
  equipment: string
  location: string
  notes: string
}

export interface Force {
  side: SideLabel
  name: string
  units: Unit[]
  combat_power: number  // 0–100
}

export interface Modifier {
  key: string
  label: string
  description: string
  value: boolean | number | string
  default_value: boolean | number | string
}

export interface Budget {
  label: string
  total: number
  remaining: number
  unit: string  // e.g. "$M", "sorties", "support-days"
}

export interface Citation {
  text: string
  source: string
  relevance: string
}

export interface SeedEvent {
  date: string         // ISO date YYYY-MM-DD
  description: string
  source: string
  source_id: string
}

export interface VictoryConditions {
  blue: string[]
  red: string[]
}

export interface Scenario {
  id: string
  name: string
  classification: string
  threat_tier: ThreatTier
  summary: string
  timeline_hours: number
  turns_total: number
  location: Location
  blue_force: Force
  red_force: Force
  victory_conditions: VictoryConditions
  available_modifiers: Modifier[]
  active_modifier_keys: string[]
  budget: Budget
  seed_events: SeedEvent[]
  doctrine_citations: Citation[]
  generated_at: string          // ISO datetime
  generated_in_seconds: number
  run_id: string
}

export interface TurnRecord {
  turn: number
  elapsed_hours: number
  blue_action_key: DecisionKey
  blue_action_label: string
  blue_note: string
  red_action_label: string
  narrative: string
  blue_cp_after: number
  red_cp_after: number
  penetration_km_after: number
  doctrine_refs: string[]
}

export interface DecisionOption {
  key: DecisionKey
  label: string
  sub_label: string
  consequence_hint: string
}

export interface PendingDecision {
  turn: number
  context: string
  options: DecisionOption[]
}

export interface AARLesson {
  category: 'strategic' | 'operational' | 'tactical' | 'doctrinal' | 'cognitive'
  text: string
}

export interface AARRecommendation {
  text: string
}

export interface Outcome {
  label: OutcomeLabel
  summary: string
  blue_cp_final: number
  red_cp_final: number
  max_penetration_km: number
  turns_played: number
  blue_conditions_met: number
  red_conditions_met: number
  conditions_total: number
}

export interface AAR {
  outcome: Outcome
  key_turns: number[]
  lessons: AARLesson[]
  recommendations: AARRecommendation[]
  doctrine_citations: Citation[]
  generated_in_seconds: number
}

export interface GameState {
  scenario_id: string
  run_id: string
  status: ScenarioStatus
  current_turn: number
  next_checkin_iso: string | null
  blue_force: Force
  red_force: Force
  max_penetration_km: number
  turn_log: TurnRecord[]
  pending_decision: PendingDecision | null
  aar: AAR | null
}

// ---- Config shape the Setup form emits ----
export interface ScenarioConfig {
  base_scenario_id: string
  label_override: string
  timeline_hours: number
  active_modifier_keys: string[]
  blue_force_strength: number   // 50–100
  red_force_strength: number    // 50–100
}
