function formatPercent(value) {
  const numberValue = Number(value ?? 0)
  return `${Number.isNaN(numberValue) ? 0 : numberValue}%`
}

function ProbabilityCard({ probability = {}, expected = {}, scenarios = {} }) {
  const rows = Object.entries(probability)

  return (
    <section className="workspace-panel probability-card">
      <div className="panel-heading">
        <p className="eyebrow">Probability</p>
        <h3>Distribution</h3>
      </div>
      <div className="probability-bars">
        {rows.length > 0 ? rows.map(([label, value]) => (
          <div className="probability-row" key={label}>
            <div className="probability-row__label">
              <span>{label.replaceAll('_', ' ')}</span>
              <strong>{formatPercent(value)}</strong>
            </div>
            <div className="probability-row__track">
              <span style={{ width: `${Math.min(Number(value) || 0, 100)}%` }} />
            </div>
          </div>
        )) : <p className="muted-copy">No probability report available.</p>}
      </div>
      <dl className="compact-metrics">
        <div>
          <dt>Expected Return</dt>
          <dd>{expected.expected_return ?? 0}%</dd>
        </div>
        <div>
          <dt>Holding Period</dt>
          <dd>{expected.expected_holding_period ?? 0}d</dd>
        </div>
        <div>
          <dt>Best/Base/Worst</dt>
          <dd>{expected.best_case ?? 0}% / {expected.base_case ?? 0}% / {expected.worst_case ?? 0}%</dd>
        </div>
      </dl>
      <div className="scenario-strip">
        <span>Scenarios</span>
        <strong>{Array.isArray(scenarios.counterfactuals) ? scenarios.counterfactuals.length : 0}</strong>
      </div>
    </section>
  )
}

export default ProbabilityCard
