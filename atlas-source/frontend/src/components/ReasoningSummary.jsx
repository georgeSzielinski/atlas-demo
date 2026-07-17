function ReasoningSummary({ reasoning }) {
  const summary = reasoning ?? {}
  const why = Array.isArray(summary.why) ? summary.why : []
  const watchOuts = Array.isArray(summary.watch_outs) ? summary.watch_outs : []

  return (
    <section className="brain-panel">
      <div className="brain-panel__heading">
        <div>
          <p className="eyebrow">Reasoning Summary</p>
          <h3>{summary.headline ?? 'Reasoning'}</h3>
        </div>
      </div>

      <p className="brain-narrative">{summary.narrative ?? 'No reasoning summary available.'}</p>

      <div className="brain-reason-grid">
        <div>
          <h4>Why Atlas likes it</h4>
          {why.length === 0 ? (
            <p className="brain-empty">No dominant positive drivers were returned.</p>
          ) : (
            <ul className="brain-list brain-list--positive">
              {why.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          )}
        </div>
        <div>
          <h4>What reduces confidence</h4>
          {watchOuts.length === 0 ? (
            <p className="brain-empty">No major confidence reducers were returned.</p>
          ) : (
            <ul className="brain-list brain-list--negative">
              {watchOuts.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          )}
        </div>
      </div>

      {summary.executive_note ? (
        <p className="brain-executive-note">{summary.executive_note}</p>
      ) : null}
    </section>
  )
}

export default ReasoningSummary
