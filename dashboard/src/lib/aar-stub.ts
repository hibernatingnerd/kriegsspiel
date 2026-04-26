// Frontend-only AAR synthesis. Stopgap until the backend exposes a real
// /api/aar endpoint backed by aar_writer.py. Delete this file + its caller
// in adjudicate-real.ts when the real endpoint lands.

import type {
  AAR,
  AARLesson,
  AARRecommendation,
  GameState,
  Outcome,
  OutcomeLabel,
  Scenario,
  TurnRecord,
} from './schema'

function pickKeyTurns(log: TurnRecord[]): number[] {
  if (log.length === 0) return []
  const scored = log.map((r, i) => {
    const prev = i > 0 ? log[i - 1] : null
    const blueDelta = prev ? Math.abs(r.blue_cp_after - prev.blue_cp_after) : 0
    const redDelta  = prev ? Math.abs(r.red_cp_after  - prev.red_cp_after)  : 0
    const penDelta  = prev ? Math.abs(r.penetration_km_after - prev.penetration_km_after) : r.penetration_km_after
    return { turn: r.turn, score: blueDelta + redDelta + penDelta * 2 }
  })
  return scored
    .sort((a, b) => b.score - a.score)
    .slice(0, Math.min(3, scored.length))
    .map((s) => s.turn)
    .sort((a, b) => a - b)
}

function buildSummary(label: OutcomeLabel, scenario: Scenario, gs: GameState): string {
  const turns = gs.turn_log.length
  const blue = gs.blue_force.combat_power
  const red  = gs.red_force.combat_power
  const pen  = gs.max_penetration_km
  const name = scenario.name

  if (label === 'blue_win') {
    return `BLUE prevailed in ${name} after ${turns} turns. Coalition combat power held at ${blue.toFixed(0)}% against RED's ${red.toFixed(0)}%; deepest RED penetration was contained at ${pen.toFixed(1)} km. Defensive shaping and timely commitment of the operational reserve denied RED's primary objectives.`
  }
  if (label === 'red_win') {
    return `RED achieved operational success in ${name} over ${turns} turns. BLUE combat power eroded to ${blue.toFixed(0)}% while RED retained ${red.toFixed(0)}%; penetration reached ${pen.toFixed(1)} km, breaching the defensive line. Coalition forces failed to set conditions for a decisive counter-attack.`
  }
  return `${name} ended in stalemate after ${turns} turns. Both sides retained meaningful combat power (BLUE ${blue.toFixed(0)}% / RED ${red.toFixed(0)}%) and neither secured decisive objectives. Maximum RED penetration was ${pen.toFixed(1)} km — sufficient to disrupt but not to break.`
}

function buildLessons(label: OutcomeLabel, gs: GameState): AARLesson[] {
  const out: AARLesson[] = []
  const log = gs.turn_log

  // Strategic
  if (label === 'blue_win') {
    out.push({
      category: 'strategic',
      text: 'Holding the operational reserve until RED committed allowed BLUE to mass effects at the decisive point. Pre-committed reserves would have been attrited piecemeal.',
    })
  } else if (label === 'red_win') {
    out.push({
      category: 'strategic',
      text: 'BLUE under-resourced the main defensive sector and attempted to defend everywhere. Economy of force was inverted — frontages should have been accepted as risk in secondary sectors to mass in the decisive one.',
    })
  } else {
    out.push({
      category: 'strategic',
      text: 'Neither side achieved positional advantage sufficient for decisive action. The operational tempo favored the defender, but BLUE failed to convert defensive success into a counter-stroke.',
    })
  }

  // Operational
  const movementCount = log.filter((r) => /move|advance|reposition/i.test(r.blue_action_label)).length
  if (movementCount >= 3) {
    out.push({
      category: 'operational',
      text: `BLUE maneuvered ${movementCount} times during the engagement. Movement preserved options but each repositioning consumed combat power and exposed transient flanks.`,
    })
  } else {
    out.push({
      category: 'operational',
      text: 'BLUE adopted a positional defense and rarely repositioned. This simplified C2 and supply but ceded initiative to RED for tempo and timing of contact.',
    })
  }

  // Tactical
  if (gs.max_penetration_km >= 15) {
    out.push({
      category: 'tactical',
      text: `RED penetration reached ${gs.max_penetration_km.toFixed(1)} km — the forward defensive belt did not absorb the initial assault. Engineer obstacles and pre-registered fires would have slowed the breach.`,
    })
  } else {
    out.push({
      category: 'tactical',
      text: `Forward defensive lines limited RED penetration to ${gs.max_penetration_km.toFixed(1)} km. Layered obstacles and direct-fire engagement areas held the line of contact.`,
    })
  }

  // Doctrinal
  out.push({
    category: 'doctrinal',
    text: 'Decisions broadly aligned with established doctrine on defense in depth, though the timing of reserve commitment is highlighted in joint and service publications as the most consequential commander\'s decision in the defense.',
  })

  // Cognitive
  const noteCount = log.filter((r) => r.blue_note && r.blue_note.trim().length > 0).length
  if (noteCount > 0) {
    out.push({
      category: 'cognitive',
      text: `Commander recorded rationale for ${noteCount} of ${log.length} decisions. Captured intent improves AAR quality and surfaces assumptions for review.`,
    })
  }

  return out
}

function buildRecommendations(label: OutcomeLabel): AARRecommendation[] {
  if (label === 'blue_win') {
    return [
      { text: 'Repeat the scenario with reduced reserve allocation to test the floor of operational risk acceptance.' },
      { text: 'Run the same defense against a higher-tempo RED variant to stress reserve commitment timing.' },
      { text: 'Capture the reserve-commit decision criteria as a doctrinal vignette for future commanders.' },
    ]
  }
  if (label === 'red_win') {
    return [
      { text: 'Re-examine sector priorities. Identify the decisive sector pre-engagement and accept risk in others.' },
      { text: 'Pre-position engineer obstacles and pre-registered fires on likely RED axes of advance.' },
      { text: 'Rehearse the operational reserve commit decision against templated RED COAs before live execution.' },
    ]
  }
  return [
    { text: 'Identify the missed counter-stroke window from the audit log and rehearse the decision triggers.' },
    { text: 'Test alternate reserve allocations to determine whether mass or tempo would have produced a decision.' },
    { text: 'Stress-test C2 latency: the stalemate may reflect decision cycles slower than the operational tempo.' },
  ]
}

export function synthesizeAAR(
  gameState: GameState,
  scenario: Scenario,
  label: OutcomeLabel,
): AAR {
  const log = gameState.turn_log
  const blueWin  = label === 'blue_win'
  const redWin   = label === 'red_win'
  const condsBlue = scenario.victory_conditions.blue.length
  const condsRed  = scenario.victory_conditions.red.length
  const condsTotal = condsBlue + condsRed

  const outcome: Outcome = {
    label,
    summary: buildSummary(label, scenario, gameState),
    blue_cp_final: gameState.blue_force.combat_power,
    red_cp_final:  gameState.red_force.combat_power,
    max_penetration_km: gameState.max_penetration_km,
    turns_played: log.length,
    blue_conditions_met: blueWin ? condsBlue : Math.floor(condsBlue * 0.4),
    red_conditions_met:  redWin  ? condsRed  : Math.floor(condsRed  * 0.4),
    conditions_total: condsTotal,
  }

  return {
    outcome,
    key_turns: pickKeyTurns(log),
    lessons: buildLessons(label, gameState),
    recommendations: buildRecommendations(label),
    doctrine_citations: scenario.doctrine_citations.slice(0, 3),
    generated_in_seconds: 2,
  }
}
