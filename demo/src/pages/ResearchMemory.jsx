import { memo, useCallback, useMemo, useState } from 'react'
import Panel from '../components/ui/Panel'
import StatusPill from '../components/ui/StatusPill'
import { LoadingState, ErrorState, EmptyState } from '../components/ui/States'
import InstitutionalReportDrawer from '../components/mission/InstitutionalReportDrawer'
import {
  HorizonEvidenceBadges,
  OutcomeSourceNotice,
} from '../components/outcomes/OutcomeEvidence'
import { DashboardDataProvider } from '../context/DashboardDataProvider'
import { useAsyncResource } from '../services/useAsyncResource'
import {
  getRecommendationHistory,
  getRecommendationIntelligenceRecords,
  getLearningCenter,
} from '../services/api'
import { dayOf, formatClock } from '../services/paperFundOps'
import { formatConfidence, formatPercent, formatSignedPercent } from '../services/formatters'
import {
  actionTone,
  buildRecommendationRows,
  buildTimeline,
  changeTone,
  computeTrendSummary,
  filterTimeline,
  tickersWithHistory,
  toCardModel,
} from '../services/researchMemory'
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

// Shared cache key with the Recommendation Explorer: both views read the same
// GET /recommendations/history payload, so opening this page after the Explorer
// (or vice-versa) issues no second request within the resource TTL.
const HISTORY_KEY = 'recommendations/history'

// Cap timeline DOM nodes so a ticker with thousands of cycles never renders them
// all at once. Filtering + trend stats still run over the full history.
const VISIBLE_LIMIT = 300

// Signed percentage-point delta for confidence/agreement badges. These are
// point differences between two stored percentages, not a percentage of a value.
function signedPts(value) {
  if (value === null || value === undefined) return null
  const num = Number(value)
  if (Number.isNaN(num)) return null
  const rounded = Math.round(num)
  return `${rounded > 0 ? '+' : ''}${rounded} pts`
}

