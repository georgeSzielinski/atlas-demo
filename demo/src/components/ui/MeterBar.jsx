import { memo } from 'react'

// Horizontal 0-100 meter used for scores/utilization.
function MeterBar({ value, max = 100, tone = 'accent', label }) {
  const numberValue = Number(value)
  const pct = Number.isNaN(numberValue)
    ? 0
    : Math.max(0, Math.min(100, (numberValue / max) * 100))
  return (
    <div className="dv2-meter">
      {label ? <div className="dv2-meter__label">{label}</div> : null}
      <div className="dv2-meter__track">
        <div
          className={`dv2-meter__fill dv2-meter__fill--${tone}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  )
}

export default memo(MeterBar)
