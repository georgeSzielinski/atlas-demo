function formatValue(value, fallback = 'Unavailable') {
  if (value === null || value === undefined || value === '') {
    return fallback
  }

  return String(value)
}

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

function RuntimeStatusCard({ runtimeStatus, paperPerformance }) {
  const systemHealth = runtimeStatus?.system_health ?? {}
  const providerHealth = runtimeStatus?.provider_health ?? {}
  const latestPerformance = paperPerformance?.paper_performance_reports?.[0]?.performance ?? {}
  const rows = [
    ['Current Phase', runtimeStatus?.market_phase ?? runtimeStatus?.current_state],
    ['Runtime State', runtimeStatus?.current_state],
    ['Last Completed Cycle', runtimeStatus?.last_update],
    ['Next Scheduled Task', runtimeStatus?.next_task],
    ['Recommendations Today', runtimeStatus?.recommendations_today],
    ['Paper Portfolio Value', formatCurrency(runtimeStatus?.paper_portfolio_value)],
    ['Daily Return', formatPercent(latestPerformance.daily_return)],
    ['Alpha vs S&P', formatPercent(latestPerformance.alpha_vs_sp)],
    ['Provider health', providerHealth.healthy === false ? 'Warning' : 'Healthy'],
    ['System health', systemHealth.status],
  ]

  return (
    <section className="operations-panel runtime-status-card">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Daily Paper Cycle</p>
          <h2>Cycle Status</h2>
        </div>
        <div className="operations-pill-row">
          <span className="operations-policy-pill">SIMULATED ONLY</span>
          <span className="operations-policy-pill">NO BROKER CONNECTED</span>
        </div>
      </div>
      <dl className="operations-stat-list">
        {rows.map(([label, value]) => (
          <div key={label}>
            <dt>{label}</dt>
            <dd>{formatValue(value)}</dd>
          </div>
        ))}
      </dl>
      <p className="runtime-status-card__note">
        SIMULATED ONLY. NO BROKER CONNECTED. NO REAL MONEY.
      </p>
    </section>
  )
}

export default RuntimeStatusCard
