'use client'
// RunView-with-map.tsx
// Replaces dashboard/src/components/RunView.tsx
//
// Changes vs original:
//  1. Imports BattleMap and renders it above the audit log
//  2. Keeps BoardUnit[] state; updates positions after each adjudication
//  3. Calls adjudicateWithLLM() instead of mockAdjudicate()
//  4. Shows unit readiness summary in the status panel

import { useState, useEffect, useRef } from 'react'
import type { Scenario, GameState, DecisionKey } from '@/lib/schema'
import type { BoardUnit, UnitMove } from '@/lib/battle-types'
import { mockAdjudicate } from '@/lib/adjudicate'
import BattleMap from '@/components/BattleMap'

// ── Seed initial unit positions from scenario forces ──────────────────────
// In production these come from the Python backend's WorldState serialisation.
// For now we scatter them deterministically across the grid.

function seedUnits(scenario: Scenario): BoardUnit[] {
  const units: BoardUnit[] = []
  let ri = 0

  for (const u of scenario.blue_force.units) {
    units.push({
      unit_id:    `BLUE_${ri}`,
      side:       'BLUE',
      designation: u.designation,
      category:   u.type,
      position:   [3 + (ri % 4), 4 + ri],
      readiness:  'FULLY_OPERATIONAL',
      strength:   1.0,
      supply_days_remaining: 5,
      posture:    'DEFENSIVE',
    })
    ri++
  }

  let rj = 0
  for (const u of scenario.red_force.units) {
    units.push({
      unit_id:    `RED_${rj}`,
      side:       'RED',
      designation: u.designation,
      category:   u.type,
      position:   [14 + (rj % 4), 16 + rj],
      readiness:  'FULLY_OPERATIONAL',
      strength:   1.0,
      supply_days_remaining: 5,
      posture:    'OFFENSIVE',
    })
    rj++
  }

  return units
}

// ── Sub-components (same as original RunView) ─────────────────────────────

const CAT_COLOR: Record<string, string> = {
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
  'Sending orders to adjudicator…',
  'LLM generating RED response…',
  'Calculating combat effects…',
  'Applying unit moves…',
]

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

interface Props {
  scenario: Scenario
  gameState: GameState
  onDecision: (nextState: GameState) => void
}

