function RebalanceCard({ actions = [] }) {
  const visibleActions = Array.isArray(actions) ? actions.slice(0, 6) : []

  return (
    <section className="paper-panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Rebalance</p>
          <h2>Suggested Actions</h2>
        </div>
        <span className="paper-policy-pill">NO AUTO EXECUTION</span>
      </div>
      <div className="paper-benchmark-list">
        {visibleActions.map((action) => (
          <dl className="paper-benchmark-row" key={`${action.ticker}-${action.action}`}>
            <div>
              <dt>{action.ticker}</dt>
              <dd>{action.action}</dd>
            </div>
            <p>{action.explanation}</p>
          </dl>
        ))}
      </div>
    </section>
  )
}

export default RebalanceCard
