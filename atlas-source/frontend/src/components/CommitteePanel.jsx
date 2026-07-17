function ListBlock({ title, items = [] }) {
  return (
    <div className="committee-block">
      <h4>{title}</h4>
      {items.length > 0 ? (
        <ul>
          {items.slice(0, 4).map((item) => (
            <li key={typeof item === 'string' ? item : JSON.stringify(item)}>
              {typeof item === 'string' ? item : item.summary ?? item.name ?? JSON.stringify(item)}
            </li>
          ))}
        </ul>
      ) : <p className="muted-copy">Unavailable</p>}
    </div>
  )
}

function CommitteePanel({ recommendation = {} }) {
  return (
    <section className="workspace-panel committee-panel">
      <div className="panel-heading">
        <p className="eyebrow">Committee</p>
        <h3>Investment Committee</h3>
      </div>
      <div className="agreement-meter">
        <span style={{ width: `${Math.min(Number(recommendation.committee_agreement) || 0, 100)}%` }} />
      </div>
      <div className="agreement-row">
        <span>Agreement</span>
        <strong>{recommendation.committee_agreement ?? 0}%</strong>
      </div>
      <div className="committee-grid">
        <ListBlock title="Bull Case" items={recommendation.committee_bull_case ?? recommendation.bull_case ?? []} />
        <ListBlock title="Bear Case" items={recommendation.committee_bear_case ?? recommendation.bear_case ?? []} />
        <ListBlock title="Neutral" items={recommendation.committee_neutral_case ?? recommendation.neutral_case ?? []} />
      </div>
      <dl className="argument-list">
        <div>
          <dt>Strongest Bull</dt>
          <dd>{recommendation.strongest_bull_argument || 'Unavailable'}</dd>
        </div>
        <div>
          <dt>Strongest Bear</dt>
          <dd>{recommendation.strongest_bear_argument || 'Unavailable'}</dd>
        </div>
      </dl>
    </section>
  )
}

export default CommitteePanel
