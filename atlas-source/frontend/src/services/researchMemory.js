// Read-only projection of GET /recommendations/history into the Research Memory
// timeline view model. Pure functions only. Everything here is derived from the
// same persisted committee-cycle rows the Recommendation Explorer consumes — we
// reuse buildRecommendationRows / actionBucket / actionTone / toCardModel from
// that module rather than re-deriving them, so both pages agree by construction.
//
// Nothing is fabricated: evolution badges and the trend summary are restatements
// of stored confidence/agreement/action facts and the deltas between them. No
// reasons or narrative are invented.

import {
  actionBucket,
  actionTone,
  buildRecommendationRows,
  toCardModel,
} from './recommendationExplorer'

export { actionBucket, actionTone, buildRecommendationRows, toCardModel }

// --- Ticker index --------------------------------------------------------
// Group the flat row set by ticker. Only tickers that actually carry recorded
// history appear (the left-rail selector shows nothing else).
export function indexByTicker(rows) {
  const list = Array.isArray(rows) ? rows : []
  const map = new Map()
  for (const row of list) {
    if (!row?.ticker) continue
    const key = row.ticker
    if (!map.has(key)) map.set(key, [])
    map.get(key).push(row)
  }
  return map
}

// Sorted directory of tickers that have history: most active first, then
// alphabetical. `lastAt` powers a recency hint in the selector.
export function tickersWithHistory(rows) {
  const map = indexByTicker(rows)
  const out = []
  for (const [ticker, tickerRows] of map) {
    let lastAt = null
    for (const row of tickerRows) {
      if (row.at !== null && (lastAt === null || row.at > lastAt)) lastAt = row.at
    }
    out.push({ ticker, count: tickerRows.length, lastAt })
  }
  out.sort((a, b) => b.count - a.count || a.ticker.localeCompare(b.ticker))
  return out
}

function confDelta(current, previous) {
  if (current === null || previous === null) return null
  return current - previous
}

// Tone for an action transition: a move to BUY reads positive, to AVOID
// negative, to HOLD neutral. Used to colour the evolution badge.
export function changeTone(toBucket) {
  if (toBucket === 'BUY') return 'positive'
  if (toBucket === 'AVOID') return 'negative'
  return 'neutral'
}

// Factual one-line summary of a single event — a restatement of stored metrics,
// never an invented rationale.
export function eventSummary(event) {
  const parts = []
  if (event.action) parts.push(String(event.action))
  if (event.confidencePct !== null) parts.push(`${Math.round(event.confidencePct)}% confidence`)
  if (event.agreementPct !== null) parts.push(`${Math.round(event.agreementPct)}% agreement`)
  if (event.strength) parts.push(String(event.strength))
  return parts.join(' · ')
}

// Build the chronological timeline for one ticker. Returned newest-first for
// display, but each event's evolution is computed against its immediately
// preceding (older) event so the deltas are true period-over-period changes.
export function buildTimeline(rows, ticker) {
  if (!ticker) return []
  const map = indexByTicker(rows)
  const tickerRows = map.get(ticker)
  if (!tickerRows || tickerRows.length === 0) return []

  // Oldest → newest for neighbour comparison.
  const chrono = [...tickerRows].sort((a, b) => (a.at ?? 0) - (b.at ?? 0))

  const events = chrono.map((row, index) => {
    const previous = index > 0 ? chrono[index - 1] : null
    const confidenceDelta = previous
      ? confDelta(row.confidencePct, previous.confidencePct)
      : null
    const agreementDelta = previous
      ? confDelta(row.agreementPct, previous.agreementPct)
      : null
    const actionChanged =
      previous !== null &&
      row.bucket !== null &&
      previous.bucket !== null &&
      row.bucket !== previous.bucket
    return {
      ...row,
      seq: index,
      isFirst: previous === null,
      previousBucket: previous ? previous.bucket : null,
      previousAction: previous ? previous.action : null,
      actionChanged,
      confidenceDelta,
      agreementDelta,
      summary: eventSummary(row),
    }
  })

  // Newest first for the vertical timeline.
  return events.reverse()
}

