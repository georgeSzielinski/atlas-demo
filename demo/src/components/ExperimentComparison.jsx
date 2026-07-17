const METRICS = [
  ['sharpe', 'Sharpe'],
  ['sortino', 'Sortino'],
  ['win_rate', 'Win Rate'],
  ['average_return', 'Average Return'],
  ['drawdown', 'Drawdown'],
  ['trade_frequency', 'Trade Frequency'],
  ['holding_period', 'Holding Period'],
  ['alpha', 'Alpha'],
  ['probability_calibration', 'Probability Calibration'],
  ['knowledge_score', 'Knowledge Score'],
  ['stability_score', 'Stability Score'],
]
const LOWER_IS_BETTER = new Set(['drawdown'])

function toNumber(value) {
  const number = Number(value)
  return Number.isNaN(number) ? 0 : number
}

function difference(metric, baseline, candidate) {
  if (LOWER_IS_BETTER.has(metric)) {
    return Math.round((Math.abs(baseline) - Math.abs(candidate)) * 100) / 100
  }
  return Math.round((candidate - baseline) * 100) / 100
}

function ExperimentComparison({ experiment }) {
  const arenaMetrics = experiment?.arena_metrics ?? {}
  const baseline = arenaMetrics.baseline ?? {}
  const candidate = arenaMetrics.candidate ?? {}
  const hasMetrics = Object.keys(baseline).length > 0 && Object.keys(candidate).length > 0

  return (
    <section className="lab-panel">
      <div className="lab-panel__heading">
        <div>
          <p className="eyebrow">Experiment Comparison</p>
          <h3>{experiment?.title ?? 'Select an experiment'}</h3>
        </div>
        <span className="lab-pill">Baseline vs Candidate</span>
      </div>

      {!experiment ? (
        <p className="lab-empty">Select an experiment to compare baseline and candidate.</p>
      ) : !hasMetrics ? (
        <p className="lab-empty">
          This experiment has not been executed in Simulation Arena yet. No metrics to compare.
        </p>
      ) : (
        <table className="lab-table">
          <thead>
            <tr>
              <th>Metric</th>
              <th>Baseline</th>
              <th>Candidate</th>
              <th>Difference</th>
            </tr>
          </thead>
          <tbody>
            {METRICS.map(([key, label]) => {
              const baselineValue = toNumber(baseline[key])
              const candidateValue = toNumber(candidate[key])
              const delta = difference(key, baselineValue, candidateValue)
              const rowClass = delta > 0 ? 'is-improved' : delta < 0 ? 'is-regressed' : ''

              return (
                <tr className={rowClass} key={key}>
                  <td>{label}</td>
                  <td>{baselineValue}</td>
                  <td>{candidateValue}</td>
                  <td>{delta > 0 ? `+${delta}` : delta}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      )}
    </section>
  )
}

export default ExperimentComparison
