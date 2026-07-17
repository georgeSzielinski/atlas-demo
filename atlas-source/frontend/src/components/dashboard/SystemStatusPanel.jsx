import { memo } from 'react'
import Panel from '../ui/Panel'
import StatusPill from '../ui/StatusPill'
import GradeBadge from '../ui/GradeBadge'
import MeterBar from '../ui/MeterBar'
import { useDashboardData } from '../../context/DashboardDataProvider'
import { formatClock, schedulerLabel, marketLabel } from '../../services/paperFundOps'

const SUBSYSTEM_LABELS = {
  scheduler: 'Scheduler',
  market_data: 'Market Data',
  provider: 'Provider',
  database: 'Database',
  paper_fund: 'Paper Fund',
  api: 'API',
  learning: 'Learning',
}

function meterTone(score) {
  if (score >= 80) return 'positive'
  if (score >= 50) return 'warn'
  return 'negative'
}

// Left-rail system panel: overall health, reliability grade, per-subsystem
// reliability meters, and the paper-fund runtime essentials. Subsystems with a
// null score are reported NOT_EVALUATED rather than shown as zero.
function SystemStatusPanel() {
  const { data } = useDashboardData()
  const operations = data?.operations ?? {}
  const reliability = data?.reliability ?? {}
  const fund = data?.paper_fund ?? {}
  const scheduler = data?.scheduler ?? {}
  const market = data?.market ?? {}

  const overall = operations.overall_health ?? {}
  const grade = reliability.overall_reliability ?? {}
  const scores = reliability.subsystem_scores ?? {}
  const provider = fund.price_provider || market.active_provider

  return (
    <Panel
      eyebrow="System"
      title="Atlas Status"
      action={<StatusPill status={overall.status ?? 'Unavailable'} />}
    >
      <div className="dv2-system__grade">
        <GradeBadge grade={grade.grade} score={grade.score} />
        <span className="dv2-system__grade-note">
          {grade.evaluated_subsystems ?? 0}/{grade.total_subsystems ?? 0} subsystems evaluated
        </span>
      </div>

      <div className="dv2-system__meters">
        {Object.entries(SUBSYSTEM_LABELS).map(([key, label]) => {
          const score = scores[key]
          if (score === null || score === undefined) {
            return (
              <div className="dv2-system__meter-row" key={key}>
                <span className="dv2-system__meter-label">{label}</span>
                <span className="dv2-system__meter-na">NOT EVALUATED</span>
              </div>
            )
          }
          return (
            <div className="dv2-system__meter-row" key={key}>
              <span className="dv2-system__meter-label">{label}</span>
              <div className="dv2-system__meter-track">
                <MeterBar value={score} tone={meterTone(score)} />
              </div>
              <span className="dv2-system__meter-score">{score}</span>
            </div>
          )
        })}
      </div>

      <div className="dv2-system__runtime">
        <div className="dv2-opsrow">
          <span className="dv2-opsrow__label">Paper Fund</span>
          <StatusPill status={fund.fund_status ?? 'OFF'} />
        </div>
        <div className="dv2-opsrow">
          <span className="dv2-opsrow__label">Scheduler</span>
          <StatusPill status={schedulerLabel(scheduler)} label={schedulerLabel(scheduler)} />
        </div>
        <div className="dv2-opsrow">
          <span className="dv2-opsrow__label">Market</span>
          <StatusPill status={marketLabel(market)} label={marketLabel(market)} />
        </div>
        <div className="dv2-opsrow">
          <span className="dv2-opsrow__label">Provider</span>
          <span className="dv2-opsrow__text">{provider || '—'}</span>
        </div>
        <div className="dv2-opsrow">
          <span className="dv2-opsrow__label">Last Tick</span>
          <span className="dv2-opsrow__text">{formatClock(scheduler.last_tick_at)}</span>
        </div>
        <div className="dv2-opsrow">
          <span className="dv2-opsrow__label">Last Cycle</span>
          <span className="dv2-opsrow__text">{formatClock(fund.last_update)}</span>
        </div>
      </div>

      {fund.last_error ? <p className="dv2-opslist__error">{fund.last_error}</p> : null}
      <p className="dv2-system__policy">Paper only · no broker · no real money</p>
    </Panel>
  )
}

export default memo(SystemStatusPanel)
