const LEVELS = [
  ['High', 'High Priority'],
  ['Medium', 'Medium Priority'],
  ['Low', 'Low Priority'],
]

function ResearchRoadmap({ roadmap }) {
  const safeRoadmap = roadmap ?? {}

  return (
    <section className="lab-panel">
      <div className="lab-panel__heading">
        <div>
          <p className="eyebrow">Research Roadmap</p>
          <h3>Deterministic Research Plan</h3>
        </div>
      </div>
      <div className="roadmap-grid">
        {LEVELS.map(([key, label]) => {
          const items = Array.isArray(safeRoadmap[key]) ? safeRoadmap[key] : []

          return (
            <div className={`roadmap-column roadmap-column--${key.toLowerCase()}`} key={key}>
              <header>{label}</header>
              {items.length === 0 ? (
                <p className="lab-empty">No items.</p>
              ) : (
                <ul>
                  {items.map((item, index) => (
                    <li key={item.experiment_id ?? `${key}-${index}`}>
                      <strong>{item.title}</strong>
                      <span>{item.feature_being_tested}</span>
                    </li>
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

export default ResearchRoadmap
