// Read-only projection of GET /recommendations/history into the Recommendation
// Explorer view model. Pure functions only: every field is read straight from
// the persisted committee-cycle payload; nothing is fabricated. A recommendation
// the committee could not evaluate degrades to an honest NOT_EVALUATED status
// rather than inventing an action/score.
//
// The source is the committee_cycle_evaluations feed: an array of cycles, each
// carrying { cycle_id, run_id, evaluated_at, evaluations: [...] } where each
// evaluation is { ticker, status, action, strength, agreement_pct, confidence }.

import { actionTone } from './missionOps'

// Canonical action buckets used by the filter chips and statistics. AVOID and
// SELL share the bearish bucket; STRONG_* fold into their base action.
export const ACTION_BUCKETS = ['BUY', 'HOLD', 'AVOID']

export function actionBucket(action) {
  const key = String(action ?? '').toUpperCase()
  if (key === 'BUY' || key === 'STRONG_BUY') return 'BUY'
  if (key === 'HOLD' || key === 'NEUTRAL') return 'HOLD'
  if (key === 'AVOID' || key === 'SELL' || key === 'STRONG_SELL') return 'AVOID'
  return null
}

export { actionTone }

function numberOrNull(value) {
  if (value === null || value === undefined || value === '') return null
  const num = Number(value)
  return Number.isNaN(num) ? null : num
}

// Confidence may arrive as a 0-1 fraction or a 0-100 score; normalise to a
// 0-100 percentage for filtering, sorting and averaging (mirrors the shared
// formatConfidence rendering logic so the slider and the labels agree).
function confidencePercent(value) {
  const num = numberOrNull(value)
  if (num === null) return null
  return num <= 1 ? num * 100 : num
}

function timestamp(value) {
  if (!value) return null
  const ms = Date.parse(value)
  return Number.isNaN(ms) ? null : ms
}

// Flatten cycles → one row per (cycle, ticker) evaluation. Newest cycles come
// first from the backend; row ids are stable across renders.
export function buildRecommendationRows(cycles) {
  const list = Array.isArray(cycles) ? cycles : []
  const rows = []
  for (const cycle of list) {
    const evaluations = Array.isArray(cycle?.evaluations) ? cycle.evaluations : []
    const evaluatedAt = cycle?.evaluated_at ?? null
    const at = timestamp(evaluatedAt)
    evaluations.forEach((item, index) => {
      const ticker = item?.ticker ? String(item.ticker) : null
      if (!ticker) return
      const status = item?.status ?? 'NOT_EVALUATED'
      rows.push({
        id: `${cycle?.cycle_id ?? 'cycle'}:${ticker}:${index}`,
        ticker,
        action: item?.action ?? null,
        bucket: actionBucket(item?.action),
        strength: item?.strength ?? null,
        confidence: item?.confidence ?? null,
        confidencePct: confidencePercent(item?.confidence),
        agreementPct: numberOrNull(item?.agreement_pct),
        researchStatus: status,
        evaluated: Boolean(status) && status !== 'NOT_EVALUATED',
        // No per-recommendation provider exists at committee granularity; the
        // column stays honest ("—") until the backend records one.
        provider: item?.provider ?? cycle?.provider ?? null,
        evaluatedAt,
        at,
        cycleId: cycle?.cycle_id ?? null,
        runId: cycle?.run_id ?? null,
        // Newer history payloads may expose the exact id directly. Legacy
        // payloads remain supported and are matched through (run_id, ticker)
        // against Recommendation Intelligence records before outcomes attach.
        recommendationId: item?.recommendation_id ?? null,
      })
    })
  }
  return rows
}

// Live statistics computed over the full (unfiltered) row set — all real data.
export function computeStats(rows) {
  const list = Array.isArray(rows) ? rows : []
  const counts = { BUY: 0, HOLD: 0, AVOID: 0 }
  let confSum = 0
  let confCount = 0
  let agrSum = 0
  let agrCount = 0
  let newest = null
  let oldest = null

  for (const row of list) {
    if (row.bucket && counts[row.bucket] !== undefined) counts[row.bucket] += 1
    if (row.confidencePct !== null) {
      confSum += row.confidencePct
      confCount += 1
    }
    if (row.agreementPct !== null) {
      agrSum += row.agreementPct
      agrCount += 1
    }
    if (row.at !== null) {
      if (newest === null || row.at > newest.at) newest = row
      if (oldest === null || row.at < oldest.at) oldest = row
    }
  }

  return {
    total: list.length,
    buy: counts.BUY,
    hold: counts.HOLD,
    avoid: counts.AVOID,
    avgConfidence: confCount ? confSum / confCount : null,
    avgAgreement: agrCount ? agrSum / agrCount : null,
    newestAt: newest?.evaluatedAt ?? null,
    oldestAt: oldest?.evaluatedAt ?? null,
  }
}