// Research Memory — how ATLAS's opinion on a ticker evolved over time. One
// history fetch feeds the ticker rail, the event timeline and the trend
// summary; clicking an event reuses the Institutional Report drawer.
function ResearchMemoryBody() {
  const { data: payload, isLoading, error } = useAsyncResource(HISTORY_KEY, () =>
    getRecommendationHistory(500),
  )
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

  const [selectedTicker, setSelectedTicker] = useState(null)
  const [search, setSearch] = useState('')
  const [from, setFrom] = useState('')
  const [to, setTo] = useState('')
  const [selectedCard, setSelectedCard] = useState(null)

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
  const tickers = useMemo(() => tickersWithHistory(rows), [rows])

  // Fall back to the most active ticker until the user picks one, without an
  // effect (keeps render pure and avoids a flash of empty state).
  const activeTicker =
    selectedTicker && tickers.some((t) => t.ticker === selectedTicker)
      ? selectedTicker
      : tickers[0]?.ticker ?? null

  const fullTimeline = useMemo(() => buildTimeline(rows, activeTicker), [rows, activeTicker])
  const visibleTimeline = useMemo(
    () => filterTimeline(fullTimeline, { from, to }),
    [fullTimeline, from, to],
  )
  const summary = useMemo(() => computeTrendSummary(visibleTimeline), [visibleTimeline])

  const filteredTickers = useMemo(() => {
    const needle = search.trim().toUpperCase()
    if (!needle) return tickers
    return tickers.filter((t) => t.ticker.toUpperCase().includes(needle))
  }, [tickers, search])

  // Stable callbacks: memoized child rows keep the same props, so opening the
  // drawer (a selectedCard change) never re-renders the timeline list.
  const openReport = useCallback((card) => setSelectedCard(card), [])
  const closeReport = useCallback(() => setSelectedCard(null), [])
  const pickTicker = useCallback((ticker) => {
    setSelectedTicker(ticker)
    setSelectedCard(null)
  }, [])

  if (isLoading && !payload) {
    return <LoadingState label="Loading research memory…" />
  }
  if (error && !payload) {
    return <ErrorState message={error.message} />
  }

  const hasAny = rows.length > 0

  if (!hasAny) {
    return (
      <div className="dv2-page rm-page">
        <Panel eyebrow="Research Memory" title="Timeline">
          <EmptyState
            title="No research history yet"
            message="ATLAS builds this timeline automatically as autonomous research cycles run. Once the committee records recommendations for a ticker, every verdict — with its confidence, agreement and the evolution between reports — appears here. Nothing is placeholdered."
          />
        </Panel>
      </div>
    )
  }

  return (
    <div className="dv2-page rm-page">
      <div className="rm-grid">
        <aside className="rm-rail">
          <Panel eyebrow="Coverage" title="Tickers">
            <div className="rm-rail__controls">
              <label className="rm-field">
                <span className="rm-field__label">Search</span>
                <input
                  className="rm-input"
                  type="search"
                  inputMode="text"
                  placeholder="Filter tickers…"
                  value={search}
                  onChange={(event) => setSearch(event.target.value)}
                />
              </label>
              <div className="rm-daterange">
                <label className="rm-field">
                  <span className="rm-field__label">From</span>
                  <input
                    className="rm-input"
                    type="date"
                    value={from}
                    onChange={(event) => setFrom(event.target.value)}
                  />
                </label>
                <label className="rm-field">
                  <span className="rm-field__label">To</span>
                  <input
                    className="rm-input"
                    type="date"
                    value={to}
                    onChange={(event) => setTo(event.target.value)}
                  />
                </label>
              </div>
            </div>
            <TickerList
              tickers={filteredTickers}
              activeTicker={activeTicker}
              onPick={pickTicker}
            />
          </Panel>
        </aside>

        <section className="rm-center">
          <Panel
            eyebrow="Evolution"
            title={activeTicker ? `${activeTicker} Timeline` : 'Timeline'}
            action={
              <span className="dv3-timestamp">
                {visibleTimeline.length === fullTimeline.length
                  ? `${fullTimeline.length} event${fullTimeline.length === 1 ? '' : 's'}`
                  : `${visibleTimeline.length} of ${fullTimeline.length} events`}
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
                  ? 'Learning Intelligence enrichment is unavailable.'
                  : learningMeta.warning}
                {learningMeta.truncated
                  ? ` Analyzed ${learningMeta.analyzedRowCount} of ${learningMeta.sourceTotalRowCount} source rows.`
                  : ''}
              </div>
            ) : null}
            <TimelineList events={visibleTimeline} onSelect={openReport} />
          </Panel>
        </section>

        <aside className="rm-side">
          <Panel eyebrow="Trend Summary" title={activeTicker ?? '—'}>
            <TrendSummary summary={summary} />
          </Panel>
        </aside>
      </div>

      <InstitutionalReportDrawer card={selectedCard} onClose={closeReport} />
    </div>
  )
}

const TickerList = memo(function TickerList({ tickers, activeTicker, onPick }) {
  if (tickers.length === 0) {
    return <p className="rm-rail__empty">No tickers match that search.</p>
  }
  return (
    <ul className="rm-tickers" role="listbox" aria-label="Tickers with research history">
      {tickers.slice(0, VISIBLE_LIMIT).map((item) => {
        const active = item.ticker === activeTicker
        return (
          <li key={item.ticker}>
            <button
              type="button"
              className={`rm-ticker${active ? ' is-active' : ''}`}
              role="option"
              aria-selected={active}
              onClick={() => onPick(item.ticker)}
            >
              <span className="rm-ticker__sym">{item.ticker}</span>
              <span className="rm-ticker__meta">
                <span className="rm-ticker__count">{item.count}</span>
                {item.lastAt ? <span className="rm-ticker__date">{dayOf(item.lastAt)}</span> : null}
              </span>
            </button>
          </li>
        )
      })}
    </ul>
  )
})

const TimelineList = memo(function TimelineList({ events, onSelect }) {
  if (events.length === 0) {
    return (
      <EmptyState
        title="No events in range"
        message="No recommendations for this ticker fall inside the selected date range. Widen the From/To dates to see more of its history."
      />
    )
  }
  const shown = events.slice(0, VISIBLE_LIMIT)
  return (
    <div className="rm-timeline">
      {shown.map((event) => (
        <TimelineEvent key={event.id} event={event} onSelect={onSelect} />
      ))}
      {events.length > VISIBLE_LIMIT ? (
        <p className="rm-timeline__more">
          Showing the {VISIBLE_LIMIT} most recent of {events.length} events. Narrow the date range to
          reach the rest.
        </p>
      ) : null}
    </div>
  )
})

