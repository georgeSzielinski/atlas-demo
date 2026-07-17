import { memo, useMemo, useState } from 'react'
import Panel from '../components/ui/Panel'
import StatusPill from '../components/ui/StatusPill'
import { LoadingState, ErrorState, EmptyState } from '../components/ui/States'
import InstitutionalReportDrawer from '../components/mission/InstitutionalReportDrawer'
import {
  HorizonEvidenceBadges,
  OutcomeSourceNotice,
} from '../components/outcomes/OutcomeEvidence'
import { DashboardDataProvider, useDashboardData } from '../context/DashboardDataProvider'
import { useAsyncResource } from '../services/useAsyncResource'
import {
  getRecommendationHistory,
  getRecommendationIntelligenceRecords,
  getLearningCenter,
} from '../services/api'
import { dayOf } from '../services/paperFundOps'
import {
  formatConfidence,
  formatPercent,
  formatSignedPercent,
  toneForDelta,
} from '../services/formatters'
import {
  ACTION_BUCKETS,
  DEFAULT_FILTERS,
  SORT_OPTIONS,
  actionTone,
  buildRecommendationRows,
  computeStats,
  executionStatus,
  filterRows,
  sortRows,
  toCardModel,
} from '../services/recommendationExplorer'
import {
  OUTCOME_RECORD_LIMIT,
  OUTCOME_RESOURCE_KEY,
  enrichRecommendationRows,
  outcomeSourceMeta,
  outcomeTone,
} from '../services/recommendationOutcomes'
import {
  LEARNING_RECORD_LIMIT,
  LEARNING_RESOURCE_KEY,
  enrichRowsWithLearning,
  learningSourceMeta,
} from '../services/learningIntelligence'

const HISTORY_KEY = 'recommendations/history'
// Cap DOM rows so a 10k+ history never renders tens of thousands of nodes at
// once. Filtering/sorting still run over the full set; only the slice is drawn.
const VISIBLE_LIMIT = 200

// Recommendation Explorer — the institutional terminal for browsing every
// recommendation the research committee has produced. One history fetch feeds
// the table + statistics; clicking a row reuses the Institutional Report drawer.
function ExplorerBody() {
  const { data: payload, isLoading, error } = useAsyncResource(HISTORY_KEY, () =>
    getRecommendationHistory(500),
  )
  const { data: dashboard } = useDashboardData()
  const paperFund = dashboard?.paper_fund ?? {}
  const hasHistory = Array.isArray(payload?.cycles) && payload.cycles.length > 0
  const {
    data: outcomePayload,
    isLoading: outcomesLoading,
    error: outcomesError,
  } = useAsyncResource(
    OUTCOME_RESOURCE_KEY,
    () => getRecommendationIntelligenceRecords(OUTCOME_RECORD_LIMIT),
    { enabled: hasHistory },
  )
  const { data: learningPayload, error: learningError } = useAsyncResource(
    LEARNING_RESOURCE_KEY,
    () => getLearningCenter({ limit: LEARNING_RECORD_LIMIT }),
    { enabled: hasHistory },
  )

  const [filters, setFilters] = useState(DEFAULT_FILTERS)
  const [sortKey, setSortKey] = useState('newest')
  const [selected, setSelected] = useState(null)

  const baseRows = useMemo(() => buildRecommendationRows(payload?.cycles), [payload])
  const rows = useMemo(
    () => enrichRowsWithLearning(
      enrichRecommendationRows(baseRows, outcomePayload),
      learningPayload,
    ),
    [baseRows, learningPayload, outcomePayload],
  )
  const outcomeMeta = useMemo(() => outcomeSourceMeta(outcomePayload), [outcomePayload])
  const learningMeta = useMemo(() => learningSourceMeta(learningPayload), [learningPayload])
  const stats = useMemo(() => computeStats(rows), [rows])
  const visibleRows = useMemo(() => {
    const filtered = filterRows(rows, filters)
    return sortRows(filtered, sortKey)
  }, [rows, filters, sortKey])

  if (isLoading && !payload) {
    return <LoadingState label="Loading recommendation history…" />
  }
  if (error && !payload) {
    return <ErrorState message={error.message} />
  }

  const hasAny = rows.length > 0

  return (
    <div className="dv2-page rx-page">
      <ExplorerStats stats={stats} />

      {!hasAny ? (
        <Panel eyebrow="Research Archive" title="Recommendation Explorer">
          <EmptyState
            title="No recommendations recorded yet"
            message="ATLAS populates this archive automatically as autonomous research cycles run. Every committee verdict — with its confidence, agreement and full institutional report — will appear here the moment a cycle completes. Nothing is placeholdered; the table stays empty until real research exists."
          />
        </Panel>
      ) : (
        <Panel
          eyebrow="Research Archive"
          title="All Recommendations"
          className="dv2-panel--wide"
          action={
            <span className="dv3-timestamp">
              {visibleRows.length === rows.length
                ? `${rows.length} record${rows.length === 1 ? '' : 's'}`
                : `${visibleRows.length} of ${rows.length} records`}
            </span>
          }
        >
          <OutcomeSourceNotice
            meta={outcomeMeta}
            error={outcomesError}
            isLoading={outcomesLoading || (hasHistory && !outcomePayload && !outcomesError)}
          />
          {learningError || learningMeta.truncated ? (
            <div className="rx-source-warning" role="status">
              {learningError
                ? 'Learning Intelligence enrichment is unavailable; historical analytics remain Unavailable.'
                : learningMeta.warning}
              {learningMeta.truncated
                ? ` Analyzed ${learningMeta.analyzedRowCount} of ${learningMeta.sourceTotalRowCount} source rows.`
                : ''}
            </div>
          ) : null}
          <ExplorerToolbar
            filters={filters}
            onFilters={setFilters}
            sortKey={sortKey}
            onSort={setSortKey}
          />
          <ExplorerTable
            rows={visibleRows}
            paperFund={paperFund}
            onSelect={setSelected}
          />
        </Panel>
      )}

      <InstitutionalReportDrawer card={selected} onClose={() => setSelected(null)} />
    </div>
  )
}

