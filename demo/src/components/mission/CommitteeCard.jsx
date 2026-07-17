import { memo } from 'react'
import MeterBar from '../ui/MeterBar'
import { formatConfidence, formatPercent } from '../../services/formatters'
import { actionTone } from '../../services/missionOps'

// A single committee verdict. Clicking opens the (placeholder) research report.
function CommitteeCard({ card, onOpen }) {
  const tone = actionTone(card.action)
  const agreement = card.agreementPct
  const confidence = card.confidence

  return (
    <button
      type="button"
      className={`dv3-committee-card dv3-committee-card--${tone}`}
      onClick={() => onOpen(card)}
      aria-label={`Open research report for ${card.ticker}`}
    >
      <div className="dv3-committee-card__top">
        <span className="dv3-committee-card__ticker">{card.ticker}</span>
        <span className={`dv3-verdict dv3-verdict--${tone}`}>
          {card.action ?? 'N/A'}
        </span>
      </div>

      <div className="dv3-committee-card__metrics">
        <div>
          <span className="dv3-committee-card__k">Confidence</span>
          <strong>{formatConfidence(confidence, { fallback: '—' })}</strong>
        </div>
        <div>
          <span className="dv3-committee-card__k">Agreement</span>
          <strong>{formatPercent(agreement, { fallback: '—' })}</strong>
        </div>
        <div>
          <span className="dv3-committee-card__k">Strength</span>
          <strong>{card.strength ?? '—'}</strong>
        </div>
      </div>

      <MeterBar
        value={agreement ?? 0}
        tone={tone === 'muted' ? 'accent' : tone === 'neutral' ? 'accent' : tone}
        label={`Committee agreement ${formatPercent(agreement, { fallback: 'n/a' })}`}
      />
      <span className="dv3-committee-card__cta">View research report →</span>
    </button>
  )
}

export default memo(CommitteeCard)
