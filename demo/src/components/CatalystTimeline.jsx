function daysUntil(dateValue) {
  if (!dateValue) {
    return 'TBD'
  }

  const target = new Date(dateValue)
  if (Number.isNaN(target.getTime())) {
    return 'TBD'
  }

  const today = new Date()
  const diff = Math.ceil((target - today) / (1000 * 60 * 60 * 24))
  return `${diff}d`
}

function CatalystTimeline({ catalysts = [] }) {
  return (
    <section className="workspace-panel">
      <div className="panel-heading">
        <p className="eyebrow">Catalysts</p>
        <h3>Timeline</h3>
      </div>
      <div className="timeline-list">
        {catalysts.length > 0 ? catalysts.map((catalyst, index) => (
          <article className="timeline-item" key={`${catalyst.event_type ?? 'event'}-${index}`}>
            <div>
              <strong>{catalyst.event_type ?? catalyst.title ?? 'Catalyst'}</strong>
              <span>{catalyst.event_date ?? catalyst.date ?? 'Date unavailable'}</span>
            </div>
            <dl>
              <div>
                <dt>Importance</dt>
                <dd>{catalyst.importance ?? catalyst.impact ?? 'Medium'}</dd>
              </div>
              <div>
                <dt>Risk</dt>
                <dd>{catalyst.risk ?? catalyst.risk_level ?? 'Monitor'}</dd>
              </div>
              <div>
                <dt>Days</dt>
                <dd>{daysUntil(catalyst.event_date ?? catalyst.date)}</dd>
              </div>
            </dl>
          </article>
        )) : <p className="muted-copy">No catalyst timeline returned.</p>}
      </div>
    </section>
  )
}

export default CatalystTimeline
