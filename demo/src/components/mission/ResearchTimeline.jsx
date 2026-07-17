import { memo } from 'react'
import Panel from '../ui/Panel'
import { useDashboardData } from '../../context/DashboardDataProvider'
import { researchTimeline } from '../../services/missionOps'
import { STAGE_STATUS, formatClock, stageTone } from '../../services/paperFundOps'

function formatDuration(seconds) {
  if (seconds === null || seconds === undefined) return null
  const total = Math.max(0, Number(seconds) || 0)
  if (total < 60) return `${Math.round(total * 10) / 10}s`
  const minutes = Math.floor(total / 60)
  const rest = Math.round(total % 60)
  return `${minutes}m ${String(rest).padStart(2, '0')}s`
}

const STATUS_LABEL = {
  [STAGE_STATUS.COMPLETE]: 'Complete',
  [STAGE_STATUS.WAITING]: 'Waiting',
  [STAGE_STATUS.SKIPPED]: 'Skipped',
  [STAGE_STATUS.ERROR]: 'Error',
  [STAGE_STATUS.NOT_EVALUATED]: 'Pending',
}

// Row 4 — the pipeline as a horizontal timeline: Research → Committee → Risk →
// Portfolio → Learning, each with its recorded timestamp and duration.
function ResearchTimeline() {
  const { data } = useDashboardData()
  const steps = researchTimeline(data)

  return (
    <Panel eyebrow="Research Timeline" title="Autonomous Pipeline" className="dv2-panel--wide">
      <ol className="dv3-timeline">
        {steps.map((step, index) => {
          const tone = stageTone(step.status)
          const duration = formatDuration(step.durationSeconds)
          return (
            <li className="dv3-timeline__step" key={step.key}>
              <div className={`dv3-timeline__node dv3-timeline__node--${tone}`}>
                <span className="dv3-timeline__dot" aria-hidden="true" />
                {index < steps.length - 1 ? (
                  <span className="dv3-timeline__line" aria-hidden="true" />
                ) : null}
              </div>
              <div className="dv3-timeline__body">
                <span className="dv3-timeline__label">{step.label}</span>
                <span className={`dv3-timeline__status dv3-timeline__status--${tone}`}>
                  {STATUS_LABEL[step.status] ?? step.status}
                </span>
                <span className="dv3-timeline__meta">{step.at ? formatClock(step.at) : '—'}</span>
                {duration ? <span className="dv3-timeline__dur">{duration}</span> : null}
                {step.detail ? <small className="dv3-timeline__detail">{step.detail}</small> : null}
              </div>
            </li>
          )
        })}
      </ol>
    </Panel>
  )
}

export default memo(ResearchTimeline)
