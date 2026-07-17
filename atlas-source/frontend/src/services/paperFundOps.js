// Read-only selectors that turn the /dashboard/v2 payload into the live
// paper-fund operating picture. Pure functions only: they never fabricate
// values, they only project fields that already exist in the payload
// (paper_fund status, scheduler, market, risk decisions, activity log).

// ---------------------------------------------------------------------------
// Time helpers
// ---------------------------------------------------------------------------

// Local calendar day as YYYY-MM-DD. Backend timestamps are naive
// datetime.now().isoformat() strings, so comparing the date prefix against the
// local day is honest on a single-host deployment.
export function todayKey(now = new Date()) {
  const year = now.getFullYear()
  const month = String(now.getMonth() + 1).padStart(2, '0')
  const day = String(now.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

export function dayOf(timestamp) {
  if (!timestamp) return ''
  return String(timestamp).slice(0, 10)
}

function isToday(timestamp, key) {
  return dayOf(timestamp) === key
}

export function formatClock(timestamp) {
  if (!timestamp) return '—'
  return String(timestamp).slice(0, 19).replace('T', ' ')
}

// ---------------------------------------------------------------------------
// Today's trade activity
// ---------------------------------------------------------------------------

// Counts today's simulated fills (paper_fund.virtual_orders) and today's risk
// verdicts (risk.decisions). Approved/rejected come from the risk gate, which
// is the authoritative APPROVED/REJECTED record; simulated trades come from the
// orders that were actually filled.
export function deriveTodayTrades(fund, risk, key = todayKey()) {
  const orders = Array.isArray(fund?.virtual_orders) ? fund.virtual_orders : []
  const decisions = Array.isArray(risk?.decisions) ? risk.decisions : []

  const simulated = orders.filter((order) =>
    isToday(order?.filled_at ?? order?.created_at, key),
  ).length

  let approved = 0
  let rejected = 0
  for (const decision of decisions) {
    if (!isToday(decision?.created_at, key)) continue
    const verdict = String(decision?.verdict ?? '').toUpperCase()
    if (verdict === 'APPROVED') approved += 1
    else if (verdict === 'REJECTED') rejected += 1
  }

  return { simulated, approved, rejected, hasRiskData: decisions.length > 0 }
}

// ---------------------------------------------------------------------------
// Latest risk rejection
// ---------------------------------------------------------------------------

// Most recent REJECTED risk decision plus the human-readable reasons taken from
// its stored checks. Returns null when nothing has been rejected.
export function latestRiskRejection(risk) {
  const decisions = Array.isArray(risk?.decisions) ? risk.decisions : []
  const rejected = decisions.find(
    (decision) => String(decision?.verdict ?? '').toUpperCase() === 'REJECTED',
  )
  if (!rejected) return null

  const checks = Array.isArray(rejected.checks)
    ? rejected.checks
    : Array.isArray(rejected.checks?.checks)
      ? [...rejected.checks.checks, ...(rejected.checks?.rejections ?? [])]
      : Array.isArray(rejected.checks?.rejections)
        ? rejected.checks.rejections
      : []
  const reasons = checks
    .filter((check) => String(check?.status ?? '').toUpperCase() === 'REJECTED')
    .map((check) => check?.reason)
    .filter(Boolean)

  return {
    symbol: rejected.symbol,
    side: rejected.side,
    quantity: rejected.quantity,
    at: rejected.created_at,
    reasons,
  }
}

// ---------------------------------------------------------------------------
// Latest learning summary
// ---------------------------------------------------------------------------

export function latestLearning(fund) {
  const log = Array.isArray(fund?.learning_log) ? fund.learning_log : []
  const latest = log[0]
  if (!latest) return null
  return {
    lesson: latest.lesson,
    at: latest.at,
    cycleId: latest.cycle_id,
    summary: latest.details?.learning_summary ?? null,
  }
}

// ---------------------------------------------------------------------------
// Automated pipeline meter
// ---------------------------------------------------------------------------

// Fund-cycle stages derived from per-cycle activity markers. The scheduler
// and the research stages live upstream of the fund cycle and are composed
// separately in deriveFullPipeline from /dashboard/v2's scheduler and
// research_cycle sections.
export const PIPELINE_STAGES = [
  { key: 'market_data', label: 'Market Data', marker: 'PRICES_REFRESHED' },
  { key: 'construction', label: 'Portfolio Construction', marker: 'CONSTRUCTION_BUILT' },
  { key: 'risk_gate', label: 'Risk Gate', marker: 'CORRELATION_EVALUATED' },
  { key: 'paper_orders', label: 'Paper Orders', marker: 'ORDERS_FILLED' },
  { key: 'accounting', label: 'Accounting', marker: 'PORTFOLIO_UPDATED' },
  { key: 'learning', label: 'Learning', marker: 'ANALYTICS_UPDATED' },
]

export const STAGE_STATUS = {
  COMPLETE: 'COMPLETE',
  WAITING: 'WAITING',
  SKIPPED: 'SKIPPED',
  ERROR: 'ERROR',
  NOT_EVALUATED: 'NOT_EVALUATED',
}

// Identify the newest cycle in the activity log and collect that cycle's
// events. Activity arrives newest-first; lifecycle events (FUND_STARTED, etc.)
// carry a null cycle_id and are ignored for cycle detection.
function latestCycleEvents(activityLog) {
  const log = Array.isArray(activityLog) ? activityLog : []
  const anchor = log.find((entry) => entry?.cycle_id)
  if (!anchor) return { cycleId: null, events: [] }
  const cycleId = anchor.cycle_id
  const events = log.filter((entry) => entry?.cycle_id === cycleId)
  return { cycleId, events }
}

// Derive each pipeline stage's status for the most recent cycle. This reads
// only the activity markers the paper-fund engine already writes per cycle:
// a present marker means the stage COMPLETEd; a CYCLE_FAILED with a missing
// marker means the failing stage ERRORed and everything after it was never
// reached; a completed cycle missing an optional marker (no rebalancing) is
// SKIPPED. When no cycle has run, stages are NOT_EVALUATED and the scheduler is
// WAITING if the fund is armed.
function toMs(timestamp) {
  if (!timestamp) return null
  const value = new Date(timestamp).getTime()
  return Number.isNaN(value) ? null : value
}

export function derivePipeline(fund) {
  const { cycleId, events } = latestCycleEvents(fund?.activity_log)
  const present = new Set(events.map((entry) => entry.activity_type))
  const failed = present.has('CYCLE_FAILED')
  const completed = present.has('CYCLE_COMPLETED')
  const inProgress = cycleId && !completed && !failed

  const fundStatus = String(fund?.fund_status ?? 'OFF').toUpperCase()
  const armed = fundStatus === 'READY' || fundStatus === 'RUNNING'

  // Marker timestamps: `at` per stage plus duration since the previous
  // recorded marker in the cycle (CYCLE_STARTED anchors the first stage).
  const markerAt = {}
  for (const entry of events) {
    if (entry.activity_type && entry.at) markerAt[entry.activity_type] = entry.at
  }
  const sequence = ['CYCLE_STARTED', ...PIPELINE_STAGES.map((stage) => stage.marker)]
  const durationOf = (marker) => {
    const index = sequence.indexOf(marker)
    const end = toMs(markerAt[marker])
    for (let i = index - 1; i >= 0; i -= 1) {
      const start = toMs(markerAt[sequence[i]])
      if (start !== null && end !== null) {
        return Math.max(0, Math.round((end - start) / 100) / 10)
      }
    }
    return null
  }

  // Orders-filled marker is always logged; distinguish a real fill from a
  // no-op rebalance so Paper Orders can report SKIPPED honestly.
  const ordersEvent = events.find((entry) => entry.activity_type === 'ORDERS_FILLED')
  const ordersFilled = Number(ordersEvent?.details?.orders ?? 0) > 0

  const { S } = { S: STAGE_STATUS }
  let boundaryConsumed = false // first not-yet-complete stage owns WAITING/ERROR

  const stages = PIPELINE_STAGES.map((stage) => {
    const hasMarker = present.has(stage.marker)

    if (hasMarker) {
      const timing = {
        at: markerAt[stage.marker] ?? null,
        durationSeconds: durationOf(stage.marker),
      }
      if (stage.key === 'paper_orders' && !ordersFilled) {
        return { ...stage, ...timing, status: S.SKIPPED, detail: 'No rebalancing needed' }
      }
      return { ...stage, ...timing, status: S.COMPLETE }
    }

    if (!cycleId) {
      // No cycle has ever run in the loaded window.
      if (stage.key === 'market_data') {
        return armed
          ? { ...stage, status: S.WAITING, detail: 'Awaiting next scheduled cycle' }
          : { ...stage, status: S.NOT_EVALUATED, detail: 'Fund not running' }
      }
      return { ...stage, status: S.NOT_EVALUATED }
    }

    // Cycle exists but this stage's marker is absent.
    if (!boundaryConsumed) {
      boundaryConsumed = true
      if (failed) return { ...stage, status: S.ERROR, detail: fund?.last_error || 'Cycle failed at this stage' }
      if (inProgress) return { ...stage, status: S.WAITING, detail: 'In progress' }
      return { ...stage, status: S.SKIPPED }
    }
    if (failed || inProgress) return { ...stage, status: S.NOT_EVALUATED }
    return { ...stage, status: S.SKIPPED }
  })

  return { cycleId, failed, completed, inProgress, stages }
}

// ---------------------------------------------------------------------------
// Full autonomous pipeline (scheduler + research + fund cycle)
// ---------------------------------------------------------------------------

function schedulerStage(scheduler) {
  if (scheduler?.status !== 'EVALUATED') {
    return {
      key: 'scheduler',
      label: 'Scheduler',
      status: STAGE_STATUS.NOT_EVALUATED,
      detail: 'Scheduler status unavailable',
    }
  }
  if (scheduler.running) {
    return {
      key: 'scheduler',
      label: 'Scheduler',
      status: STAGE_STATUS.COMPLETE,
      at: scheduler.last_tick_at ?? null,
      detail: scheduler.tick_count
        ? `${scheduler.tick_count} tick${scheduler.tick_count === 1 ? '' : 's'}`
        : 'Loop running',
    }
  }
  if (scheduler.enabled) {
    return {
      key: 'scheduler',
      label: 'Scheduler',
      status: STAGE_STATUS.WAITING,
      detail: 'Enabled — loop not running yet',
    }
  }
  return {
    key: 'scheduler',
    label: 'Scheduler',
    status: STAGE_STATUS.NOT_EVALUATED,
    detail: 'Disabled (ATLAS_SCHEDULER_ENABLED)',
  }
}

function researchDueStage(research) {
  const base = { key: 'research_due', label: 'Research Due Check' }
  if (!research || typeof research !== 'object' || research.status === 'Unavailable') {
    return { ...base, status: STAGE_STATUS.NOT_EVALUATED, detail: 'Research view unavailable' }
  }
  if (!research.enabled) {
    return {
      ...base,
      status: STAGE_STATUS.NOT_EVALUATED,
      detail: 'Autonomous research disabled (AUTO_RESEARCH_ENABLED)',
    }
  }
  if (research.research_due === true) {
    return {
      ...base,
      status: STAGE_STATUS.WAITING,
      detail: 'Research due — awaiting next scheduler tick',
    }
  }
  if (research.research_due === false) {
    return {
      ...base,
      status: STAGE_STATUS.COMPLETE,
      at: research.last_recommendation_run_time ?? null,
      detail: 'Recommendations are fresh',
    }
  }
  return { ...base, status: STAGE_STATUS.NOT_EVALUATED, detail: 'Due-ness unavailable' }
}

function researchStage(research, stageKey, key, label) {
  const base = { key, label }
  const recorded = Array.isArray(research?.stages)
    ? research.stages.find((stage) => stage.stage === stageKey)
    : null
  if (!recorded) {
    return {
      ...base,
      status: STAGE_STATUS.NOT_EVALUATED,
      detail: 'Research pipeline data unavailable',
    }
  }
  if (recorded.status === 'COMPLETED') {
    const details = recorded.details ?? {}
    const count = stageKey === 'research_generation'
      ? details.recommendation_count
      : Array.isArray(details.evaluations) ? details.evaluations.length : null
    return {
      ...base,
      status: STAGE_STATUS.COMPLETE,
      at: recorded.at ?? null,
      durationSeconds: recorded.duration_seconds ?? null,
      detail: count !== null && count !== undefined
        ? `${count} record${count === 1 ? '' : 's'}`
        : null,
    }
  }
  return {
    ...base,
    status: STAGE_STATUS[recorded.status] ?? STAGE_STATUS.NOT_EVALUATED,
    detail: recorded.reason ?? null,
  }
}

// The full 10-stage autonomous pipeline: Scheduler → Research Due Check →
// Recommendation Generation → Investment Committee → the six fund-cycle
// stages. Composed entirely from /dashboard/v2 sections; statuses are never
// fabricated — anything unrecorded is NOT_EVALUATED with a reason.
export function deriveFullPipeline(data) {
  const fund = data?.paper_fund ?? {}
  const scheduler = data?.scheduler ?? {}
  const research = data?.research_cycle ?? {}
  const fundPipeline = derivePipeline(fund)

  return {
    ...fundPipeline,
    stages: [
      schedulerStage(scheduler),
      researchDueStage(research),
      researchStage(research, 'research_generation', 'recommendation_generation', 'Recommendation Generation'),
      researchStage(research, 'committee_evaluation', 'investment_committee', 'Investment Committee'),
      ...fundPipeline.stages,
    ],
  }
}

// Map a stage status to one of the shared dv2 tones.
export function stageTone(status) {
  switch (status) {
    case STAGE_STATUS.COMPLETE:
      return 'positive'
    case STAGE_STATUS.WAITING:
      return 'neutral'
    case STAGE_STATUS.ERROR:
      return 'negative'
    case STAGE_STATUS.SKIPPED:
    case STAGE_STATUS.NOT_EVALUATED:
    default:
      return 'muted'
  }
}

// ---------------------------------------------------------------------------
// Scheduler / market / fund status projection
// ---------------------------------------------------------------------------

export function schedulerLabel(scheduler) {
  if (scheduler?.status !== 'EVALUATED') return 'Unavailable'
  if (scheduler.running) return 'RUNNING'
  if (scheduler.enabled) return 'READY'
  return 'OFF'
}

export function marketLabel(market) {
  if (market?.status !== 'EVALUATED') return 'Unavailable'
  if (market.market_is_open) return 'Open'
  return market.market_session
    ? String(market.market_session).replace(/\b\w/g, (c) => c.toUpperCase())
    : 'Closed'
}

// ---------------------------------------------------------------------------
// Equity curve
// ---------------------------------------------------------------------------

// Chronological equity-curve rows. Prefers the backend-computed
// trading_history.equity_curve; falls back to the raw snapshot list
// (newest-first in the payload). Rows without a positive value are dropped —
// never invented.
export function equityCurveRows(fund) {
  const history = fund?.trading_history?.equity_curve
  const source = Array.isArray(history) && history.length > 0
    ? history.map((point) => ({
        at: point.date ?? point.as_of,
        value: Number(point.portfolio_value ?? 0),
        cash: Number(point.cash ?? 0),
      }))
    : (Array.isArray(fund?.snapshots) ? [...fund.snapshots] : [])
        .reverse()
        .map((snapshot) => ({
          at: snapshot.as_of ?? snapshot.date,
          value: Number(snapshot.portfolio_value ?? 0),
          cash: Number(snapshot.cash ?? 0),
        }))

  return source
    .filter((row) => row.value > 0)
    .map((row) => ({
      ...row,
      date: dayOf(row.at),
      time: String(row.at ?? '').slice(11, 16),
    }))
}

// ---------------------------------------------------------------------------
// Live trades (simulated fills)
// ---------------------------------------------------------------------------

// Newest-first simulated fills from virtual_orders, normalized for display.
export function liveTradeRows(fund, limit = 15) {
  const orders = Array.isArray(fund?.virtual_orders) ? fund.virtual_orders : []
  return orders.slice(0, limit).map((order) => ({
    id: order.order_id ?? `${order.ticker}-${order.filled_at ?? order.created_at}`,
    side: String(order.side ?? '').toUpperCase(),
    ticker: order.ticker ?? order.symbol,
    quantity: order.quantity,
    fillPrice: order.fill_price ?? order.price,
    at: order.filled_at ?? order.created_at,
    status: order.status ?? 'FILLED_SIMULATED',
    source: order.price_source,
  }))
}

// ---------------------------------------------------------------------------
// Ticker strip prices
// ---------------------------------------------------------------------------

// Last known validated prices per symbol: open positions carry the latest
// snapshot price; the newest learning entry carries the last cycle's full
// validated price map for the whole watchlist. Symbols with no recorded price
// are omitted (no fabricated quotes). plPercent exists only for held
// positions, measured against cost basis.
export function tickerRows(fund) {
  const positions = fund?.open_positions ?? {}
  const learningPrices = fund?.learning_log?.[0]?.details?.prices ?? {}
  const watchlist = Array.isArray(fund?.watchlist) ? fund.watchlist : []
  const symbols = [...new Set([
    ...watchlist,
    ...Object.keys(positions),
    ...Object.keys(learningPrices),
  ])].sort()

  return symbols
    .map((symbol) => {
      const position = positions[symbol]
      const price = position?.current_price ?? learningPrices[symbol]
      if (price === null || price === undefined) return null
      const basis = Number(position?.cost_basis ?? 0)
      const held = Boolean(position)
      const plPercent = held && basis > 0 && position?.current_price
        ? ((Number(price) - basis) / basis) * 100
        : null
      return { symbol, price: Number(price), plPercent, held }
    })
    .filter(Boolean)
}

// ---------------------------------------------------------------------------
// Live event stream (floating popups)
// ---------------------------------------------------------------------------

// Tones: 'profit' (green — executed buy / positive cycle), 'loss' (red — loss,
// risk block, failure), 'system' (blue — neutral lifecycle event). Every event
// comes from a stored record: virtual orders, snapshots, risk decisions, and
// the activity log. Nothing is synthesized.
export function deriveLiveEvents(fund, risk, limit = 30) {
  const events = []

  for (const order of Array.isArray(fund?.virtual_orders) ? fund.virtual_orders : []) {
    const side = String(order.side ?? '').toUpperCase()
    const price = Number(order.fill_price ?? order.price ?? 0)
    events.push({
      key: `order-${order.order_id ?? `${order.ticker}-${order.filled_at}`}`,
      at: order.filled_at ?? order.created_at,
      // A buy is an executed simulated trade (green); a sell's realized P/L is
      // not recorded per order, so it stays a neutral system event.
      tone: side === 'BUY' ? 'profit' : 'system',
      title: `${side} ${order.quantity} ${order.ticker ?? order.symbol}`,
      detail: `Simulated fill @ $${price.toLocaleString('en-US', { maximumFractionDigits: 2 })}`,
    })
  }

  for (const snapshot of Array.isArray(fund?.snapshots) ? fund.snapshots : []) {
    const daily = Number(snapshot.daily_return ?? 0)
    if (!snapshot.cycle_id || daily === 0) continue
    events.push({
      key: `snapshot-${snapshot.cycle_id}`,
      at: snapshot.as_of ?? snapshot.date,
      tone: daily > 0 ? 'profit' : 'loss',
      title: `${daily > 0 ? '+' : ''}${daily}% cycle return`,
      detail: `Paper portfolio $${Number(snapshot.portfolio_value ?? 0).toLocaleString('en-US', { maximumFractionDigits: 2 })}`,
    })
  }

  for (const decision of Array.isArray(risk?.decisions) ? risk.decisions : []) {
    if (String(decision.verdict ?? '').toUpperCase() !== 'REJECTED') continue
    events.push({
      key: `risk-${decision.decision_id}`,
      at: decision.created_at,
      tone: 'loss',
      title: `Risk gate blocked ${decision.side} ${decision.quantity} ${decision.symbol}`,
      detail: 'Order rejected by risk controls',
    })
  }

  const SYSTEM_TYPES = new Set([
    'CYCLE_STARTED', 'CYCLE_COMPLETED', 'FUND_STARTED',
    'FUND_PAUSED', 'FUND_RESUMED', 'FUND_STOPPED',
  ])
  for (const entry of Array.isArray(fund?.activity_log) ? fund.activity_log : []) {
    const type = entry?.activity_type
    if (type === 'CYCLE_FAILED') {
      events.push({
        key: `activity-${entry.at}-${type}`,
        at: entry.at,
        tone: 'loss',
        title: 'Cycle failed',
        detail: String(entry.message ?? '').slice(0, 140),
      })
    } else if (SYSTEM_TYPES.has(type)) {
      events.push({
        key: `activity-${entry.at}-${type}`,
        at: entry.at,
        tone: 'system',
        title: String(type).replace(/_/g, ' '),
        detail: String(entry.message ?? '').slice(0, 140),
      })
    }
  }

  return events
    .sort((a, b) => String(b.at ?? '').localeCompare(String(a.at ?? '')))
    .slice(0, limit)
}

// ---------------------------------------------------------------------------
// Next-cycle countdown
// ---------------------------------------------------------------------------

// Remaining time until the fund's next scheduled cycle. Returns null when no
// cycle is scheduled or the timestamp is unparseable.
export function cycleCountdown(nextUpdate, now = Date.now()) {
  if (!nextUpdate) return null
  const target = new Date(nextUpdate).getTime()
  if (Number.isNaN(target)) return null
  const ms = target - now
  const total = Math.max(0, Math.floor(ms / 1000))
  const hours = Math.floor(total / 3600)
  const minutes = Math.floor((total % 3600) / 60)
  const seconds = total % 60
  const pad = (value) => String(value).padStart(2, '0')
  return {
    ms,
    due: ms <= 0,
    label: hours > 0
      ? `${hours}:${pad(minutes)}:${pad(seconds)}`
      : `${pad(minutes)}:${pad(seconds)}`,
  }
}
