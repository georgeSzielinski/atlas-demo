function ArenaComparison({ arena }) {
  if (!arena) {
    return (
      <section className="lab-panel">
        <div className="lab-panel__heading">
          <div>
            <p className="eyebrow">Simulation Arena</p>
            <h3>Strategy Comparison</h3>
          </div>
        </div>
        <p className="lab-empty">
          No Simulation Arena runs yet. Arena results appear here once an experiment is executed.
        </p>
      </section>
    )
  }

  const comparison = arena.comparison ?? {}
  const ordered = Array.isArray(comparison.ordered)
    ? comparison.ordered
    : Array.isArray(arena.results)
      ? arena.results
      : []
  const highlights = [
    ['Best Overall', comparison.best_overall],
    ['Best Risk Adjusted', comparison.best_risk_adjusted],
    ['Best Low Drawdown', comparison.best_low_drawdown],
    ['Most Stable', comparison.most_stable],
    ['Most Knowledgeable', comparison.most_knowledgeable],
  ]

  return (
    <section className="lab-panel">
      <div className="lab-panel__heading">
        <div>
          <p className="eyebrow">Simulation Arena</p>
          <h3>Strategy Comparison</h3>
        </div>
        <span className="lab-pill">{arena.arena_id ?? 'arena'}</span>
      </div>

      <div className="arena-highlights">
        {highlights.map(([label, value]) => (
          <div className="arena-highlight" key={label}>
            <span>{label}</span>
            <strong>{value ?? 'Unavailable'}</strong>
          </div>
        ))}
      </div>

      {ordered.length > 0 ? (
        <table className="lab-table">
          <thead>
            <tr>
              <th>Strategy</th>
              <th>Score</th>
              <th>Win Rate</th>
              <th>Sharpe</th>
              <th>Recommendation</th>
            </tr>
          </thead>
          <tbody>
            {ordered.map((item) => (
              <tr key={item.strategy_name}>
                <td>{item.strategy_name}</td>
                <td>{item.overall_score}</td>
                <td>{item.metrics?.win_rate ?? 0}</td>
                <td>{item.metrics?.sharpe_ratio ?? 0}</td>
                <td>{item.recommendation ?? 'Unavailable'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : null}
    </section>
  )
}

export default ArenaComparison
