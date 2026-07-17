function formatPercent(value) {
  const numberValue = Number(value)

  if (Number.isNaN(numberValue)) {
    return 'Unavailable'
  }

  return `${numberValue.toFixed(2).replace(/\.00$/, '')}%`
}

function PaperBenchmarkComparison({ comparisons }) {
  const rows = Array.isArray(comparisons) ? comparisons : []

  return (
    <section className="paper-panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">BENCHMARKS</p>
          <h2>Paper vs Market</h2>
        </div>
        <span className="paper-policy-pill">SIMULATED ONLY</span>
      </div>
      {rows.length === 0 ? (
        <p className="muted-copy">No benchmark comparison is available yet.</p>
      ) : (
        <div className="paper-benchmark-list">
          {rows.map((item) => (
            <article className="paper-benchmark-row" key={item.benchmark}>
              <div>
                <strong>{item.benchmark}</strong>
                <span>Benchmark return {formatPercent(item.benchmark_return)}</span>
              </div>
              <dl>
                <div>
                  <dt>Paper</dt>
                  <dd>{formatPercent(item.paper_return)}</dd>
                </div>
                <div>
                  <dt>Alpha</dt>
                  <dd>{formatPercent(item.alpha)}</dd>
                </div>
              </dl>
            </article>
          ))}
        </div>
      )}
    </section>
  )
}

export default PaperBenchmarkComparison
