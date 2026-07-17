// Read-only selectors for Portfolio Intelligence. Pure functions that project
// the single /dashboard/v2 payload (portfolio, performance, learning,
// reliability, paper_fund, research_cycle) into the panel's view model. Every
// value is read straight from the payload — missing/NOT_EVALUATED sections are
// surfaced as `available: false`, never fabricated.

import { committeeBoard } from './missionOps'
import { isEvaluated } from './formatters'

function num(value) {
  if (value === null || value === undefined || value === '') return null
  const parsed = Number(value)
  return Number.isNaN(parsed) ? null : parsed
}

function firstNumber(...values) {
  for (const value of values) {
    const parsed = num(value)
    if (parsed !== null) return parsed
  }
  return null
}

function investedValue(positions, snapshot) {
  const snapValue = num(snapshot?.current_value)
  if (snapValue !== null) return snapValue
  const keys = Object.keys(positions ?? {})
  if (keys.length === 0) return null
  return keys.reduce((total, key) => {
    const position = positions[key]
    const value =
      position?.current_value ??
      (num(position?.quantity) ?? 0) *
        (num(position?.current_price ?? position?.cost_basis) ?? 0)
    return total + (num(value) ?? 0)
  }, 0)
}

// ---------------------------------------------------------------- 1. Summary
export function portfolioSummary(data) {
  const fund = data?.paper_fund ?? {}
  const performance = data?.performance ?? {}
  const portfolio = data?.portfolio ?? {}
  const snapshot = fund.latest_snapshot ?? {}
  const positions = fund.open_positions ?? {}

  const openPositions = Object.keys(positions).length
  const cash = firstNumber(snapshot.cash, fund.cash)
  const invested = investedValue(positions, snapshot)
  const portfolioValue = firstNumber(
    snapshot.portfolio_value,
    cash !== null || invested !== null ? (cash ?? 0) + (invested ?? 0) : null,
  )
  const realizedUnrealized = performance.realized_vs_unrealized ?? {}

  return {
    available: portfolioValue !== null,
    portfolioValue,
    cash,
    invested,
    totalReturn: firstNumber(snapshot.total_return),
    realizedPl: firstNumber(fund.realized_pl, realizedUnrealized.realized_pl),
    unrealizedPl: firstNumber(realizedUnrealized.unrealized_pl),
    openPositions,
    lastUpdate:
      fund.last_update ?? portfolio.portfolio_status?.last_update ?? snapshot.as_of ?? null,
  }
}

// -------------------------------------------------- 2. Performance attribution
export function performanceAttribution(data) {
  const performance = data?.performance ?? {}
  const symbol = performance.symbol_contribution ?? {}
  const sector = performance.sector_contribution ?? {}
  const drivers = Array.isArray(performance.portfolio_return_drivers?.drivers)
    ? performance.portfolio_return_drivers.drivers
    : []
  const cashDrag = performance.cash_drag ?? {}

  const positive = drivers.filter((driver) => (num(driver.value) ?? 0) > 0)
  const negative = drivers.filter((driver) => (num(driver.value) ?? 0) < 0)

  const best = mapContribution(symbol.best)
  const worst = mapContribution(symbol.worst)
  const largestContributor = mapDriver(positive[0])
  const largestDetractor = mapDriver(negative[negative.length - 1])

  return {
    available:
      isEvaluated(symbol) || drivers.length > 0 || isEvaluated(performance.cash_drag),
    best,
    worst,
    largestContributor,
    largestDetractor,
    cashDrag: isEvaluated(performance.cash_drag)
      ? {
          contribution: firstNumber(cashDrag.cash_pl_contribution),
          weightPercent: firstNumber(cashDrag.cash_weight_percent),
        }
      : null,
    sectors: (Array.isArray(sector.items) ? sector.items : [])
      .map((item) => ({
        sector: item.sector ?? 'Unclassified',
        contribution: firstNumber(
          item.contribution_to_portfolio_percent,
          item.unrealized_pl,
        ),
      }))
      .filter((item) => item.contribution !== null),
  }
}

function mapContribution(item) {
  if (!item || typeof item !== 'object') return null
  return {
    symbol: item.symbol ?? null,
    unrealizedPl: firstNumber(item.unrealized_pl),
    contributionPercent: firstNumber(item.contribution_to_portfolio_percent),
  }
}

function mapDriver(item) {
  if (!item || typeof item !== 'object') return null
  return {
    symbol: item.symbol ?? item.driver ?? null,
    value: firstNumber(item.value),
  }
}

