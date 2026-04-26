'use client'
// BattleMap.tsx
// Drop in dashboard/src/components/BattleMap.tsx
//
// Shows a tactical grid with unit icons colored by side and readiness.
// Called from RunView after each adjudication step to snapshot the board.
// Positions update only on prop change — no real-time animation needed,
// just a clean per-iteration snapshot.

import { useMemo } from 'react'
import type { BoardUnit, UnitMove, ReadinessLevel } from '@/lib/battle-types'

// ── Constants ─────────────────────────────────────────────────────────────

const CELL_PX  = 28
const GRID_ROWS = 20
const GRID_COLS = 24

// ── Readiness → color ─────────────────────────────────────────────────────

const READINESS_COLORS: Record<ReadinessLevel, string> = {
  FULLY_OPERATIONAL: 'var(--green,  #4ade80)',
  DEGRADED:          'var(--amber,  #fbbf24)',
  SUPPRESSED:        'var(--red,    #f87171)',
  DESTROYED:         'var(--dimmer, #555)',
}

// ── Unit icon (SVG symbol for each category) ──────────────────────────────

function unitSymbol(category: string): string {
  const c = category.toUpperCase()
  if (c.includes('ARMOR'))   return '▲'
  if (c.includes('INFANTRY') || c.includes('LIGHT')) return '●'
  if (c.includes('ARTILL'))  return '✦'
  if (c.includes('AIR'))     return '✈'
  if (c.includes('MARITIME') || c.includes('SEA'))   return '⛵'
  if (c.includes('SPECIAL')) return '★'
  return '■'
}

// ── Single unit chip ──────────────────────────────────────────────────────

function UnitChip({ unit, flash }: { unit: BoardUnit; flash?: boolean }) {
  const color = READINESS_COLORS[unit.readiness]
  const bg    = unit.side === 'BLUE' ? 'rgba(59,130,246,0.18)' : 'rgba(239,68,68,0.18)'
  const border = unit.side === 'BLUE' ? 'rgba(59,130,246,0.6)' : 'rgba(239,68,68,0.6)'

  return (
    <div
      title={`${unit.designation} | ${unit.readiness} | str ${(unit.strength * 100).toFixed(0)}%`}
      style={{
        position:      'absolute',
        left:          unit.position[1] * CELL_PX + 2,
        top:           unit.position[0] * CELL_PX + 2,
        width:         CELL_PX - 4,
        height:        CELL_PX - 4,
        background:    bg,
        border:        `1px solid ${border}`,
        borderRadius:  3,
        display:       'flex',
        alignItems:    'center',
        justifyContent:'center',
        fontSize:      11,
        color,
        cursor:        'default',
        transition:    'left 0.4s ease, top 0.4s ease',
        zIndex:        unit.readiness === 'DESTROYED' ? 1 : 2,
        opacity:       unit.readiness === 'DESTROYED' ? 0.35 : 1,
        outline:       flash ? `2px solid ${color}` : 'none',
        outlineOffset: 1,
      }}
    >
      {unitSymbol(unit.category)}
    </div>
  )
}

// ── Move arrow (SVG overlay) ──────────────────────────────────────────────

function MoveArrow({ move }: { move: UnitMove }) {
  const [r0, c0] = move.from_position
  const [r1, c1] = move.to_position
  if (r0 === r1 && c0 === c1) return null

  const x0 = c0 * CELL_PX + CELL_PX / 2
  const y0 = r0 * CELL_PX + CELL_PX / 2
  const x1 = c1 * CELL_PX + CELL_PX / 2
  const y1 = r1 * CELL_PX + CELL_PX / 2

  const color = move.action === 'ASSAULT' ? '#f87171' :
                move.action === 'WITHDRAW' ? '#fbbf24' : '#94a3b8'

  return (
    <line
      x1={x0} y1={y0} x2={x1} y2={y1}
      stroke={color}
      strokeWidth={1.5}
      strokeDasharray="4 2"
      markerEnd="url(#arrow)"
      opacity={0.7}
    />
  )
}

