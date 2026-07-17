// Read-only selector for the Executive Briefing. Accepts the single
// /dashboard/v2 payload and returns ONE stable briefing view model. Pure: it
// never mutates the input and tolerates null / empty / malformed / partial
// payloads. It reuses the existing section selectors (portfolioIntel,
// missionOps, paperFundOps) instead of re-deriving them, so there is one source
// of truth per metric and no fabricated commentary.

import {
  committeeBoard,
} from './missionOps'
import {
  portfolioSummary,
  performanceAttribution,
  committeePerformance,
  learningStatus,
} from './portfolioIntel'
import {
  cycleCountdown,
  marketLabel,
  schedulerLabel,
  todayKey,
  dayOf,
} from './paperFundOps'
import { asArray, isEvaluated } from './formatters'

function num(value) {
  if (value === null || value === undefined || value === '') return null
  const parsed = Number(value)
  return Number.isNaN(parsed) ? null : parsed
}

export function greetingFor(now = new Date()) {
  const hour = now.getHours()
  if (hour < 12) return 'Good morning'
  if (hour < 18) return 'Good afternoon'
  return 'Good evening'
}

// ------------------------------------------------------------------- Header
function briefingHeader(data, now) {
  const operations = data?.operations ?? {}
  const mode = operations.operational_mode ?? {}
  return {
    greeting: greetingFor(now),
    date: now.toLocaleDateString(undefined, {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    }),
    mode: mode.mode ?? null,
    paperOnly: mode.paper_only !== false,
    lastRefresh: data?.generated_at ?? null,
  }
}

// -------------------------------------------------------- Section 1: Portfolio
function portfolioBrief(data, now) {
  const summary = portfolioSummary(data)
  const attribution = performanceAttribution(data)
  const portfolio = data?.portfolio ?? {}
  const snapshot = data?.paper_fund?.latest_snapshot ?? {}

  const cashReserve = portfolio.cash_reserve_status ?? {}
  const cashPercent = isEvaluated(cashReserve)
    ? num(cashReserve.cash_percent)
    : summary.portfolioValue && summary.cash !== null
      ? (summary.cash / summary.portfolioValue) * 100
      : null

  const updatedToday =
    summary.lastUpdate ? dayOf(summary.lastUpdate) === todayKey(now) : false

  return {
    available: summary.available,
    portfolioValue: summary.portfolioValue,
    totalReturn: summary.totalReturn,
    dailyReturn: num(snapshot.daily_return),
    realizedPl: summary.realizedPl,
    unrealizedPl: summary.unrealizedPl,
    cashPercent,
    openPositions: summary.openPositions,
    best: attribution.best,
    worst: attribution.worst,
    attributionAvailable: attribution.available,
    updatedToday,
    lastUpdate: summary.lastUpdate,
  }
}

// ---------------------------------------------------- Section 2: Market/runtime
function marketRuntime(data) {
  const market = data?.market ?? {}
  const scheduler = data?.scheduler ?? {}
  const fund = data?.paper_fund ?? {}

  const nextCycle = fund.next_update ?? null
  const countdown = nextCycle ? cycleCountdown(nextCycle) : null

  return {
    marketOpen: market.status === 'EVALUATED' ? Boolean(market.market_is_open) : null,
    session: marketLabel(market),
    provider: market.active_provider ?? null,
    providerHealthy: market.status === 'EVALUATED' ? Boolean(market.healthy) : null,
    providerFallback: Boolean(market.fallback_used),
    scheduler: schedulerLabel(scheduler),
    lastTick: scheduler.last_tick_at ?? null,
    lastCycleResult: scheduler.last_status ?? null,
    lastCycleReason: scheduler.last_reason ?? null,
    nextCycle,
    // Only expose a countdown when a real, parseable timestamp exists.
    countdownLabel: countdown ? countdown.label : null,
    countdownDue: countdown ? countdown.due : null,
  }
}

// ------------------------------------------------- Section 3: Research/committee
function researchCommittee(data) {
  const research = data?.research_cycle ?? {}
  const committee = committeePerformance(data)
  const cards = committeeBoard(data).cards
  const market = data?.market ?? {}

  const withConfidence = cards.filter((card) => num(card.confidence) !== null)
  const withAgreement = cards.filter((card) => num(card.agreementPct) !== null)
  const highestConfidence = withConfidence.length
    ? withConfidence.reduce((best, card) => (num(card.confidence) > num(best.confidence) ? card : best))
    : null
  const weakestAgreement = withAgreement.length
    ? withAgreement.reduce((low, card) => (num(card.agreementPct) < num(low.agreementPct) ? card : low))
    : null

  return {
    available: committee.available,
    recommendationCount: committee.recommendationCount,
    buy: committee.buy,
    hold: committee.hold,
    avoid: committee.avoid,
    highestConfidence,
    weakestAgreement,
    provider: market.active_provider ?? null,
    latestAt: research.last_recommendation_run_time ?? null,
    enabled: Boolean(research.enabled),
  }
}

