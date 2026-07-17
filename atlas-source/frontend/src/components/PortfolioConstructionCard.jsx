function formatMetric(value, suffix = '') {
  const numberValue = Number(value)

  if (Number.isNaN(numberValue)) {
    return 'Unavailable'
  }

  return `${numberValue.toFixed(2).replace(/\.00$/, '')}${suffix}`
}

function PortfolioConstructionCard({ construction }) {
  const summary = construction?.operations_summary ?? {}
  const rows = [
    ['Portfolio Health', summary.portfolio_health ?? 'Unavailable'],
    ['Risk Budget', summary.risk_budget ?? 'Unavailable'],
    ['Largest Position', formatMetric(summary.largest_position, '%')],
    ['Most Concentrated Sector', summary.most_concentrated_sector ?? 'Unavailable'],
    ['Diversification Score', formatMetric(summary.diversification_score)],
    ['Suggested Rebalance', summary.suggested_rebalance ?? 'Maintain'],
  ]

  return (
    <section className="paper-panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Portfolio Construction</p>
          <h2>Institutional Allocation</h2>
        </div>
        <span className="paper-policy-pill">HUMAN APPROVAL</span>
      </div>
      <dl className="paper-performance-list">
        {rows.map(([label, value]) => (
          <div key={label}>
            <dt>{label}</dt>
            <dd>{value}</dd>
          </div>
        ))}
      </dl>
    </section>
  )
}

export default PortfolioConstructionCard
