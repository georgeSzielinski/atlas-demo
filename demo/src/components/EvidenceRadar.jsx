function polarPoint(cx, cy, radius, angle) {
  return [cx + radius * Math.cos(angle), cy + radius * Math.sin(angle)]
}

function EvidenceRadar({ evidence }) {
  const items = Array.isArray(evidence?.items) ? evidence.items.slice(0, 8) : []
  const size = 260
  const center = size / 2
  const maxRadius = center - 34

  const axes = items.map((item, index) => {
    const angle = (Math.PI * 2 * index) / Math.max(items.length, 1) - Math.PI / 2
    const value = Math.max(0, Math.min(100, Number(item.score) || 0))
    const radius = (value / 100) * maxRadius
    const [px, py] = polarPoint(center, center, radius, angle)
    const [lx, ly] = polarPoint(center, center, maxRadius + 14, angle)
    return { item, px, py, lx, ly }
  })

  const polygon = axes.map((axis) => `${axis.px},${axis.py}`).join(' ')

  return (
    <section className="brain-panel">
      <div className="brain-panel__heading">
        <div>
          <p className="eyebrow">Evidence Contribution</p>
          <h3>What evidence mattered most</h3>
        </div>
        <span className="brain-pill">{evidence?.top_category ?? 'No evidence'} leads</span>
      </div>

      {items.length === 0 ? (
        <p className="brain-empty">
          No evidence breakdown is available yet. Atlas can still show the recommendation,
          but this panel needs saved engine contribution data.
        </p>
      ) : (
        <div className="brain-radar">
          <svg className="brain-radar__svg" viewBox={`0 0 ${size} ${size}`}>
            {[0.25, 0.5, 0.75, 1].map((ring) => (
              <circle
                className="brain-radar__ring"
                cx={center}
                cy={center}
                key={ring}
                r={maxRadius * ring}
              />
            ))}
            {axes.map((axis) => (
              <line
                className="brain-radar__axis"
                key={`axis-${axis.item.category}`}
                x1={center}
                x2={axis.lx}
                y1={center}
                y2={axis.ly}
              />
            ))}
            <polygon className="brain-radar__area" points={polygon} />
            {axes.map((axis) => (
              <circle className="brain-radar__dot" cx={axis.px} cy={axis.py} key={`dot-${axis.item.category}`} r="3" />
            ))}
          </svg>
          <ul className="brain-radar__legend">
            {items.map((item) => (
              <li key={item.category}>
                <span>{item.category}</span>
                <strong>{item.percent}%</strong>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  )
}

export default EvidenceRadar
