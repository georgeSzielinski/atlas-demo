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

function EquityCurve({ equity }) {
  const points = Array.isArray(equity?.points) ? equity.points : []
  const width = 640
  const height = 180
  const polyline = buildPoints(points, 'portfolio_value', width, height)

  const stats = [
    ['Daily', formatNumber(equity?.daily_return, '%')],
    ['Weekly', formatNumber(equity?.weekly_return, '%')],
    ['Monthly', formatNumber(equity?.monthly_return, '%')],
    ['Rolling', formatNumber(equity?.rolling_return, '%')],
    ['Cumulative', formatNumber(equity?.cumulative_return, '%')],
  ]

  return (
    <section className="analytics-panel">
      <div className="analytics-panel__heading">
        <div>
          <p className="eyebrow">Equity Curve</p>
          <h3>Portfolio Value Over Time</h3>
        </div>
        <span className="analytics-pill">PAPER ONLY</span>
      </div>

      {points.length === 0 ? (
        <p className="analytics-empty">No equity history is available yet.</p>
      ) : (
        <>
          <svg aria-label="Equity curve" className="analytics-chart" viewBox={`0 0 ${width} ${height}`}>
            <polyline points={polyline} />
          </svg>
          <div className="analytics-inline-stats">
            {stats.map(([label, value]) => (
              <div key={label}>
                <span>{label}</span>
                <strong>{value}</strong>
              </div>
            ))}
          </div>
        </>
      )}
    </section>
  )
}

export default EquityCurve
