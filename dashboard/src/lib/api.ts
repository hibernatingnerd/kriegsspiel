// api.ts
// Thin client for the Kriegsspiel FastAPI backend at localhost:8000.
// All functions return null on network failure so callers can fall back to mock.

import type { GameState, Scenario, ScenarioConfig, DecisionKey } from './schema'

const BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

async function post<T>(path: string, body: unknown): Promise<T | null> {
  try {
    const res = await fetch(`${BASE}${path}`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify(body),
    })
    if (!res.ok) {
      console.warn(`[api] POST ${path} → ${res.status}`)
      return null
    }
    return res.json() as Promise<T>
  } catch (err) {
    console.warn(`[api] POST ${path} failed:`, err)
    return null
  }
}

async function get<T>(path: string): Promise<T | null> {
  try {
    const res = await fetch(`${BASE}${path}`)
    if (!res.ok) {
      console.warn(`[api] GET ${path} → ${res.status}`)
      return null
    }
    return res.json() as Promise<T>
  } catch (err) {
    console.warn(`[api] GET ${path} failed (backend offline?)`, err)
    return null
  }
}

export async function apiHealth(): Promise<boolean> {
  const r = await get<{ status: string }>('/health')
  return r?.status === 'ok'
}

export async function apiScenarios(): Promise<Scenario[] | null> {
  return get<Scenario[]>('/scenarios')
}

export async function apiStartGame(config: ScenarioConfig): Promise<GameState | null> {
  return post<GameState>('/game/start', config)
}

export async function apiDecide(
  run_id: string,
  decision_key: DecisionKey,
  note: string,
): Promise<GameState | null> {
  return post<GameState>(`/game/${run_id}/decide`, { decision_key, note })
}

export async function apiSimulate(
  run_id: string,
  turns: number,
  blue_strategy = 'hold',
): Promise<GameState | null> {
  return post<GameState>(`/game/${run_id}/simulate`, { turns, blue_strategy })
}
