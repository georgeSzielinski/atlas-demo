function clampScore(value) {
  const numberValue = Number(value)

  if (Number.isNaN(numberValue)) {
    return 0
  }

  return Math.max(0, Math.min(100, numberValue))
}

function formatScore(value, suffix = '') {
  if (value === null || value === undefined || value === '') {
    return 'Unavailable'
  }

  return `${value}${suffix}`
}

function ScoreBar({ label, suffix = '', value }) {
  const score = clampScore(value)

  return (
    <div className="score-block">
      <div className="score-block__row">
        <span>{label}</span>
        <strong>{formatScore(value, suffix)}</strong>
      </div>
      <div className="score-bar" aria-label={`${label} ${score} out of 100`}>
        <span style={{ width: `${score}%` }} />
      </div>
    </div>
  )
}

export default ScoreBar
