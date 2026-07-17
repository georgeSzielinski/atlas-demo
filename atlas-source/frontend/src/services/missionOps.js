// Read-only selectors that project the /dashboard/v2 payload into the Mission
// Control (Dashboard V3) view model. Pure functions only: they never fabricate
// values — every field is read straight from the payload, and anything the
// backend reports as NOT_EVALUATED / missing degrades to an honest empty state.
//
// These build on the shared paper-fund selectors in paperFundOps.js so the
// pipeline, scheduler, market and clock logic is defined exactly once.

import {
  STAGE_STATUS,
  derivePipeline,
  formatClock,
  marketLabel,
  schedulerLabel,
} from './paperFundOps'

// ---------------------------------------------------------------------------
// Investment committee cards
// ---------------------------------------------------------------------------

// The committee's freshest verdicts, projected from the research cycle's
// committee_evaluation stage (written only when the committee actually ran).
// Returns { status, at, reason, cards } — cards is [] when nothing is recorded.
export function committeeBoard(data) {
  const research = data?.research_cycle ?? {}
  const stages = Array.isArray(research.stages) ? research.stages : []
  const stage = stages.find((item) => item?.stage === 'committee_evaluation')
  const evaluations = Array.isArray(stage?.details?.evaluations)
    ? stage.details.evaluations
    : []

  const cards = evaluations
    .filter((item) => item && item.ticker)
    .map((item) => ({
      ticker: String(item.ticker),
      action: item.action ?? null, // BUY / HOLD / AVOID
      strength: item.strength ?? null,
      agreementPct: numberOrNull(item.agreement_pct),
      confidence: numberOrNull(item.confidence),
      evaluated: Boolean(item.status) && item.status !== 'NOT_EVALUATED',
      reason: item.reason ?? null,
    }))

  return {
    status: stage?.status ?? research.status ?? 'NOT_EVALUATED',
    at: stage?.at ?? null,
    reason: stage?.reason ?? research.reason ?? null,
    cards,
  }
}

// BUY -> positive, HOLD -> neutral, AVOID/SELL -> negative.
export function actionTone(action) {
  const key = String(action ?? '').toUpperCase()
  if (key === 'BUY' || key === 'STRONG_BUY') return 'positive'
  if (key === 'AVOID' || key === 'SELL' || key === 'STRONG_SELL') return 'negative'
  if (key === 'HOLD') return 'neutral'
  return 'muted'
}

// ---------------------------------------------------------------------------
// Research → Committee → Risk → Portfolio → Learning timeline
// ---------------------------------------------------------------------------

const RESEARCH_STEP = { COMPLETED: STAGE_STATUS.COMPLETE }

function fromResearchStage(stages, stageKey, key, label) {
  const recorded = Array.isArray(stages)
    ? stages.find((item) => item?.stage === stageKey)
    : null
  if (!recorded) {
    return { key, label, status: STAGE_STATUS.NOT_EVALUATED, at: null, durationSeconds: null }
  }
  const details = recorded.details ?? {}
  const count =
    stageKey === 'research_generation'
      ? details.recommendation_count
      : Array.isArray(details.evaluations)
        ? details.evaluations.length
        : null
  return {
    key,
    label,
    status: RESEARCH_STEP[recorded.status] ?? recorded.status ?? STAGE_STATUS.NOT_EVALUATED,
    at: recorded.at ?? null,
    durationSeconds: recorded.duration_seconds ?? null,
    detail:
      count !== null && count !== undefined
        ? `${count} record${count === 1 ? '' : 's'}`
        : recorded.reason ?? null,
  }
}

function fromFundStage(pipelineStages, stageKey, key, label) {
  const recorded = pipelineStages.find((item) => item.key === stageKey)
  if (!recorded) {
    return { key, label, status: STAGE_STATUS.NOT_EVALUATED, at: null, durationSeconds: null }
  }
  return {
    key,
    label,
    status: recorded.status,
    at: recorded.at ?? null,
    durationSeconds: recorded.durationSeconds ?? null,
    detail: recorded.detail ?? null,
  }
}

