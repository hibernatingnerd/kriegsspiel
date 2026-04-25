// adjudicate.ts
// Mock adjudication engine. Replace with API call to Python backend.
// Contract: (state, decisionKey, note) → new GameState

import type { GameState, TurnRecord, DecisionKey } from './schema'
import { GREY_HORIZON_DECISIONS } from './mock-data'

interface Delta {
  blue_cp: number
  red_cp: number
  penetration_km: number
  quality: 'good' | 'neutral' | 'poor'
}

const DELTAS: Record<string, Delta> = {
  hold:           { blue_cp: -2,  red_cp: -4,  penetration_km: 1,  quality: 'neutral' },
  reorient_fires: { blue_cp: -4,  red_cp: -16, penetration_km: 0,  quality: 'good'    },
  commit_reserve: { blue_cp: -6,  red_cp: -10, penetration_km: -1, quality: 'good'    },
  withdraw:       { blue_cp: -1,  red_cp: -2,  penetration_km: 4,  quality: 'poor'    },
  advance:        { blue_cp: -8,  red_cp: -12, penetration_km: -3, quality: 'neutral' },
  escalate:       { blue_cp: -3,  red_cp: -6,  penetration_km: 0,  quality: 'neutral' },
  hold_cyber:     { blue_cp: -1,  red_cp: -3,  penetration_km: 0,  quality: 'neutral' },
  strike:         { blue_cp: -5,  red_cp: -18, penetration_km: 0,  quality: 'good'    },
}

const RED_ACTIONS: Record<string, string> = {
  hold:           'PRESS FORWARD',
  reorient_fires: 'TACTICAL PAUSE',
  commit_reserve: 'FLANK ATTEMPT',
  withdraw:       'EXPLOITATION',
  advance:        'COUNTER-ATTACK',
  escalate:       'EW INTENSIFICATION',
  hold_cyber:     'INFORMATION STRIKE',
  strike:         'DISPERSE + EVADE',
}

const NARRATIVES: Record<string, (turn: number) => string> = {
  hold:           (t) => `Blue held forward positions. Red pressed on primary axis. Attrition exchange roughly even. Turn ${t} ends with blue line intact.`,
  reorient_fires: (t) => `Blue fires reoriented to canalization point. Red advance disrupted; lead element took significant losses. Red operational tempo reduced. Turn ${t}.`,
  commit_reserve: (t) => `Blue committed reserve element. Red flank attempt detected and repelled. Intelligence gain on red order of battle. Turn ${t}.`,
  withdraw:       (t) => `Blue executed local withdrawal. Red exploited 3–4 km of terrain. Blue combat power preserved; new defensive line established. Turn ${t}.`,
  advance:        (t) => `Blue pushed forward aggressively. High-intensity exchange; both sides took losses. Blue gained terrain but at cost. Turn ${t}.`,
  escalate:       (t) => `Blue escalated; NATO consultations accelerated. Red EW intensified but political pressure building. Turn ${t}.`,
  hold_cyber:     (t) => `Blue cyber posture hardened. Red information strike attempted but partially mitigated. C2 integrity maintained. Turn ${t}.`,
  strike:         (t) => `Blue direct action strikes hit red logistics node. Red dispersed to avoid follow-on fires. Red sustainment disrupted. Turn ${t}.`,
}

function clamp(v: number, min: number, max: number) {
  return Math.max(min, Math.min(max, v))
}

function deriveDoctrineRefs(key: DecisionKey): string[] {
  const map: Record<string, string[]> = {
    hold:           ['FM 3-90 §3.4'],
    reorient_fires: ['FM 3-0 §5.3', 'JP 3-0 §IV-12'],
    commit_reserve: ['JP 2-01 §III-7'],
    withdraw:       ['FM 3-90 §4.2'],
    advance:        ['FM 3-0 §3.1'],
    escalate:       ['JP 5-0 §III-8'],
    hold_cyber:     ['JP 3-12 §II-4'],
    strike:         ['JP 3-60 §III-2'],
  }
  return map[key] ?? []
}