export default function RunViewWithMap({ scenario, gameState, onDecision }: Props) {
  const [selectedKey, setSelectedKey]     = useState<DecisionKey | null>(null)
  const [note, setNote]                   = useState('')
  const [isAdjudicating, setIsAdjudicating] = useState(false)
  const [adjStep, setAdjStep]             = useState(0)
  const [adjError, setAdjError]           = useState<string | null>(null)
  const [units, setUnits]                 = useState<BoardUnit[]>(() => seedUnits(scenario))
  const [lastMoves, setLastMoves]         = useState<UnitMove[]>([])
  const logRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    setSelectedKey(null)
    setNote('')
    setAdjError(null)
  }, [gameState.current_turn])

  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight
  }, [gameState.current_turn, gameState.turn_log.length, isAdjudicating])

  async function handleSubmit() {
    if (!selectedKey) return
    setIsAdjudicating(true)
    setAdjStep(0)
    setAdjError(null)

    // Animate the adjudication steps while waiting for the real API
    const stepTimer = setInterval(() => {
      setAdjStep(s => Math.min(s + 1, ADJ_STEPS.length - 1))
    }, 800)

    try {
      const nextGS = mockAdjudicate(gameState, selectedKey, note)
      setLastMoves([])
      onDecision(nextGS)
    } catch (err) {
      setAdjError(err instanceof Error ? err.message : 'Adjudication failed')
    } finally {
      clearInterval(stepTimer)
      setIsAdjudicating(false)
    }
  }

  const { pending_decision: pending, turn_log, current_turn } = gameState
  const blueCP = gameState.blue_force.combat_power
  const redCP  = gameState.red_force.combat_power
  const turnsToShow = Array.from({ length: current_turn }, (_, i) => i + 1)

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>

      {/* ── Battle Map (full width, snapshot per iteration) ── */}
      <div className="card" style={{ padding: '12px 16px' }}>
        <div className="card-header" style={{ marginBottom: 10 }}>
          <span className="title">TACTICAL MAP</span>
          <span className="dim" style={{ fontSize: 11 }}>
            {units.filter(u => u.readiness !== 'DESTROYED').length} units active
          </span>
        </div>
        <div style={{ overflowX: 'auto' }}>
          <BattleMap units={units} lastMoves={lastMoves} turn={current_turn} />
        </div>
      </div>

      {/* ── Bottom row: Audit log + Status/Decision ── */}
      <div style={{ display: 'flex', gap: 20, alignItems: 'flex-start' }}>

        {/* Audit log */}
        <div style={{ flex: '0 0 62%' }}>
          <div className="card" style={{ height: 420, display: 'flex', flexDirection: 'column' }}>
            <div className="card-header" style={{ flexShrink: 0 }}>
              <div>
                <span className="title">AUDIT LOG</span>
                <span className="dim" style={{ marginLeft: 12, fontSize: 11 }}>{scenario.name}</span>
              </div>
              <div className="dim" style={{ fontSize: 11 }}>
                {turn_log.length} turns · T+{(current_turn - 1) * 6}h elapsed
              </div>
            </div>
            <div
              ref={logRef}
              className="card-body"
              style={{ flex: 1, overflowY: 'auto', padding: '12px 20px', fontSize: 12, lineHeight: 1.6 }}
            >
              {turnsToShow.map((t) => {
                const baseHour = (t - 1) * 6
                const record = turn_log.find(r => r.turn === t)
                const isPending = t === current_turn && !record

                return (
                  <div key={t}>
                    <div style={{
                      color: 'var(--dimmer)', fontSize: 10, letterSpacing: '0.1em',
                      borderTop: t === 1 ? 'none' : '1px solid var(--border-soft)',
                      paddingTop: t === 1 ? 0 : 12, marginTop: t === 1 ? 0 : 12, marginBottom: 8,
                    }}>
                      {'─'.repeat(4)} T+{String(baseHour).padStart(2, '0')}:00 {'─'.repeat(40)}
                    </div>

                    {record ? (
                      <>
                        <div style={{ marginBottom: 4, display: 'flex', gap: 10 }}>
                          <span style={{ color: 'var(--green)', fontSize: 10, letterSpacing: '0.1em', minWidth: 90, display: 'inline-block' }}>[ADJUDICATED]</span>
                          <span style={{ color: 'var(--dim)' }}>{record.narrative}</span>
                        </div>
                        <div style={{ marginBottom: 8, paddingLeft: 100, fontSize: 11, color: 'var(--dimmer)' }}>
                          CP: BLUE {record.blue_cp_after.toFixed(0)}% · RED {record.red_cp_after.toFixed(0)}%
                          &nbsp;·&nbsp; Penetration {record.penetration_km_after.toFixed(1)} km
                          {record.doctrine_refs.length > 0 && <span> · {record.doctrine_refs.join(', ')}</span>}
                        </div>
                      </>
                    ) : isPending ? (
                      <div style={{
                        margin: '10px 0', borderTop: '1px solid rgba(255,210,74,0.4)',
                        borderBottom: '1px solid rgba(255,210,74,0.4)', padding: '8px 0',
                        color: 'var(--accent)', fontSize: 11, letterSpacing: '0.1em',
                      }}>
                        {isAdjudicating
                          ? `▸ ${ADJ_STEPS[adjStep]}`
                          : `━━ T+${String(baseHour + 6).padStart(2, '0')}:00  DECISION ${t} — AWAITING INPUT ░░░░░░ ━━`
                        }
                      </div>
                    ) : null}
                  </div>
                )
              })}
              {adjError && (
                <div style={{ color: 'var(--red)', marginTop: 8, fontSize: 11 }}>
                  ⚠ {adjError}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Status + Decision */}
        <div style={{ flex: '0 0 calc(38% - 20px)', display: 'flex', flexDirection: 'column', gap: 16 }}>

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

            {/* Readiness summary */}
            <div style={{ fontSize: 10, color: 'var(--dimmer)', marginTop: 8 }}>
              {['FULLY_OPERATIONAL','DEGRADED','SUPPRESSED','DESTROYED'].map(r => {
                const count = units.filter(u => u.readiness === r).length
                return count > 0 ? (
                  <span key={r} style={{ marginRight: 12 }}>
                    {r.slice(0,3)}: {count}
                  </span>
                ) : null
              })}
            </div>
          </div>

          {/* Decision panel */}
          {isAdjudicating ? (
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
                  background: 'var(--surface-2)', padding: '10px 12px', borderRadius: 4, marginBottom: 14,
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
                  disabled={!selectedKey}
                  onClick={handleSubmit}
                >
                  SUBMIT DECISION  →
                </button>
              </div>
            </div>
          ) : (
            <div className="panel" style={{ textAlign: 'center', padding: 24 }}>
              <div className="accent" style={{ marginBottom: 6 }}>AWAITING NEXT CHECK-IN</div>
              <div className="dim" style={{ fontSize: 11 }}>Next decision window T+{current_turn * 6}h</div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
