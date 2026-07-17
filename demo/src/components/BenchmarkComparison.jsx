function formatNumber(value, suffix = '') {
  const number = Number(value)
  if (Number.isNaN(number)) {
    return 'Unavailable'
  }
  return `${number.toFixed(2).replace(/\.00$/, '')}${suffix}`
}

function BenchmarkComparison({ benchmarks }) {
  const rows = Array.isArray(benchmarks?.benchmarks) ? benchmarks.benchmarks : []

  return (
    <section className="analytics-panel">
      <div className="analytics-panel__heading">
        <div>
          <p className="eyebrow">Benchmark Comparison</p>
          <h3>Alpha vs Market Benchmarks</h3>
        </div>
      </div>

      {rows.length === 0 ? (
        <p className="analytics-empty">No benchmark comparison is available yet.</p>
      ) : (
        <table className="analytics-table">
          <thead>
            <tr>
              <th>Benchmark</th>
              <th>Benchmark Return</th>
              <th>Paper Return</th>
              <th>Alpha</th>
              <th>Relative</th>
              <th>Outperformance</th>
              <th>Tracking Diff</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr className={Number(row.alpha) > 0 ? 'is-positive' : Number(row.alpha) < 0 ? 'is-negative' : ''} key={row.benchmark}>
                <td>{row.benchmark}</td>
                <td>{formatNumber(row.benchmark_return, '%')}</td>
                <td>{formatNumber(row.paper_return, '%')}</td>
                <td>{formatNumber(row.alpha, '%')}</td>
                <td>{formatNumber(row.relative_return, '%')}</td>
                <td>{formatNumber(row.outperformance_rate, '%')}</td>
                <td>{formatNumber(row.tracking_difference)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  )
}

export default BenchmarkComparison
