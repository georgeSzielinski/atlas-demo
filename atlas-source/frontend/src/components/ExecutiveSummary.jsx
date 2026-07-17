function ExecutiveSummary({ recommendation = {}, report = {} }) {
  const section = report?.sections?.find((item) => item.title === 'Executive Summary')

  return (
    <section className="workspace-panel executive-summary-panel">
      <div className="panel-heading">
        <p className="eyebrow">Executive</p>
        <h3>Summary</h3>
      </div>
      <p className="summary-copy">
        {section?.summary ?? recommendation.executive_summary ?? 'Executive summary unavailable.'}
      </p>
      <dl className="compact-metrics">
        <div>
          <dt>Status</dt>
          <dd>{recommendation.executive_status ?? 'Unavailable'}</dd>
        </div>
        <div>
          <dt>Confidence</dt>
          <dd>{recommendation.executive_confidence ?? 0}%</dd>
        </div>
        <div>
          <dt>Warnings</dt>
          <dd>{Array.isArray(recommendation.executive_warnings) ? recommendation.executive_warnings.length : 0}</dd>
        </div>
      </dl>
    </section>
  )
}

export default ExecutiveSummary
