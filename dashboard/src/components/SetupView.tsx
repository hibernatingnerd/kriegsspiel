'use client'

import { useState } from 'react'
import type { Scenario, ScenarioConfig, Force } from '@/lib/schema'
import { ALL_SCENARIOS } from '@/lib/mock-data'

interface Props {
  onLaunch: (config: ScenarioConfig) => void
  disabled?: boolean
}

const TYPE_COLOR: Record<string, string> = {
  LAND:        'var(--amber)',
  AMPHIBIOUS:  'var(--blue)',
  URBAN:       'var(--red)',
  HYBRID:      'var(--accent)',
}

const OBJ_LABEL: Record<string, string> = {
  ANNIHILATION:     'ANNIHILATION',
  RESOURCE_CONTROL: 'RESOURCE CONTROL',
  DECAPITATION:     'DECAPITATION',
}

const TIER_LABEL: Record<string, string> = {
  near_peer:  'NEAR-PEER',
  peer:       'PEER',
  hybrid:     'HYBRID',
  asymmetric: 'ASYMMETRIC',
}

function CpBar({ value, color }: { value: number; color: string }) {
  return (
    <div className="cp-bar-track" style={{ marginTop: 3 }}>
      <div className="cp-bar-fill" style={{ width: `${value}%`, background: color }} />
    </div>
  )
}

function ResourceGrid({ label, res, color }: {
  label: string
  res: Scenario['blue_resources']
  color: string
}) {
  return (
    <div>
      <div style={{ fontSize: 10, color, letterSpacing: '0.1em', marginBottom: 6 }}>{label}</div>
      <div className="row" style={{ fontSize: 11, marginBottom: 3 }}>
        <span className="dim">Budget</span>
        <span style={{ color }}>${res.dollars_millions.toLocaleString()}M</span>
      </div>
      <div className="row" style={{ fontSize: 11, marginBottom: 3 }}>
        <span className="dim">Income / turn</span>
        <span>${res.income_per_turn_millions}M</span>
      </div>
      <div style={{ marginTop: 6 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, marginBottom: 2 }}>
          <span className="dim">Supply Chain</span>
          <span style={{ color, fontWeight: 600 }}>{res.supply_chain}</span>
        </div>
        <CpBar value={res.supply_chain} color={color} />
      </div>
      <div style={{ marginTop: 5 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, marginBottom: 2 }}>
          <span className="dim">Stability</span>
          <span style={{ color: 'var(--green)', fontWeight: 600 }}>{res.stability}</span>
        </div>
        <CpBar value={res.stability} color="var(--green)" />
      </div>
      <div style={{ marginTop: 5 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, marginBottom: 2 }}>
          <span className="dim">Intel</span>
          <span style={{ color: 'var(--accent)', fontWeight: 600 }}>{res.intel}</span>
        </div>
        <CpBar value={res.intel} color="var(--accent)" />
      </div>
    </div>
  )
}

