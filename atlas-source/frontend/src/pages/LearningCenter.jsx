import { useMemo } from 'react'
import Panel from '../components/ui/Panel'
import StatusPill from '../components/ui/StatusPill'
import { EmptyState, ErrorState, LoadingState } from '../components/ui/States'
import { useAsyncResource } from '../services/useAsyncResource'
import { getLearningCenter } from '../services/api'
import {
  LEARNING_RECORD_LIMIT,
  LEARNING_RESOURCE_KEY,
  buildLearningCenterModel,
} from '../services/learningIntelligence'
import {
  formatNumber,
  formatPercent,
  formatSignedPercent,
  toneForDelta,
} from '../services/formatters'
import { dayOf } from '../services/paperFundOps'

function availablePercent(value) {
  return value === null || value === undefined
    ? 'Unavailable'
    : formatPercent(value, { fallback: 'Unavailable' })
}

function LearningCenter() {
  const { data, isLoading, error } = useAsyncResource(
    LEARNING_RESOURCE_KEY,
    () => getLearningCenter({ limit: LEARNING_RECORD_LIMIT }),
  )
  const model = useMemo(() => buildLearningCenterModel(data), [data])

  if (isLoading && !data) return <LoadingState label="Loading Learning Center…" />
  if (error && !data) return <ErrorState message={error.message} />

  return (
    <div className="dv2-page li-page">
      <section className="li-hero">
        <div>
          <p className="eyebrow">Learning Intelligence</p>
          <h2>ATLAS Learning Center</h2>
          <p>
            Deterministic analytics over stored recommendation-horizon evaluations.
            Every completed horizon is a separate sample; no causal attribution or execution is implied.
          </p>
        </div>
        <div className="li-notices">
          <span>READ-ONLY</span>
          <span>PAPER-ONLY</span>
          <span>DETERMINISTIC</span>
        </div>
      </section>

      {model.source.truncated ? (
        <div className="li-warning" role="alert">
          {model.source.warning} Analyzed {model.source.analyzedRowCount} of{' '}
          {model.source.sourceTotalRowCount} source rows.
        </div>
      ) : null}

      {model.status === 'NOT_EVALUATED' ? (
        <Panel eyebrow="Evidence" title="Learning health">
          <EmptyState
            title="No recommendation outcomes evaluated yet"
            message="Accuracy, returns, completion, calibration, and leaderboards remain unavailable until stored paper-only outcome evidence exists."
          />
        </Panel>
      ) : (
        <>
          <KpiGrid model={model} />
          <div className="li-grid li-grid--wide">
            <OutcomePanel model={model} />
            <MaturityPanel model={model} />
          </div>
          <CalibrationPanel model={model} />
          <div className="li-grid">
            <LeaderboardPanel title="Committee Leaderboard" rows={model.committeeLeaderboard} keyName="committee" />
            <LeaderboardPanel title="Engine Leaderboard" rows={model.engineLeaderboard} keyName="engine" notice={model.engineAssociationNotice} />
          </div>
          <div className="li-grid li-grid--wide">
            <PerformancePanel title="Best Recommendations" rows={model.best} />
            <PerformancePanel title="Worst Recommendations" rows={model.worst} />
          </div>
          <div className="li-grid li-grid--wide">
            <HistoryPanel model={model} />
            <SystemHealthPanel model={model} />
          </div>
        </>
      )}
    </div>
  )
}

function KpiGrid({ model }) {
  const summary = model.summary
  const lastRolling = model.rollingAccuracy.at(-1)?.accuracy ?? null
  const items = [
    ['Overall accuracy', availablePercent(summary.accuracy)],
    ['Rolling accuracy', availablePercent(lastRolling)],
    ['Recommendations', formatNumber(summary.recommendationVolume)],
    ['Completed evaluations', formatNumber(summary.completed)],
    ['Pending', formatNumber(summary.pending)],
    ['Deferred', formatNumber(summary.deferred)],
    ['Expired', formatNumber(summary.expired)],
    ['Outcome completion', availablePercent(summary.completionRate)],
    ['Recommendation coverage', availablePercent(summary.coverage)],
    ['Data maturity', summary.dataMaturity],
    [
      'Average raw return',
      summary.averageReturn === null
        ? 'Unavailable'
        : formatSignedPercent(summary.averageReturn, { fallback: 'Unavailable' }),
    ],
    ['Return samples', formatNumber(summary.returnSampleSize)],
  ]
  return (
    <section className="li-kpis" aria-label="Learning health summary">
      {items.map(([label, value]) => (
        <article className="li-kpi" key={label}>
          <span>{label}</span>
          <strong>{value}</strong>
        </article>
      ))}
    </section>
  )
}

function OutcomePanel({ model }) {
  return (
    <Panel eyebrow="Evidence" title="Outcome Distribution">
      <div className="li-bars">
        {model.distribution.map((row) => (
          <div className="li-bar" key={row.status}>
            <StatusPill status={row.status} label={row.status} />
            <strong>{formatNumber(row.count)}</strong>
          </div>
        ))}
      </div>
    </Panel>
  )
}

