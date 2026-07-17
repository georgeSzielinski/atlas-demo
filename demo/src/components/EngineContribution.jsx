function EngineContribution({ contributions }) {
  const items = Array.isArray(contributions) ? contributions : []
  const max = items.reduce((acc, item) => Math.max(acc, Number(item.percent) || 0), 0) || 100

  return (
    <section className="brain-panel">
      <div className="brain-panel__heading">
        <div>
          <p className="eyebrow">Engine Contribution</p>
          <h3>What evidence mattered most</h3>
        </div>
      </div>

      {items.length === 0 ? (
        <p className="brain-empty">
          No engine contribution data is available. Provider or saved recommendation
          details may be missing for this ticker.
        </p>
      ) : (
        <div className="brain-bars">
          {items.map((item) => (
            <div className="brain-bar" key={item.engine ?? item.category}>
              <div className="brain-bar__label">
                <span>{item.engine ?? item.category}</span>
                <strong>{item.percent}%</strong>
              </div>
              <div className="brain-bar__track">
                <div
                  className="brain-bar__fill"
                  style={{ width: `${((Number(item.percent) || 0) / max) * 100}%` }}
                />
              </div>
              {item.summary ? <p className="brain-bar__summary">{item.summary}</p> : null}
            </div>
          ))}
        </div>
      )}
    </section>
  )
}

export default EngineContribution