function ExplorerStats({ stats }) {
  const items = [
    { label: 'Total', value: String(stats.total) },
    { label: 'Buy', value: String(stats.buy), tone: 'positive' },
    { label: 'Hold', value: String(stats.hold), tone: 'neutral' },
    { label: 'Avoid', value: String(stats.avoid), tone: 'negative' },
    { label: 'Avg confidence', value: formatPercent(stats.avgConfidence, { fallback: '—' }) },
    { label: 'Avg agreement', value: formatPercent(stats.avgAgreement, { fallback: '—' }) },
    { label: 'Newest', value: stats.newestAt ? dayOf(stats.newestAt) : '—' },
    { label: 'Oldest', value: stats.oldestAt ? dayOf(stats.oldestAt) : '—' },
  ]
  return (
    <div className="rx-stats" role="group" aria-label="Recommendation statistics">
      {items.map((item) => (
        <div className="rx-stat" key={item.label}>
          <span className="rx-stat__label">{item.label}</span>
          <strong className={`rx-stat__value${item.tone ? ` rx-stat__value--${item.tone}` : ''}`}>
            {item.value}
          </strong>
        </div>
      ))}
    </div>
  )
}

function ExplorerToolbar({ filters, onFilters, sortKey, onSort }) {
  const set = (patch) => onFilters({ ...filters, ...patch })
  const toggleAction = (bucket) => {
    const active = filters.actions.includes(bucket)
    set({ actions: active ? filters.actions.filter((a) => a !== bucket) : [...filters.actions, bucket] })
  }
  const isDefault =
    filters.ticker === '' &&
    filters.actions.length === 0 &&
    Number(filters.minConfidence) === 0 &&
    filters.from === '' &&
    filters.to === '' &&
    sortKey === 'newest'

  return (
    <div className="rx-toolbar" role="search">
      <label className="rx-field">
        <span className="rx-field__label">Ticker</span>
        <input
          className="rx-input"
          type="search"
          inputMode="text"
          placeholder="Search ticker…"
          value={filters.ticker}
          onChange={(event) => set({ ticker: event.target.value })}
        />
      </label>

      <div className="rx-field rx-field--chips">
        <span className="rx-field__label">Action</span>
        <div className="rx-chips">
          {ACTION_BUCKETS.map((bucket) => {
            const active = filters.actions.includes(bucket)
            return (
              <button
                key={bucket}
                type="button"
                className={`rx-chip rx-chip--${actionTone(bucket)}${active ? ' is-active' : ''}`}
                aria-pressed={active}
                onClick={() => toggleAction(bucket)}
              >
                {bucket}
              </button>
            )
          })}
        </div>
      </div>

      <label className="rx-field rx-field--slider">
        <span className="rx-field__label">Min confidence · {Math.round(Number(filters.minConfidence))}%</span>
        <input
          className="rx-slider"
          type="range"
          min="0"
          max="100"
          step="5"
          value={filters.minConfidence}
          onChange={(event) => set({ minConfidence: Number(event.target.value) })}
        />
      </label>

      <label className="rx-field">
        <span className="rx-field__label">From</span>
        <input
          className="rx-input"
          type="date"
          value={filters.from}
          onChange={(event) => set({ from: event.target.value })}
        />
      </label>

      <label className="rx-field">
        <span className="rx-field__label">To</span>
        <input
          className="rx-input"
          type="date"
          value={filters.to}
          onChange={(event) => set({ to: event.target.value })}
        />
      </label>

      <label className="rx-field">
        <span className="rx-field__label">Sort</span>
        <select
          className="rx-input rx-select"
          value={sortKey}
          onChange={(event) => onSort(event.target.value)}
        >
          {SORT_OPTIONS.map((option) => (
            <option key={option.key} value={option.key}>
              {option.label}
            </option>
          ))}
        </select>
      </label>

      <button
        type="button"
        className="rx-reset"
        disabled={isDefault}
        onClick={() => {
          onFilters(DEFAULT_FILTERS)
          onSort('newest')
        }}
      >
        Reset filters
      </button>
    </div>
  )
}

