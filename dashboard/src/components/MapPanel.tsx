'use client'

import { useMemo, useState } from 'react'
import ms from 'milsymbol'
import type { ScenarioType } from '@/lib/schema'
import type { BoardUnit, UnitMove, ReadinessLevel } from '@/lib/battle-types'
import { deriveSidc } from '@/lib/sidc'

interface Props {
  scenarioType: ScenarioType
  scenarioName: string
  locationName: string
  units?: BoardUnit[]
  lastMoves?: UnitMove[]
  turn?: number
  // Optional grid override. Falls back to GRID_DIMS[scenarioType] (200x200 / 300x300).
  gridRows?: number
  gridCols?: number
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

const READINESS_OPACITY: Record<ReadinessLevel, number> = {
  FULLY_OPERATIONAL: 1.0,
  DEGRADED:          0.85,
  SUPPRESSED:        0.6,
  DESTROYED:         0.25,
}

const MOVE_COLOR: Record<UnitMove['action'], string> = {
  ASSAULT:  'var(--red)',
  WITHDRAW: 'var(--amber)',
  MOVE:     'var(--blue)',
  HOLD:     'var(--dim)',
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
  lastMoves = [],
  turn,
  gridRows,
  gridCols,
}: Props) {
  const [collapsed, setCollapsed] = useState(false)
  const [showGrid, setShowGrid] = useState(true)
  const src = BACKDROP[scenarioType]
  const rows = gridRows ?? GRID_DIMS[scenarioType].rows
  const cols = gridCols ?? GRID_DIMS[scenarioType].cols

  // Symbol render scale: ~12 cells tall on a 200-cell grid.
  const symbolCellSize = Math.max(rows, cols) * 0.06

  // Memoize per-unit symbol renders so we only recompute when units change.
  const rendered = useMemo(() => {
    return units.map((u) => {
      const sidc = deriveSidc({
        side: u.side,
        category: u.category,
        echelon: 'F',
      })
      try {
        return { unit: u, render: renderSymbol(sidc, u.designation) }
      } catch {
        return { unit: u, render: null }
      }
    })
  }, [units])

  const movedIds = useMemo(
    () => new Set(
      lastMoves
        .filter(m => m.from_position[0] !== m.to_position[0] || m.from_position[1] !== m.to_position[1])
        .map(m => m.unit_id),
    ),
    [lastMoves],
  )

  const vLines: number[] = []
  for (let c = GRID_STEP; c < cols; c += GRID_STEP) vLines.push(c)
  const hLines: number[] = []
  for (let r = GRID_STEP; r < rows; r += GRID_STEP) hLines.push(r)

  const activeBlue = units.filter((u) => u.side === 'BLUE' && u.readiness !== 'DESTROYED').length
  const activeRed  = units.filter((u) => u.side === 'RED'  && u.readiness !== 'DESTROYED').length

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
            {turn !== undefined && ` · T${turn}`}
            {' · '}
            <span style={{ color: 'var(--blue)' }}>{activeBlue}B</span>
            {' '}
            <span style={{ color: 'var(--red)' }}>{activeRed}R</span>
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
            <defs>
              {(['ASSAULT', 'WITHDRAW', 'MOVE', 'HOLD'] as const).map((act) => (
                <marker
                  key={act}
                  id={`arrow-${act}`}
                  markerWidth={6}
                  markerHeight={6}
                  refX={5}
                  refY={3}
                  orient="auto"
                >
                  <path d="M0,0 L0,6 L6,3 z" fill={MOVE_COLOR[act]} opacity={0.85} />
                </marker>
              ))}
            </defs>

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

            {/* Move arrows from last adjudication */}
            {lastMoves.map((m, i) => {
              const [r0, c0] = m.from_position
              const [r1, c1] = m.to_position
              if (r0 === r1 && c0 === c1) return null
              return (
                <line
                  key={`mv${i}`}
                  x1={c0 + 0.5}
                  y1={r0 + 0.5}
                  x2={c1 + 0.5}
                  y2={r1 + 0.5}
                  stroke={MOVE_COLOR[m.action]}
                  strokeWidth={Math.max(rows, cols) * 0.004}
                  strokeDasharray={`${Math.max(rows, cols) * 0.012} ${Math.max(rows, cols) * 0.006}`}
                  opacity={0.85}
                  markerEnd={`url(#arrow-${m.action})`}
                />
              )
            })}

            {/* Unit symbols */}
            {rendered.map(({ unit, render }) => {
              if (!render) return null
              const aspect = render.width / render.height
              const w = symbolCellSize * aspect
              const h = symbolCellSize
              const ax = (render.anchorX / render.width) * w
              const ay = (render.anchorY / render.height) * h
              const opacity = READINESS_OPACITY[unit.readiness]
              const moved = movedIds.has(unit.unit_id)
              return (
                <g key={unit.unit_id} opacity={opacity}>
                  {moved && (
                    <circle
                      cx={unit.position[1] + 0.5}
                      cy={unit.position[0] + 0.5}
                      r={symbolCellSize * 0.55}
                      fill="none"
                      stroke="var(--accent)"
                      strokeWidth={Math.max(rows, cols) * 0.003}
                      opacity={0.6}
                    />
                  )}
                  <image
                    href={render.dataUrl}
                    x={unit.position[1] + 0.5 - ax}
                    y={unit.position[0] + 0.5 - ay}
                    width={w}
                    height={h}
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
