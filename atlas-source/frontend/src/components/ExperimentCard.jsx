function statusModifier(status) {
  return String(status ?? 'unknown').toLowerCase().replace(/_/g, '-')
}

function ExperimentCard({ experiment, isActive = false, onSelect }) {
  if (!experiment) {
    return null
  }

  const {
    experiment_id: experimentId,
    title,
    status,
    priority,
    feature_being_tested: feature,
    validation_state: validationState,
    adoption_decision: adoptionDecision,
    is_example: isExample,
  } = experiment

  const className = isActive
    ? 'experiment-card is-selected'
    : 'experiment-card'

  return (
    <button
      className={className}
      onClick={onSelect ? () => onSelect(experiment) : undefined}
      type="button"
    >
      <div className="experiment-card__top">
        <span className={`experiment-status experiment-status--${statusModifier(status)}`}>
          {status ?? 'UNKNOWN'}
        </span>
        <span className={`experiment-priority experiment-priority--${statusModifier(priority)}`}>
          {priority ?? 'Medium'}
        </span>
      </div>
      <h4>{title ?? 'Untitled experiment'}</h4>
      <p className="experiment-card__feature">{feature ?? 'Unspecified feature'}</p>
      <div className="experiment-card__meta">
        <span>Result: {validationState ?? 'Not Enough Evidence'}</span>
        <span>Decision: {adoptionDecision ?? 'RETEST'}</span>
      </div>
      {isExample ? <span className="experiment-card__example">Example</span> : null}
      <span className="experiment-card__id">{experimentId}</span>
    </button>
  )
}

export default ExperimentCard
