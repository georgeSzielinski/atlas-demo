import { memo, useMemo } from 'react'
import Panel from '../ui/Panel'
import StatusPill from '../ui/StatusPill'
import { useDashboardData } from '../../context/DashboardDataProvider'
import { deriveFullPipeline, stageTone, formatClock } from '../../services/paperFundOps'

// Prominent autonomous-pipeline status meter:
// Scheduler → Research Due Check → Recommendation Generation → Investment
// Committee → Market Data → Portfolio Construction → Risk Gate → Paper Orders
// → Accounting → Learning. Each stage shows COMPLETE / WAITING / SKIPPED /
// ERROR / NOT_EVALUATED with timestamps and durations when recorded — all
// derived from real /dashboard/v2 sections (scheduler, research_cycle, and
// the fund cycle's activity markers). Paper only; no broker; no real money.
function stageMeta(stage) {
  const parts = []
  if (stage.at) parts.push(String(stage.at).slice(11, 19))
  if (stage.durationSeconds !== null && stage.durationSeconds !== undefined) {
    parts.push(`${stage.durationSeconds}s`)
  }
  return parts.join(' · ')
}

function PipelineMeter() {
  const { data } = useDashboardData()

  const pipeline = useMemo(() => deriveFullPipeline(data), [data])

  const completeCount = pipeline.stages.filter((s) => s.status === 'COMPLETE').length
  const headline = pipeline.failed
    ? 'ERROR'
    : pipeline.inProgress
      ? 'RUNNING'
      : pipeline.completed
        ? 'COMPLETE'
        : pipeline.cycleId
          ? 'IDLE'
          : 'WAITING'

  const fund = data?.paper_fund ?? {}
  const cycleLabel = pipeline.cycleId
    ? `Cycle ${pipeline.cycleId} · last update ${formatClock(fund.last_update)} · simulated paper fund only`
    : 'No fund cycle has run yet — the pipeline advances once the scheduler triggers a cycle. Simulated paper fund only.'

  return (
    <Panel
      eyebrow="Autonomous Pipeline"
      title="Live Cycle Progress"
      className="dv2-panel--wide"
      action={
        <div className="dv2-pipeline__headline">
          <StatusPill status={headline} label={headline} />
          <span className="dv2-pipeline__count">{completeCount}/{pipeline.stages.length} complete</span>
        </div>
      }
    >
      <ol className="dv2-pipeline">
        {pipeline.stages.map((stage, index) => {
          const tone = stageTone(stage.status)
          const meta = stageMeta(stage)
          return (
            <li className="dv2-pipeline__stage" key={stage.key}>
              {index > 0 ? (
                <span
                  className={`dv2-pipeline__connector dv2-pipeline__connector--${tone}`}
                  aria-hidden="true"
                />
              ) : null}
              <span className="dv2-pipeline__node">
                <span className={`dv2-pipeline__dot dv2-pipeline__dot--${tone}`} aria-hidden="true" />
                <span className="dv2-pipeline__label">{stage.label}</span>
                <span className={`dv2-pill dv2-pill--${tone} dv2-pipeline__status`}>
                  {stage.status.replace(/_/g, ' ')}
                </span>
                {meta ? <span className="dv2-pipeline__meta">{meta}</span> : null}
                {stage.detail ? (
                  <span className="dv2-pipeline__detail">{stage.detail}</span>
                ) : null}
              </span>
            </li>
          )
        })}
      </ol>
      <p className="dv2-pipeline__cycle">{cycleLabel}</p>
    </Panel>
  )
}

export default memo(PipelineMeter)
