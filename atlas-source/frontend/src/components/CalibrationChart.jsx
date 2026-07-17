function toPercent(value) {
  const number = Number(value)
  if (Number.isNaN(number)) {
    return 0
  }
  return Math.max(0, Math.min(100, number))
}

function formatNumber(value, suffix = '') {
  const number = Number(value)
  if (Number.isNaN(number)) {
    return 'Unavailable'
  }
  return `${number.toFixed(2).replace(/\.00$/, '')}${suffix}`
}

function CalibrationChart({ calibration, recommendation }) {
  const confidence = toPercent(calibration?.confidence_calibration)
  const probability = toPercent(calibration?.probability_calibration)

  const bars = [
    ['Confidence Calibration', confidence],
    ['Probability Calibration', probability],
  ]

  const accuracy = [
    ['BUY Success Rate', recommendation?.buy_success_rate],
    ['HOLD Accuracy', recommendation?.hold_accuracy],
    ['AVOID Accuracy', recommendation?.avoid_accuracy],
    ['Avg Holding Period', recommendation?.average_holding_period],
  ]

  return (
    <section className="analytics-panel">
      <div className="analytics-panel__heading">
        <div>
          <p className="eyebrow">Recommendation Analytics</p>
          <h3>Calibration &amp; Accuracy</h3>
        </div>
      </div>

      <div className="calibration-bars">
        {bars.map(([label, value]) => (
          <div className="calibration-bar" key={label}>
            <div className="calibration-bar__label">
              <span>{label}</span>
              <strong>{formatNumber(value, '%')}</strong>
            </div>
            <div className="calibration-bar__track">
              <div className="calibration-bar__fill" style={{ width: `${value}%` }} />
            </div>
          </div>
        ))}
      </div>

      <div className="analytics-inline-stats">
        {accuracy.map(([label, value]) => (
          <div key={label}>
            <span>{label}</span>
            <strong>{formatNumber(value)}</strong>
          </div>
        ))}
      </div>
    </section>
  )
}

export default CalibrationChart
