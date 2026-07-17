import { memo } from 'react'
import { formatSignedPercent } from '../../services/formatters'
import { outcomeTone } from '../../services/recommendationOutcomes'

export const HorizonEvidenceBadges = memo(function HorizonEvidenceBadges({
  badges,
  compact = false,
}) {
  const list = Array.isArray(badges) ? badges : []
  if (!list.length) return null

  return (
    <div className={`outcome-badges${compact ? ' outcome-badges--compact' : ''}`}>
      {list.map((badge) => {
        const result = badge?.result ?? 'Unavailable'
        const rawReturn = badge?.rawReturn
        const detail = rawReturn === null || rawReturn === undefined
          ? result
          : `${result} · raw return ${formatSignedPercent(rawReturn, { fallback: 'Unavailable' })}`
        return (
          <span
            className={`outcome-badge outcome-badge--${outcomeTone(result)}`}
            key={badge?.horizonDays ?? badge?.label}
            title={`${badge?.label ?? 'Horizon'}: ${detail}`}
          >
            <strong>{badge?.label ?? '—'}</strong>
            <span>{result}</span>
          </span>
        )
      })}
    </div>
  )
})

export const OutcomeSourceNotice = memo(function OutcomeSourceNotice({ meta, error, isLoading }) {
  if (error) {
    return (
      <div className="outcome-source-note outcome-source-note--warning" role="status">
        Outcome evidence is unavailable. Recommendation data remains visible, but outcome fields
        cannot be treated as complete.
      </div>
    )
  }
  if (meta?.warning) {
    return (
      <div className="outcome-source-note outcome-source-note--warning" role="alert">
        {meta.warning}
      </div>
    )
  }
  if (isLoading) {
    return (
      <div className="outcome-source-note" role="status">
        Loading stored outcome evidence…
      </div>
    )
  }
  if (meta?.available === false) {
    return (
      <div className="outcome-source-note outcome-source-note--warning" role="status">
        Outcome evidence is unavailable. Recommendation data remains visible, but outcome fields
        cannot be treated as complete.
      </div>
    )
  }
  return null
})