const TimelineEvent = memo(function TimelineEvent({ event, onSelect }) {
  const tone = actionTone(event.action)
  const outcome = event.outcomeEvidence
  const learning = event.learningIntelligence
  const badges = []
  if (event.isFirst) {
    badges.push({ key: 'first', label: 'Initial coverage', tone: 'neutral' })
  }
  if (event.actionChanged) {
    badges.push({
      key: 'action',
      label: `${event.previousBucket} → ${event.bucket}`,
      tone: changeTone(event.bucket),
    })
  }
  if (event.confidenceDelta !== null && Math.round(event.confidenceDelta) !== 0) {
    badges.push({
      key: 'conf',
      label: `Confidence ${signedPts(event.confidenceDelta)}`,
      tone: event.confidenceDelta > 0 ? 'positive' : 'negative',
    })
  }
  if (event.agreementDelta !== null && Math.round(event.agreementDelta) !== 0) {
    badges.push({
      key: 'agr',
      label: `Agreement ${signedPts(event.agreementDelta)}`,
      tone: event.agreementDelta > 0 ? 'positive' : 'negative',
    })
  }

  return (
    <article
      className="rm-event"
      tabIndex={0}
      role="button"
      aria-label={`Open institutional report for ${event.ticker} on ${dayOf(event.evaluatedAt)}`}
      onClick={() => onSelect(toCardModel(event))}
      onKeyDown={(keyEvent) => {
        if (keyEvent.key === 'Enter' || keyEvent.key === ' ') {
          keyEvent.preventDefault()
          onSelect(toCardModel(event))
        }
      }}
    >
      <div className="rm-event__rail" aria-hidden="true">
        <span className={`rm-event__dot rm-event__dot--${tone}`} />
      </div>
      <div className="rm-event__body">
        <div className="rm-event__head">
          <span className="rm-event__date">{event.evaluatedAt ? dayOf(event.evaluatedAt) : '—'}</span>
          <span className={`dv3-verdict dv3-verdict--${tone}`}>{event.action ?? '—'}</span>
        </div>
        <div className="rm-event__metrics">
          <Metric label="Confidence" value={formatConfidence(event.confidence, { fallback: '—' })} />
          <Metric label="Agreement" value={formatPercent(event.agreementPct, { fallback: '—' })} />
          <Metric label="Strength" value={event.strength ?? '—'} />
          <Metric
            label="Latest completed horizon"
            value={outcome?.latestCompletedHorizon
              ? `${outcome.latestCompletedHorizon}d`
              : outcome?.available ? 'Not evaluated' : 'Unavailable'}
          />
          <span className="rm-metric">
            <span className="rm-metric__label">Latest correctness</span>
            <StatusPill
              status={outcome?.latestResult ?? 'Unavailable'}
              label={outcome?.latestResult ?? 'Unavailable'}
              tone={outcomeTone(outcome?.latestResult)}
            />
          </span>
          <Metric
            label="Raw return"
            value={outcome?.latestRawReturn !== null && outcome?.latestRawReturn !== undefined
              ? formatSignedPercent(outcome.latestRawReturn, { fallback: 'Unavailable' })
              : 'Unavailable'}
          />
          <Metric
            label="Outcome evaluated"
            value={outcome?.latestEvaluationAt ? formatClock(outcome.latestEvaluationAt) : 'Unavailable'}
          />
          <Metric
            label="Committee historical accuracy"
            value={learning?.committeeHistoricalAccuracy !== null && learning?.committeeHistoricalAccuracy !== undefined
              ? formatPercent(learning.committeeHistoricalAccuracy, { fallback: 'Unavailable' })
              : 'Unavailable'}
          />
          <Metric
            label="Primary engine accuracy"
            value={learning?.engineHistoricalAccuracy !== null && learning?.engineHistoricalAccuracy !== undefined
              ? formatPercent(learning.engineHistoricalAccuracy, { fallback: 'Unavailable' })
              : 'Unavailable'}
          />
          <Metric
            label="Calibration gap"
            value={learning?.calibrationGap !== null && learning?.calibrationGap !== undefined
              ? formatSignedPercent(learning.calibrationGap, { fallback: 'Unavailable' })
              : 'Unavailable'}
          />
          <Metric label="Recommendation maturity" value={learning?.recommendationMaturity ?? 'Unavailable'} />
          <Metric
            label="Outcome maturity"
            value={learning?.outcomeMaturity !== null && learning?.outcomeMaturity !== undefined
              ? formatPercent(learning.outcomeMaturity, { fallback: 'Unavailable' })
              : 'Unavailable'}
          />
          <Metric
            label="Evaluation coverage"
            value={learning?.evaluationCoverage !== null && learning?.evaluationCoverage !== undefined
              ? formatPercent(learning.evaluationCoverage, { fallback: 'Unavailable' })
              : 'Unavailable'}
          />
        </div>
        <p className="rm-event__summary">{event.summary || '—'}</p>
        {badges.length ? (
          <div className="rm-event__badges">
            {badges.map((badge) => (
              <span key={badge.key} className={`rm-badge rm-badge--${badge.tone}`}>
                {badge.label}
              </span>
            ))}
          </div>
        ) : null}
        <HorizonEvidenceBadges badges={outcome?.horizonBadges} compact />
      </div>
    </article>
  )
})

