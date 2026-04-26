'use client'

import { useState, useEffect } from 'react'

const API = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

type Status = 'checking' | 'ok' | 'offline'

export default function ApiStatus() {
  const [status, setStatus] = useState<Status>('checking')

  useEffect(() => {
    let cancelled = false

    async function ping() {
      try {
        const res = await fetch(`${API}/health`, { cache: 'no-store' })
        if (!cancelled) setStatus(res.ok ? 'ok' : 'offline')
      } catch {
        if (!cancelled) setStatus('offline')
      }
    }

    ping()
    const id = setInterval(ping, 15_000)
    return () => { cancelled = true; clearInterval(id) }
  }, [])

  const dot: React.CSSProperties = {
    display: 'inline-block',
    width: 7,
    height: 7,
    borderRadius: '50%',
    marginRight: 6,
    background: status === 'ok' ? 'var(--green)' : status === 'offline' ? 'var(--red)' : 'var(--dimmer)',
    boxShadow: status === 'ok' ? '0 0 5px var(--green)' : 'none',
  }

  const label = status === 'ok' ? 'API' : status === 'offline' ? 'OFFLINE' : '…'

  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', fontSize: 10, letterSpacing: '0.08em', color: 'var(--dimmer)' }}>
      <span style={dot} />
      {label}
    </span>
  )
}
