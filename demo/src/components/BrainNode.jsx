function statusModifier(status) {
  return String(status ?? 'missing').toLowerCase()
}

function BrainNode({ node, index = 0, isActive = false, onSelect }) {
  if (!node) {
    return null
  }

  return (
    <button
      className={`brain-node brain-node--${statusModifier(node.status)}${isActive ? ' is-active' : ''}`}
      onClick={onSelect ? () => onSelect(node) : undefined}
      style={{ animationDelay: `${index * 60}ms` }}
      type="button"
    >
      <span className="brain-node__label">{node.label}</span>
      <span className="brain-node__score">{Math.round(Number(node.score) || 0)}</span>
      <span className="brain-node__status">{node.status}</span>
    </button>
  )
}

export default BrainNode
