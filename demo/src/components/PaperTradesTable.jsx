function formatCurrency(value) {
  const numberValue = Number(value)

  if (Number.isNaN(numberValue)) {
    return 'Unavailable'
  }

  return new Intl.NumberFormat('en-US', {
    currency: 'USD',
    maximumFractionDigits: 2,
    style: 'currency',
  }).format(numberValue)
}

function formatValue(value, fallback = 'Open') {
  if (value === null || value === undefined || value === '') {
    return fallback
  }

  return String(value)
}

function PaperTradesTable({ trades }) {
  const rows = Array.isArray(trades) ? trades.slice(0, 10) : []

  return (
    <section className="paper-panel paper-table-panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">PRICE-BACKED REPLAY</p>
          <h2>Replay Trades</h2>
        </div>
        <span className="paper-policy-pill">HISTORICAL PRICE REPLAY</span>
      </div>
      {rows.length === 0 ? (
        <p className="muted-copy">No replay trades have been recorded yet.</p>
      ) : (
        <div className="paper-table-wrap">
          <table className="paper-table">
            <thead>
              <tr>
                <th>Action</th>
                <th>Ticker</th>
                <th>Entry/Exit</th>
                <th>Run</th>
                <th>P/L</th>
                <th>Holding</th>
                <th>Reason</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((trade) => (
                <tr key={trade.trade_id}>
                  <td>
                    <span className={`paper-action paper-action--${String(trade.action).toLowerCase()}`}>
                      {formatValue(trade.action, 'N/A')}
                    </span>
                  </td>
                  <td>{formatValue(trade.ticker, 'N/A')}</td>
                  <td>
                    {formatCurrency(trade.entry_price)} / {trade.exit_price ? formatCurrency(trade.exit_price) : 'Open'}
                  </td>
                  <td>
                    {formatValue(trade.run_number, 'n/a')} · {formatValue(trade.simulated_at ?? trade.exit_date ?? trade.entry_date, 'No timestamp')}
                  </td>
                  <td>{formatCurrency(trade.profit_loss)}</td>
                  <td>{formatValue(trade.holding_period, 'Open')}</td>
                  <td>{formatValue(trade.reason, 'Replay trade')}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}

export default PaperTradesTable