function Metric({ label, value }) {
  return (
    <span className="rm-metric">
      <span className="rm-metric__label">{label}</span>
      <strong className="rm-metric__value">{value}</strong>
    </span>
  )
}

function TrendSummary({ summary }) {
  if (!summary) {
    return (
      <EmptyState
        title="No trend yet"
        message="Select a ticker with recorded history to see how its recommendation, confidence and committee agreement evolved."
      />
    )
  }

  const dateOrDash = (value) => (value ? dayOf(value) : '—')
  const stats = [
    { label: 'Total recommendations', value: String(summary.total) },
    { label: 'Current', value: summary.currentAction ?? '—', tone: toneFor(summary.currentBucket) },
    { label: 'Previous', value: summary.previousAction ?? '—', tone: toneFor(summary.previousBucket) },
    { label: 'Recommendation changes', value: String(summary.recommendationChanges) },
    { label: 'Average confidence', value: formatPercent(summary.avgConfidence, { fallback: '—' }) },
    {
      label: 'Highest confidence',
      value: summary.highestConfidence ? formatPercent(summary.highestConfidence.value, { fallback: '—' }) : '—',
      hint: summary.highestConfidence ? dateOrDash(summary.highestConfidence.at) : null,
    },
    {
      label: 'Lowest confidence',
      value: summary.lowestConfidence ? formatPercent(summary.lowestConfidence.value, { fallback: '—' }) : '—',
      hint: summary.lowestConfidence ? dateOrDash(summary.lowestConfidence.at) : null,
    },
    {
      label: 'Largest confidence increase',
      value: summary.largestIncrease ? signedPts(summary.largestIncrease.delta) : '—',
      hint: summary.largestIncrease ? dateOrDash(summary.largestIncrease.at) : null,
      tone: summary.largestIncrease ? 'positive' : undefined,
    },
    {
      label: 'Largest confidence decrease',
      value: summary.largestDecrease ? signedPts(summary.largestDecrease.delta) : '—',
      hint: summary.largestDecrease ? dateOrDash(summary.largestDecrease.at) : null,
      tone: summary.largestDecrease ? 'negative' : undefined,
    },
    { label: 'BUY', value: String(summary.buy), tone: 'positive' },
    { label: 'HOLD', value: String(summary.hold), tone: 'neutral' },
    { label: 'AVOID', value: String(summary.avoid), tone: 'negative' },
    { label: 'First recommendation', value: summary.firstAction ?? '—', hint: dateOrDash(summary.firstAt) },
    { label: 'Most recent', value: summary.mostRecentAction ?? '—', hint: dateOrDash(summary.mostRecentAt) },
  ]

  return (
    <dl className="rm-summary">
      {stats.map((stat) => (
        <div className="rm-summary__row" key={stat.label}>
          <dt className="rm-summary__label">{stat.label}</dt>
          <dd className={`rm-summary__value${stat.tone ? ` rm-summary__value--${stat.tone}` : ''}`}>
            {stat.value}
            {stat.hint ? <span className="rm-summary__hint">{stat.hint}</span> : null}
          </dd>
        </div>
      ))}
    </dl>
  )
}

function toneFor(bucket) {
  if (bucket === 'BUY') return 'positive'
  if (bucket === 'AVOID') return 'negative'
  if (bucket === 'HOLD') return 'neutral'
  return undefined
}

function ResearchMemory() {
  return (
    <DashboardDataProvider>
      <ResearchMemoryBody />
    </DashboardDataProvider>
  )
}

export default ResearchMemory
