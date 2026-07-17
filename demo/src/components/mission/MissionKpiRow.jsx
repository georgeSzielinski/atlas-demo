import { memo } from 'react'
import StatTile from '../ui/StatTile'
import StatusPill from '../ui/StatusPill'
import GradeBadge from '../ui/GradeBadge'
import { useDashboardData } from '../../context/DashboardDataProvider'
import {
  formatCurrency,
  formatSignedPercent,
  toneForDelta,
} from '../../services/formatters'
import { marketLabel, schedulerLabel } from '../../services/paperFundOps'

// Row 1 — the six vitals a desk needs within ten seconds:
// Portfolio Value · Daily P/L · Reliability · Market · Scheduler · Research.
function MissionKpiRow() {
  const { data } = useDashboardData()
  const fund = data?.paper_fund ?? {}
  const reliability = data?.reliability ?? {}
  const scheduler = data?.scheduler ?? {}
  const market = data?.market ?? {}
  const research = data?.research_cycle ?? {}
  const snapshot = fund.latest_snapshot ?? {}

  const portfolioValue = snapshot.portfolio_value ?? fund.cash ?? fund.starting_cash
  const fundStatus = String(fund.fund_status ?? 'OFF').toUpperCase()
  const dailyReturn = snapshot.daily_return
  const totalReturn = snapshot.total_return

  const grade = reliability.overall_reliability?.grade
  const gradeScore = reliability.overall_reliability?.score
  const marketState = marketLabel(market)
  const schedulerState = schedulerLabel(scheduler)
  const researchState =
    research.status === 'EVALUATED'
      ? 'Active'
      : research.enabled
        ? 'Armed'
        : 'Idle'
  const researchTone =
    research.status === 'EVALUATED' ? 'positive' : research.enabled ? 'warn' : 'muted'

  return (
    <div className="dv3-kpis">
      <StatTile
        label="Portfolio Value"
        value={
          portfolioValue === null || portfolioValue === undefined
            ? fundStatus === 'OFF'
              ? 'Not started'
              : '—'
            : formatCurrency(portfolioValue)
        }
        delta={formatSignedPercent(totalReturn, { fallback: null })}
        deltaTone={toneForDelta(totalReturn)}
        hint="total return"
      />
      <StatTile
        label="Daily P/L"
        value={formatSignedPercent(dailyReturn, { fallback: '—' })}
        deltaTone={toneForDelta(dailyReturn)}
        hint="since last cycle"
      />
      <StatTile
        label="Reliability"
        value={<GradeBadge grade={grade} score={gradeScore} />}
        hint={reliability.overall_reliability?.status ?? 'not evaluated'}
      />
      <StatTile
        label="Market"
        value={<StatusPill status={marketState} label={marketState} />}
        hint={market.active_provider ? `via ${market.active_provider}` : 'provider n/a'}
      />
      <StatTile
        label="Scheduler"
        value={<StatusPill status={schedulerState} />}
        hint={
          scheduler.interval_seconds
            ? `${Math.round(scheduler.interval_seconds / 60)} min loop`
            : 'interval n/a'
        }
      />
      <StatTile
        label="Research"
        value={<StatusPill status={researchState} tone={researchTone} label={researchState} />}
        hint={research.enabled ? 'autonomous enabled' : 'autonomous off'}
      />
    </div>
  )
}

export default memo(MissionKpiRow)
