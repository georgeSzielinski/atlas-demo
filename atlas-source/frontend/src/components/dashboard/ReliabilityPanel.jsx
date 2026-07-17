import { memo } from 'react'
import Panel from '../ui/Panel'
import MeterBar from '../ui/MeterBar'
import GradeBadge from '../ui/GradeBadge'
import StatusPill from '../ui/StatusPill'
import AlertList from '../ui/AlertList'
import { EmptyState } from '../ui/States'
import { useDashboardData } from '../../context/DashboardDataProvider'
import { isEvaluated, formatValue } from '../../services/formatters'

function meterTone(score) {
  if (score >= 90) return 'positive'
  if (score >= 75) return 'accent'
  if (score >= 50) return 'warn'
  return 'negative'
}

function ReliabilityPanel() {
  const { data } = useDashboardData()
  const reliability = data?.reliability ?? {}
  const overall = reliability.overall_reliability ?? {}

  if (!isEvaluated(overall) && overall.score === undefined) {
    return (
      <Panel eyebrow="Reliability" title="Reliability Summary">
        <EmptyState title="Not evaluated" message="Reliability telemetry is unavailable." />
      </Panel>
    )
  }

  const score = Number(overall.score ?? 0)
  const incidents = reliability.recent_incidents ?? []
  const trend = reliability.reliability_trend?.direction

  return (
    <Panel
      eyebrow="Reliability"
      title="Reliability Summary"
      action={<GradeBadge grade={overall.grade} score={overall.score} />}
    >
      <MeterBar value={score} tone={meterTone(score)} label={`Score · ${formatValue(overall.status)}`} />
      <div className="dv2-kv">
        <div className="dv2-kv__row">
          <span className="dv2-kv__key">Warnings / Errors / Critical</span>
          <span className="dv2-kv__val">
            {formatValue(reliability.warning_count, '0')} / {formatValue(reliability.error_count, '0')} /{' '}
            {formatValue(reliability.critical_count, '0')}
          </span>
        </div>
        <div className="dv2-kv__row">
          <span className="dv2-kv__key">Trend</span>
          <span className="dv2-kv__val">
            <StatusPill status={trend ?? 'NOT_EVALUATED'} label={trend ?? 'N/A'} />
          </span>
        </div>
      </div>
      {incidents.length > 0 ? <AlertList items={incidents} max={3} /> : null}
    </Panel>
  )
}

export default memo(ReliabilityPanel)
