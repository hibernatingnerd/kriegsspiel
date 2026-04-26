'use client'

import { useMemo, useState } from 'react'
import ms from 'milsymbol'
import type { ScenarioType, GridUnit, SideLabel } from '@/lib/schema'

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

// Generic fallback SIDCs when the backend hasn't provided one yet.
const FALLBACK_SIDC: Record<SideLabel, string> = {
  blue: 'SFGPU-----H----',
  red:  'SHGPU-----H----',
}

interface RenderedSymbol {
  dataUrl: string
  width: number
  height: number
  anchorX: number
  anchorY: number
}

function renderSymbol(sidc: string, label: string): RenderedSymbol {
  const sym = new ms.Symbol(sidc, {
    size: 32,
    uniqueDesignation: label,
    fillOpacity: 0.9,
    outlineWidth: 2,
    outlineColor: 'rgba(0,0,0,0.8)',
  })
  const { width, height } = sym.getSize()
  const anchor = sym.getAnchor()
  return { dataUrl: sym.toDataURL(), width, height, anchorX: anchor.x, anchorY: anchor.y }
}

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

  // Symbol render scale: ~12 cells tall on a 200-cell grid.
  const symbolCellSize = Math.max(rows, cols) * 0.06

  // Memoize per-unit symbol renders so we only recompute when sidc/label change.
  const rendered = useMemo(() => {
    return units.map((u) => {
      const sidc = u.sidc ?? FALLBACK_SIDC[u.side]
      try {
        return { unit: u, render: renderSymbol(sidc, u.label) }
      } catch {
        return { unit: u, render: null }
      }
    })
  }, [units])

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
            {locationName} · {scenarioType} · {rows}×{cols} · {units.length} units
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

            {rendered.map(({ unit, render }) => {
              if (!render) return null
              const aspect = render.width / render.height
              const w = symbolCellSize * aspect
              const h = symbolCellSize
              // milsymbol anchor is in its own coord space; normalize then place.
              const ax = (render.anchorX / render.width) * w
              const ay = (render.anchorY / render.height) * h
              return (
                <image
                  key={unit.id}
                  href={render.dataUrl}
                  x={unit.col + 0.5 - ax}
                  y={unit.row + 0.5 - ay}
                  width={w}
                  height={h}
                />
              )
            })}
          </svg>
        </div>
      )}
    </div>
  )
}
