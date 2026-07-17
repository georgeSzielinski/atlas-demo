function formatMetric(value, suffix = '') {
  const numberValue = Number(value)

  if (Number.isNaN(numberValue)) {
    return 'Unavailable'
  }

  return `${numberValue.toFixed(2).replace(/\.00$/, '')}${suffix}`
}

function RiskBudgetCard({ riskBudget }) {
  const summary = riskBudget?.summary ?? {}
  const holdings = Array.isArray(riskBudget?.holdings) ? riskBudget.holdings : []

  return (
    <section className="paper-panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Risk Budget</p>
          <h2>{summary.risk_budget ?? 'Unavailable'}</h2>
        </div>
      </div>
      <dl className="paper-performance-list">
        <div>
          <dt>Total Risk Contribution</dt>
          <dd>{formatMetric(summary.total_risk_contribution)}</dd>
        </div>
        <div>
          <dt>Portfolio Volatility</dt>
          <dd>{formatMetric(summary.portfolio_volatility, '%')}</dd>
        </div>
        {holdings.slice(0, 4).map((holding) => (
          <div key={holding.ticker}>
            <dt>{holding.ticker}</dt>
            <dd>{holding.risk_level}</dd>
          </div>
        ))}
      </dl>
    </section>
  )
}

export default RiskBudgetCard
