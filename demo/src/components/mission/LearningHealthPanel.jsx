import { memo, useMemo } from 'react'
import Panel from '../ui/Panel'
import StatusPill from '../ui/StatusPill'
import { ErrorState, LoadingState } from '../ui/States'
import { useAsyncResource } from '../../services/useAsyncResource'
import { getLearningCenterStatus } from '../../services/api'
import {
  LEARNING_RECORD_LIMIT,
  LEARNING_STATUS_RESOURCE_KEY,
  buildLearningStatusModel,
} from '../../services/learningIntelligence'
import { formatPercent } from '../../services/formatters'
import { dayOf } from '../../services/paperFundOps'

function percent(value) {
  return value === null ? 'Unavailable' : formatPercent(value, { fallback: 'Unavailable' })
}

function LearningHealthPanel() {
  const { data, isLoading, error } = useAsyncResource(
    LEARNING_STATUS_RESOURCE_KEY,
    () => getLearningCenterStatus(LEARNING_RECORD_LIMIT),
  )
  const model = useMemo(() => buildLearningStatusModel(data), [data])

  return (
    <Panel
      eyebrow="Learning Intelligence"
      title="Learning Health"
      action={<StatusPill status={model.status} label={model.status} />}
    >
      {isLoading && !data ? <LoadingState label="Loading learning health…" /> : null}
      {error && !data ? <ErrorState message={error.message} /> : null}
      {data ? (
        <div className="li-mission-grid">
          <HealthCard label="Overall Accuracy" value={percent(model.accuracy)} />
          <HealthCard label="Rolling Accuracy" value={percent(model.rollingAccuracy)} />
          <HealthCard label="Outcome Maturity" value={model.maturity} />
          <HealthCard label="Recommendation Coverage" value={percent(model.coverage)} />
          <HealthCard label="Calibration Health" value={model.calibrationHealth} />
          <HealthCard
            label="Committee Leaderboard"
            value={model.committeeLeader
              ? `${model.committeeLeader.committee} · ${percent(model.committeeLeader.accuracy)}`
              : model.committeeHealth}
          />
          <HealthCard
            label="Engine Leaderboard"
            value={model.engineLeader
              ? `${model.engineLeader.engine} · ${percent(model.engineLeader.accuracy)}`
              : model.engineHealth}
          />
          <HealthCard label="Completed / Pending" value={`${model.completed} / ${model.pending}`} />
          <HealthCard label="Data Freshness" value={model.dataFreshness ? dayOf(model.dataFreshness) : 'Unavailable'} />
        </div>
      ) : null}
      {model.truncated ? (
        <p className="li-warning" role="alert">{model.warning}</p>
      ) : null}
      <p className="li-note">Read-only · deterministic · paper-only outcome evidence.</p>
    </Panel>
  )
}

function HealthCard({ label, value, hint }) {
  return (
    <article className="li-health-card">
      <span>{label}</span>
      <strong>{value}</strong>
      {hint ? <small>{hint}</small> : null}
    </article>
  )
}

export default memo(LearningHealthPanel)
