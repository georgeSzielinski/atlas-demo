function CatalystImpact({ catalystImpact }) {
  const data = catalystImpact ?? {}
  const catalysts = Array.isArray(data.catalysts) ? data.catalysts : []
  const mostImportant = data.most_important ?? null

  return (
    <section className="brain-panel">
      <div className="brain-panel__heading">
        <div>
          <p className="eyebrow">Catalyst Impact</p>
          <h3>Upcoming Events</h3>
        </div>
        <span className="brain-pill">{data.event_count ?? 0} events</span>
      </div>

      {mostImportant ? (
        <p className="brain-note">
          Nearest catalyst: <strong>{mostImportant.event_type}</strong> in{' '}
          {mostImportant.days_until_event ?? '?'} days
          {mostImportant.potential_volatility_level
            ? ` · ${mostImportant.potential_volatility_level} volatility`
            : ''}
          .
        </p>
      ) : null}

      {catalysts.length === 0 ? (
        <p className="brain-empty">
          {data.summary ?? 'No upcoming catalysts are recorded for this ticker.'}
        </p>
      ) : (
        <ul className="brain-catalyst-list">
          {catalysts.map((catalyst, index) => (
            <li key={`${catalyst.event_type}-${index}`}>
              <span>{catalyst.event_type ?? 'Event'}</span>
              <span>{catalyst.days_until_event ?? '?'}d</span>
              <span className={`brain-vol brain-vol--${String(catalyst.potential_volatility_level ?? 'low').toLowerCase()}`}>
                {catalyst.potential_volatility_level ?? 'Low'}
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}

export default CatalystImpact
