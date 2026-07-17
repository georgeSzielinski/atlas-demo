function valueOrFallback(value, fallback = 'Unavailable') {
  if (value === null || value === undefined || value === '') {
    return fallback
  }

  return value
}

function ResearchHeader({ report, recommendation }) {
  const metadata = report?.metadata ?? {}
  const action = recommendation?.action ?? report?.sections?.[1]?.data?.action
  const probabilities = report?.sections?.[2]?.data ?? {}

  const metrics = [
    ['Probability', `${valueOrFallback(probabilities.outperformance, 0)}%`],
    ['Confidence', `${valueOrFallback(recommendation?.confidence, 0)}%`],
    ['Knowledge', valueOrFallback(recommendation?.knowledge_score, 0)],
    ['Stability', valueOrFallback(recommendation?.stability_score, 0)],
    ['Executive', valueOrFallback(recommendation?.executive_status)],
  ]

  return (
    <section className="research-header">
      <div>
        <p className="eyebrow">Research Workspace</p>
        <div className="research-header__title-row">
          <h2>{valueOrFallback(report?.ticker ?? recommendation?.ticker, 'Atlas')}</h2>
          <span className={`action-pill action-pill--${String(action).toLowerCase()}`}>
            {valueOrFallback(action)}
          </span>
        </div>
        <p className="research-header__meta">
          Version {valueOrFallback(metadata.report_version, '1.0')} · Generated{' '}
          {valueOrFallback(metadata.generation_time)}
        </p>
      </div>
      <div className="research-header__metrics" aria-label="Research summary metrics">
        {metrics.map(([label, value]) => (
          <div className="metric-tile" key={label}>
            <span>{label}</span>
            <strong>{value}</strong>
          </div>
        ))}
      </div>
    </section>
  )
}

export default ResearchHeader
