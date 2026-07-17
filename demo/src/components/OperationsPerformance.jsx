function formatMetric(value, suffix = '') {
  const numberValue = Number(value)

  if (Number.isNaN(numberValue)) {
    return 'Unavailable'
  }

  return `${numberValue.toFixed(2).replace(/\.00$/, '')}${suffix}`
}

function OperationsPerformance({ dashboard, paperPerformance }) {
  const recommendation = dashboard?.recommendation_metrics ?? {}
  const latestPaper = paperPerformance?.paper_performance_reports?.[0]?.performance ?? {}
  const rows = [
    ['Recommendation Hit Rate', formatMetric(recommendation.hit_rate, '%')],
    ['Average Validated Return', formatMetric(recommendation.average_return, '%')],
    ['Paper Total Return', formatMetric(latestPaper.total_return, '%')],
    ['Paper Alpha vs S&P', formatMetric(latestPaper.alpha_vs_sp, '%')],
    ['Paper Sharpe', formatMetric(latestPaper.sharpe)],
    ['Paper Max Drawdown', formatMetric(latestPaper.max_drawdown, '%')],
  ]

  return (
    <section className="operations-panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Performance</p>
          <h2>Research Performance</h2>
        </div>
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

export default OperationsPerformance
