function formatMetric(value, suffix = '') {
  const numberValue = Number(value)

  if (Number.isNaN(numberValue)) {
    return 'Unavailable'
  }

  return `${numberValue.toFixed(2).replace(/\.00$/, '')}${suffix}`
}

function PaperPerformanceCard({ performance }) {
  const metadata = performance?.metadata ?? {}
  const metrics = [
    ['Daily Return', formatMetric(performance?.daily_return, '%')],
    ['Total Return', formatMetric(performance?.total_return, '%')],
    ['Win Rate', formatMetric(performance?.win_rate, '%')],
    ['Sharpe', formatMetric(performance?.sharpe)],
    ['Sortino', formatMetric(performance?.sortino)],
    ['Max Drawdown', formatMetric(performance?.max_drawdown, '%')],
    ['Alpha vs S&P', formatMetric(performance?.alpha_vs_sp, '%')],
  ]

  return (
    <section className="paper-panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">NO BROKER CONNECTED</p>
          <h2>Replay Performance</h2>
          <p className="muted-copy">
            Run {metadata.run_number ?? 'n/a'} · {metadata.simulated_at ?? 'No run timestamp'}
          </p>
        </div>
        <span className="paper-policy-pill">HISTORICAL PRICE REPLAY</span>
      </div>
      <dl className="paper-performance-list">
        {metrics.map(([label, value]) => (
          <div key={label}>
            <dt>{label}</dt>
            <dd>{value}</dd>
          </div>
        ))}
      </dl>
    </section>
  )
}

export default PaperPerformanceCard
