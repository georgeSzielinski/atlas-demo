function PatternList({ title, patterns = [] }) {
  return (
    <div>
      <h4>{title}</h4>
      {patterns.length > 0 ? (
        <ul className="pattern-list">
          {patterns.slice(0, 4).map((item) => (
            <li key={item.pattern ?? item.name ?? JSON.stringify(item)}>
              <span>{item.pattern ?? item.name}</span>
              <strong>{item.count ?? item.value ?? ''}</strong>
            </li>
          ))}
        </ul>
      ) : <p className="muted-copy">Unavailable</p>}
    </div>
  )
}

function ResearchMemoryCard({ memory = {} }) {
  const lessons = memory.lessons ?? {}

  return (
    <section className="workspace-panel research-memory-panel">
      <div className="panel-heading">
        <p className="eyebrow">Research Memory</p>
        <h3>Lessons</h3>
      </div>
      <dl className="compact-metrics">
        <div>
          <dt>Avg Return</dt>
          <dd>{lessons.average_historical_return ?? 0}%</dd>
        </div>
        <div>
          <dt>Avg Hold</dt>
          <dd>{lessons.average_holding_period ?? 0}d</dd>
        </div>
        <div>
          <dt>Win Rate</dt>
          <dd>{lessons.win_rate ?? 0}%</dd>
        </div>
      </dl>
      <div className="memory-grid">
        <PatternList title="Success Patterns" patterns={lessons.common_successful_patterns ?? []} />
        <PatternList title="Failure Patterns" patterns={lessons.common_failure_patterns ?? []} />
      </div>
    </section>
  )
}

export default ResearchMemoryCard