// The five headline pipeline milestones. Research + Committee come from the
// autonomous research cycle; Risk, Portfolio and Learning come from the most
// recent paper-fund cycle's recorded activity markers.
export function researchTimeline(data) {
  const research = data?.research_cycle ?? {}
  const stages = Array.isArray(research.stages) ? research.stages : []
  const fundPipeline = derivePipeline(data?.paper_fund ?? {})

  return [
    fromResearchStage(stages, 'research_generation', 'research', 'Research'),
    fromResearchStage(stages, 'committee_evaluation', 'committee', 'Committee'),
    fromFundStage(fundPipeline.stages, 'risk_gate', 'risk', 'Risk'),
    fromFundStage(fundPipeline.stages, 'construction', 'portfolio', 'Portfolio'),
    fromFundStage(fundPipeline.stages, 'learning', 'learning', 'Learning'),
  ]
}

// ---------------------------------------------------------------------------
// Operations center cells
// ---------------------------------------------------------------------------

// The six operational vitals for the second row. Each cell is
// { label, value, status, hint } — status drives the pill/dot tone.
export function operationsCells(data) {
  const operations = data?.operations ?? {}
  const scheduler = data?.scheduler ?? {}
  const market = data?.market ?? {}
  const fund = data?.paper_fund ?? {}
  const database = operations.database ?? {}
  const cycle = fund.cycle_state ?? {}

  const schedulerState = schedulerLabel(scheduler)
  const lastCycle = fund.last_update ?? cycle.last_successful_cycle_time ?? null
  const providerHealthy = market.status === 'EVALUATED' ? market.healthy : null

  return [
    {
      key: 'scheduler',
      label: 'Scheduler Heartbeat',
      value: schedulerState,
      status: schedulerState,
      hint:
        scheduler.status === 'EVALUATED'
          ? scheduler.running
            ? `${scheduler.tick_count ?? 0} tick${scheduler.tick_count === 1 ? '' : 's'} · last ${formatClock(scheduler.last_tick_at)}`
            : scheduler.enabled
              ? 'Enabled — loop idle'
              : 'Disabled'
          : 'Status unavailable',
    },
    {
      key: 'last_cycle',
      label: 'Last Cycle',
      value: lastCycle ? formatClock(lastCycle) : 'None yet',
      status: lastCycle ? 'EVALUATED' : 'NOT_EVALUATED',
      hint: cycle.state ? `state: ${cycle.state}` : 'no cycle recorded',
    },
    {
      key: 'next_cycle',
      label: 'Next Cycle',
      value: fund.next_update ? formatClock(fund.next_update) : 'Not scheduled',
      status: fund.next_update ? 'READY' : 'NOT_EVALUATED',
      hint: fund.interval_minutes ? `every ${fund.interval_minutes} min` : 'interval n/a',
    },
    {
      key: 'provider',
      label: 'Provider Health',
      value: market.active_provider ?? 'Unavailable',
      status: providerHealthy === null ? 'Unavailable' : providerHealthy ? 'Healthy' : 'Degraded',
      hint: market.fallback_used ? 'fallback active' : marketLabel(market),
    },
    {
      key: 'database',
      label: 'Database Health',
      value: database.exists ? 'Connected' : 'Unavailable',
      status: database.status === 'EVALUATED' && database.exists ? 'Healthy' : 'NOT_EVALUATED',
      hint:
        database.table_count !== undefined
          ? `${database.table_count} tables · ${database.total_rows ?? 0} rows`
          : 'schema unavailable',
    },
    {
      key: 'paper_fund',
      label: 'Paper Fund',
      value: String(fund.fund_status ?? 'OFF').toUpperCase(),
      status: String(fund.fund_status ?? 'OFF').toUpperCase(),
      hint: fund.price_provider ? `provider: ${fund.price_provider}` : 'simulated only',
    },
  ]
}

// ---------------------------------------------------------------------------
// Portfolio overview
// ---------------------------------------------------------------------------

