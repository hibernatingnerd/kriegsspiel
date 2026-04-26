'use client'

import { useState, useEffect, useRef } from 'react'
import type { Scenario, GameState, DecisionKey } from '@/lib/schema'
import { GREY_HORIZON_AUDIT, type AuditEntry, type AuditCategory } from '@/lib/mock-audit'

interface Props {
  scenario: Scenario
  gameState: GameState
  onDecision: (key: DecisionKey, note: string) => void
  disabled?: boolean
  simulating?: boolean
}

// ── Category styling ──────────────────────────────────────────────────────

const CAT_COLOR: Record<AuditCategory, string> = {
  INTEL:      'var(--blue)',
  MOVEMENT:   'var(--text)',
  FIRES:      'var(--red)',
  CYBER:      'var(--amber)',
  EW:         'var(--amber)',
  C2:         'var(--green)',
  ASSESSMENT: 'var(--accent)',
  SYSTEM:     'var(--dimmer)',
}

const ADJ_STEPS = [
  'Running scenario engine…',
  'Cross-referencing doctrine…',
  'Calculating combat effects…',
  'Generating adversary response…',
]

function CatBadge({ cat }: { cat: AuditCategory }) {
  return (
    <span style={{
      color: CAT_COLOR[cat],
      fontSize: 10,
      letterSpacing: '0.1em',
      minWidth: 80,
      display: 'inline-block',
    }}>
      [{cat}]
    </span>
  )
}

function CpBar({ label, value, side }: { label: string; value: number; side: 'blue' | 'red' }) {
  const fill = side === 'blue' ? 'var(--blue)' : 'var(--red)'
  const textColor = value < 35 ? 'var(--red)' : value < 55 ? 'var(--amber)' : fill
  return (
    <div style={{ marginBottom: 10 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, marginBottom: 3 }}>
        <span className="dim">{label}</span>
        <span style={{ color: textColor, fontWeight: 600 }}>{value}%</span>
      </div>
      <div className="cp-bar-track">
        <div className="cp-bar-fill" style={{ width: `${value}%`, background: fill }} />
      </div>
    </div>
  )
}

// ── Main component ────────────────────────────────────────────────────────

