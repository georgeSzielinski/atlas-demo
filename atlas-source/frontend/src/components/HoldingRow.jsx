function HoldingRow({ holding }) {
  return (
    <div className="holding-row">
      <div>
        <strong>{holding.ticker}</strong>
        <span>{holding.name}</span>
      </div>
      <span>{holding.allocation}%</span>
      <span>{holding.value}</span>
    </div>
  )
}

export default HoldingRow
