function ValidationStatus({ trust, probability }) {
  const validation = trust?.validation_status ?? {}
  const probabilityDetail = probability ?? {}

  const rows = [
    ['Recommendation Validation', validation.recommendation_validation ?? 'Pending'],
    ['Latest Scientific Result', validation.latest_scientific_result ?? 'No validation yet'],
    ['Adoption Decision', validation.latest_adoption_decision ?? 'Not Enough Evidence'],
    ['Validation Reports', validation.validation_count ?? 0],
    ['Probability Uncertainty', probabilityDetail.uncertainty_level ?? 'Unknown'],
    ['Probability Sample Size', probabilityDetail.sample_size ?? 0],
  ]

  return (
    <section className="brain-panel">
      <div className="brain-panel__heading">
        <div>
          <p className="eyebrow">Validation Status</p>
          <h3>Evidence Standing</h3>
        </div>
        <span className="brain-pill">HUMAN APPROVAL REQUIRED</span>
      </div>

      <dl className="brain-detail-list">
        {rows.map(([label, value]) => (
          <div key={label}>
            <dt>{label}</dt>
            <dd>{String(value)}</dd>
          </div>
        ))}
      </dl>

      {probabilityDetail.calibration_note ? (
        <p className="brain-note">{probabilityDetail.calibration_note}</p>
      ) : (
        <p className="brain-empty">
          Probability calibration detail is unavailable for this recommendation.
        </p>
      )}
    </section>
  )
}

export default ValidationStatus
