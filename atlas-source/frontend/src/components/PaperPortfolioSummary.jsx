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

function PaperPortfolioSummary({ portfolio }) {
  const positions = portfolio?.positions ?? {}
  const positionCount = Object.keys(positions).length
  const runNumber = portfolio?.run_number ?? portfolio?.policy?.run_number
  const simulatedAt = portfolio?.simulated_at ?? portfolio?.policy?.simulated_at ?? portfolio?.date
  const policy = portfolio?.policy ?? {}
  const cards = [
    ['Historical Replay Portfolio Value', formatCurrency(portfolio?.portfolio_value), `${positionCount} replay positions`],
    ['Replay Cash', formatCurrency(portfolio?.cash), 'Replay cash balance'],
    ['Replay P/L (Realized)', formatCurrency(portfolio?.realized_pl), 'Closed replay trades'],
    ['Replay P/L (Unrealized)', formatCurrency(portfolio?.unrealized_pl), 'Open replay positions'],
    ['Replay Total Return', formatPercent(portfolio?.total_return), 'Return over the replay window'],
    ['Mode', policy.mode ?? portfolio?.mode ?? 'historical_price_replay', 'Paper trading mode'],
    ['Price-backed', policy.price_backed ? 'Yes' : 'No', 'Uses historical close prices'],
    ['Data Source', policy.data_source ?? portfolio?.data_source ?? 'Unavailable', 'Replay price source'],
    ['Fallback Used', policy.fallback_used ? 'Yes' : 'No', 'Historical provider fallback'],
    ['Last Price Date', policy.last_price_date ?? simulatedAt ?? 'Unavailable', 'Latest price row'],
  ]

  return (
    <section className="paper-panel paper-summary-panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">HISTORICAL PRICE REPLAY</p>
          <h2>Replay Portfolio</h2>
          <p className="muted-copy">
            {`Run ${runNumber ?? 'n/a'} · ${simulatedAt ?? 'No run timestamp'}`}
          </p>
        </div>
        <div className="paper-hero__badges">
          <span>NO REAL MONEY</span>
          <span>NO BROKER CONNECTED</span>
        </div>
      </div>
      <div className="paper-metric-grid">
        {cards.map(([label, value, detail]) => (
          <article className="paper-metric-card" key={label}>
            <span>{label}</span>
            <strong>{value}</strong>
            <small>{detail}</small>
          </article>
        ))}
      </div>
    </section>
  )
}

export default PaperPortfolioSummary