export default function RunView({ scenario, gameState, onDecision, disabled = false, simulating = false }: Props) {
  const [selectedKey, setSelectedKey] = useState<DecisionKey | null>(null)
  const [note, setNote] = useState('')
  const [isAdjudicating, setIsAdjudicating] = useState(false)
  const [adjStep, setAdjStep] = useState(0)
  const logRef = useRef<HTMLDivElement>(null)

  // Reset selection when turn advances
  useEffect(() => {
    setSelectedKey(null)
    setNote('')
  }, [gameState.current_turn])

  // Auto-scroll log to bottom when state changes
  useEffect(() => {
    if (logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight
    }
  }, [gameState.current_turn, gameState.turn_log.length, isAdjudicating])

  async function handleSubmit() {
    if (!selectedKey) return
    setIsAdjudicating(true)
    setAdjStep(0)
    for (let i = 0; i < ADJ_STEPS.length; i++) {
      await new Promise((r) => setTimeout(r, 420))
      setAdjStep(i + 1)
    }
    await new Promise((r) => setTimeout(r, 300))
    setIsAdjudicating(false)
    onDecision(selectedKey, note)
  }

  const { pending_decision: pending, turn_log, current_turn } = gameState
  const blueCP = gameState.blue_force.combat_power
  const redCP  = gameState.red_force.combat_power

  // Build the full list of turns to render in the log
  const turnsToShow = Array.from({ length: current_turn }, (_, i) => i + 1)

  return (
    <div style={{ display: 'flex', gap: 20, alignItems: 'flex-start' }}>

      {/* ── LEFT: Audit log ── */}
      <div style={{ flex: '0 0 62%' }}>
        <div className="card" style={{ height: 'calc(100vh - 200px)', display: 'flex', flexDirection: 'column' }}>
          <div className="card-header" style={{ flexShrink: 0 }}>
            <div>
              <span className="title">AUDIT LOG</span>
              <span className="dim" style={{ marginLeft: 12, fontSize: 11 }}>{scenario.name}</span>
            </div>
            <div className="dim" style={{ fontSize: 11 }}>
              {turn_log.length} turns adjudicated · T+{(current_turn - 1) * 6}h elapsed
            </div>
          </div>

          {/* Scrollable log body */}
          <div
            ref={logRef}
            className="card-body"
            style={{
              flex: 1,
              overflowY: 'auto',
              padding: '12px 20px',
              fontFamily: 'var(--font)',
              fontSize: 12,
              lineHeight: 1.6,
            }}
          >
            {turnsToShow.map((t) => {
              const entries: AuditEntry[] = GREY_HORIZON_AUDIT[t] ?? []
              const baseHour = (t - 1) * 6
              const record = turn_log.find((r) => r.turn === t)
              const isPending = t === current_turn && !record

              return (
                <div key={t}>
                  {/* Turn block header */}
                  <div style={{
                    color: 'var(--dimmer)',
                    fontSize: 10,
                    letterSpacing: '0.1em',
                    borderTop: t === 1 ? 'none' : '1px solid var(--border-soft)',
                    paddingTop: t === 1 ? 0 : 12,
                    marginTop: t === 1 ? 0 : 12,
                    marginBottom: 8,
                  }}>
                    {'─'.repeat(4)} T+{String(baseHour).padStart(2, '0')}:00 {'─'.repeat(60)}
                  </div>

                  {/* Log entries */}
                  {entries.map((e, i) => (
                    <div key={i} style={{ marginBottom: 4, display: 'flex', gap: 10 }}>
                      <span style={{ color: 'var(--dimmer)', minWidth: 60, flexShrink: 0 }}>{e.time}</span>
                      <CatBadge cat={e.category} />
                      <span style={{ color: e.category === 'SYSTEM' ? 'var(--dimmer)' : 'var(--text)' }}>
                        {e.text}
                      </span>
                    </div>
                  ))}

                  {/* Decision separator */}
                  {record ? (
                    <>
                      {/* Completed decision */}
                      <div style={{
                        margin: '10px 0 6px',
                        color: 'var(--accent)',
                        fontSize: 11,
                        letterSpacing: '0.08em',
                        borderTop: '1px solid rgba(255,210,74,0.25)',
                        paddingTop: 8,
                      }}>
                        ━━ T+{String(baseHour + 6).padStart(2, '0')}:00 &nbsp;
                        DECISION {t} &nbsp;·&nbsp; BLUE: {record.blue_action_label}
                        {record.blue_note && (
                          <span className="dim"> — &ldquo;{record.blue_note}&rdquo;</span>
                        )}
                        &nbsp; ━━
                      </div>
                      <div style={{ marginBottom: 4, display: 'flex', gap: 10 }}>
                        <span style={{ color: 'var(--dimmer)', minWidth: 60, flexShrink: 0 }}>T+{String(baseHour + 6).padStart(2, '0')}:01</span>
                        <span style={{ color: 'var(--green)', fontSize: 10, letterSpacing: '0.1em', minWidth: 80, display: 'inline-block' }}>[ADJUDICATED]</span>
                        <span style={{ color: 'var(--dim)' }}>{record.narrative}</span>
                      </div>
                      <div style={{ marginBottom: 8, paddingLeft: 152, fontSize: 11, color: 'var(--dimmer)' }}>
                        CP: BLUE {record.blue_cp_after}% · RED {record.red_cp_after}%
                        &nbsp;·&nbsp; Penetration {record.penetration_km_after.toFixed(1)} km
                        {record.doctrine_refs.length > 0 && (
                          <span> · {record.doctrine_refs.join(', ')}</span>
                        )}
                      </div>
                    </>
                  ) : isPending ? (
                    /* Pending decision marker */
                    <div style={{
                      margin: '10px 0',
                      borderTop: '1px solid rgba(255,210,74,0.4)',
                      borderBottom: '1px solid rgba(255,210,74,0.4)',
                      padding: '8px 0',
                      color: 'var(--accent)',
                      fontSize: 11,
                      letterSpacing: '0.1em',
                    }}>
                      {isAdjudicating ? (
                        <span>
                          <span className="adj-spinner" style={{ display: 'inline-block', width: 6, height: 6, borderRadius: '50%', background: 'var(--accent)', marginRight: 8, verticalAlign: 'middle' }} />
                          ADJUDICATING — {ADJ_STEPS[adjStep] ?? ADJ_STEPS[ADJ_STEPS.length - 1]}
                        </span>
                      ) : (
                        <>━━ T+{String(baseHour + 6).padStart(2, '0')}:00 &nbsp; DECISION {t} — AWAITING INPUT &nbsp; {'░'.repeat(12)} ━━</>
                      )}
                    </div>
                  ) : null}
                </div>
              )
            })}
          </div>
        </div>
      </div>

      {/* ── RIGHT: Status + Decision ── */}
      <div style={{ flex: '0 0 calc(38% - 20px)', display: 'flex', flexDirection: 'column', gap: 16 }}>

        {/* Status */}
        <div className="panel">
          <div className="panel-title">Status — Turn {current_turn} / {scenario.turns_total}</div>
          <div className="grid-2" style={{ gap: 8, marginBottom: 14 }}>
            <div className="stat">
              <div className="v accent">{current_turn} / {scenario.turns_total}</div>
              <div className="l">Turn</div>
            </div>
            <div className="stat">
              <div className="v" style={{ color: gameState.max_penetration_km >= 22 ? 'var(--red)' : 'var(--amber)' }}>
                {gameState.max_penetration_km.toFixed(1)} km
              </div>
              <div className="l">Max Penetration</div>
            </div>
          </div>
          <CpBar label={`BLUE — ${scenario.blue_force.name.slice(0, 28)}`} value={blueCP} side="blue" />
          <CpBar label={`RED — ${scenario.red_force.name.slice(0, 28)}`}  value={redCP}  side="red" />
          <div className="small-meta" style={{ marginTop: 10 }}>
            T+{(current_turn - 1) * 6}h elapsed · {scenario.timeline_hours}h total · next check-in T+{current_turn * 6}h
          </div>
        </div>

        {/* Decision panel */}
        {simulating ? (
          <div className="adjudicating">
            <div style={{ marginBottom: 14 }}>
              <span className="adj-spinner" />
              <span className="accent" style={{ letterSpacing: '0.12em', fontSize: 12 }}>AUTO-SIM RUNNING</span>
            </div>
            <div style={{ marginBottom: 10 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, marginBottom: 4 }}>
                <span className="dim">Turn</span>
                <span style={{ color: 'var(--amber)', fontWeight: 600 }}>{current_turn} / {scenario.turns_total}</span>
              </div>
              <div className="cp-bar-track">
                <div className="cp-bar-fill" style={{
                  width: `${(current_turn / scenario.turns_total) * 100}%`,
                  background: 'var(--amber)',
                  transition: 'width 0.4s ease',
                }} />
              </div>
            </div>
            <CpBar label={`BLUE — ${scenario.blue_force.name.slice(0, 22)}`} value={blueCP} side="blue" />
            <CpBar label={`RED — ${scenario.red_force.name.slice(0, 22)}`}   value={redCP}  side="red"  />
            <div className="small-meta" style={{ textAlign: 'center', marginTop: 8 }}>
              engine resolving both sides · BLUE strategy: HOLD
            </div>
          </div>
        ) : isAdjudicating ? (
          <div className="adjudicating">
            <div style={{ marginBottom: 14 }}>
              <span className="adj-spinner" />
              <span className="accent" style={{ letterSpacing: '0.12em', fontSize: 12 }}>ADJUDICATING</span>
            </div>
            {ADJ_STEPS.map((step, i) => (
              <div key={i} style={{
                fontSize: 11, marginBottom: 5,
                color: i < adjStep ? 'var(--green)' : i === adjStep ? 'var(--accent)' : 'var(--dimmer)',
              }}>
                {i < adjStep ? '✓' : i === adjStep ? '▸' : '○'} {step}
              </div>
            ))}
            <div className="small-meta" style={{ textAlign: 'center', marginTop: 12 }}>
              claude-opus-4-7 · doctrine cross-reference · {scenario.doctrine_citations.length} refs loaded
            </div>
          </div>
        ) : pending ? (
          <div className="card">
            <div className="card-header" style={{ borderColor: 'rgba(255,210,74,0.3)' }}>
              <span className="title">DECISION {pending.turn}</span>
              <span className="pill warn">⚡ CHECK-IN DUE</span>
            </div>
            <div className="card-body">
              <div style={{
                fontSize: 12, lineHeight: 1.65,
                background: 'var(--surface-2)',
                padding: '10px 12px',
                borderRadius: 4,
                marginBottom: 14,
                color: 'var(--text)',
              }}>
                {pending.context}
              </div>

              {pending.options.map((opt) => (
                <button
                  key={opt.key}
                  className={`decision-opt${selectedKey === opt.key ? ' selected' : ''}`}
                  onClick={() => setSelectedKey(opt.key)}
                >
                  <div className="opt-label">{opt.label}</div>
                  <div className="opt-sub">{opt.sub_label}</div>
                  <div className="opt-hint">{opt.consequence_hint}</div>
                </button>
              ))}

              <div style={{ marginTop: 12 }}>
                <div className="label" style={{ marginBottom: 6 }}>Commander&apos;s Note (optional)</div>
                <textarea
                  placeholder="Rationale for the AAR…"
                  value={note}
                  onChange={(e) => setNote(e.target.value)}
                  style={{ minHeight: 52, fontSize: 12 }}
                />
              </div>

              <button
                className="btn-primary"
                style={{ width: '100%', marginTop: 12, padding: '11px 0' }}
                disabled={!selectedKey || disabled}
                onClick={handleSubmit}
              >
                {disabled ? 'RESOLVING…' : 'SUBMIT DECISION  →'}
              </button>
            </div>
          </div>
        ) : (
          <div className="panel" style={{ textAlign: 'center', padding: 24 }}>
            <div className="accent" style={{ marginBottom: 6 }}>AWAITING NEXT CHECK-IN</div>
            <div className="dim" style={{ fontSize: 11 }}>Next decision window T+{current_turn * 6}h</div>
          </div>
        )}

        {/* Quick doctrine ref */}
        {scenario.doctrine_citations.slice(0, 1).map((c, i) => (
          <div className="citation" key={i} style={{ marginBottom: 0 }}>
            <div className="text" style={{ fontSize: 11 }}>"{c.text}"</div>
            <div className="src">{c.source}</div>
          </div>
        ))}

      </div>
    </div>
  )
}
