'use client'

import { useState } from 'react'
import type { ScenarioType, GridUnit } from '@/lib/schema'

interface Props {
  scenarioType: ScenarioType
  scenarioName: string
  locationName: string
  units?: GridUnit[]
}

const BACKDROP: Record<ScenarioType, string> = {
  LAND:       '/backdrops/rural_backdrop.png',
  AMPHIBIOUS: '/backdrops/coast_backdrop.png',
  URBAN:      '/backdrops/rural_backdrop.png',
  HYBRID:     '/backdrops/water_backdrop.png',
}

// Backend grid dimensions per scenario_type (matches backend npz shapes).
const GRID_DIMS: Record<ScenarioType, { rows: number; cols: number }> = {
  LAND:       { rows: 200, cols: 200 },
  AMPHIBIOUS: { rows: 200, cols: 200 },
  URBAN:      { rows: 200, cols: 200 },
  HYBRID:     { rows: 300, cols: 300 },
}

const GRID_STEP = 20  // draw a faint line every N cells

export default function MapPanel({
  scenarioType,
  scenarioName,
  locationName,
  units = [],
}: Props) {
  const [collapsed, setCollapsed] = useState(false)
  const [showGrid, setShowGrid] = useState(true)
  const src = BACKDROP[scenarioType]
  const { rows, cols } = GRID_DIMS[scenarioType]

  const vLines: number[] = []
  for (let c = GRID_STEP; c < cols; c += GRID_STEP) vLines.push(c)
  const hLines: number[] = []
  for (let r = GRID_STEP; r < rows; r += GRID_STEP) hLines.push(r)

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
            {locationName} · {scenarioType} · {rows}×{cols}
          </span>
        </div>
        <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
          {!collapsed && (
            <button
              onClick={(e) => { e.stopPropagation(); setShowGrid((g) => !g) }}
              className="pill"
              style={{
                cursor: 'pointer',
                background: 'transparent',
                fontFamily: 'var(--font)',
                color: showGrid ? 'var(--accent)' : 'var(--dim)',
                borderColor: showGrid ? 'var(--accent)' : 'var(--border)',
              }}
            >
              {showGrid ? '▦ GRID ON' : '▦ GRID OFF'}
            </button>
          )}
          <span className="dim" style={{ fontSize: 11, letterSpacing: '0.1em' }}>
            {collapsed ? '▸ EXPAND' : '▾ COLLAPSE'}
          </span>
        </div>
      </div>

      {!collapsed && (
        <div
          style={{
            position: 'relative',
            width: '100%',
            maxWidth: 720,
            margin: '0 auto',
            aspectRatio: '1 / 1',
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
              objectFit: 'fill',
              display: 'block',
            }}
          />

          <svg
            viewBox={`0 0 ${cols} ${rows}`}
            preserveAspectRatio="none"
            style={{
              position: 'absolute',
              inset: 0,
              width: '100%',
              height: '100%',
              pointerEvents: 'none',
            }}
          >
            {showGrid && (
              <g stroke="rgba(255,210,74,0.18)" strokeWidth={0.5}>
                {vLines.map((c) => (
                  <line key={`v${c}`} x1={c} y1={0} x2={c} y2={rows} />
                ))}
                {hLines.map((r) => (
                  <line key={`h${r}`} x1={0} y1={r} x2={cols} y2={r} />
                ))}
                <rect x={0} y={0} width={cols} height={rows} fill="none" stroke="rgba(255,210,74,0.35)" strokeWidth={1} />
              </g>
            )}

            {units.map((u) => {
              const fill = u.side === 'blue' ? 'var(--blue)' : 'var(--red)'
              return (
                <g key={u.id}>
                  <circle
                    cx={u.col + 0.5}
                    cy={u.row + 0.5}
                    r={Math.max(rows, cols) * 0.012}
                    fill={fill}
                    stroke="rgba(0,0,0,0.7)"
                    strokeWidth={0.5}
                  />
                </g>
              )
            })}
          </svg>
        </div>
      )}
    </div>
  )
}