// ------------------------------------------------------------- 3. Health
export function portfolioHealth(data) {
  const portfolio = data?.portfolio ?? {}
  const healthScore = portfolio.portfolio_health_score ?? {}
  const cashReserve = portfolio.cash_reserve_status ?? {}
  const concentration = portfolio.largest_position_concentration ?? {}
  const sector = portfolio.sector_exposure_summary ?? {}
  const risk = portfolio.risk_utilization ?? {}

  return {
    available: isEvaluated(healthScore) || num(healthScore.score) !== null,
    score: num(healthScore.score),
    scoreStatus: healthScore.status ?? null,
    cashReserve: {
      available: isEvaluated(cashReserve),
      percent: firstNumber(cashReserve.cash_percent),
      status: cashReserve.status ?? null,
    },
    concentration: {
      available: isEvaluated(concentration),
      percent: firstNumber(concentration.concentration_percent),
      symbol: concentration.symbol ?? null,
    },
    sectors: (Array.isArray(sector.items) ? sector.items : [])
      .map((item) => ({ name: item.sector ?? 'Unclassified', value: firstNumber(item.exposure_percent) }))
      .filter((item) => item.value !== null && item.value > 0),
    largestSector: sector.largest_sector ?? null,
    riskUtilization: {
      available: isEvaluated(risk),
      decisions: num(risk.decision_count) ?? 0,
      rejected: num(risk.rejected_decisions) ?? 0,
      rules: (Array.isArray(risk.by_rule) ? risk.by_rule : []).map((row) => row.rule).filter(Boolean),
    },
  }
}

// -------------------------------------------------- 4. Committee performance
export function committeePerformance(data) {
  const research = data?.research_cycle ?? {}
  const reliability = data?.reliability ?? {}
  const learning = data?.learning ?? {}
  const board = committeeBoard(data)
  const cards = board.cards

  const generation = (Array.isArray(research.stages) ? research.stages : []).find(
    (stage) => stage?.stage === 'research_generation',
  )
  const counts = { BUY: 0, HOLD: 0, AVOID: 0 }
  const agreements = []
  for (const card of cards) {
    const action = String(card.action ?? '').toUpperCase()
    if (action in counts) counts[action] += 1
    if (card.agreementPct !== null && card.agreementPct !== undefined) {
      agreements.push(Number(card.agreementPct))
    }
  }
  const completed = cards.filter((card) => card.evaluated).length

  return {
    available: cards.length > 0 || num(generation?.details?.recommendation_count) !== null,
    recommendationCount: num(generation?.details?.recommendation_count) ?? cards.length,
    completed,
    buy: counts.BUY,
    hold: counts.HOLD,
    avoid: counts.AVOID,
    agreementPercent:
      agreements.length > 0
        ? agreements.reduce((total, value) => total + value, 0) / agreements.length
        : null,
    reliabilityGrade: reliability.overall_reliability?.grade ?? null,
    reliabilityScore: num(reliability.overall_reliability?.score),
    // Only surface outcome accuracy when the backend actually evaluated it.
    outcomesAvailable: isEvaluated(learning.recommendation_outcomes),
  }
}

// ------------------------------------------------------------- 5. Learning
export function learningStatus(data) {
  const operations = data?.operations ?? {}
  const reliability = data?.reliability ?? {}
  const learning = operations.learning ?? {}
  const confidence = reliability.confidence ?? {}

  return {
    available: learning.status === 'EVALUATED' || (num(learning.learning_entries) ?? 0) > 0,
    active: Boolean(learning.learning_active),
    entries: num(learning.learning_entries) ?? 0,
    latestLesson: learning.latest_lesson ?? null,
    latestAt: learning.latest_learning_at ?? null,
    confidenceLevel: confidence.level ?? null,
    coverage: confidence.coverage ?? null,
    historyAvailable: confidence.history_available ?? null,
  }
}

// ------------------------------------------------------------- 6. Timeline
const ACTIVITY_LABELS = {
  RECOMMENDATIONS_GENERATED: 'Recommendation Generated',
  COMMITTEE_EVALUATED: 'Committee Evaluated',
  ORDERS_FILLED: 'Paper Trade Executed',
  PORTFOLIO_UPDATED: 'Snapshot Saved',
  ANALYTICS_UPDATED: 'Learning Event',
}

const ACTIVITY_TONES = {
  RECOMMENDATIONS_GENERATED: 'neutral',
  COMMITTEE_EVALUATED: 'neutral',
  ORDERS_FILLED: 'positive',
  PORTFOLIO_UPDATED: 'neutral',
  ANALYTICS_UPDATED: 'positive',
}

export function portfolioTimeline(data, limit = 12) {
  const activity = Array.isArray(data?.paper_fund?.activity_log)
    ? data.paper_fund.activity_log
    : []

  const events = activity
    .filter((entry) => entry && ACTIVITY_LABELS[entry.activity_type])
    .map((entry) => ({
      title: ACTIVITY_LABELS[entry.activity_type],
      detail: entry.message ? String(entry.message).slice(0, 140) : null,
      at: entry.at ?? null,
      tone: ACTIVITY_TONES[entry.activity_type] ?? 'neutral',
    }))

  // activity_log arrives newest-first; keep that order.
  return { available: events.length > 0, events: events.slice(0, limit) }
}

// Aggregate: compute the whole model once from the shared payload.
export function portfolioIntelligence(data) {
  return {
    summary: portfolioSummary(data),
    attribution: performanceAttribution(data),
    health: portfolioHealth(data),
    committee: committeePerformance(data),
    learning: learningStatus(data),
    timeline: portfolioTimeline(data),
  }
}
