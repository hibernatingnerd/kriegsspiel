'use client'

import { useState } from 'react'
import type { ScenarioType } from '@/lib/schema'

interface Props {
  scenarioType: ScenarioType
  scenarioName: string
  locationName: string
}

const BACKDROP: Record<ScenarioType, string> = {
  LAND:       '/backdrops/rural_backdrop.png',
  AMPHIBIOUS: '/backdrops/coast_backdrop.png',
  URBAN:      '/backdrops/rural_backdrop.png',
  HYBRID:     '/backdrops/water_backdrop.png',
}

export default function MapPanel({ scenarioType, scenarioName, locationName }: Props) {
  const [collapsed, setCollapsed] = useState(false)
  const src = BACKDROP[scenarioType]

  return (
    <div className="card" style={{ marginBottom: 16 }}>
      <div
        className="card-header"
        style={{ cursor: 'pointer', userSelect: 'none' }}
        onClick={() => setCollapsed((c) => !c)}
      >
        <div>
          <span className="title">MAP</span>
          <span className="dim" style={{ marginLeft: 12, fontSize: 11 }}>
            {locationName} · {scenarioType}
          </span>
        </div>
        <span className="dim" style={{ fontSize: 11, letterSpacing: '0.1em' }}>
          {collapsed ? '▸ EXPAND' : '▾ COLLAPSE'}
        </span>
      </div>

      {!collapsed && (
        <div
          style={{
            position: 'relative',
            width: '100%',
            aspectRatio: '16 / 7',
            background: 'var(--surface-2)',
            overflow: 'hidden',
          }}
        >
          <img
            src={src}
            alt={`${scenarioType} backdrop for ${scenarioName}`}
            style={{
              width: '100%',
              height: '100%',
              objectFit: 'cover',
              display: 'block',
            }}
          />
        </div>
      )}
    </div>
  )
}
