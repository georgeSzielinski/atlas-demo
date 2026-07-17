function isProviderUnhealthy(providerHealth) {
  if (!providerHealth) {
    return false
  }

  if (providerHealth.healthy === false) {
    return true
  }

  return providerHealth.summary?.healthy === false
}

function macroRiskValue(macroSummary) {
  const summary = macroSummary?.summary ?? macroSummary ?? {}
  return Number(summary.macro_risk_score ?? summary.risk_score ?? 0)
}

function hasHighRiskCatalyst(catalystSummary) {
  try {
    const text = JSON.stringify(catalystSummary ?? '').toLowerCase()
    return text.includes('high') || text.includes('risk') || text.includes('volatility')
  } catch {
    const text = String(catalystSummary ?? '').toLowerCase()
    return text.includes('high') || text.includes('risk') || text.includes('volatility')
  }
}

function paperDrawdown(performance) {
  const latest = performance?.paper_performance_reports?.[0]?.performance ?? {}
  return Number(latest.max_drawdown ?? 0)
}

function OperationsAlerts({ providerHealth, macroSummary, catalystSummary, paperPerformance }) {
  const alerts = [
    {
      active: isProviderUnhealthy(providerHealth),
      title: 'Provider unhealthy',
      detail: 'One or more data providers reported degraded health.',
      tone: 'warning',
    },
    {
      active: macroRiskValue(macroSummary) >= 75,
      title: 'High macro risk',
      detail: `Macro risk score is ${macroRiskValue(macroSummary) || 'unavailable'}.`,
      tone: 'warning',
    },
    {
      active: hasHighRiskCatalyst(catalystSummary),
      title: 'Upcoming high-risk catalyst',
      detail: 'Catalyst summary references high risk or volatility.',
      tone: 'warning',
    },
    {
      active: paperDrawdown(paperPerformance) <= -5,
      title: 'Paper drawdown warning',
      detail: `Paper max drawdown is ${paperDrawdown(paperPerformance)}%.`,
      tone: 'warning',
    },
    {
      active: true,
      title: 'Simulated-only safety notice',
      detail: 'SIMULATED ONLY. NO REAL MONEY. NO BROKER CONNECTED.',
      tone: 'safety',
    },
  ].filter((alert) => alert.active)

  return (
    <section className="operations-panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Alerts</p>
          <h2>Operating Notices</h2>
        </div>
      </div>
      <div className="operations-alert-list">
        {alerts.length > 0 ? (
          alerts.map((alert) => (
            <article className={`operations-alert operations-alert--${alert.tone}`} key={alert.title}>
              <strong>{alert.title}</strong>
              <span>{alert.detail}</span>
            </article>
          ))
        ) : (
          <p className="operations-empty">No operating notices.</p>
        )}
      </div>
    </section>
  )
}

export default OperationsAlerts
