function formatNumber(value, suffix = '') {
  const number = Number(value)
  if (Number.isNaN(number)) {
    return 'Unavailable'
  }
  return `${number.toFixed(2).replace(/\.00$/, '')}${suffix}`
}

function verdictModifier(verdict) {
  return String(verdict ?? 'unknown').toLowerCase().replace(/\s+/g, '-')
}

function PerformanceDashboard({ analytics }) {
  const equity = analytics?.equity_curve ?? {}
  const risk = analytics?.risk_statistics ?? {}
  const benchmarks = analytics?.benchmark_comparison ?? {}
  const trust = analytics?.trust_assessment ?? {}

  const cards = [
    ['Portfolio Value', formatNumber(equity.latest_value)],
    ['Daily Return', formatNumber(equity.daily_return, '%')],
    ['Weekly Return', formatNumber(equity.weekly_return, '%')],
    ['Monthly Return', formatNumber(equity.monthly_return, '%')],
    ['Cumulative Return', formatNumber(equity.cumulative_return, '%')],
    ['Sharpe', formatNumber(risk.sharpe)],
    ['Sortino', formatNumber(risk.sortino)],
    ['Max Drawdown', formatNumber(risk.max_drawdown, '%')],
    ['Best Benchmark Alpha', formatNumber(benchmarks.best_benchmark_alpha, '%')],
  ]

  return (
    <section className="analytics-panel">
      <div className="analytics-panel__heading">
        <div>
          <p className="eyebrow">Performance Analytics</p>
          <h3>Atlas Measured Against Itself</h3>
        </div>
        <span className={`trust-badge trust-badge--${verdictModifier(trust.verdict)}`}>
          {trust.verdict ?? 'Not Enough Evidence'}
        </span>
      </div>

      <div className="analytics-summary-grid">
        {cards.map(([label, value]) => (
          <article className="analytics-metric-card" key={label}>
            <span>{label}</span>
            <strong>{value}</strong>
          </article>
        ))}
      </div>

      {Array.isArray(trust.evidence) && trust.evidence.length > 0 ? (
        <div className="trust-evidence">
          <h4>Evidence (not opinion)</h4>
          <ul>
            {trust.evidence.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
      ) : null}
    </section>
  )
}

export default PerformanceDashboard
