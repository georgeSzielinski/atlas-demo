import { memo } from 'react'
import { useDashboardData } from '../../context/DashboardDataProvider'
import StatTile from '../ui/StatTile'
import StatusPill from '../ui/StatusPill'
import {
  formatCurrency,
  formatSignedPercent,
  formatPercent,
  toneForDelta,
} from '../../services/formatters'

// Row 1: Portfolio Value · Daily Return · Reliability · Paper Fund Status.
function StatTiles() {
  const { data } = useDashboardData()
  const fund = data?.paper_fund ?? {}
  const reliability = data?.reliability ?? {}
  const snapshot = fund.latest_snapshot ?? {}

  const portfolioValue = snapshot.portfolio_value ?? fund.cash ?? fund.starting_cash
  const totalReturn = snapshot.total_return
  const dailyReturn = snapshot.daily_return
  const score = reliability.overall_reliability?.score
  const grade = reliability.overall_reliability?.grade
  const fundStatus = fund.fund_status ?? 'OFF'

  return (
    <div className="dv2-row dv2-row--4">
      <StatTile
        label="Portfolio Value"
        value={formatCurrency(portfolioValue)}
        delta={formatSignedPercent(totalReturn)}
        deltaTone={toneForDelta(totalReturn)}
        hint="total return"
      />
      <StatTile
        label="Daily Return"
        value={formatSignedPercent(dailyReturn)}
        deltaTone={toneForDelta(dailyReturn)}
        hint="since last cycle"
      />
      <StatTile
        label="Reliability"
        value={score !== null && score !== undefined ? `${score}` : '—'}
        badge={<StatusPill status={grade ?? 'NOT_EVALUATED'} label={grade ?? 'N/A'} />}
        hint={formatPercent(reliability.availability?.availability_percent, { fallback: 'availability n/a' })}
      />
      <StatTile
        label="Paper Fund"
        value={<StatusPill status={fundStatus} />}
        hint={fund.price_provider ? `provider: ${fund.price_provider}` : 'simulated only'}
      />
    </div>
  )
}

export default memo(StatTiles)
