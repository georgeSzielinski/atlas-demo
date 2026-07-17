function formatNumber(value, suffix = '') {
  const number = Number(value)
  if (Number.isNaN(number)) {
    return 'Unavailable'
  }
  return `${number.toFixed(2).replace(/\.00$/, '')}${suffix}`
}

function tradeLine(trade) {
  if (!trade) {
    return ''
  }
  return `${trade.ticker ?? '—'} (${trade.action ?? '—'}): ${formatNumber(trade.profit_loss)}`
}

function MonthlyReport({ report }) {
  if (!report) {
    return (
      <section className="analytics-panel">
        <div className="analytics-panel__heading">
          <div>
            <p className="eyebrow">Monthly Report</p>
            <h3>Deterministic Monthly Summary</h3>
          </div>
        </div>
        <p className="analytics-empty">No monthly report is available yet.</p>
      </section>
    )
  }

  const performance = report.performance ?? {}
  const lessons = Array.isArray(report.major_lessons) ? report.major_lessons : []
  const best = Array.isArray(report.best_decisions) ? report.best_decisions : []
  const mistakes = Array.isArray(report.largest_mistakes) ? report.largest_mistakes : []
  const validation = report.validation_summary ?? {}

  const performanceCards = [
    ['Month Return', formatNumber(performance.month_return, '%')],
    ['Cumulative Return', formatNumber(performance.cumulative_return, '%')],
    ['Best Day', formatNumber(performance.best_day, '%')],
    ['Worst Day', formatNumber(performance.worst_day, '%')],
  ]

  return (
    <section className="analytics-panel">
      <div className="analytics-panel__heading">
        <div>
          <p className="eyebrow">Monthly Report</p>
          <h3>{report.month ?? 'Monthly Summary'}</h3>
        </div>
        <span className="analytics-pill">DETERMINISTIC</span>
      </div>

      <div className="analytics-summary-grid">
        {performanceCards.map(([label, value]) => (
          <article className="analytics-metric-card" key={label}>
            <span>{label}</span>
            <strong>{value}</strong>
          </article>
        ))}
      </div>

      <div className="monthly-report-grid">
        <div>
          <h4>Major Lessons</h4>
          {lessons.length === 0 ? (
            <p className="analytics-empty">No lessons recorded.</p>
          ) : (
            <ul>
              {lessons.map((lesson) => (
                <li key={lesson}>{lesson}</li>
              ))}
            </ul>
          )}
        </div>
        <div>
          <h4>Best Decisions</h4>
          {best.length === 0 ? (
            <p className="analytics-empty">No decisions recorded.</p>
          ) : (
            <ul>
              {best.map((trade) => (
                <li key={`best-${trade.ticker}`}>{tradeLine(trade)}</li>
              ))}
            </ul>
          )}
        </div>
        <div>
          <h4>Largest Mistakes</h4>
          {mistakes.length === 0 ? (
            <p className="analytics-empty">No mistakes recorded.</p>
          ) : (
            <ul>
              {mistakes.map((trade) => (
                <li key={`mistake-${trade.ticker}`}>{tradeLine(trade)}</li>
              ))}
            </ul>
          )}
        </div>
        <div>
          <h4>Validation Summary</h4>
          <p>Validations: {validation.validation_count ?? 0}</p>
          <ul>
            {Object.entries(validation.decision_distribution ?? {}).map(([key, value]) => (
              <li key={key}>
                {key}: {value}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  )
}

export default MonthlyReport
