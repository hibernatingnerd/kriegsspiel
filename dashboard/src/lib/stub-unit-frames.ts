// Throwaway stub for demoing unit movement per turn until the backend
// supplies real GameState.units. Delete this file + its single import in
// RunView.tsx to remove.

import type { GridUnit } from './schema'
import { deriveSidc } from './sidc'

interface Frame {
  minTurn: number  // applies for turns >= minTurn (until next frame)
  units: GridUnit[]
}

const SIDC = {
  bArmor:  deriveSidc({ side: 'blue', category: 'ARMOR',          echelon: 'H' }),
  bInf:    deriveSidc({ side: 'blue', category: 'LIGHT_INFANTRY', echelon: 'H' }),
  bArty:   deriveSidc({ side: 'blue', category: 'ARTILLERY',      echelon: 'F' }),
  bSus:    deriveSidc({ side: 'blue', category: 'SUSTAINMENT',    echelon: 'F' }),
  rArmor:  deriveSidc({ side: 'red',  category: 'ARMOR',          echelon: 'I' }),
  rInf:    deriveSidc({ side: 'red',  category: 'LIGHT_INFANTRY', echelon: 'I' }),
  rRecon:  deriveSidc({ side: 'red',  category: 'SPECIAL',        echelon: 'E' }),
  rAd:     deriveSidc({ side: 'red',  category: 'AIR_DEFENSE',    echelon: 'F' }),
}

// Keyframes: blue defends south, red attacks from north, contact mid-map,
// blue counters by T18. Interim turns reuse the latest preceding frame.
const FRAMES: Frame[] = [
  {
    minTurn: 1,
    units: [
      { id: 'b1', side: 'blue', label: '1 BCT', row: 150, col:  60, sidc: SIDC.bArmor },
      { id: 'b2', side: 'blue', label: '2 BCT', row: 145, col: 100, sidc: SIDC.bInf   },
      { id: 'b3', side: 'blue', label: 'ARTY',  row: 170, col:  90, sidc: SIDC.bArty  },
      { id: 'b4', side: 'blue', label: 'SUS',   row: 180, col:  70, sidc: SIDC.bSus   },
      { id: 'r1', side: 'red',  label: '1 MRD', row:  35, col:  80, sidc: SIDC.rArmor },
      { id: 'r2', side: 'red',  label: '2 MRD', row:  30, col: 130, sidc: SIDC.rInf   },
      { id: 'r3', side: 'red',  label: 'RECON', row:  55, col: 110, sidc: SIDC.rRecon },
      { id: 'r4', side: 'red',  label: 'AD',    row:  20, col:  95, sidc: SIDC.rAd    },
    ],
  },
  {
    minTurn: 6,
    units: [
      { id: 'b1', side: 'blue', label: '1 BCT', row: 130, col:  70, sidc: SIDC.bArmor },
      { id: 'b2', side: 'blue', label: '2 BCT', row: 125, col: 105, sidc: SIDC.bInf   },
      { id: 'b3', side: 'blue', label: 'ARTY',  row: 165, col:  95, sidc: SIDC.bArty  },
      { id: 'b4', side: 'blue', label: 'SUS',   row: 175, col:  75, sidc: SIDC.bSus   },
      { id: 'r1', side: 'red',  label: '1 MRD', row:  70, col:  90, sidc: SIDC.rArmor },
      { id: 'r2', side: 'red',  label: '2 MRD', row:  65, col: 130, sidc: SIDC.rInf   },
      { id: 'r3', side: 'red',  label: 'RECON', row:  90, col: 115, sidc: SIDC.rRecon },
      { id: 'r4', side: 'red',  label: 'AD',    row:  40, col:  95, sidc: SIDC.rAd    },
    ],
  },
  {
    minTurn: 12,
    units: [
      { id: 'b1', side: 'blue', label: '1 BCT', row: 110, col:  85, sidc: SIDC.bArmor },
      { id: 'b2', side: 'blue', label: '2 BCT', row: 105, col: 115, sidc: SIDC.bInf   },
      { id: 'b3', side: 'blue', label: 'ARTY',  row: 155, col: 100, sidc: SIDC.bArty  },
      { id: 'b4', side: 'blue', label: 'SUS',   row: 170, col:  80, sidc: SIDC.bSus   },
      { id: 'r1', side: 'red',  label: '1 MRD', row:  95, col:  95, sidc: SIDC.rArmor },
      { id: 'r2', side: 'red',  label: '2 MRD', row:  90, col: 130, sidc: SIDC.rInf   },
      { id: 'r3', side: 'red',  label: 'RECON', row: 115, col: 120, sidc: SIDC.rRecon },
      { id: 'r4', side: 'red',  label: 'AD',    row:  55, col: 100, sidc: SIDC.rAd    },
    ],
  },
  {
    minTurn: 18,
    units: [
      { id: 'b1', side: 'blue', label: '1 BCT', row:  90, col:  95, sidc: SIDC.bArmor },
      { id: 'b2', side: 'blue', label: '2 BCT', row:  95, col: 125, sidc: SIDC.bInf   },
      { id: 'b3', side: 'blue', label: 'ARTY',  row: 145, col: 105, sidc: SIDC.bArty  },
      { id: 'b4', side: 'blue', label: 'SUS',   row: 165, col:  85, sidc: SIDC.bSus   },
      { id: 'r1', side: 'red',  label: '1 MRD', row: 110, col: 100, sidc: SIDC.rArmor },
      { id: 'r2', side: 'red',  label: '2 MRD', row: 105, col: 135, sidc: SIDC.rInf   },
      { id: 'r3', side: 'red',  label: 'RECON', row: 130, col: 125, sidc: SIDC.rRecon },
      { id: 'r4', side: 'red',  label: 'AD',    row:  70, col: 105, sidc: SIDC.rAd    },
    ],
  },
  {
    minTurn: 24,
    units: [
      { id: 'b1', side: 'blue', label: '1 BCT', row:  75, col: 100, sidc: SIDC.bArmor },
      { id: 'b2', side: 'blue', label: '2 BCT', row:  80, col: 130, sidc: SIDC.bInf   },
      { id: 'b3', side: 'blue', label: 'ARTY',  row: 135, col: 110, sidc: SIDC.bArty  },
      { id: 'b4', side: 'blue', label: 'SUS',   row: 160, col:  90, sidc: SIDC.bSus   },
      { id: 'r1', side: 'red',  label: '1 MRD', row: 120, col: 105, sidc: SIDC.rArmor },
      { id: 'r2', side: 'red',  label: '2 MRD', row: 115, col: 140, sidc: SIDC.rInf   },
      { id: 'r3', side: 'red',  label: 'RECON', row: 140, col: 130, sidc: SIDC.rRecon },
      { id: 'r4', side: 'red',  label: 'AD',    row:  80, col: 110, sidc: SIDC.rAd    },
    ],
  },
]

export function getStubUnits(turn: number): GridUnit[] {
  let pick = FRAMES[0]
  for (const f of FRAMES) {
    if (f.minTurn <= turn) pick = f
    else break
  }
  return pick.units
}
