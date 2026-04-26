import type {
  BattleIterationRequest,
  BattleIterationResponse,
  WorldStateBattleIterationRequest,
  WorldStateBattleIterationResponse,
} from './battle-types'

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

export async function adjudicateTurn(
  req: BattleIterationRequest,
): Promise<BattleIterationResponse> {
  const res = await fetch(`${API_BASE}/api/adjudicate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  })

  if (!res.ok) {
    const text = await res.text()
    throw new Error(`Adjudication failed (${res.status}): ${text}`)
  }

  return res.json() as Promise<BattleIterationResponse>
}

export async function adjudicateWorldTurn(
  req: WorldStateBattleIterationRequest,
): Promise<WorldStateBattleIterationResponse> {
  const res = await fetch(`${API_BASE}/api/adjudicate/world`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  })

  if (!res.ok) {
    const text = await res.text()
    throw new Error(`World adjudication failed (${res.status}): ${text}`)
  }

  return res.json() as Promise<WorldStateBattleIterationResponse>
}