export function mockAdjudicate(
  state: GameState,
  decisionKey: DecisionKey,
  note: string
): GameState {
  const delta = DELTAS[decisionKey] ?? DELTAS['hold']
  const pending = state.pending_decision!
  const option = pending.options.find((o) => o.key === decisionKey) ?? pending.options[0]

  const newBlueCp = clamp(state.blue_force.combat_power + delta.blue_cp, 0, 100)
  const newRedCp = clamp(state.red_force.combat_power + delta.red_cp, 0, 100)
  const newPenetration = clamp(state.max_penetration_km + delta.penetration_km, 0, 60)
  const elapsedHours = state.current_turn * 6

  const record: TurnRecord = {
    turn: state.current_turn,
    elapsed_hours: elapsedHours,
    blue_action_key: decisionKey,
    blue_action_label: option.label,
    blue_note: note,
    red_action_label: RED_ACTIONS[decisionKey] ?? 'CONTINUE ATTACK',
    narrative: (NARRATIVES[decisionKey] ?? NARRATIVES['hold'])(state.current_turn),
    blue_cp_after: newBlueCp,
    red_cp_after: newRedCp,
    penetration_km_after: newPenetration,
    doctrine_refs: deriveDoctrineRefs(decisionKey),
  }

  const newLog = [...state.turn_log, record]
  const nextTurn = state.current_turn + 1
  const scenario = { turns_total: 10 }  // replaced by real scenario in prod

  const isEnded =
    nextTurn > scenario.turns_total ||
    newBlueCp <= 0 ||
    newRedCp <= 0 ||
    newPenetration >= 30

  if (isEnded) {
    const blueWins = newPenetration < 25 && newBlueCp > 30
    const label = blueWins ? 'blue_win' : newPenetration >= 25 ? 'red_win' : 'draw'

    return {
      ...state,
      status: 'ended',
      current_turn: nextTurn - 1,
      blue_force: { ...state.blue_force, combat_power: newBlueCp },
      red_force: { ...state.red_force, combat_power: newRedCp },
      max_penetration_km: newPenetration,
      turn_log: newLog,
      pending_decision: null,
      aar: {
        outcome: {
          label,
          summary: blueWins
            ? `Blue achieved mission. Daugavpils held; penetration contained at ${newPenetration.toFixed(1)} km. Red failed to achieve fait accompli before Article 5 trigger.`
            : `Red achieved strategic objective. Penetration reached ${newPenetration.toFixed(1)} km. Blue combat power degraded below sustainable threshold.`,
          blue_cp_final: newBlueCp,
          red_cp_final: newRedCp,
          max_penetration_km: newPenetration,
          turns_played: nextTurn - 1,
          blue_conditions_met: blueWins ? 3 : 1,
          red_conditions_met: blueWins ? 1 : 3,
          conditions_total: 4,
        },
        key_turns: newLog.slice(-3).map((r) => r.turn),
        lessons: [
          { category: 'tactical', text: 'Terrain canalization proved decisive — restrictive terrain negated red armor advantage on primary axis.' },
          { category: 'operational', text: 'Combat power curves diverged after turn 3; early fires reorientation was the inflection point.' },
          { category: 'doctrinal', text: 'Decision quality tracked closely with FM 3-90 trade-space framework; doctrine-aligned turns produced better outcomes.' },
        ],
        recommendations: [
          { text: 'Re-run with red reserves committed at T+0 to stress-test blue combat power floor.' },
          { text: 'Add civilian infrastructure axis modifier to surface humanitarian constraints.' },
          { text: 'Compare this run against alternate timeline with blue fires held in counter-battery role.' },
        ],
        doctrine_citations: [
          { text: 'Defending forces canalize the attacker into restrictive terrain to mass fires at decisive points while preserving combat power for the counter-attack.', source: 'FM 3-90 §3.4', relevance: 'primary lesson' },
          { text: 'Trading ground for posture is a legitimate defensive option when terrain offers superior subsequent positions.', source: 'FM 3-90 §4.2', relevance: 'withdrawal decision rationale' },
        ],
        generated_in_seconds: 8.3,
      },
    }
  }

  const nextDecision =
    GREY_HORIZON_DECISIONS[nextTurn] ??
    GREY_HORIZON_DECISIONS[10]

  return {
    ...state,
    current_turn: nextTurn,
    blue_force: { ...state.blue_force, combat_power: newBlueCp },
    red_force: { ...state.red_force, combat_power: newRedCp },
    max_penetration_km: newPenetration,
    turn_log: newLog,
    pending_decision: nextDecision,
  }
}
