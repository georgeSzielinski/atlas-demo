import { memo } from 'react'

const POSITIVE = new Set([
  'Healthy', 'Reliable', 'RUNNING', 'READY', 'APPROVED', 'EVALUATED',
  'HIGH', 'Fresh', 'IMPROVING', 'ok', 'Online', 'Connected', 'PASS',
])
const WARN = new Set(['Warning', 'Watch', 'PAUSED', 'MEDIUM', 'Recent', 'STABLE', 'PARTIAL'])
const NEGATIVE = new Set([
  'Degraded', 'Critical', 'ERROR', 'REJECTED', 'Offline', 'FAIL', 'DEGRADING', 'Stale',
])
const MUTED = new Set(['NOT_EVALUATED', 'OFF', 'Unavailable', 'LOW', 'NOT_STARTED'])

function toneFor(status) {
  const key = String(status ?? '')
  if (POSITIVE.has(key)) return 'positive'
  if (WARN.has(key)) return 'warn'
  if (NEGATIVE.has(key)) return 'negative'
  if (MUTED.has(key)) return 'muted'
  return 'neutral'
}

function StatusPill({ status, label, tone }) {
  const resolvedTone = tone ?? toneFor(status)
  const text = label ?? String(status ?? 'Unknown')
  return <span className={`dv2-pill dv2-pill--${resolvedTone}`}>{text}</span>
}

export default memo(StatusPill)
