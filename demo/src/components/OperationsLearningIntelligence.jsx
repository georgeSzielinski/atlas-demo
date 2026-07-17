import { useMemo } from 'react'
import { useAsyncResource } from '../services/useAsyncResource'
import { getLearningCenterStatus } from '../services/api'
import {
  LEARNING_RECORD_LIMIT,
  LEARNING_STATUS_RESOURCE_KEY,
  buildLearningStatusModel,
} from '../services/learningIntelligence'
import { formatPercent } from '../services/formatters'

function percent(value) {
  return value === null ? 'Unavailable' : formatPercent(value, { fallback: 'Unavailable' })
}

function OperationsLearningIntelligence() {
  const { data, isLoading, error } = useAsyncResource(
    LEARNING_STATUS_RESOURCE_KEY,
    () => getLearningCenterStatus(LEARNING_RECORD_LIMIT),
  )
  const model = useMemo(() => buildLearningStatusModel(data), [data])
  const rows = [
    ['Recommendation accuracy', percent(model.accuracy)],
    ['Completed evaluations', String(model.completed)],
    ['Pending evaluations', String(model.pending)],
    ['Recommendation coverage', percent(model.coverage)],
    ['Committee analytics health', model.committeeHealth],
    ['Engine analytics health', model.engineHealth],
    ['Deterministic status', model.deterministic ? 'CONFIRMED' : 'Unavailable'],
    ['Paper-only status', model.paperOnly ? 'CONFIRMED' : 'Unavailable'],
  ]

  return (
    <section className="operations-panel">
      <div className="operations-pill-row">
        <h2>Learning Intelligence</h2>
        <span className="operations-policy-pill">READ-ONLY</span>
      </div>
      {isLoading && !data ? <p className="operations-empty">Loading learning health…</p> : null}
      {error && !data ? <p className="operations-empty">Learning Intelligence is unavailable.</p> : null}
      {data ? (
        <dl className="operations-stat-list">
          {rows.map(([label, value]) => (
            <div key={label}><dt>{label}</dt><dd>{value}</dd></div>
          ))}
        </dl>
      ) : null}
      {model.truncated ? (
        <p className="li-warning" role="alert">{model.warning}</p>
      ) : null}
    </section>
  )
}

export default OperationsLearningIntelligence
