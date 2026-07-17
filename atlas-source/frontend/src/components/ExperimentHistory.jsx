import { useMemo, useState } from 'react'

function ExperimentHistory({ history, onSelect }) {
  const safeHistory = history ?? {}
  const experiments = Array.isArray(safeHistory.experiments) ? safeHistory.experiments : []
  const statuses = Array.isArray(safeHistory.statuses) ? safeHistory.statuses : []
  const results = Array.isArray(safeHistory.results) ? safeHistory.results : []

  const [feature, setFeature] = useState('')
  const [status, setStatus] = useState('')
  const [result, setResult] = useState('')

  const filtered = useMemo(() => {
    return experiments.filter((experiment) => {
      const matchesFeature = feature
        ? String(experiment.feature_being_tested ?? '')
            .toLowerCase()
            .includes(feature.toLowerCase())
        : true
      const matchesStatus = status ? experiment.status === status : true
      const matchesResult = result ? experiment.validation_state === result : true

      return matchesFeature && matchesStatus && matchesResult
    })
  }, [experiments, feature, status, result])

  return (
    <section className="lab-panel">
      <div className="lab-panel__heading">
        <div>
          <p className="eyebrow">History</p>
          <h3>Experiment History</h3>
        </div>
        <span className="lab-pill">{filtered.length} records</span>
      </div>

      <div className="history-filters">
        <label>
          <span>Feature</span>
          <input
            onChange={(event) => setFeature(event.target.value)}
            placeholder="Search feature"
            type="text"
            value={feature}
          />
        </label>
        <label>
          <span>Status</span>
          <select onChange={(event) => setStatus(event.target.value)} value={status}>
            <option value="">All</option>
            {statuses.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
        </label>
        <label>
          <span>Result</span>
          <select onChange={(event) => setResult(event.target.value)} value={result}>
            <option value="">All</option>
            {results.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
        </label>
      </div>

      {filtered.length === 0 ? (
        <p className="lab-empty">No experiments match the current filters.</p>
      ) : (
        <table className="lab-table">
          <thead>
            <tr>
              <th>Date</th>
              <th>Title</th>
              <th>Feature</th>
              <th>Status</th>
              <th>Result</th>
              <th>Decision</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((experiment) => (
              <tr
                className="history-row"
                key={experiment.experiment_id}
                onClick={onSelect ? () => onSelect(experiment) : undefined}
              >
                <td>{String(experiment.created_date ?? '').slice(0, 10)}</td>
                <td>{experiment.title}</td>
                <td>{experiment.feature_being_tested}</td>
                <td>{experiment.status}</td>
                <td>{experiment.validation_state}</td>
                <td>{experiment.adoption_decision}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  )
}

export default ExperimentHistory
