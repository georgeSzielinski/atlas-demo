import BrainNode from './BrainNode'

function BrainFlow({ flow, selectedNodeId, onSelect }) {
  const nodes = Array.isArray(flow) ? flow : []

  return (
    <section className="brain-panel">
      <div className="brain-panel__heading">
        <div>
          <p className="eyebrow">Reasoning Pipeline</p>
          <h3>What evidence mattered most</h3>
        </div>
        <span className="brain-pill">Click any stage</span>
      </div>

      {nodes.length === 0 ? (
        <p className="brain-empty">No reasoning pipeline is available for this ticker yet.</p>
      ) : (
        <div className="brain-flow">
          {nodes.map((node, index) => (
            <div className="brain-flow__item" key={node.id ?? node.label}>
              <BrainNode
                index={index}
                isActive={node.id === selectedNodeId}
                node={node}
                onSelect={onSelect}
              />
              {index < nodes.length - 1 ? <span className="brain-flow__arrow">↓</span> : null}
            </div>
          ))}
        </div>
      )}
    </section>
  )
}

export default BrainFlow