function ForcePanel({ force, color }: { force: Force; color: string }) {
  return (
    <div>
      <div style={{ fontSize: 10, color, letterSpacing: '0.1em', marginBottom: 4 }}>{force.side.toUpperCase()}</div>
      <div style={{ fontSize: 11, color, marginBottom: 4, fontWeight: 600 }}>{force.name}</div>
      <div style={{ fontSize: 10, marginBottom: 6 }}>
        <span className="dim">Starting CP: </span>
        <span style={{ color, fontWeight: 600 }}>{force.combat_power}</span>
        <span className="dim"> · {force.units.length} assets</span>
      </div>
      <CpBar value={force.combat_power} color={color} />
      <div style={{ marginTop: 8 }}>
        {force.units.map((u, i) => (
          <div key={i} style={{ fontSize: 10, color: 'var(--dim)', marginBottom: 2 }}>
            <span style={{ color: 'var(--dimmer)' }}>▸ </span>
            {u.designation}
            <span style={{ color: 'var(--dimmer)' }}> — {u.type}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

export default function SetupView({ onLaunch, disabled = false }: Props) {
  const [selectedId, setSelectedId] = useState<string>(ALL_SCENARIOS[0].id)
  const [label, setLabel]           = useState('')
  const [mode, setMode]             = useState<'manual' | 'auto'>('manual')
  const [autoTurns, setAutoTurns]   = useState(ALL_SCENARIOS[0].turns_total)

  const scenario  = ALL_SCENARIOS.find((s) => s.id === selectedId)!
  const typeColor = TYPE_COLOR[scenario.scenario_type] ?? 'var(--accent)'

  function handleSelectScenario(id: string) {
    setSelectedId(id)
    setLabel('')
    setAutoTurns(ALL_SCENARIOS.find((s) => s.id === id)!.turns_total)
  }

  function handleLaunch() {
    onLaunch({
      base_scenario_id: selectedId,
      label_override:   label.trim() || scenario.name,
      mode,
      auto_turns:       autoTurns,
    })
  }

  return (
    <div className="grid-2" style={{ gap: 24, alignItems: 'start' }}>

      {/* ── Left: scenario selector ── */}
      <div>
        <div className="label" style={{ marginBottom: 12 }}>Starter Kit Scenarios</div>

        {ALL_SCENARIOS.map((s) => {
          const tc       = TYPE_COLOR[s.scenario_type] ?? 'var(--accent)'
          const selected = s.id === selectedId
          return (
            <div
              key={s.id}
              className={`scenario-card${selected ? ' selected' : ''}`}
              onClick={() => handleSelectScenario(s.id)}
            >
              {selected && <div className="selected-badge">SELECTED</div>}

              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                <div className="sc-name" style={{ color: tc }}>{s.name}</div>
                <span className="pill" style={{ borderColor: tc, color: tc, fontSize: 9 }}>{s.scenario_type}</span>
                <span className="pill" style={{ fontSize: 9 }}>{TIER_LABEL[s.threat_tier]}</span>
              </div>

              <div style={{ display: 'flex', gap: 16, marginBottom: 6, fontSize: 10, color: 'var(--dim)' }}>
                <span>{s.classification}</span>
                <span>·</span>
                <span>{s.turns_total} turns · {s.timeline_hours}h</span>
                <span>·</span>
                <span style={{ color: tc }}>OBJ: {OBJ_LABEL[s.strategic_objective]}</span>
              </div>

              <div className="sc-summary">{s.summary.slice(0, 160)}…</div>

              <div style={{ display: 'flex', gap: 16, marginTop: 8, fontSize: 10 }}>
                <span className="dim">
                  OBJ: <span style={{ color: tc }}>{s.nodes.objective_node.split(' —')[0]}</span>
                </span>
                <span className="dim">
                  <span className="blue">{s.blue_force.units.length} BLUE</span>
                  {' · '}
                  <span className="red">{s.red_force.units.length} RED</span>
                </span>
              </div>
            </div>
          )
        })}
      </div>

      {/* ── Right: scenario briefing (read-only) ── */}
      <div>
        <div className="label" style={{ marginBottom: 12 }}>Scenario Briefing</div>

        {/* Header */}
        <div className="panel" style={{ marginBottom: 14 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
            <div style={{ fontSize: 16, fontWeight: 700, color: typeColor, letterSpacing: '0.1em' }}>
              {scenario.name}
            </div>
            <span className="pill" style={{ borderColor: typeColor, color: typeColor }}>{scenario.scenario_type}</span>
            <span className="pill">{TIER_LABEL[scenario.threat_tier]}</span>
            <span className="pill" style={{ marginLeft: 'auto', fontSize: 9, color: 'var(--dimmer)' }}>
              {scenario.classification}
            </span>
          </div>
          <div style={{ fontSize: 11, color: 'var(--dim)', lineHeight: 1.6 }}>{scenario.summary}</div>
          <div style={{ marginTop: 8, fontSize: 10, color: 'var(--dimmer)' }}>
            {scenario.turns_total} turns · {scenario.timeline_hours}h · {scenario.location.region}
          </div>
        </div>

        {/* Map nodes */}
        <div className="panel" style={{ marginBottom: 14 }}>
          <div className="panel-title">
            Map Nodes
            <span className="pill" style={{ borderColor: typeColor, color: typeColor, marginLeft: 8 }}>
              {scenario.nodes.contested_nodes.length} contested
            </span>
          </div>

          <div className="grid-2" style={{ gap: 12, marginBottom: 10 }}>
            <div>
              <div className="label" style={{ marginBottom: 4, fontSize: 9 }}>Entry Points</div>
              {[
                { label: 'BLUE land', val: scenario.nodes.blue_land_entry,  color: 'var(--blue)' },
                { label: 'BLUE sea',  val: scenario.nodes.blue_sea_entry,   color: 'var(--blue)' },
                { label: 'RED land',  val: scenario.nodes.red_land_entry,   color: 'var(--red)'  },
                { label: 'RED sea',   val: scenario.nodes.red_sea_entry,    color: 'var(--red)'  },
              ].map(({ label: l, val, color }) => (
                <div key={l} className="row" style={{ fontSize: 11, marginBottom: 2 }}>
                  <span style={{ color, fontSize: 9, letterSpacing: '0.06em' }}>{l}</span>
                  <span className="dim">{val}</span>
                </div>
              ))}
            </div>
            <div>
              <div className="label" style={{ marginBottom: 4, fontSize: 9 }}>Contested Nodes</div>
              {scenario.nodes.contested_nodes.map((n) => (
                <div key={n} className="row" style={{ fontSize: 11, marginBottom: 2 }}>
                  <span className="dim">▸ {n.split(' —')[0]}</span>
                  {n.split(' —')[0] === scenario.nodes.objective_node.split(' —')[0] && (
                    <span style={{ color: typeColor, fontSize: 9 }}>OBJECTIVE</span>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Forces */}
        <div className="panel" style={{ marginBottom: 14 }}>
          <div className="panel-title">Order of Battle</div>
          <div className="grid-2" style={{ gap: 16 }}>
            <ForcePanel force={scenario.blue_force} color="var(--blue)" />
            <ForcePanel force={scenario.red_force}  color="var(--red)"  />
          </div>
        </div>

        {/* Resources */}
        <div className="panel" style={{ marginBottom: 14 }}>
          <div className="panel-title">Opening Resources</div>
          <div className="grid-2" style={{ gap: 16 }}>
            <ResourceGrid label="BLUE" res={scenario.blue_resources} color="var(--blue)" />
            <ResourceGrid label="RED"  res={scenario.red_resources}  color="var(--red)"  />
          </div>
        </div>

        {/* Victory conditions */}
        <div className="panel" style={{ marginBottom: 14 }}>
          <div className="panel-title">Victory Conditions</div>
          <div className="grid-2" style={{ gap: 12 }}>
            <div>
              <div style={{ fontSize: 9, color: 'var(--blue)', letterSpacing: '0.1em', marginBottom: 6 }}>BLUE WIN</div>
              {scenario.victory_conditions.blue.map((c, i) => (
                <div key={i} style={{ fontSize: 10, color: 'var(--blue)', marginBottom: 4, lineHeight: 1.5 }}>▸ {c}</div>
              ))}
            </div>
            <div>
              <div style={{ fontSize: 9, color: 'var(--red)', letterSpacing: '0.1em', marginBottom: 6 }}>RED WIN</div>
              {scenario.victory_conditions.red.map((c, i) => (
                <div key={i} style={{ fontSize: 10, color: 'var(--red)', marginBottom: 4, lineHeight: 1.5 }}>▸ {c}</div>
              ))}
            </div>
          </div>
        </div>

        {/* Active rules / modifiers (display-only) */}
        {scenario.active_modifier_keys.length > 0 && (
          <div className="panel" style={{ marginBottom: 14 }}>
            <div className="panel-title">Active Rules</div>
            {scenario.available_modifiers
              .filter((m) => scenario.active_modifier_keys.includes(m.key))
              .map((m) => (
                <div key={m.key} style={{ marginBottom: 8 }}>
                  <div style={{ fontSize: 11, color: typeColor, marginBottom: 2 }}>{m.label}</div>
                  <div style={{ fontSize: 10, color: 'var(--dim)' }}>{m.description}</div>
                </div>
              ))}
          </div>
        )}

        {/* Run label + mode + launch */}
        <div className="panel" style={{ marginBottom: 14 }}>
          <div className="panel-title">Run Label <span className="dim" style={{ fontWeight: 400 }}>(optional)</span></div>
          <input
            type="text"
            placeholder={scenario.name}
            value={label}
            onChange={(e) => setLabel(e.target.value)}
            style={{ marginBottom: 16 }}
          />

          <div className="panel-title" style={{ marginBottom: 8 }}>Execution Mode</div>
          <div style={{ display: 'flex', gap: 8, marginBottom: mode === 'auto' ? 12 : 0 }}>
            {(['manual', 'auto'] as const).map((m) => (
              <button
                key={m}
                onClick={() => setMode(m)}
                style={{
                  flex: 1,
                  padding: '8px 0',
                  fontSize: 11,
                  letterSpacing: '0.1em',
                  background: mode === m ? (m === 'auto' ? 'rgba(255,210,74,0.12)' : 'rgba(74,158,255,0.12)') : 'var(--surface-2)',
                  border: `1px solid ${mode === m ? (m === 'auto' ? 'var(--amber)' : 'var(--blue)') : 'var(--border)'}`,
                  color: mode === m ? (m === 'auto' ? 'var(--amber)' : 'var(--blue)') : 'var(--dim)',
                  borderRadius: 4,
                  cursor: 'pointer',
                  fontFamily: 'var(--font)',
                }}
              >
                {m === 'manual' ? 'MANUAL' : 'AUTO-SIM'}
              </button>
            ))}
          </div>

          {mode === 'auto' && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, paddingTop: 4 }}>
              <span style={{ fontSize: 11, color: 'var(--dim)', letterSpacing: '0.08em', flex: 1 }}>
                Turns to simulate
              </span>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <button
                  onClick={() => setAutoTurns((n) => Math.max(1, n - 1))}
                  style={{
                    width: 26, height: 26, fontSize: 14, lineHeight: 1,
                    background: 'var(--surface-2)', border: '1px solid var(--border)',
                    color: 'var(--text)', borderRadius: 3, cursor: 'pointer', fontFamily: 'var(--font)',
                  }}
                >−</button>
                <span style={{ fontSize: 16, fontWeight: 700, color: 'var(--amber)', minWidth: 28, textAlign: 'center' }}>
                  {autoTurns}
                </span>
                <button
                  onClick={() => setAutoTurns((n) => Math.min(scenario.turns_total, n + 1))}
                  style={{
                    width: 26, height: 26, fontSize: 14, lineHeight: 1,
                    background: 'var(--surface-2)', border: '1px solid var(--border)',
                    color: 'var(--text)', borderRadius: 3, cursor: 'pointer', fontFamily: 'var(--font)',
                  }}
                >+</button>
              </div>
              <span style={{ fontSize: 10, color: 'var(--dimmer)' }}>/ {scenario.turns_total}</span>
            </div>
          )}
        </div>

        <button
          className="btn-primary"
          style={{
            width: '100%', fontSize: 14, padding: '12px 0',
            ...(mode === 'auto' ? { borderColor: 'var(--amber)', color: 'var(--amber)' } : {}),
          }}
          onClick={handleLaunch}
          disabled={disabled}
        >
          {disabled
            ? 'LAUNCHING…'
            : mode === 'auto'
              ? `LAUNCH AUTO-SIM  (${autoTurns} turns)  ▸▸`
              : 'GENERATE & LAUNCH  ▸▸'
          }
        </button>
        <div className="small-meta" style={{ marginTop: 10, textAlign: 'center' }}>
          {scenario.turns_total}-turn run · 6h check-in cadence
          {mode === 'auto' ? ' · auto-sim on HOLD strategy' : ' · claude-opus-4-7'}
        </div>
      </div>

    </div>
  )
}
