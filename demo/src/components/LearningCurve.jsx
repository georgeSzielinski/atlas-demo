function formatNumber(value, suffix = '') {
  const number = Number(value)
  if (Number.isNaN(number)) {
    return 'Unavailable'
  }
  return `${number.toFixed(2).replace(/\.00$/, '')}${suffix}`
}

function buildPoints(rows, key, width, height) {
  if (rows.length === 0) {
    return ''
  }
  const values = rows.map((row) => Number(row[key] ?? 0))
  const min = Math.min(...values)
  const max = Math.max(...values)
  const span = max - min || 1
  const step = rows.length > 1 ? width / (rows.length - 1) : width

  return rows
    .map((row, index) => {
      const value = Number(row[key] ?? 0)
      const x = rows.length > 1 ? index * step : width / 2
      const y = height - ((value - min) / span) * (height - 20) - 10
      return `${x},${y}`
    })
    .join(' ')
}

function LearningCurve({ learning }) {
  const metrics = Array.isArray(learning?.metrics) ? learning.metrics : []
  const points = Array.isArray(learning?.points) ? learning.points : []
  const width = 640
  const height = 160
  const polyline = buildPoints(points, 'win_rate', width, height)

  return (
    <section className="analytics-panel">
      <div className="analytics-panel__heading">
        <div>
          <p className="eyebrow">Learning Curve</p>
          <h3>How Atlas Changes Over Time</h3>
        </div>
      </div>

      <div className="analytics-summary-grid">
        {metrics.map((metric) => (
          <article className="analytics-metric-card" key={metric.label}>
            <span>{metric.label}</span>
            <strong>{formatNumber(metric.value)}</strong>
          </article>
        ))}
      </div>

      {points.length === 0 ? (
        <p className="analytics-empty">No journal history yet for the learning curve.</p>
      ) : (
        <svg aria-label="Learning curve win rate" className="analytics-chart" viewBox={`0 0 ${width} ${height}`}>
          <polyline points={polyline} />
        </svg>
      )}
    </section>
  )
}

export default LearningCurve
