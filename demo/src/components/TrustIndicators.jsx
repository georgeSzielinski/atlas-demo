function TrustIndicators({ trust }) {
  const data = trust ?? {}
  const validation = data.validation_status ?? {}
  const experiment = data.experiment_status ?? {}
  const provider = data.data_provider_health ?? {}
  const freshness = data.market_freshness ?? {}
  const research = data.research_confidence ?? {}

  const cards = [
    ['Validation', validation.latest_scientific_result ?? validation.recommendation_validation ?? 'Pending'],
    ['Adoption Decision', validation.latest_adoption_decision ?? 'Not Enough Evidence'],
    ['Active Experiments', experiment.active_experiments ?? 0],
    ['Probability Calibration', `${data.probability_calibration ?? 0}%`],
    ['Data Provider', `${provider.active_provider ?? 'mock'}${provider.healthy ? ' ✓' : ''}`],
    ['Market Freshness', freshness.label ?? 'Unknown'],
    ['Research Confidence', research.label ?? 'Insufficient'],
  ]

  return (
    <section className="brain-panel">
      <div className="brain-panel__heading">
        <div>
          <p className="eyebrow">Trust Indicators</p>
          <h3>Why You Can Trust This</h3>
        </div>
        <span className="brain-pill">Read-only · Deterministic</span>
      </div>

      <div className="brain-trust-grid">
        {cards.map(([label, value]) => (
          <article className="brain-trust-card" key={label}>
            <span>{label}</span>
            <strong>{value}</strong>
          </article>
        ))}
      </div>
    </section>
  )
}

export default TrustIndicators
