// Throwaway stub for demoing unit movement per turn until the backend
// supplies real GameState.units. Delete this file + its single import in
// RunView.tsx to remove.

import type { BoardUnit } from './battle-types'

interface Frame {
  minTurn: number  // applies for turns >= minTurn (until next frame)
  units: BoardUnit[]
}

function unit(
  id: string,
  side: 'BLUE' | 'RED',
  designation: string,
  category: string,
  row: number,
  col: number,
): BoardUnit {
  return {
    unit_id: id,
    side,
    designation,
    category,
    position: [row, col],
    readiness: 'FULLY_OPERATIONAL',
    strength: 1.0,
    supply_days_remaining: 5,
    posture: side === 'BLUE' ? 'DEFENSIVE' : 'OFFENSIVE',
  }
}

// Keyframes: blue defends south, red attacks from north, contact mid-map,
// blue counters by T18. Interim turns reuse the latest preceding frame.
const FRAMES: Frame[] = [
  {
    minTurn: 1,
    units: [
      unit('b1', 'BLUE', '1 BCT', 'ARMOR',          150,  60),
      unit('b2', 'BLUE', '2 BCT', 'LIGHT_INFANTRY', 145, 100),
      unit('b3', 'BLUE', 'ARTY',  'ARTILLERY',      170,  90),
      unit('b4', 'BLUE', 'SUS',   'SUSTAINMENT',    180,  70),
      unit('r1', 'RED',  '1 MRD', 'ARMOR',           35,  80),
      unit('r2', 'RED',  '2 MRD', 'LIGHT_INFANTRY',  30, 130),
      unit('r3', 'RED',  'RECON', 'SPECIAL',         55, 110),
      unit('r4', 'RED',  'AD',    'AIR_DEFENSE',     20,  95),
    ],
  },
  {
    minTurn: 6,
    units: [
      unit('b1', 'BLUE', '1 BCT', 'ARMOR',          130,  70),
      unit('b2', 'BLUE', '2 BCT', 'LIGHT_INFANTRY', 125, 105),
      unit('b3', 'BLUE', 'ARTY',  'ARTILLERY',      165,  95),
      unit('b4', 'BLUE', 'SUS',   'SUSTAINMENT',    175,  75),
      unit('r1', 'RED',  '1 MRD', 'ARMOR',           70,  90),
      unit('r2', 'RED',  '2 MRD', 'LIGHT_INFANTRY',  65, 130),
      unit('r3', 'RED',  'RECON', 'SPECIAL',         90, 115),
      unit('r4', 'RED',  'AD',    'AIR_DEFENSE',     40,  95),
    ],
  },
  {
    minTurn: 12,
    units: [
      unit('b1', 'BLUE', '1 BCT', 'ARMOR',          110,  85),
      unit('b2', 'BLUE', '2 BCT', 'LIGHT_INFANTRY', 105, 115),
      unit('b3', 'BLUE', 'ARTY',  'ARTILLERY',      155, 100),
      unit('b4', 'BLUE', 'SUS',   'SUSTAINMENT',    170,  80),
      unit('r1', 'RED',  '1 MRD', 'ARMOR',           95,  95),
      unit('r2', 'RED',  '2 MRD', 'LIGHT_INFANTRY',  90, 130),
      unit('r3', 'RED',  'RECON', 'SPECIAL',        115, 120),
      unit('r4', 'RED',  'AD',    'AIR_DEFENSE',     55, 100),
    ],
  },
  {
    minTurn: 18,
    units: [
      unit('b1', 'BLUE', '1 BCT', 'ARMOR',           90,  95),
      unit('b2', 'BLUE', '2 BCT', 'LIGHT_INFANTRY',  95, 125),
      unit('b3', 'BLUE', 'ARTY',  'ARTILLERY',      145, 105),
      unit('b4', 'BLUE', 'SUS',   'SUSTAINMENT',    165,  85),
      unit('r1', 'RED',  '1 MRD', 'ARMOR',          110, 100),
      unit('r2', 'RED',  '2 MRD', 'LIGHT_INFANTRY', 105, 135),
      unit('r3', 'RED',  'RECON', 'SPECIAL',        130, 125),
      unit('r4', 'RED',  'AD',    'AIR_DEFENSE',     70, 105),
    ],
  },
  {
    minTurn: 24,
    units: [
      unit('b1', 'BLUE', '1 BCT', 'ARMOR',           75, 100),
      unit('b2', 'BLUE', '2 BCT', 'LIGHT_INFANTRY',  80, 130),
      unit('b3', 'BLUE', 'ARTY',  'ARTILLERY',      135, 110),
      unit('b4', 'BLUE', 'SUS',   'SUSTAINMENT',    160,  90),
      unit('r1', 'RED',  '1 MRD', 'ARMOR',          120, 105),
      unit('r2', 'RED',  '2 MRD', 'LIGHT_INFANTRY', 115, 140),
      unit('r3', 'RED',  'RECON', 'SPECIAL',        140, 130),
      unit('r4', 'RED',  'AD',    'AIR_DEFENSE',     80, 110),
    ],
  },
]

export function getStubUnits(turn: number): BoardUnit[] {
  let pick = FRAMES[0]
  for (const f of FRAMES) {
    if (f.minTurn <= turn) pick = f
    else break
  }
  return pick.units
}
