import ExperimentCard from './ExperimentCard'

const columns = [
  ['highest_priority', 'Highest Priority'],
  ['waiting', 'Waiting'],
  ['running', 'Currently Running'],
  ['recently_completed', 'Recently Completed'],
]

function ExperimentQueue({ queue, selectedId, onSelect }) {
  const safeQueue = queue ?? {}

  return (
    <section className="lab-panel">
      <div className="lab-panel__heading">
        <div>
          <p className="eyebrow">Experiment Queue</p>
          <h3>Research Pipeline</h3>
        </div>
      </div>
      <div className="experiment-queue">
        {columns.map(([key, label]) => {
          const items = Array.isArray(safeQueue[key]) ? safeQueue[key] : []

          return (
            <div className="experiment-queue__column" key={key}>
              <header>
                <span>{label}</span>
                <strong>{items.length}</strong>
              </header>
              {items.length === 0 ? (
                <p className="lab-empty">No experiments.</p>
              ) : (
                items.map((experiment) => (
                  <ExperimentCard
                    experiment={experiment}
                    isActive={experiment.experiment_id === selectedId}
                    key={`${key}-${experiment.experiment_id}`}
                    onSelect={onSelect}
                  />
                ))
              )}
            </div>
          )
        })}
      </div>
    </section>
  )
}

export default ExperimentQueue
