function resultModifier(value) {
  return String(value ?? 'unknown').toLowerCase().replace(/\s+/g, '-')
}

function ValidationResults({ validation }) {
  if (!validation) {
    return (
      <section className="lab-panel">
        <div className="lab-panel__heading">
          <div>
            <p className="eyebrow">Scientific Validation</p>
            <h3>Latest Validation</h3>
          </div>
        </div>
        <p className="lab-empty">
          No scientific validation reports yet. Run an experiment through Simulation Arena to
          generate one.
        </p>
      </section>
    )
  }

  const metricComparison = Array.isArray(validation.metric_comparison)
    ? validation.metric_comparison
    : []

  return (
    <section className="lab-panel">
      <div className="lab-panel__heading">
        <div>
          <p className="eyebrow">Scientific Validation</p>
          <h3>{validation.feature_tested ?? 'Latest Validation'}</h3>
        </div>
        <div className="validation-badges">
          <span className={`validation-badge validation-badge--${resultModifier(validation.scientific_result)}`}>
            {validation.scientific_result ?? 'Not Enough Evidence'}
          </span>
          <span className={`validation-badge validation-badge--${resultModifier(validation.adoption_decision)}`}>
            {validation.adoption_decision ?? 'RETEST'}
          </span>
        </div>
      </div>

      <p className="validation-explanation">
        {validation.adoption_explanation ?? 'Adoption requires human approval.'}
      </p>
      <p className="lab-note">Sample size: {validation.sample_size ?? 0}</p>

      {metricComparison.length > 0 ? (
        <table className="lab-table">
          <thead>
            <tr>
              <th>Metric</th>
              <th>Baseline</th>
              <th>Candidate</th>
              <th>Delta</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {metricComparison.map((item) => (
              <tr
                className={
                  item.status === 'Improved'
                    ? 'is-improved'
                    : item.status === 'Regression'
                      ? 'is-regressed'
                      : ''
                }
                key={item.metric}
              >
                <td>{item.metric}</td>
                <td>{item.baseline}</td>
                <td>{item.candidate}</td>
                <td>{item.delta}</td>
                <td>{item.status}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : null}
    </section>
  )
}

export default ValidationResults
