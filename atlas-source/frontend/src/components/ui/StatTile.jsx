import { memo } from 'react'

// KPI tile: label, big value, optional delta + trailing badge.
function StatTile({ label, value, delta, deltaTone = 'neutral', badge, hint }) {
  return (
    <div className="dv2-stat">
      <div className="dv2-stat__label">{label}</div>
      <div className="dv2-stat__value">{value}</div>
      <div className="dv2-stat__foot">
        {delta !== undefined && delta !== null ? (
          <span className={`dv2-stat__delta dv2-stat__delta--${deltaTone}`}>{delta}</span>
        ) : null}
        {hint ? <span className="dv2-stat__hint">{hint}</span> : null}
        {badge ? <span className="dv2-stat__badge">{badge}</span> : null}
      </div>
    </div>
  )
}

export default memo(StatTile)
