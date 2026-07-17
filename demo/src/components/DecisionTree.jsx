function DecisionTree({ tree }) {
  const data = tree ?? {}
  const branches = Array.isArray(data.branches) ? data.branches : []

  return (
    <section className="brain-panel">
      <div className="brain-panel__heading">
        <div>
          <p className="eyebrow">Decision Tree</p>
          <h3>What would change Atlas's mind</h3>
        </div>
        <span className="brain-pill">{data.final_outcome ?? 'Unavailable'}</span>
      </div>

      {branches.length === 0 ? (
        <p className="brain-empty">
          No decision branches are available yet. When present, this panel shows the
          conditions that could raise, lower, or flip the recommendation.
        </p>
      ) : (
        <ul className="brain-tree">
          {branches.map((branch, index) => (
            <li
              className={`brain-tree__branch brain-tree__branch--${branch.passed ? 'pass' : 'caution'}`}
              key={branch.branch ?? index}
            >
              <div className="brain-tree__head">
                <span className="brain-tree__icon">{branch.passed ? '✓' : '!'}</span>
                <strong>{branch.branch}</strong>
              </div>
              <span className="brain-tree__condition">{branch.condition}</span>
              <p className="brain-tree__why">{branch.why}</p>
            </li>
          ))}
        </ul>
      )}

      {data.why ? <p className="brain-tree__summary">{data.why}</p> : null}
    </section>
  )
}

export default DecisionTree
