function HistoricalAnalogs({ analogs = [], caseStudies = [] }) {
  return (
    <section className="workspace-panel">
      <div className="panel-heading">
        <p className="eyebrow">History</p>
        <h3>Historical Analogs</h3>
      </div>
      <div className="analog-list">
        {analogs.length > 0 ? analogs.slice(0, 5).map((analog) => (
          <article className="analog-row" key={`${analog.case_id}-${analog.ticker}`}>
            <div>
              <strong>{analog.ticker ?? 'Case'}</strong>
              <span>{analog.market_regime ?? analog.outcome ?? 'Historical case'}</span>
            </div>
            <dl>
              <div>
                <dt>Similarity</dt>
                <dd>{analog.similarity_score ?? 0}</dd>
              </div>
              <div>
                <dt>Return</dt>
                <dd>{analog.return ?? 0}%</dd>
              </div>
            </dl>
          </article>
        )) : <p className="muted-copy">No analogs available.</p>}
      </div>
      <div className="case-study-strip">
        <span>Case Studies</span>
        <strong>{caseStudies.length}</strong>
      </div>
    </section>
  )
}

export default HistoricalAnalogs
