import { memo } from 'react'

function toneForGrade(grade) {
  const key = String(grade ?? '')
  if (key.startsWith('A')) return 'positive'
  if (key.startsWith('B')) return 'neutral'
  if (key.startsWith('C')) return 'warn'
  if (key === 'NOT_EVALUATED') return 'muted'
  return 'negative' // D / F
}

function GradeBadge({ grade, score }) {
  const tone = toneForGrade(grade)
  return (
    <span className={`dv2-grade dv2-grade--${tone}`}>
      <span className="dv2-grade__letter">{grade ?? '—'}</span>
      {score !== null && score !== undefined ? (
        <span className="dv2-grade__score">{score}</span>
      ) : null}
    </span>
  )
}

export default memo(GradeBadge)
