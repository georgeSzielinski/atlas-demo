function formatNumber(value, suffix = '') {
  const number = Number(value)
  if (Number.isNaN(number)) {
    return 'n/a'
  }
  return `${number.toFixed(2).replace(/\.00$/, '')}${suffix}`
}

function HistoricalInfluence({ historical }) {
  const data = historical ?? {}
  const analogs = Array.isArray(data.analogs) ? data.analogs : []
  const caseStudies = Array.isArray(data.case_studies) ? data.case_studies : []
  const outcomes = data.past_outcomes ?? {}

  return (
    <section className="brain-panel">
      <div className="brain-panel__heading">
        <div>
          <p className="eyebrow">Historical Influence</p>
          <h3>What History Suggests</h3>
        </div>
        <span className="brain-pill">Similarity {formatNumber(data.average_similarity)}</span>
      </div>

      <div className="brain-history-stats">
        <div>
          <span>Win rate</span>
          <strong>{formatNumber(outcomes.win_rate, '%')}</strong>
        </div>
        <div>
          <span>Avg return</span>
          <strong>{formatNumber(outcomes.average_historical_return, '%')}</strong>
        </div>
        <div>
          <span>Avg hold</span>
          <strong>{formatNumber(outcomes.average_holding_period)}</strong>
        </div>
      </div>

      <h4>Top analogs</h4>
      {analogs.length === 0 ? (
        <p className="brain-empty">
          No historical analogs are available yet. Atlas needs saved comparable cases
          before this section can influence trust.
        </p>
      ) : (
        <ul className="brain-analog-list">
          {analogs.map((analog, index) => (
            <li key={analog.case_id ?? `${analog.ticker}-${index}`}>
              <span>{analog.ticker ?? 'Unknown'}</span>
              <span>{formatNumber(analog.return ?? analog.percentage_return, '%')}</span>
              <span>sim {formatNumber(analog.similarity_score)}</span>
            </li>
          ))}
        </ul>
      )}

      {caseStudies.length > 0 ? (
        <p className="brain-note">{caseStudies.length} related validated case studies.</p>
      ) : null}
    </section>
  )
}

export default HistoricalInfluence
