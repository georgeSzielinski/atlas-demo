function formatMetric(value, suffix = '') {
  const numberValue = Number(value)

  if (Number.isNaN(numberValue)) {
    return 'Unavailable'
  }

  return `${numberValue.toFixed(2).replace(/\.00$/, '')}${suffix}`
}

function chartPoints(rows, width, height) {
  const values = rows.map((row) => Number(row.portfolio_value ?? 0))
  const min = Math.min(...values)
  const max = Math.max(...values)
  const span = max - min || 1
  const step = rows.length > 1 ? width / (rows.length - 1) : width

  return rows.map((row, index) => {
    const value = Number(row.portfolio_value ?? 0)
    const x = rows.length > 1 ? index * step : width / 2
    const y = height - ((value - min) / span) * (height - 30) - 15
    return { x, y, row }
  })
}

function PaperPnLChart({
  history = [],
  replay = null,
  eyebrow = 'REPLAY P/L CHART',
  title = 'Historical Replay Portfolio Value',
  pill = 'PRICE BACKED',
  pointsLabel = 'price-backed replay points',
}) {
  // History arrives newest-first from the API; chart oldest-to-newest.
  const rows = Array.isArray(history) ? [...history].reverse().slice(-60) : []
  const width = 640
  const height = 200
  const replayFailed = replay != null && replay.price_backed === false

  if (replayFailed) {
    return (
      <section className="paper-panel paper-pnl-chart">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">REPLAY P/L CHART</p>
            <h2>Historical Replay Portfolio Value</h2>
          </div>
          <span className="paper-policy-pill paper-policy-pill--danger">NOT PRICE BACKED</span>
        </div>
        <p className="paper-not-price-backed">
          No P/L chart because replay was not price-backed.
          {replay.error ? ` ${replay.error}.` : ''}
        </p>
      </section>
    )
  }

  if (rows.length === 0) {
    return null
  }

  const points = chartPoints(rows, width, height)
  const polyline = points.map((point) => `${point.x},${point.y}`).join(' ')
  const first = rows[0]
  const latest = rows[rows.length - 1]
  const startingValue = Number(first.portfolio_value ?? 0)
  const cumulativePl = Number(latest.portfolio_value ?? 0) - startingValue
  const axisLabels = [
    points[0],
    points[Math.floor(points.length / 2)],
    points[points.length - 1],
  ].filter((point, index, all) => all.indexOf(point) === index)

  return (
    <section className="paper-panel paper-pnl-chart">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">{eyebrow}</p>
          <h2>{title}</h2>
          <p className="muted-copy">{rows.length} {pointsLabel}</p>
        </div>
        <span className="paper-policy-pill">{pill}</span>
      </div>

      <svg aria-label={`${title} chart`} viewBox={`0 0 ${width} ${height + 24}`}>
        <polyline points={polyline} />
        {points.map((point) => (
          <circle className="paper-pnl-chart__point" cx={point.x} cy={point.y} key={point.row.date} r="4">
            <title>
              {`${point.row.date} · value ${formatMetric(point.row.portfolio_value)} · cumulative P/L ${formatMetric(Number(point.row.portfolio_value ?? 0) - startingValue)} · daily return ${formatMetric(point.row.daily_return, '%')}`}
            </title>
          </circle>
        ))}
        {axisLabels.map((point) => (
          <text
            className="paper-pnl-chart__axis-label"
            key={`label-${point.row.date}`}
            textAnchor="middle"
            x={Math.min(Math.max(point.x, 34), width - 34)}
            y={height + 18}
          >
            {String(point.row.date).slice(0, 10)}
          </text>
        ))}
      </svg>
      <dl className="paper-performance-list">
        <div>
          <dt>Portfolio value</dt>
          <dd>{formatMetric(latest.portfolio_value)}</dd>
        </div>
        <div>
          <dt>Cumulative P/L</dt>
          <dd>{formatMetric(cumulativePl)}</dd>
        </div>
        <div>
          <dt>Latest daily return</dt>
          <dd>{formatMetric(latest.daily_return, '%')}</dd>
        </div>
        <div>
          <dt>Total return</dt>
          <dd>{formatMetric(latest.total_return, '%')}</dd>
        </div>
      </dl>
    </section>
  )
}

export default PaperPnLChart
