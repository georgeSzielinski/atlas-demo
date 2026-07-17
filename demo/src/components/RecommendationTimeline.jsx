function RecommendationTimeline({ timeline }) {
  const steps = Array.isArray(timeline) ? timeline : []

  return (
    <section className="brain-panel">
      <div className="brain-panel__heading">
        <div>
          <p className="eyebrow">Reasoning Timeline</p>
          <h3>Chronological Reasoning</h3>
        </div>
      </div>

      {steps.length === 0 ? (
        <p className="brain-empty">No reasoning timeline is available.</p>
      ) : (
        <ol className="brain-timeline">
          {steps.map((step, index) => (
            <li className="brain-timeline__item" key={step.step ?? index} style={{ animationDelay: `${index * 70}ms` }}>
              <span className="brain-timeline__marker">{step.step ?? index + 1}</span>
              <div>
                <strong>{step.label}</strong>
                <span>{step.detail}</span>
              </div>
            </li>
          ))}
        </ol>
      )}
    </section>
  )
}

export default RecommendationTimeline