export const DEFAULT_FILTERS = {
  ticker: '',
  actions: [], // empty = all buckets
  minConfidence: 0,
  from: '', // yyyy-mm-dd
  to: '', // yyyy-mm-dd
}

// Client-side filtering over the full row set (the backend exposes no
// pagination, so the Explorer keeps filtering local per the design brief).
export function filterRows(rows, filters = DEFAULT_FILTERS) {
  const list = Array.isArray(rows) ? rows : []
  const needle = String(filters.ticker ?? '').trim().toUpperCase()
  const actions = Array.isArray(filters.actions) ? filters.actions : []
  const min = numberOrNull(filters.minConfidence) ?? 0
  const fromMs = filters.from ? Date.parse(`${filters.from}T00:00:00`) : null
  const toMs = filters.to ? Date.parse(`${filters.to}T23:59:59`) : null

  return list.filter((row) => {
    if (needle && !row.ticker.toUpperCase().includes(needle)) return false
    if (actions.length && (!row.bucket || !actions.includes(row.bucket))) return false
    if (min > 0 && (row.confidencePct === null || row.confidencePct < min)) return false
    if (fromMs !== null && (row.at === null || row.at < fromMs)) return false
    if (toMs !== null && (row.at === null || row.at > toMs)) return false
    return true
  })
}

export const SORT_OPTIONS = [
  { key: 'newest', label: 'Newest' },
  { key: 'oldest', label: 'Oldest' },
  { key: 'confidence_desc', label: 'Highest confidence' },
  { key: 'confidence_asc', label: 'Lowest confidence' },
  { key: 'committee_accuracy_desc', label: 'Committee historical accuracy' },
  { key: 'engine_accuracy_desc', label: 'Engine historical accuracy' },
  { key: 'calibration_gap_desc', label: 'Calibration gap' },
  { key: 'evaluation_maturity_desc', label: 'Evaluation maturity' },
  { key: 'recommendation_maturity_desc', label: 'Recommendation maturity' },
  { key: 'completion_rate_desc', label: 'Outcome completion rate' },
]

export function sortRows(rows, sortKey = 'newest') {
  const list = Array.isArray(rows) ? [...rows] : []
  const byTime = (a, b) => (a.at ?? 0) - (b.at ?? 0)
  const byConf = (a, b) => (a.confidencePct ?? -1) - (b.confidencePct ?? -1)
  const byLearning = (field) => (a, b) => {
    const left = numberOrNull(a.learningIntelligence?.[field])
    const right = numberOrNull(b.learningIntelligence?.[field])
    if (left === null && right === null) return byTime(b, a)
    if (left === null) return 1
    if (right === null) return -1
    return right - left || byTime(b, a)
  }
  switch (sortKey) {
    case 'oldest':
      return list.sort(byTime)
    case 'confidence_desc':
      return list.sort((a, b) => byConf(b, a))
    case 'confidence_asc':
      return list.sort(byConf)
    case 'committee_accuracy_desc':
      return list.sort(byLearning('committeeHistoricalAccuracy'))
    case 'engine_accuracy_desc':
      return list.sort(byLearning('engineHistoricalAccuracy'))
    case 'calibration_gap_desc':
      return list.sort(byLearning('calibrationGap'))
    case 'evaluation_maturity_desc':
    case 'recommendation_maturity_desc':
      return list.sort(byLearning('evaluationMaturity'))
    case 'completion_rate_desc':
      return list.sort(byLearning('completionRate'))
    case 'newest':
    default:
      return list.sort((a, b) => byTime(b, a))
  }
}

// Map a table row to the exact card shape the Institutional Report drawer
// consumes, so the details panel is fully reused (no duplicate rendering).
export function toCardModel(row) {
  if (!row) return null
  return {
    ticker: row.ticker,
    action: row.action,
    confidence: row.confidence,
    agreementPct: row.agreementPct,
    strength: row.strength,
    recommendationId: row.recommendationId ?? null,
    outcomeEvidence: row.outcomeEvidence ?? null,
    learningIntelligence: row.learningIntelligence ?? null,
  }
}

// Paper-trade status for a ticker, derived from the shared /dashboard/v2
// paper-fund payload — the same signal the drawer uses. A real open position
// or recorded simulated order counts as "Executed"; otherwise it is a
// research recommendation only. Latest return is surfaced when the position
// carries an unrealized figure, else null.
export function executionStatus(paperFund, ticker) {
  const fund = paperFund ?? {}
  const position = (fund.open_positions ?? {})[ticker] ?? null
  const orders = (Array.isArray(fund.virtual_orders) ? fund.virtual_orders : []).filter(
    (order) => (order?.ticker ?? order?.symbol) === ticker,
  )
  const executed = Boolean(position) || orders.length > 0
  let latestReturn = null
  if (position) {
    const candidate =
      position.unrealized_return_pct ??
      position.return_pct ??
      position.unrealized_pnl_pct ??
      null
    latestReturn = numberOrNull(candidate)
  }
  return { executed, latestReturn }
}
