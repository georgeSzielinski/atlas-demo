function AllocationChart({ allocations }) {
  return (
    <section className="portfolio-panel allocation-panel">
      <div className="section-heading">
        <p className="eyebrow">Allocation</p>
        <h2>Allocation Chart</h2>
      </div>

      <div className="allocation-chart" aria-label="Portfolio allocation chart">
        {allocations.map((item) => (
          <span
            aria-label={`${item.label} ${item.value}%`}
            key={item.label}
            style={{
              backgroundColor: item.color,
              width: `${item.value}%`,
            }}
          />
        ))}
      </div>

      <div className="allocation-list">
        {allocations.map((item) => (
          <div className="allocation-item" key={item.label}>
            <span className="allocation-swatch" style={{ backgroundColor: item.color }} />
            <span>{item.label}</span>
            <strong>{item.value}%</strong>
          </div>
        ))}
      </div>
    </section>
  )
}

export default AllocationChart