function MaturityPanel({ model }) {
  return (
    <Panel eyebrow="Evidence" title="Evaluation Maturity by Horizon">
      <div className="li-table-wrap">
        <table className="li-table">
          <thead><tr><th>Horizon</th><th>Completed</th><th>Pending</th><th>Deferred</th><th>Expired</th><th>Completion</th></tr></thead>
          <tbody>
            {model.horizonMaturity.map((row) => (
              <tr key={row.horizon_days}>
                <td>{row.horizon_days}d</td>
                <td>{row.completed}</td>
                <td>{row.pending}</td>
                <td>{row.deferred}</td>
                <td>{row.expired}</td>
                <td>{availablePercent(row.completion_rate)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Panel>
  )
}

function CalibrationPanel({ model }) {
  const calibration = model.calibration
  return (
    <Panel
      eyebrow="Reliability"
      title="Confidence Calibration"
      action={<StatusPill status={calibration.status} label={calibration.status} />}
    >
      <div className="li-calibration-summary">
        <Metric label="Expected confidence" value={availablePercent(calibration.expectedConfidence)} />
        <Metric label="Observed accuracy" value={availablePercent(calibration.observedAccuracy)} />
        <Metric
          label="Calibration gap"
          value={calibration.gap === null ? 'Unavailable' : formatSignedPercent(calibration.gap)}
        />
        <Metric label="Sample size" value={formatNumber(calibration.sampleSize)} />
      </div>
      {calibration.warning ? <p className="li-note">{calibration.warning}</p> : null}
      <div className="li-table-wrap">
        <table className="li-table">
          <thead><tr><th>Bucket</th><th>Expected</th><th>Observed</th><th>Gap</th><th>Samples</th><th>State</th></tr></thead>
          <tbody>
            {calibration.buckets.map((row) => (
              <tr key={row.bucket}>
                <td>{row.bucket}%</td>
                <td>{availablePercent(row.average_confidence)}</td>
                <td>{availablePercent(row.observed_accuracy)}</td>
                <td>{row.calibration_gap === null ? 'Unavailable' : formatSignedPercent(row.calibration_gap)}</td>
                <td>{row.sample_size}</td>
                <td>{row.sample_warning ?? row.calibration}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Panel>
  )
}

function LeaderboardPanel({ title, rows, keyName, notice }) {
  return (
    <Panel eyebrow="Historical association" title={title}>
      {rows.length === 0 ? (
        <EmptyState title="NOT_EVALUATED" message="No provable stored relationship is available." />
      ) : (
        <div className="li-table-wrap">
          <table className="li-table">
            <thead><tr><th>Name</th><th>Accuracy</th><th>Samples</th><th>Coverage</th><th>Calibration</th><th>Avg raw return</th></tr></thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row[keyName]}>
                  <td>{row[keyName]}</td>
                  <td>{availablePercent(row.accuracy)}</td>
                  <td>{row.accuracy_sample_size}</td>
                  <td>{availablePercent(row.recommendation_coverage)}</td>
                  <td>{row.calibration_state}</td>
                  <td>{row.average_return === null ? 'Unavailable' : formatSignedPercent(row.average_return)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {notice ? <p className="li-note">{notice}</p> : null}
    </Panel>
  )
}

function PerformancePanel({ title, rows }) {
  return (
    <Panel eyebrow="Raw outcome return" title={title}>
      {rows.length === 0 ? (
        <EmptyState title="NOT_EVALUATED" message="No scored return evidence is available." />
      ) : (
        <div className="li-performance-list">
          {rows.slice(0, 5).map((row) => (
            <article key={row.outcome_id}>
              <div><strong>{row.ticker ?? 'Unavailable'}</strong><span>{row.action ?? 'Unavailable'} · {row.horizon_days}d</span></div>
              <strong className={`li-return li-return--${toneForDelta(row.percentage_return)}`}>
                {formatSignedPercent(row.percentage_return)}
              </strong>
            </article>
          ))}
        </div>
      )}
    </Panel>
  )
}

function HistoryPanel({ model }) {
  const latest = [...model.volume].slice(-12).reverse()
  return (
    <Panel eyebrow="Chronology" title="Historical Recommendation Volume">
      {latest.length === 0 ? (
        <EmptyState title="NOT_EVALUATED" message="No dated recommendations are available." />
      ) : (
        <div className="li-volume-list">
          {latest.map((row) => (
            <div key={row.date}><span>{dayOf(row.date)}</span><strong>{row.count}</strong></div>
          ))}
        </div>
      )}
    </Panel>
  )
}

function SystemHealthPanel({ model }) {
  const health = model.systemHealth
  const rows = [
    ['Deterministic', health.deterministic_status],
    ['Paper-only', health.paper_only_status],
    ['Read-only', health.read_only_status],
    ['Outcome evidence', health.outcome_evidence],
    ['Committee analytics', health.committee_analytics],
    ['Engine analytics', health.engine_analytics],
    ['Calibration', health.calibration],
    ['Data maturity', health.data_maturity],
    ['Data freshness', health.data_freshness ? dayOf(health.data_freshness) : 'Unavailable'],
  ]
  return (
    <Panel eyebrow="Controls" title="System Health Indicators">
      <div className="li-health-list">
        {rows.map(([label, value]) => (
          <div key={label}><span>{label}</span><StatusPill status={value} label={value ?? 'Unavailable'} /></div>
        ))}
      </div>
    </Panel>
  )
}

function Metric({ label, value }) {
  return <div className="li-metric"><span>{label}</span><strong>{value}</strong></div>
}

export default LearningCenter
