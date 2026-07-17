const categories = ['Technical', 'Fundamentals', 'Forecast', 'News', 'SEC', 'Portfolio', 'Risk']

function scoreFor(category, evidence, recommendation) {
  const match = evidence.find((item) => (
    item.category === category ||
    item.name === category ||
    (category === 'Fundamentals' && item.category === 'Fundamental')
  ))

  if (match) {
    return match.score ?? 0
  }

  const fallback = {
    Technical: recommendation?.technical_score,
    Fundamentals: recommendation?.fundamental_score,
    Forecast: recommendation?.forecast_score,
    News: recommendation?.news_confidence,
    SEC: recommendation?.sec_score,
    Portfolio: recommendation?.portfolio_score,
    Risk: recommendation?.risk_score,
  }

  return fallback[category] ?? 0
}

function EvidenceBreakdown({ recommendation = {} }) {
  const evidence = Array.isArray(recommendation.evidence_breakdown)
    ? recommendation.evidence_breakdown
    : []

  return (
    <section className="workspace-panel evidence-panel">
      <div className="panel-heading">
        <p className="eyebrow">Evidence</p>
        <h3>Signal Stack</h3>
      </div>
      <div className="evidence-grid">
        {categories.map((category) => {
          const score = scoreFor(category, evidence, recommendation)
          return (
            <div className="evidence-cell" key={category}>
              <span>{category}</span>
              <strong>{score}</strong>
              <div className="mini-track">
                <i style={{ width: `${Math.min(Number(score) || 0, 100)}%` }} />
              </div>
            </div>
          )
        })}
      </div>
    </section>
  )
}

export default EvidenceBreakdown
