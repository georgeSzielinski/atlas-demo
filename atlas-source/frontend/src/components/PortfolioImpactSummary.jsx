function formatValue(value, fallback = 'Unavailable') {
  if (value === null || value === undefined || value === '') {
    return fallback
  }
  return String(value)
}

function PortfolioImpactSummary({ impact }) {
  const data = impact ?? {}
  const allocation = data.allocation ?? {}
  const riskBudget = data.risk_budget ?? {}
  const sector = data.sector_impact ?? {}
  const cash = data.cash_impact ?? {}
  const diversification = data.diversification_impact ?? {}

  const rows = [
    ['Target Weight', allocation.target_weight !== undefined ? `${allocation.target_weight}%` : 'Unavailable'],
    ['Allocation Action', formatValue(allocation.action)],
    ['Risk Budget', formatValue(riskBudget.risk_budget ?? riskBudget.level)],
    ['Sector', formatValue(sector.sector)],
    ['Most Concentrated Sector', formatValue(sector.most_concentrated_sector)],
    ['Suggested Rebalance', formatValue(cash.suggested_rebalance)],
    ['Diversification Score', formatValue(diversification.diversification_score)],
  ]
  const hasImpact = rows.some(([, value]) => value !== 'Unavailable')

  return (
    <section className="brain-panel">
      <div className="brain-panel__heading">
        <div>
          <p className="eyebrow">Portfolio Impact</p>
          <h3>How This Fits The Paper Portfolio</h3>
        </div>
        <span className="brain-pill">PAPER ONLY</span>
      </div>

      {hasImpact ? (
        <dl className="brain-detail-list">
          {rows.map(([label, value]) => (
            <div key={label}>
              <dt>{label}</dt>
              <dd>{value}</dd>
            </div>
          ))}
        </dl>
      ) : (
        <p className="brain-empty">
          No portfolio impact is available. Atlas will show paper-portfolio fit after
          construction data is saved.
        </p>
      )}
    </section>
  )
}

export default PortfolioImpactSummary
