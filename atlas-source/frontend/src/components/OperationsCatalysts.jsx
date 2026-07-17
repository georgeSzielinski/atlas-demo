function summaryText(catalystSummary) {
  if (!catalystSummary) {
    return 'No catalyst summary returned.'
  }

  if (typeof catalystSummary === 'string') {
    return catalystSummary
  }

  return (
    catalystSummary.summary
    ?? catalystSummary.message
    ?? catalystSummary.description
    ?? JSON.stringify(catalystSummary)
  )
}

function OperationsCatalysts({ catalystSummary, macroSummary }) {
  const macro = macroSummary?.summary ?? macroSummary ?? {}

  return (
    <section className="operations-panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Macro & Catalysts</p>
          <h2>Market Context</h2>
        </div>
      </div>
      <div className="operations-context-grid">
        <article>
          <span>Current macro regime</span>
          <strong>{macro.current_macro_regime ?? macro.regime ?? 'Unavailable'}</strong>
          <small>Risk score {macro.macro_risk_score ?? macro.risk_score ?? 'Unavailable'}</small>
        </article>
        <article>
          <span>Upcoming catalyst summary</span>
          <strong>{summaryText(catalystSummary)}</strong>
          <small>Research-only event context</small>
        </article>
      </div>
    </section>
  )
}

export default OperationsCatalysts