function ExplorerTable({ rows, paperFund, onSelect }) {
  if (rows.length === 0) {
    return (
      <EmptyState
        title="No matching recommendations"
        message="No records match the current filters. Adjust the search, action or confidence filters to widen the results."
      />
    )
  }
  const shown = rows.slice(0, VISIBLE_LIMIT)
  return (
    <div className="rx-table-wrap">
      <table className="rx-table">
        <thead>
          <tr>
            <th scope="col">Ticker</th>
            <th scope="col">Recommendation</th>
            <th scope="col">Confidence</th>
            <th scope="col">Agreement</th>
            <th scope="col">Strength</th>
            <th scope="col">Date</th>
            <th scope="col">Provider</th>
            <th scope="col">Research</th>
            <th scope="col">Paper trade</th>
            <th scope="col">Latest return</th>
            <th scope="col">Outcome status</th>
            <th scope="col">Latest completed horizon</th>
            <th scope="col">Latest result</th>
            <th scope="col">Raw outcome return</th>
            <th scope="col">Horizon evidence</th>
            <th scope="col">Committee accuracy</th>
            <th scope="col">Primary engine accuracy</th>
            <th scope="col">Calibration gap</th>
            <th scope="col">Evaluation maturity</th>
            <th scope="col">Recommendation maturity</th>
            <th scope="col">Completion rate</th>
          </tr>
        </thead>
        <tbody>
          {shown.map((row) => (
            <ExplorerRow key={row.id} row={row} paperFund={paperFund} onSelect={onSelect} />
          ))}
        </tbody>
      </table>
      {rows.length > VISIBLE_LIMIT ? (
        <p className="rx-table__more">
          Showing the first {VISIBLE_LIMIT} of {rows.length} matches. Narrow the filters to reach the
          rest.
        </p>
      ) : null}
    </div>
  )
}

