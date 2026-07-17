function formatMetric(value, suffix = '') {
  const numberValue = Number(value)

  if (Number.isNaN(numberValue)) {
    return 'Unavailable'
  }

  return `${numberValue.toFixed(2).replace(/\.00$/, '')}${suffix}`
}

function formatValue(value, fallback = 'Unavailable') {
  if (value === null || value === undefined || value === '') {
    return fallback
  }

  return String(value)
}

function DailyJournalCard({ dailyJournal }) {
  const latest = dailyJournal?.latest_daily_journal ?? null
  const entries = Array.isArray(dailyJournal?.daily_journals)
    ? dailyJournal.daily_journals
    : []
  const performance = latest?.performance_summary ?? {}
  const recommendations = latest?.recommendation_summary ?? {}
  const lessons = latest?.lessons_learned ?? {}
  const tasks = Array.isArray(latest?.research_tasks) ? latest.research_tasks : []
  const lessonRows = [
    ['Most useful evidence', lessons.most_useful_evidence_today],
    ['Weakest evidence', lessons.weakest_evidence_today],
    ['Most important catalyst', lessons.most_important_catalyst],
    ['Macro influence', lessons.macro_influence],
    ['Committee observations', lessons.committee_observations],
    ['Forecast observations', lessons.forecast_observations],
  ]

  if (!latest) {
    return (
      <section className="operations-panel daily-journal-card">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">Daily Journal</p>
            <h2>Research Record</h2>
          </div>
          <div className="operations-pill-row">
            <span className="operations-policy-pill">SIMULATED ONLY</span>
            <span className="operations-policy-pill">NO REAL MONEY</span>
          </div>
        </div>
        <p className="operations-empty">
          No completed daily journal entries yet. Atlas will show the latest
          paper-testing research record here after a completed daily cycle.
        </p>
      </section>
    )
  }

  return (
    <section className="operations-panel daily-journal-card">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Daily Journal</p>
          <h2>{formatValue(latest.date, 'Latest Entry')}</h2>
        </div>
        <div className="operations-pill-row">
          <span className="operations-policy-pill">SIMULATED ONLY</span>
          <span className="operations-policy-pill">NO REAL MONEY</span>
          <span className="operations-policy-pill">NO BROKER CONNECTED</span>
        </div>
      </div>

      <dl className="operations-stat-list">
        <div>
          <dt>Market Regime</dt>
          <dd>{formatValue(latest.market_regime)}</dd>
        </div>
        <div>
          <dt>Portfolio Value</dt>
          <dd>{formatMetric(performance.portfolio_value)}</dd>
        </div>
        <div>
          <dt>Daily Return</dt>
          <dd>{formatMetric(performance.daily_return, '%')}</dd>
        </div>
        <div>
          <dt>Alpha vs S&P</dt>
          <dd>{formatMetric(performance.alpha_vs_sp, '%')}</dd>
        </div>
        <div>
          <dt>Recommendations</dt>
          <dd>{formatValue(recommendations.recommendations_today, '0')}</dd>
        </div>
        <div>
          <dt>Open Positions</dt>
          <dd>{formatValue(performance.open_positions, '0')}</dd>
        </div>
      </dl>

      <div className="daily-journal-card__notes">
        <strong>Latest Journal Summary</strong>
        <p>
          {formatValue(latest.runtime_state?.summary, 'No cycle summary recorded.')}
        </p>
        <strong>Lessons Learned</strong>
        <div className="daily-journal-card__lesson-grid">
          {lessonRows.map(([label, value]) => (
            <span key={label}>
              <b>{label}</b>
              {formatValue(value)}
            </span>
          ))}
        </div>
        <strong>Research Tasks</strong>
        {tasks.length > 0 ? (
          <ul className="daily-journal-card__task-list">
            {tasks.slice(0, 5).map((task) => (
              <li key={task}>{task}</li>
            ))}
          </ul>
        ) : (
          <p>No research tasks recorded.</p>
        )}
      </div>

      <div className="daily-journal-card__recent">
        <strong>Recent Entries</strong>
        {entries.length > 0 ? (
          entries.slice(0, 5).map((entry) => (
            <span key={entry.journal_id ?? entry.date}>
              {formatValue(entry.date)} · {formatValue(entry.market_regime)}
            </span>
          ))
        ) : (
          <span>No recent journal entries.</span>
        )}
      </div>
    </section>
  )
}

export default DailyJournalCard
