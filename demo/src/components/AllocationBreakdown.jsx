function formatPercent(value) {
  const numberValue = Number(value)

  if (Number.isNaN(numberValue)) {
    return 'Unavailable'
  }

  return `${numberValue.toFixed(2).replace(/\.00$/, '')}%`
}

function AllocationBreakdown({ allocations = [], diversification = {} }) {
  const safeAllocations = Array.isArray(allocations) ? allocations : []
  const safeDiversification = diversification ?? {}
  const sectorExposure = safeDiversification.sector_exposure ?? {}
  const sectors = Object.entries(sectorExposure)
  const ranked = safeAllocations.slice(0, 6)

  return (
    <section className="paper-panel allocation-panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Capital Allocation</p>
          <h2>Suggested Allocation</h2>
        </div>
      </div>

      <div className="allocation-list">
        {ranked.map((allocation) => (
          <div className="allocation-item" key={allocation.ticker}>
            <span className="allocation-swatch" />
            <strong>{allocation.ticker}</strong>
            <span>
              {formatPercent(allocation.suggested_allocation)} · {allocation.position_priority}
            </span>
          </div>
        ))}
      </div>

      <h3 className="section-subtitle">Sector Allocation</h3>
      <div className="allocation-list">
        {sectors.map(([sector, weight]) => (
          <div className="allocation-item" key={sector}>
            <span className="allocation-swatch" />
            <strong>{sector}</strong>
            <span>{formatPercent(weight)}</span>
          </div>
        ))}
      </div>
    </section>
  )
}

export default AllocationBreakdown
