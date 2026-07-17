const LEVELS = [
  ['High', 'High Priority'],
  ['Medium', 'Medium Priority'],
  ['Low', 'Low Priority'],
]

function ResearchProgress({ research }) {
  const roadmap = research?.roadmap ?? {}

  const cards = [
    ['Active', research?.active_experiments ?? 0],
    ['Completed', research?.completed ?? 0],
    ['Rejected', research?.rejected ?? 0],
    ['Adopted', research?.adopted ?? 0],
    ['Completion Rate', `${research?.completion_rate ?? 0}%`],
    ['Adoption Rate', `${research?.adoption_rate ?? 0}%`],
  ]

  return (
    <section className="analytics-panel">
      <div className="analytics-panel__heading">
        <div>
          <p className="eyebrow">Research Progress</p>
          <h3>Experiment Portfolio</h3>
        </div>
      </div>

      <div className="analytics-summary-grid">
        {cards.map(([label, value]) => (
          <article className="analytics-metric-card" key={label}>
            <span>{label}</span>
            <strong>{value}</strong>
          </article>
        ))}
      </div>

      <div className="research-roadmap-mini">
        {LEVELS.map(([key, label]) => {
          const items = Array.isArray(roadmap[key]) ? roadmap[key] : []
          return (
            <div className={`roadmap-mini roadmap-mini--${key.toLowerCase()}`} key={key}>
              <header>{label}</header>
              {items.length === 0 ? (
                <p className="analytics-empty">None.</p>
              ) : (
                <ul>
                  {items.map((item, index) => (
                    <li key={item.experiment_id ?? `${key}-${index}`}>{item.title}</li>
                  ))}
                </ul>
              )}
            </div>
          )
        })}
      </div>
    </section>
  )
}

export default ResearchProgress
