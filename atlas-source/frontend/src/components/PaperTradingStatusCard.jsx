function statusLabel(status, isRunning, lastReplayFailed) {
  if (isRunning) {
    return 'Replay running'
  }

  if (lastReplayFailed) {
    return 'Replay failed'
  }

  return status ?? 'Not started'
}

function PaperTradingStatusCard({ status, isRunning = false, lastReplayFailed = false }) {
  const label = statusLabel(status?.paper_trading_status, isRunning, lastReplayFailed)
  const priceBacked = status?.price_backed === true
  const metrics = [
    ['Last replay time', status?.last_replay_time ?? 'Never'],
    ['Last successful replay', status?.last_successful_replay ?? 'Never'],
    ['Replays completed', status?.replays_completed ?? 0],
    ['Replay trades generated', status?.trades_generated ?? 0],
    ['Portfolio points generated', status?.portfolio_points_generated ?? 0],
    ['Price-backed', priceBacked ? 'Yes' : 'No'],
    ['Current mode', status?.current_mode ?? 'not_started'],
  ]

  return (
    <section className="paper-panel paper-status-panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">PAPER TRADING ACTIVITY</p>
          <h2>Paper Trading Status</h2>
        </div>
        <span className={`paper-policy-pill${label === 'Replay failed' ? ' paper-policy-pill--danger' : ''}`}>
          {label.toUpperCase()}
        </span>
      </div>
      <dl className="paper-performance-list">
        {metrics.map(([metricLabel, value]) => (
          <div key={metricLabel}>
            <dt>{metricLabel}</dt>
            <dd>{String(value)}</dd>
          </div>
        ))}
      </dl>
      <p className="muted-copy">
        Supported modes: historical_price_replay (active), live_paper_fund
        (simulated forward paper fund), broker_paper_pending (disabled).
      </p>
    </section>
  )
}

export default PaperTradingStatusCard