// Date-range filter over an already-built timeline (from/to are yyyy-mm-dd).
// Order is preserved.
export function filterTimeline(events, { from = '', to = '' } = {}) {
  const list = Array.isArray(events) ? events : []
  const fromMs = from ? Date.parse(`${from}T00:00:00`) : null
  const toMs = to ? Date.parse(`${to}T23:59:59`) : null
  if (fromMs === null && toMs === null) return list
  return list.filter((event) => {
    if (event.at === null) return false
    if (fromMs !== null && event.at < fromMs) return false
    if (toMs !== null && event.at > toMs) return false
    return true
  })
}

// Trend summary over the FULL (chronological) timeline for a ticker. Consumes
// the newest-first array buildTimeline returns and walks it in time order.
export function computeTrendSummary(events) {
  const list = Array.isArray(events) ? events : []
  if (list.length === 0) return null

  // buildTimeline returns newest-first; restore chronological order here.
  const chrono = [...list].reverse()
  const counts = { BUY: 0, HOLD: 0, AVOID: 0 }
  let confSum = 0
  let confCount = 0
  let highest = null
  let lowest = null
  let largestIncrease = null
  let largestDecrease = null
  let changes = 0

  chrono.forEach((event, index) => {
    if (event.bucket && counts[event.bucket] !== undefined) counts[event.bucket] += 1
    if (event.confidencePct !== null) {
      confSum += event.confidencePct
      confCount += 1
      if (highest === null || event.confidencePct > highest.confidencePct) highest = event
      if (lowest === null || event.confidencePct < lowest.confidencePct) lowest = event
    }
    if (index > 0) {
      const previous = chrono[index - 1]
      if (event.bucket && previous.bucket && event.bucket !== previous.bucket) changes += 1
      const delta = confDelta(event.confidencePct, previous.confidencePct)
      if (delta !== null) {
        if (delta > 0 && (largestIncrease === null || delta > largestIncrease.delta)) {
          largestIncrease = { delta, event, previous }
        }
        if (delta < 0 && (largestDecrease === null || delta < largestDecrease.delta)) {
          largestDecrease = { delta, event, previous }
        }
      }
    }
  })

  const first = chrono[0]
  const current = chrono[chrono.length - 1]
  const previous = chrono.length > 1 ? chrono[chrono.length - 2] : null

  return {
    total: chrono.length,
    currentAction: current.action,
    currentBucket: current.bucket,
    currentAt: current.evaluatedAt,
    previousAction: previous ? previous.action : null,
    previousBucket: previous ? previous.bucket : null,
    previousAt: previous ? previous.evaluatedAt : null,
    recommendationChanges: changes,
    avgConfidence: confCount ? confSum / confCount : null,
    highestConfidence: highest
      ? { value: highest.confidencePct, at: highest.evaluatedAt }
      : null,
    lowestConfidence: lowest
      ? { value: lowest.confidencePct, at: lowest.evaluatedAt }
      : null,
    largestIncrease: largestIncrease
      ? {
          delta: largestIncrease.delta,
          at: largestIncrease.event.evaluatedAt,
          fromAt: largestIncrease.previous.evaluatedAt,
        }
      : null,
    largestDecrease: largestDecrease
      ? {
          delta: largestDecrease.delta,
          at: largestDecrease.event.evaluatedAt,
          fromAt: largestDecrease.previous.evaluatedAt,
        }
      : null,
    buy: counts.BUY,
    hold: counts.HOLD,
    avoid: counts.AVOID,
    firstAction: first.action,
    firstAt: first.evaluatedAt,
    mostRecentAction: current.action,
    mostRecentAt: current.evaluatedAt,
  }
}
