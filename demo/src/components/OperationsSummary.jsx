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

function OperationsSummary({ dashboard, macroSummary, catalystSummary, runtimeStatus, paperPerformance }) {
  const health = dashboard?.system_health ?? {}
  const macro = macroSummary?.summary ?? macroSummary ?? {}
  const catalystText = typeof catalystSummary === 'string'
    ? catalystSummary
    : catalystSummary?.summary ?? catalystSummary?.message ?? 'Unavailable'
  const latestPerformance = paperPerformance?.paper_performance_reports?.[0]?.performance ?? {}

  const cards = [
    ['Current Phase', runtimeStatus?.market_phase ?? runtimeStatus?.current_state, 'Daily paper cycle phase'],
    ['Last Completed Cycle', runtimeStatus?.last_update, 'Most recent runtime update'],
    ['Next Task', runtimeStatus?.next_task, 'Next scheduled paper task'],
    ['Recommendations Today', runtimeStatus?.recommendations_today, 'Paper review count'],
    ['Paper Portfolio Value', formatCurrency(runtimeStatus?.paper_portfolio_value), 'Simulated capital only'],
    ['Daily Return', formatPercent(latestPerformance.daily_return), 'Latest paper return'],
    ['Alpha vs S&P', formatPercent(latestPerformance.alpha_vs_sp), 'Latest paper benchmark spread'],
    ['Macro Regime', macro.current_macro_regime ?? macro.regime, 'Current macro context'],
    ['Catalysts', catalystText, 'Upcoming event summary'],
    ['Backend', health.backend_status, 'FastAPI operating state'],
  ]

  return (
    <section className="operations-panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Operations</p>
          <h2>Daily Operating State</h2>
        </div>
        <span className="operations-policy-pill">SIMULATED ONLY</span>
      </div>
      <div className="operations-summary-grid">
        {cards.map(([label, value, detail]) => (
          <article className="operations-metric-card" key={label}>
            <span>{label}</span>
            <strong>{formatValue(value)}</strong>
            <small>{detail}</small>
          </article>
        ))}
      </div>
    </section>
  )
}

export default OperationsSummary
