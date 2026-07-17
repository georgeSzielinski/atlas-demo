function formatCurrency(value) {
  const numberValue = Number(value)

  if (Number.isNaN(numberValue)) {
    return 'Unavailable'
  }

  return new Intl.NumberFormat('en-US', {
    currency: 'USD',
    maximumFractionDigits: 0,
    style: 'currency',
  }).format(numberValue)
}

function formatPercent(value) {
  const numberValue = Number(value)

  if (Number.isNaN(numberValue)) {
    return 'Unavailable'
  }

  return `${numberValue.toFixed(2).replace(/\.00$/, '')}%`
}

function OperationsPaperPortfolio({ paperPortfolio, paperPerformance }) {
  const portfolio = paperPortfolio?.latest_portfolio ?? {}
  const performance = paperPerformance?.paper_performance_reports?.[0]?.performance ?? {}
  const rows = [
    ['Paper portfolio value', formatCurrency(portfolio.portfolio_value)],
    ['Paper cash', formatCurrency(portfolio.cash)],
    ['Paper total return', formatPercent(portfolio.total_return ?? performance.total_return)],
    ['Alpha vs S&P', formatPercent(performance.alpha_vs_sp)],
  ]

  return (
    <section className="operations-panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Paper Portfolio</p>
          <h2>Simulated Capital</h2>
        </div>
        <span className="operations-policy-pill">NO REAL MONEY</span>
      </div>
      <dl className="operations-stat-list">
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

export default OperationsPaperPortfolio