// ------------------------------------------------ Section 4: Learning/reliability
function learningReliability(data) {
  const learning = learningStatus(data)
  const reliability = data?.reliability ?? {}
  const overall = reliability.overall_reliability ?? {}
  const confidence = reliability.confidence ?? {}

  return {
    learningActive: learning.active,
    learningEntries: learning.entries,
    latestLesson: learning.latestLesson,
    reliabilityGrade: overall.grade ?? null,
    reliabilityScore: num(overall.score),
    reliabilityStatus: overall.status ?? null,
    incidentCount: asArray(reliability.recent_incidents).length,
    warningCount: num(reliability.warning_count) ?? 0,
    errorCount: num(reliability.error_count) ?? 0,
    criticalCount: num(reliability.critical_count) ?? 0,
    confidenceLevel: confidence.level ?? null,
    coverage: confidence.coverage ?? null,
    historyAvailable: confidence.history_available ?? null,
  }
}

// --------------------------------------------------- Section 5: Important events
// A routine "market closed" scheduler skip is expected, not urgent.
function isRoutineSkip(text) {
  const value = String(text ?? '').toLowerCase()
  return value.includes('market closed') || value.includes('market is closed')
}

function importantEvents(data, limit = 5) {
  const operations = data?.operations ?? {}
  const reliability = data?.reliability ?? {}
  const scheduler = data?.scheduler ?? {}
  const market = data?.market ?? {}
  const fund = data?.paper_fund ?? {}
  const research = researchCommittee(data)

  const events = []
  const add = (priority, key, tone, title, detail, at) => {
    events.push({ priority, key, tone, title, detail: detail ?? null, at: at ?? null })
  }

  // 1 — critical errors
  for (const error of asArray(operations.recent_errors)) {
    const text = typeof error === 'string' ? error : error?.message ?? error?.reason
    if (text) add(1, `err-${text}`, 'negative', 'Critical error', String(text).slice(0, 140), error?.at)
  }
  for (const incident of asArray(reliability.recent_incidents)) {
    const severity = String(incident?.severity ?? '').toLowerCase()
    if (severity === 'critical' || severity === 'error') {
      add(1, `inc-${incident?.subsystem}-${incident?.at}`, 'negative',
        `${incident?.subsystem ?? 'Subsystem'} incident`, incident?.message ?? incident?.reason, incident?.at)
    }
  }

  // 2 — provider / scheduler failures
  if (num(scheduler.error_count) > 0 || scheduler.last_error_at) {
    add(2, 'sched-fail', 'negative', 'Scheduler error',
      scheduler.last_reason ?? `${scheduler.error_count} scheduler error(s)`, scheduler.last_error_at)
  }
  if (market.status === 'EVALUATED' && market.healthy === false) {
    add(2, 'provider-down', 'negative', 'Market provider unhealthy',
      market.last_error || `Provider ${market.active_provider} reported unhealthy`, null)
  } else if (market.fallback_used) {
    add(2, 'provider-fallback', 'warn', 'Market provider fell back',
      `Active provider ${market.active_provider} is a fallback`, null)
  }

  // 3 — paper orders (executed simulated fills)
  for (const order of asArray(fund.virtual_orders).slice(0, 5)) {
    const side = String(order?.side ?? '').toUpperCase()
    const ticker = order?.ticker ?? order?.symbol
    if (!ticker) continue
    add(3, `order-${order?.order_id ?? `${ticker}-${order?.filled_at}`}`, 'positive',
      `Paper ${side} ${order?.quantity ?? ''} ${ticker}`.trim(),
      'Simulated fill — no real money', order?.filled_at ?? order?.created_at)
  }

  // 4 — new recommendations
  if (research.recommendationCount > 0) {
    add(4, 'recs', 'neutral', `${research.recommendationCount} recommendation(s) generated`,
      `BUY ${research.buy} · HOLD ${research.hold} · AVOID ${research.avoid}`, research.latestAt)
  }

  // 5 — completed research / learning events
  for (const entry of asArray(fund.activity_log)) {
    const type = entry?.activity_type
    if (isRoutineSkip(entry?.message)) continue
    if (type === 'COMMITTEE_EVALUATED') {
      add(5, `act-committee-${entry.at}`, 'neutral', 'Committee evaluation completed', entry?.message, entry?.at)
    } else if (type === 'ANALYTICS_UPDATED') {
      add(5, `act-learning-${entry.at}`, 'positive', 'Learning event recorded', entry?.message, entry?.at)
    }
  }

  // Dedupe by key, then order by priority (asc) and recency (desc).
  const seen = new Set()
  const deduped = events.filter((event) => {
    if (seen.has(event.key)) return false
    seen.add(event.key)
    return true
  })
  deduped.sort((a, b) => {
    if (a.priority !== b.priority) return a.priority - b.priority
    return String(b.at ?? '').localeCompare(String(a.at ?? ''))
  })
  return deduped.slice(0, limit)
}

// ------------------------------------------------------------ Aggregate model
export function executiveBriefing(data, now = new Date()) {
  return {
    header: briefingHeader(data, now),
    portfolio: portfolioBrief(data, now),
    market: marketRuntime(data),
    research: researchCommittee(data),
    learning: learningReliability(data),
    events: importantEvents(data),
  }
}