// ── Legend ────────────────────────────────────────────────────────────────

function Legend() {
  return (
    <div style={{
      display:    'flex',
      gap:        16,
      fontSize:   10,
      color:      'var(--dim, #888)',
      marginTop:  8,
      flexWrap:   'wrap',
    }}>
      {Object.entries(READINESS_COLORS).map(([r, c]) => (
        <span key={r} style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          <span style={{ color: c, fontSize: 14 }}>■</span> {r.replace('_', ' ')}
        </span>
      ))}
      <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
        <span style={{ color: 'rgba(59,130,246,0.8)', fontSize: 14 }}>■</span> BLUE
      </span>
      <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
        <span style={{ color: 'rgba(239,68,68,0.8)', fontSize: 14 }}>■</span> RED
      </span>
    </div>
  )
}

// ── Main component ────────────────────────────────────────────────────────

interface BattleMapProps {
  units: BoardUnit[]
  lastMoves?: UnitMove[]          // Highlight moves from the last iteration
  turn: number
}

export default function BattleMap({ units, lastMoves = [], turn }: BattleMapProps) {
  const movedIds = useMemo(
    () => new Set(lastMoves.filter(m => m.from_position[0] !== m.to_position[0]
                                    || m.from_position[1] !== m.to_position[1])
                           .map(m => m.unit_id)),
    [lastMoves],
  )

  const width  = GRID_COLS * CELL_PX
  const height = GRID_ROWS * CELL_PX

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
        <span style={{ fontSize: 10, letterSpacing: '0.12em', color: 'var(--dimmer, #555)' }}>
          TACTICAL DISPLAY — TURN {turn}
        </span>
        <span style={{ fontSize: 10, color: 'var(--dimmer, #555)' }}>
          {units.filter(u => u.side === 'BLUE' && u.readiness !== 'DESTROYED').length}B &nbsp;
          {units.filter(u => u.side === 'RED'  && u.readiness !== 'DESTROYED').length}R active
        </span>
      </div>

      {/* Grid container */}
      <div style={{
        position:   'relative',
        width:      width,
        height:     height,
        background: 'var(--surface-2, #0e1117)',
        border:     '1px solid var(--border, #222)',
        overflow:   'hidden',
        flexShrink: 0,
      }}>

        {/* Grid lines */}
        <svg
          style={{ position: 'absolute', inset: 0, pointerEvents: 'none' }}
          width={width}
          height={height}
        >
          <defs>
            <marker id="arrow" markerWidth="6" markerHeight="6" refX="3" refY="3" orient="auto">
              <path d="M0,0 L0,6 L6,3 z" fill="#94a3b8" opacity={0.7} />
            </marker>
          </defs>

          {/* Vertical grid lines */}
          {Array.from({ length: GRID_COLS + 1 }, (_, c) => (
            <line key={`v${c}`}
              x1={c * CELL_PX} y1={0}
              x2={c * CELL_PX} y2={height}
              stroke="rgba(255,255,255,0.04)" strokeWidth={1}
            />
          ))}

          {/* Horizontal grid lines */}
          {Array.from({ length: GRID_ROWS + 1 }, (_, r) => (
            <line key={`h${r}`}
              x1={0} y1={r * CELL_PX}
              x2={width} y2={r * CELL_PX}
              stroke="rgba(255,255,255,0.04)" strokeWidth={1}
            />
          ))}

          {/* Move arrows */}
          {lastMoves.map((m, i) => (
            <MoveArrow key={i} move={m} />
          ))}
        </svg>

        {/* Unit chips */}
        {units.map((u) => (
          <UnitChip
            key={u.unit_id}
            unit={u}
            flash={movedIds.has(u.unit_id)}
          />
        ))}
      </div>

      <Legend />
    </div>
  )
}
