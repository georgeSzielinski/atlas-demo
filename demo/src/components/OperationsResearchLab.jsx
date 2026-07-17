function OperationsResearchLab({ researchLab }) {
  const operations = researchLab?.operations_summary ?? {}
  const progress = operations.research_progress ?? {}
  const activeExperiments = Array.isArray(operations.active_experiments)
    ? operations.active_experiments
    : []
  const latestValidation = operations.latest_validation ?? null

  const cards = [
    ['Active Experiments', operations.active_experiment_count ?? 0],
    ['Latest Adoption Decision', operations.latest_adoption_decision ?? 'Not Enough Evidence'],
    ['Completion Rate', `${progress.completion_rate ?? 0}%`],
    ['Adopted', progress.adopted ?? 0],
  ]

  return (
    <section className="operations-panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Research Laboratory</p>
          <h2>Experiment Operations</h2>
        </div>
        <span className="operations-policy-pill">RESEARCH ONLY</span>
      </div>

      <div className="operations-summary-grid">
        {cards.map(([label, value]) => (
          <article className="operations-metric-card" key={label}>
            <span>{label}</span>
            <strong>{value}</strong>
            <small>Deterministic research signal</small>
          </article>
        ))}
      </div>

      <div className="operations-lab-detail">
        <div>
          <h4>Active Experiments</h4>
          {activeExperiments.length === 0 ? (
            <p className="lab-empty">No active experiments.</p>
          ) : (
            <ul>
              {activeExperiments.map((experiment) => (
                <li key={experiment.experiment_id}>
                  <strong>{experiment.title}</strong>
                  <span>
                    {experiment.status} · {experiment.validation_state}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>
        <div>
          <h4>Latest Validation</h4>
          {latestValidation ? (
            <p>
              {latestValidation.feature_tested ?? 'Latest validation'} —{' '}
              {latestValidation.scientific_result ?? 'Not Enough Evidence'} (
              {latestValidation.adoption_decision ?? 'RETEST'})
            </p>
          ) : (
            <p className="lab-empty">No validation reports yet.</p>
          )}
        </div>
      </div>
    </section>
  )
}

export default OperationsResearchLab
