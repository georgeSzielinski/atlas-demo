function formatValue(value, fallback = 'Unavailable') {
  if (value === null || value === undefined || value === '') {
    return fallback
  }
  return String(value)
}

function MarketStatusCard({ marketStatus }) {
  const status = marketStatus?.market_status ?? {}
  const snapshot = marketStatus?.snapshot ?? {}
  const freshness = marketStatus?.data_freshness ?? {}
  const isOpen = status.is_open === true

  const rows = [
    ['Current Provider', formatValue(snapshot.provider)],
    ['Last Market Update', formatValue(snapshot.snapshot_date)],
    ['Cache Age', freshness.age_seconds === null || freshness.age_seconds === undefined
      ? 'Unknown'
      : `${freshness.age_seconds}s (${freshness.label})`],
    ['Fallback Used', snapshot.fallback_used ? 'Yes' : 'No'],
    ['Validated', snapshot.validated ? 'Yes' : 'No'],
  ]

  return (
    <section className="operations-panel market-status-card">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Market Data</p>
          <h2>Market Status</h2>
        </div>
        <span className={`market-session market-session--${isOpen ? 'open' : 'closed'}`}>
          {isOpen ? 'MARKET OPEN' : 'MARKET CLOSED'}
        </span>
      </div>

      <dl className="market-detail-list">
        {rows.map(([label, value]) => (
          <div key={label}>
            <dt>{label}</dt>
            <dd>{value}</dd>
          </div>
        ))}
      </dl>
      <p className="market-note">
        {formatValue(status.note, 'Deterministic placeholder session.')}
      </p>
    </section>
  )
}

export default MarketStatusCard
