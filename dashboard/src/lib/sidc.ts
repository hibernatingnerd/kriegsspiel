// Build MIL-STD-2525C SIDCs from backend Category + Side.
// Backend can send `sidc` directly later; this is the bridge until then.

import type { SideLabel } from './schema'

// Mirrors backend kriegsspiel/engine/enums.py::Category
export type UnitCategory =
  | 'LIGHT_INFANTRY'
  | 'ARMOR'
  | 'ARTILLERY'
  | 'AIR_DEFENSE'
  | 'TRANSPORT'
  | 'SUSTAINMENT'
  | 'ENABLER'
  | 'SPECIAL'
  | 'IRREGULAR'
  | 'AIR'
  | 'MARITIME_BATTLE'
  | 'MARITIME_CARGO'
  | 'MANEUVER'
  | 'FIRES'

// Echelon code goes in pos 11 of a 15-char SIDC.
// A=team, B=squad, C=section, D=platoon, E=company, F=battalion,
// G=regiment, H=brigade, I=division, J=corps, K=army.
export type EchelonCode = 'A' | 'B' | 'C' | 'D' | 'E' | 'F' | 'G' | 'H' | 'I' | 'J' | 'K'

// Function ID (positions 5-10) — the inner icon.
const FUNCTION_ID: Record<UnitCategory, { dim: 'G' | 'A' | 'S'; fn: string }> = {
  LIGHT_INFANTRY:  { dim: 'G', fn: 'UCI---' },
  ARMOR:           { dim: 'G', fn: 'UCA---' },
  ARTILLERY:       { dim: 'G', fn: 'UCF---' },
  AIR_DEFENSE:     { dim: 'G', fn: 'UCD---' },
  TRANSPORT:       { dim: 'G', fn: 'USTC--' },
  SUSTAINMENT:     { dim: 'G', fn: 'US----' },
  ENABLER:         { dim: 'G', fn: 'UCE---' },
  SPECIAL:         { dim: 'G', fn: 'UCFS--' },
  IRREGULAR:       { dim: 'G', fn: 'UCI---' },
  MANEUVER:        { dim: 'G', fn: 'UC----' },
  FIRES:           { dim: 'G', fn: 'UCF---' },
  AIR:             { dim: 'A', fn: 'MF----' },
  MARITIME_BATTLE: { dim: 'S', fn: 'C-----' },
  MARITIME_CARGO:  { dim: 'S', fn: 'CL----' },
}

export interface SidcInput {
  side: SideLabel
  category: UnitCategory
  echelon?: EchelonCode
}

export function deriveSidc({ side, category, echelon = 'F' }: SidcInput): string {
  const aff = side === 'blue' ? 'F' : 'H'           // friend / hostile
  const { dim, fn } = FUNCTION_ID[category]
  // 15 chars: scheme + affiliation + dim + status + fn(6) + echelon + reserved(3) + reserved
  return `S${aff}${dim}P${fn}-${echelon}-----`.padEnd(15, '-').slice(0, 15)
}
