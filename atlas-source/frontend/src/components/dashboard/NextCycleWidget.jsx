import { memo, useEffect, useState } from 'react'
import Panel from '../ui/Panel'
import MeterBar from '../ui/MeterBar'
import StatusPill from '../ui/StatusPill'
import { useDashboardData } from '../../context/DashboardDataProvider'
import { cycleCountdown, formatClock, marketLabel } from '../../services/paperFundOps'

// Live-ticking countdown to the fund's next scheduled cycle. Reads only
// paper_fund.next_update / interval_minutes; when no cycle is scheduled it
// says so instead of inventing a timer.
function NextCycleWidget() {
  const { data } = useDashboardData()
  const fund = data?.paper_fund ?? {}
  const market = data?.market ?? {}
  const [now, setNow] = useState(() => Date.now())

  const fundStatus = String(fund.fund_status ?? 'OFF').toUpperCase()
  const armed = fundStatus === 'READY' || fundStatus === 'RUNNING'
  const countdown = armed ? cycleCountdown(fund.next_update, now) : null

  // Tick each second only while an actual countdown is on screen.
  useEffect(() => {
    if (!countdown || countdown.due) return undefined
    const id = setInterval(() => setNow(Date.now()), 1000)
    return () => clearInterval(id)
  }, [countdown?.due, fund.next_update]) // eslint-disable-line react-hooks/exhaustive-deps

  const intervalMs = Number(fund.interval_minutes ?? 0) * 60000
  const progress = countdown && !countdown.due && intervalMs > 0
    ? Math.max(0, Math.min(100, (1 - countdown.ms / intervalMs) * 100))
    : null

  return (
    <Panel
      eyebrow="Automation"
      title="Next Cycle"
      className="dv2-countdown"
      action={<StatusPill status={fundStatus} />}
    >
      {countdown ? (
        <>
          <div className="dv2-countdown__time" role="timer" aria-live="off">
            {countdown.due ? 'DUE' : countdown.label}
          </div>
          <p className="dv2-countdown__hint">
            {countdown.due
              ? market.market_is_open === false
                ? 'Awaiting scheduler tick — market is closed, cycle will be skipped until it opens.'
                : 'Awaiting scheduler tick.'
              : `Scheduled ${formatClock(fund.next_update)} · every ${fund.interval_minutes ?? '—'} min`}
          </p>
          {progress !== null ? <MeterBar value={progress} tone="accent" /> : null}
          <p className="dv2-countdown__market">
            Market: {marketLabel(market)} · paper only
          </p>
        </>
      ) : (
        <>
          <div className="dv2-countdown__time dv2-countdown__time--idle">--:--</div>
          <p className="dv2-countdown__hint">
            {fundStatus === 'PAUSED'
              ? 'Fund is paused — resume it to schedule cycles.'
              : fundStatus === 'ERROR'
                ? 'Fund is in an error state — no cycle is scheduled.'
                : 'Fund not started. Start the paper fund to schedule automated cycles.'}
          </p>
        </>
      )}
    </Panel>
  )
}

export default memo(NextCycleWidget)