const ExplorerRow = memo(function ExplorerRow({ row, paperFund, onSelect }) {
  const exec = executionStatus(paperFund, row.ticker)
  const tone = actionTone(row.action)
  const outcome = row.outcomeEvidence
  return (
    <tr
      className="rx-row"
      tabIndex={0}
      role="button"
      aria-label={`Open institutional report for ${row.ticker}`}
      onClick={() => onSelect(toCardModel(row))}
      onKeyDown={(event) => {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault()
          onSelect(toCardModel(row))
        }
      }}
    >
      <td className="rx-cell--ticker">{row.ticker}</td>
      <td>
        <span className={`dv3-verdict dv3-verdict--${tone}`}>{row.action ?? '—'}</span>
      </td>
      <td className="rx-cell--num">{formatConfidence(row.confidence, { fallback: '—' })}</td>
      <td className="rx-cell--num">{formatPercent(row.agreementPct, { fallback: '—' })}</td>
      <td>{row.strength ?? '—'}</td>
      <td className="rx-cell--muted">{row.evaluatedAt ? dayOf(row.evaluatedAt) : '—'}</td>
      <td className="rx-cell--muted">{row.provider ?? '—'}</td>
      <td>
        <StatusPill status={row.researchStatus} label={row.evaluated ? 'Evaluated' : 'Not evaluated'} />
      </td>
      <td>
        {exec.executed ? (
          <StatusPill status="EVALUATED" label="Executed" />
        ) : (
          <StatusPill status="NOT_EVALUATED" label="Recommendation only" />
        )}
      </td>
      <td className={`rx-cell--num rx-cell--${toneForDelta(exec.latestReturn)}`}>
        {exec.latestReturn !== null ? formatSignedPercent(exec.latestReturn, { fallback: '—' }) : '—'}
      </td>
      <td>
        <StatusPill
          status={outcome?.outcomeStatus ?? 'Unavailable'}
          label={outcome?.outcomeStatus ?? 'Unavailable'}
          tone={outcomeTone(outcome?.outcomeStatus)}
        />
      </td>
      <td className="rx-cell--muted">
        {outcome?.latestCompletedHorizon
          ? `${outcome.latestCompletedHorizon}d`
          : outcome?.available ? 'Not evaluated' : 'Unavailable'}
      </td>
      <td>
        <StatusPill
          status={outcome?.latestResult ?? 'Unavailable'}
          label={outcome?.latestResult ?? 'Unavailable'}
          tone={outcomeTone(outcome?.latestResult)}
        />
      </td>
      <td className={`rx-cell--num rx-cell--${toneForDelta(outcome?.latestRawReturn)}`}>
        {outcome?.latestRawReturn !== null && outcome?.latestRawReturn !== undefined
          ? formatSignedPercent(outcome.latestRawReturn, { fallback: 'Unavailable' })
          : 'Unavailable'}
      </td>
      <td>
        <HorizonEvidenceBadges badges={outcome?.horizonBadges} compact />
      </td>
      <LearningCells learning={row.learningIntelligence} />
    </tr>
  )
})

function LearningCells({ learning }) {
  return (
    <>
      <td className="rx-cell--num">
        {learning?.committeeHistoricalAccuracy !== null && learning?.committeeHistoricalAccuracy !== undefined
          ? formatPercent(learning.committeeHistoricalAccuracy, { fallback: 'Unavailable' })
          : 'Unavailable'}
      </td>
      <td className="rx-cell--num">
        {learning?.engineHistoricalAccuracy !== null && learning?.engineHistoricalAccuracy !== undefined
          ? formatPercent(learning.engineHistoricalAccuracy, { fallback: 'Unavailable' })
          : 'Unavailable'}
      </td>
      <td className="rx-cell--num">
        {learning?.calibrationGap !== null && learning?.calibrationGap !== undefined
          ? formatSignedPercent(learning.calibrationGap, { fallback: 'Unavailable' })
          : 'Unavailable'}
      </td>
      <td className="rx-cell--num">
        {learning?.evaluationMaturity !== null && learning?.evaluationMaturity !== undefined
          ? formatPercent(learning.evaluationMaturity, { fallback: 'Unavailable' })
          : 'Unavailable'}
      </td>
      <td>{learning?.recommendationMaturity ?? 'Unavailable'}</td>
      <td className="rx-cell--num">
        {learning?.completionRate !== null && learning?.completionRate !== undefined
          ? formatPercent(learning.completionRate, { fallback: 'Unavailable' })
          : 'Unavailable'}
      </td>
    </>
  )
}

function RecommendationExplorer() {
  return (
    <DashboardDataProvider>
      <ExplorerBody />
    </DashboardDataProvider>
  )
}

export default RecommendationExplorer
