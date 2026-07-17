function ConfidenceBreakdown({ breakdown }) {
  const data = breakdown ?? {}
  const raised = Array.isArray(data.raised) ? data.raised : []
  const reduced = Array.isArray(data.reduced) ? data.reduced : []

  return (
    <section className="brain-panel">
      <div className="brain-panel__heading">
        <div>
          <p className="eyebrow">Confidence Breakdown</p>
          <h3>Why confidence moved</h3>
        </div>
        <span className="brain-pill">
          {data.confidence === null || data.confidence === undefined ? 'Unavailable' : `${data.confidence}% confidence`}
        </span>
      </div>

      <div className="brain-confidence-grid">
        <div className="brain-confidence-col brain-confidence-col--up">
          <h4>Why Atlas likes it</h4>
          {raised.length === 0 ? (
            <p className="brain-empty">No positive confidence drivers were provided.</p>
          ) : (
            <ul>
              {raised.map((item) => (
                <li key={item.factor}>
                  <strong>{item.factor}</strong>
                  <span>{item.detail}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
        <div className="brain-confidence-col brain-confidence-col--down">
          <h4>What reduces confidence</h4>
          {reduced.length === 0 ? (
            <p className="brain-empty">No confidence reducers were provided.</p>
          ) : (
            <ul>
              {reduced.map((item) => (
                <li key={item.factor}>
                  <strong>{item.factor}</strong>
                  <span>{item.detail}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </section>
  )
}

export default ConfidenceBreakdown
