'use client'

import type { Scenario, GameState } from '@/lib/schema'

interface Props {
  scenario: Scenario
  gameState: GameState
  onRunAgain: () => void
  onNewScenario: () => void
}

const OUTCOME_DISPLAY = {
  blue_win: { label: 'BLUE WIN',  color: 'var(--green)' },
  red_win:  { label: 'RED WIN',   color: 'var(--red)'   },
  draw:     { label: 'DRAW',      color: 'var(--amber)'  },
}

const CATEGORY_COLOR: Record<string, string> = {
  strategic:   'var(--accent)',
  operational: 'var(--blue)',
  tactical:    'var(--green)',
  doctrinal:   'var(--amber)',
  cognitive:   'var(--dim)',
}

export default function DebriefView({ scenario, gameState, onRunAgain, onNewScenario }: Props) {
  const { aar } = gameState
  if (!aar) return <div className="dim" style={{ padding: 32 }}>No AAR data available.</div>

  const { outcome } = aar
  const outDisp = OUTCOME_DISPLAY[outcome.label] ?? OUTCOME_DISPLAY['draw']

  const keyTurnRecords = gameState.turn_log.filter((r) => aar.key_turns.includes(r.turn))

  return (
    <div>
      {/* Outcome header */}
      <div className="card" style={{ marginBottom: 20 }}>
        <div className="card-header">
          <div>
            <span className="title">AFTER-ACTION REVIEW //</span>
            <span style={{ marginLeft: 10 }}>{scenario.name}</span>
            <span className="pill" style={{ marginLeft: 10 }}>{scenario.run_id}</span>
            <span
              className="pill warn"
              style={{ marginLeft: 10 }}
              title="Locally synthesized — backend /api/aar endpoint not yet implemented"
            >
              STUB AAR
            </span>
          </div>
          <div className="dim" style={{ fontSize: 11 }}>
            RUN-{gameState.run_id} · {outcome.turns_played} turns · GEN. {aar.generated_in_seconds}s
          </div>
        </div>
        <div className="card-body">
          <h2 style={{ marginBottom: 8 }}>{scenario.name} — After-Action Review</h2>
          <p className="summary-text">{outcome.summary}</p>

          <div className="grid-4" style={{ marginBottom: 20 }}>
            <div className="stat">
              <div className="v" style={{ color: outDisp.color }}>{outDisp.label}</div>
              <div className="l">Outcome</div>
            </div>
            <div className="stat">
              <div className="v">{outcome.turns_played} / {scenario.turns_total}</div>
              <div className="l">Turns Played</div>
            </div>
            <div className="stat">
              <div className="v amber">{outcome.blue_cp_final}%</div>
              <div className="l">Blue CP Retained</div>
            </div>
            <div className="stat">
              <div className="v">{outcome.max_penetration_km.toFixed(1)} km</div>
              <div className="l">Max Penetration</div>
            </div>
          </div>

          <div className="grid-2">
            <div className="panel">
              <div className="panel-title" style={{ color: 'var(--blue)' }}>
                Blue Objectives
                <span style={{ color: 'var(--green)', fontSize: 11 }}>{outcome.blue_conditions_met} / {outcome.conditions_total} met</span>
              </div>
              {scenario.victory_conditions.blue.map((c, i) => {
                const met = i < outcome.blue_conditions_met
                return (
                  <div key={i} className="row" style={{ fontSize: 11 }}>
                    <span style={{ color: met ? 'var(--green)' : 'var(--red)' }}>
                      {met ? '✓' : '✗'} {c}
                    </span>
                  </div>
                )
              })}
            </div>
            <div className="panel">
              <div className="panel-title" style={{ color: 'var(--red)' }}>
                Red Objectives
                <span style={{ color: 'var(--red)', fontSize: 11 }}>{outcome.red_conditions_met} / {outcome.conditions_total} met</span>
              </div>
              {scenario.victory_conditions.red.map((c, i) => {
                const met = i < outcome.red_conditions_met
                return (
                  <div key={i} className="row" style={{ fontSize: 11 }}>
                    <span style={{ color: met ? 'var(--red)' : 'var(--green)' }}>
                      {met ? '✓' : '✗'} {c}
                    </span>
                  </div>
                )
              })}
            </div>
          </div>
        </div>
      </div>

      {/* Main AAR content */}
      <div className="grid-2" style={{ gap: 20, alignItems: 'start' }}>

        {/* Left: key decisions + doctrine */}
        <div>
          <div className="panel" style={{ marginBottom: 16 }}>
            <div className="panel-title">Key Decisions</div>
            {keyTurnRecords.length === 0 && (
              <div className="dim" style={{ fontSize: 12 }}>No key turns marked.</div>
            )}
            {keyTurnRecords.map((r) => (
              <div className="decision" key={r.turn}>
                <div className="head">
                  <span className="turn accent">TURN {r.turn}</span>
                  <span className="pair dim">BLUE: {r.blue_action_label}  ·  RED: {r.red_action_label}</span>
                </div>
                <div className="what">{r.narrative}</div>
                {r.blue_note && (
                  <div className="alt">Commander note: "{r.blue_note}"</div>
                )}
                {r.doctrine_refs.length > 0 && (
                  <div className="dim" style={{ fontSize: 10, marginTop: 4 }}>
                    Refs: {r.doctrine_refs.join(' · ')}
                  </div>
                )}
              </div>
            ))}
          </div>

          <div className="panel">
            <div className="panel-title">Doctrine Grounding</div>
            {aar.doctrine_citations.map((c, i) => (
              <div className="citation" key={i}>
                <div className="text">"{c.text}"</div>
                <div className="src">{c.source}</div>
                <div className="why">{c.relevance}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Right: lessons + recommendations */}
        <div>
          <div className="panel" style={{ marginBottom: 16 }}>
            <div className="panel-title">Lessons</div>
            <ul className="lessons">
              {aar.lessons.map((l, i) => (
                <li key={i}>
                  <span
                    className="tag"
                    style={{ color: CATEGORY_COLOR[l.category] ?? 'var(--accent)' }}
                  >
                    {l.category.toUpperCase()}
                  </span>
                  {l.text}
                </li>
              ))}
            </ul>
          </div>

          <div className="panel" style={{ marginBottom: 20 }}>
            <div className="panel-title">Recommendations</div>
            <ul className="recs">
              {aar.recommendations.map((r, i) => (
                <li key={i}>{r.text}</li>
              ))}
            </ul>
          </div>

          <div style={{ display: 'flex', gap: 10 }}>
            <button
              className="btn-primary"
              style={{ flex: 1, padding: '11px 0' }}
              onClick={onRunAgain}
            >
              RUN AGAIN  ↺
            </button>
            <button
              style={{ flex: 1, padding: '11px 0' }}
              onClick={onNewScenario}
            >
              NEW SCENARIO
            </button>
          </div>

          <div className="small-meta" style={{ textAlign: 'center', marginTop: 12 }}>
            Generated by Kriegsspiel After-Action Reviewer · {aar.generated_in_seconds}s wall
            · sources: scenario audit log, JCS Doctrine Library, FM corpus
            · model: claude-opus-4-7
          </div>
        </div>

      </div>
    </div>
  )
}