// Allocation, cash, sector exposure, largest position and cash-reserve health,
// projected from the composed portfolio section + live open positions. Never
// renders a broken chart: hasPositions gates the allocation view.
export function portfolioOverview(data) {
  const fund = data?.paper_fund ?? {}
  const portfolio = data?.portfolio ?? {}
  const snapshot = fund.latest_snapshot ?? {}
  const positions = fund.open_positions ?? {}
  const positionKeys = Object.keys(positions)

  const allocation = positionKeys.map((ticker) => {
    const position = positions[ticker]
    const value =
      position?.current_value ??
      Number(position?.quantity ?? 0) *
        Number(position?.current_price ?? position?.cost_basis ?? 0)
    return { name: ticker, value: Number(value) || 0 }
  })
  const cash = numberOrNull(snapshot.cash ?? fund.cash)
  if (cash && cash > 0) {
    allocation.push({ name: 'Cash', value: cash })
  }

  const sectorSummary = portfolio.sector_exposure_summary ?? {}
  const largest = portfolio.largest_position_concentration ?? {}
  const reserve = portfolio.cash_reserve_status ?? {}
  const health = portfolio.portfolio_health_score ?? {}

  return {
    hasPositions: positionKeys.length > 0,
    allocation: allocation.filter((row) => row.value > 0),
    cash,
    portfolioValue: numberOrNull(snapshot.portfolio_value ?? portfolio.portfolio_value),
    healthScore: numberOrNull(health.score),
    healthStatus: health.status ?? null,
    cashReservePercent: numberOrNull(reserve.cash_percent),
    largestPosition:
      largest.symbol && largest.concentration_percent !== null
        ? {
            symbol: largest.symbol,
            percent: numberOrNull(largest.concentration_percent),
            value: numberOrNull(largest.current_value),
          }
        : null,
    sectors: (Array.isArray(sectorSummary.items) ? sectorSummary.items : [])
      .map((item) => ({
        name: item.sector ?? item.name ?? 'Unclassified',
        percent: numberOrNull(item.exposure_percent ?? item.percent),
      }))
      .filter((item) => item.percent !== null),
  }
}

// ---------------------------------------------------------------------------
// System intelligence
// ---------------------------------------------------------------------------

export function systemIntelligence(data) {
  const operations = data?.operations ?? {}
  const reliability = data?.reliability ?? {}
  const research = data?.research_cycle ?? {}
  const market = data?.market ?? {}
  const learning = operations.learning ?? {}

  const generation = (Array.isArray(research.stages) ? research.stages : []).find(
    (item) => item?.stage === 'research_generation',
  )
  const recommendationCount =
    generation?.details?.recommendation_count ?? committeeBoard(data).cards.length

  return {
    warnings: asWarnings(operations.warnings),
    reliabilityGrade: reliability.overall_reliability?.grade ?? null,
    reliabilityScore: numberOrNull(reliability.overall_reliability?.score),
    reliabilityTrend: reliability.reliability_trend ?? {},
    warningCount: reliability.warning_count ?? 0,
    errorCount: reliability.error_count ?? 0,
    learning: {
      active: Boolean(learning.learning_active),
      entries: learning.learning_entries ?? 0,
      latestLesson: learning.latest_lesson ?? null,
      at: learning.latest_learning_at ?? null,
    },
    recommendationCount,
    provider: market.active_provider ?? null,
    providerHealthy: market.status === 'EVALUATED' ? market.healthy : null,
  }
}

function asWarnings(warnings) {
  if (!Array.isArray(warnings)) return []
  return warnings
    .map((item) => (typeof item === 'string' ? item : item?.message ?? item?.reason))
    .filter(Boolean)
}

// ---------------------------------------------------------------------------
// Small shared helpers
// ---------------------------------------------------------------------------

function numberOrNull(value) {
  if (value === null || value === undefined || value === '') return null
  const number = Number(value)
  return Number.isNaN(number) ? null : number
}
