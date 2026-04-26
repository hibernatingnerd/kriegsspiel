'use client'

import { useState } from 'react'
import type { AppPhase, Scenario, GameState, ScenarioConfig, DecisionKey } from '@/lib/schema'
import {
  ALL_SCENARIOS,
  SCENARIO_IRON_CORRIDOR,
  GAME_STATE_IN_PROGRESS,
  GAME_STATE_COMPLETED,
  GREY_HORIZON_DECISIONS,
} from '@/lib/mock-data'

import SetupView   from '@/components/SetupView'
import RunView     from '@/components/RunView-with-map'
import DebriefView from '@/components/DebriefView'

const NOW  = '2026-04-25 17:42 UTC'
const USER = 'JEFF.CAMPBELL'

function buildInitialGameState(scenario: Scenario): GameState {
  return {
    scenario_id: scenario.id,
    run_id: Math.random().toString(36).slice(2, 8).toUpperCase(),
    status: 'running',
    current_turn: 1,
    next_checkin_iso: null,
    blue_force: { ...scenario.blue_force },
    red_force:  { ...scenario.red_force  },
    max_penetration_km: 0,
    turn_log: [],
    pending_decision: GREY_HORIZON_DECISIONS[1] ?? null,
    aar: null,
  }
}

// ── Phase stepper ─────────────────────────────────────────────────────────

interface StepperProps {
  phase: AppPhase
  onSelect: (p: AppPhase) => void
}

function PhaseStep({
  label,
  stepPhase,
  currentPhase,
  onClick,
}: {
  label: string
  stepPhase: AppPhase
  currentPhase: AppPhase
  onClick: () => void
}) {
  const order: AppPhase[] = ['setup', 'run', 'debrief']
  const stepIdx    = order.indexOf(stepPhase)
  const currentIdx = order.indexOf(currentPhase)
  const isDone   = stepIdx < currentIdx
  const isActive = stepPhase === currentPhase

  return (
    <div
      className={`phase-step${isActive ? ' active' : isDone ? ' done' : ''}`}
      onClick={onClick}
      style={{ cursor: 'pointer', userSelect: 'none' }}
      title={`Jump to ${label}`}
    >
      <span className="phase-dot">{isDone ? '✓' : isActive ? '●' : '○'}</span>
      {label}
    </div>
  )
}

function PhaseStepper({ phase, onSelect }: StepperProps) {
  return (
    <div className="phase-stepper">
      <PhaseStep label="SETUP"   stepPhase="setup"   currentPhase={phase} onClick={() => onSelect('setup')}   />
      <PhaseStep label="RUN"     stepPhase="run"     currentPhase={phase} onClick={() => onSelect('run')}     />
      <PhaseStep label="DEBRIEF" stepPhase="debrief" currentPhase={phase} onClick={() => onSelect('debrief')} />
    </div>
  )
}

// ── App ───────────────────────────────────────────────────────────────────

export default function Home() {
  const [phase,     setPhase]     = useState<AppPhase>('setup')
  const [scenario,  setScenario]  = useState<Scenario>(ALL_SCENARIOS[0])
  const [gameState, setGameState] = useState<GameState>(GAME_STATE_IN_PROGRESS)

  function handleLaunch(config: ScenarioConfig) {
    const base = ALL_SCENARIOS.find((s) => s.id === config.base_scenario_id) ?? ALL_SCENARIOS[0]
    const next: Scenario = {
      ...base,
      name: config.label_override || base.name,
    }
    setScenario(next)
    setGameState(buildInitialGameState(next))
    setPhase('run')
  }

  function handleDecision(next: GameState) {
    setGameState(next)
    if (next.status === 'ended') setPhase('debrief')
  }

  function handleRunAgain() {
    setGameState(buildInitialGameState(scenario))
    setPhase('run')
  }

  // Clicking a tab directly loads demo data for that phase
  function handleTabSelect(p: AppPhase) {
    if (p === 'run') {
      // If no active run, jump to the in-progress demo
      if (phase === 'setup') {
        setScenario(SCENARIO_IRON_CORRIDOR)
        setGameState(GAME_STATE_IN_PROGRESS)
      }
    } else if (p === 'debrief') {
      setScenario(SCENARIO_IRON_CORRIDOR)
      setGameState(GAME_STATE_COMPLETED)
    }
    setPhase(p)
  }

  return (
    <div className="page-wrap">

      <div className="top-bar">
        <div>
          <span className="brand">KRIEGSSPIEL</span>
          <span className="meta" style={{ marginLeft: 14 }}>AI Wargame Production · v0.1</span>
        </div>
        <div className="meta">{USER} · {NOW}</div>
      </div>

      <PhaseStepper phase={phase} onSelect={handleTabSelect} />

      {phase === 'setup' && (
        <SetupView onLaunch={handleLaunch} />
      )}

      {phase === 'run' && (
        <RunView
          scenario={scenario}
          gameState={gameState}
          onDecision={handleDecision}
        />
      )}

      {phase === 'debrief' && (
        <DebriefView
          scenario={scenario}
          gameState={gameState}
          onRunAgain={handleRunAgain}
          onNewScenario={() => setPhase('setup')}
        />
      )}

    </div>
  )
}
