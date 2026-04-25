'use client'

import { useState } from 'react'
import type { Scenario, ScenarioConfig } from '@/lib/schema'
import { ALL_SCENARIOS } from '@/lib/mock-data'

interface Props {
  onLaunch: (config: ScenarioConfig) => void
}

const TIER_LABEL: Record<string, string> = {
  near_peer:  'NEAR-PEER',
  peer:       'PEER',
  hybrid:     'HYBRID',
  asymmetric: 'ASYMMETRIC',
}

export default function SetupView({ onLaunch }: Props) {
  const [selectedId, setSelectedId] = useState<string>(ALL_SCENARIOS[0].id)
  const [label, setLabel] = useState('')
  const [timelineHours, setTimelineHours] = useState(72)
  const [activeModifiers, setActiveModifiers] = useState<Set<string>>(
    new Set(ALL_SCENARIOS[0].active_modifier_keys)
  )
  const [blueStrength, setBlueStrength] = useState(100)
  const [redStrength, setRedStrength] = useState(85)

  const scenario = ALL_SCENARIOS.find((s) => s.id === selectedId)!

  function selectScenario(s: Scenario) {
    setSelectedId(s.id)
    setTimelineHours(s.timeline_hours)
    setActiveModifiers(new Set(s.active_modifier_keys))
    setBlueStrength(100)
    setRedStrength(s.red_force.combat_power)
    setLabel('')
  }

  function toggleModifier(key: string) {
    setActiveModifiers((prev) => {
      const next = new Set(prev)
      next.has(key) ? next.delete(key) : next.add(key)
      return next
    })
  }

  function handleLaunch() {
    onLaunch({
      base_scenario_id: selectedId,
      label_override: label || scenario.name,
      timeline_hours: timelineHours,
      active_modifier_keys: [...activeModifiers],
      blue_force_strength: blueStrength,
      red_force_strength: redStrength,
    })
  }

  return (
    <div>
      <div className="grid-2" style={{ gap: 24, alignItems: 'start' }}>

        {/* ── Left: scenario selector ── */}
        <div>
          <div className="label" style={{ marginBottom: 12 }}>Prefab Scenarios</div>

          {ALL_SCENARIOS.map((s) => (
            <div
              key={s.id}
              className={`scenario-card${s.id === selectedId ? ' selected' : ''}`}
              onClick={() => selectScenario(s)}
            >
              {s.id === selectedId && <div className="selected-badge">SELECTED</div>}
              <div className="sc-name accent">{s.name}</div>
              <div className="sc-meta">
                <span className="dim">{s.classification}</span>
                <span style={{ margin: '0 8px', color: 'var(--border)' }}>·</span>
                <span className="pill">{TIER_LABEL[s.threat_tier] ?? s.threat_tier}</span>
                <span style={{ margin: '0 8px', color: 'var(--border)' }}>·</span>
                <span className="dim">{s.location.name} · {s.timeline_hours}h · {s.turns_total} turns</span>
              </div>
              <div className="sc-summary">{s.summary.slice(0, 160)}…</div>
            </div>
          ))}

          {/* Seed events */}
          {scenario.seed_events.length > 0 && (
            <div className="panel" style={{ marginTop: 16 }}>
              <div className="panel-title">
                Real-World Seed Events
                <span className="pill live">● GDELT + ACLED</span>
              </div>
              {scenario.seed_events.map((e, i) => (
                <div className="event-row" key={i}>
                  <div><span className="date accent">{e.date}</span> · {e.description}</div>
                  <div className="src dim">{e.source} · {e.source_id}</div>
                </div>
              ))}
              {scenario.seed_events.length === 0 && (
                <div className="dim" style={{ fontSize: 11 }}>No seed events for this scenario</div>
              )}
            </div>
          )}
        </div>

        {/* ── Right: configuration ── */}
        <div>
          <div className="label" style={{ marginBottom: 12 }}>Configure</div>

          <div className="panel" style={{ marginBottom: 16 }}>
            <div className="panel-title">Scenario Label</div>
            <input
              type="text"
              placeholder={scenario.name}
              value={label}
              onChange={(e) => setLabel(e.target.value)}
            />
          </div>

          <div className="panel" style={{ marginBottom: 16 }}>
            <div className="panel-title">Timeline</div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
              <span className="dim" style={{ fontSize: 11 }}>24h</span>
              <span className="accent">{timelineHours}h</span>
              <span className="dim" style={{ fontSize: 11 }}>120h</span>
            </div>
            <input
              type="range"
              min={24}
              max={120}
              step={6}
              value={timelineHours}
              onChange={(e) => setTimelineHours(Number(e.target.value))}
            />
          </div>

          <div className="panel" style={{ marginBottom: 16 }}>
            <div className="panel-title">Modifiers</div>
            {scenario.available_modifiers.map((m) => (
              <label className="check-row" key={m.key}>
                <input
                  type="checkbox"
                  checked={activeModifiers.has(m.key)}
                  onChange={() => toggleModifier(m.key)}
                />
                <div style={{ flex: 1 }}>
                  <div className="check-label">{m.label}</div>
                  <div className="check-desc dim">{m.description}</div>
                </div>
              </label>
            ))}
          </div>

          <div className="panel" style={{ marginBottom: 16 }}>
            <div className="panel-title">Force Strength</div>
            <div style={{ marginBottom: 14 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                <span className="blue" style={{ fontSize: 11 }}>BLUE — {scenario.blue_force.name.slice(0, 30)}</span>
                <span className="blue">{blueStrength}%</span>
              </div>
              <input
                type="range" min={50} max={100} value={blueStrength}
                onChange={(e) => setBlueStrength(Number(e.target.value))}
              />
            </div>
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                <span className="red" style={{ fontSize: 11 }}>RED — {scenario.red_force.name.slice(0, 30)}</span>
                <span className="red">{redStrength}%</span>
              </div>
              <input
                type="range" min={50} max={100} value={redStrength}
                onChange={(e) => setRedStrength(Number(e.target.value))}
              />
            </div>
          </div>

          <div className="panel" style={{ marginBottom: 20 }}>
            <div className="panel-title">Budget</div>
            <div className="row">
              <span className="dim">Package</span>
              <span>{scenario.budget.label}</span>
            </div>
            <div className="row">
              <span className="dim">Total</span>
              <span className="accent">{scenario.budget.total} {scenario.budget.unit}</span>
            </div>
          </div>

          <button className="btn-primary" style={{ width: '100%', fontSize: 14, padding: '12px 0' }} onClick={handleLaunch}>
            GENERATE &amp; LAUNCH  ▸▸
          </button>
          <div className="small-meta" style={{ marginTop: 10, textAlign: 'center' }}>
            Scenario will be generated by AI engine · check-ins every 6h real-time
          </div>
        </div>

      </div>
    </div>
  )
}
