import { memo } from 'react'
import { useDashboardData } from '../../context/DashboardDataProvider'
import StatusPill from '../ui/StatusPill'
import GradeBadge from '../ui/GradeBadge'
import { formatCurrency, formatSignedPercent, toneForDelta } from '../../services/formatters'

function Cell({ label, children }) {
  return (
    <div className="dv2-statusbar__cell">
      <span className="dv2-statusbar__label">{label}</span>
      <span className="dv2-statusbar__value">{children}</span>
    </div>
  )
}

function TopStatusBar() {
  const { data } = useDashboardData()
  const operations = data?.operations ?? {}
  const reliability = data?.reliability ?? {}
  const fund = data?.paper_fund ?? {}
  const scheduler = data?.scheduler ?? {}
  const market = data?.market ?? {}

  const snapshot = fund.latest_snapshot ?? {}
  const fundStatus = fund.fund_status ?? 'OFF'
  const portfolioValue = snapshot.portfolio_value ?? fund.cash ?? fund.starting_cash
  const portfolioLabel =
    portfolioValue === null || portfolioValue === undefined
      ? fundStatus === 'OFF' ? 'Not started' : 'Unavailable'
      : formatCurrency(portfolioValue)
  const dailyReturn = snapshot.daily_return
  const grade = reliability.overall_reliability?.grade
  const gradeScore = reliability.overall_reliability?.score
  const schedulerStatus = scheduler.status === 'EVALUATED'
    ? (scheduler.running ? 'RUNNING' : scheduler.enabled ? 'READY' : 'OFF')
    : 'Unavailable'
  const marketStatus = market.status === 'EVALUATED'
    ? (market.market_is_open ? 'Open' : market.market_session ?? 'Closed')
    : 'Unavailable'

  return (
    <div className="dv2-statusbar" aria-label="Atlas status summary">
      <Cell label="Atlas Status">
        <StatusPill status={operations.overall_health?.status ?? 'Unavailable'} />
      </Cell>
      <Cell label="Reliability">
        <GradeBadge grade={grade} score={gradeScore} />
      </Cell>
      <Cell label="Portfolio Value">{portfolioLabel}</Cell>
      <Cell label="Today's Return">
        <span className={`dv2-stat__delta dv2-stat__delta--${toneForDelta(dailyReturn)}`}>
          {formatSignedPercent(dailyReturn)}
        </span>
      </Cell>
      <Cell label="Scheduler">
        <StatusPill status={schedulerStatus} />
      </Cell>
      <Cell label="Market">
        <StatusPill status={marketStatus} label={marketStatus} />
      </Cell>
    </div>
  )
}

export default memo(TopStatusBar)
