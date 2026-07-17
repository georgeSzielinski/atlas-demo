function clamp(value) {
  const number = Number(value)
  if (Number.isNaN(number)) {
    return 0
  }
  return Math.max(0, Math.min(100, number))
}

function RecommendationConfidenceGauge({ overview }) {
  const hasProbability = overview?.probability !== null && overview?.probability !== undefined
  const confidence = clamp(overview?.confidence)
  const probability = clamp(overview?.probability)
  const action = overview?.recommendation ?? 'Unavailable'
  const radius = 52
  const circumference = 2 * Math.PI * radius
  const dash = (confidence / 100) * circumference

  return (
    <section className="brain-panel brain-gauge">
      <div className="brain-panel__heading">
        <div>
          <p className="eyebrow">Conviction</p>
          <h3>Recommendation Confidence</h3>
        </div>
      </div>

      <div className="brain-gauge__body">
        <svg className="brain-gauge__svg" viewBox="0 0 140 140">
          <circle className="brain-gauge__track" cx="70" cy="70" r={radius} />
          <circle
            className="brain-gauge__value"
            cx="70"
            cy="70"
            r={radius}
            strokeDasharray={`${dash} ${circumference - dash}`}
            transform="rotate(-90 70 70)"
          />
          <text className="brain-gauge__number" x="70" y="66">{Math.round(confidence)}%</text>
          <text className="brain-gauge__caption" x="70" y="88">confidence</text>
        </svg>
        <div className="brain-gauge__meta">
          <span className={`brain-action brain-action--${String(action).toLowerCase()}`}>{action}</span>
          <div>
            <span>Outperformance probability</span>
            <strong>{hasProbability ? `${Math.round(probability)}%` : 'Unavailable'}</strong>
          </div>
          {!hasProbability ? (
            <p className="brain-empty">Probability detail is missing for this recommendation.</p>
          ) : null}
        </div>
      </div>
    </section>
  )
}

export default RecommendationConfidenceGauge
