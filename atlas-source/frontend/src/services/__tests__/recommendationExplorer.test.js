import { describe, it, expect } from 'vitest'
import {
  actionBucket,
  buildRecommendationRows,
  computeStats,
  filterRows,
  sortRows,
  toCardModel,
  executionStatus,
  DEFAULT_FILTERS,
} from '../recommendationExplorer'
import { committeeCycles, paperFundForExecution } from './fixtures'

const rowFor = (rows, ticker, cycleId) =>
  rows.find((row) => row.ticker === ticker && row.cycleId === cycleId)

describe('recommendationExplorer — buildRecommendationRows', () => {
  it('flattens every (cycle, ticker) evaluation into one row', () => {
    const rows = buildRecommendationRows(committeeCycles())
    expect(rows).toHaveLength(6) // AAPL×4, MSFT×1, NVDA×1
    expect(rows.filter((r) => r.ticker === 'AAPL')).toHaveLength(4)
  })

  it('normalizes BUY/HOLD/AVOID into buckets', () => {
    const rows = buildRecommendationRows(committeeCycles())
    expect(rowFor(rows, 'AAPL', 'c4').bucket).toBe('AVOID')
    expect(rowFor(rows, 'AAPL', 'c3').bucket).toBe('HOLD')
    expect(rowFor(rows, 'MSFT', 'c4').bucket).toBe('BUY')
  })

  it('accepts confidence as a 0–1 fraction or a 0–100 score', () => {
    const rows = buildRecommendationRows(committeeCycles())
    expect(rowFor(rows, 'AAPL', 'c4').confidencePct).toBe(40) // 0.4 → 40
    expect(rowFor(rows, 'MSFT', 'c4').confidencePct).toBe(88) // 88 stays 88
  })

  it('degrades an unevaluated row honestly and invents no provider/return', () => {
    const rows = buildRecommendationRows(committeeCycles())
    const nvda = rowFor(rows, 'NVDA', 'c1')
    expect(nvda.action).toBeNull()
    expect(nvda.bucket).toBeNull()
    expect(nvda.confidence).toBeNull()
    expect(nvda.confidencePct).toBeNull()
    expect(nvda.evaluated).toBe(false)
    expect(nvda.researchStatus).toBe('NOT_EVALUATED')
    // No per-recommendation provider exists in the payload; it must stay null.
    expect(rows.every((row) => row.provider === null)).toBe(true)
  })

  it('returns [] for null/undefined/malformed input', () => {
    expect(buildRecommendationRows(null)).toEqual([])
    expect(buildRecommendationRows(undefined)).toEqual([])
    expect(buildRecommendationRows('nope')).toEqual([])
    expect(buildRecommendationRows([{ evaluations: null }])).toEqual([])
  })
})

describe('recommendationExplorer — actionBucket', () => {
  it('folds STRONG_* and SELL into base buckets, unknown → null', () => {
    expect(actionBucket('STRONG_BUY')).toBe('BUY')
    expect(actionBucket('SELL')).toBe('AVOID')
    expect(actionBucket('NEUTRAL')).toBe('HOLD')
    expect(actionBucket('weird')).toBeNull()
    expect(actionBucket(null)).toBeNull()
  })
})

describe('recommendationExplorer — computeStats', () => {
  it('computes real counts and averages over the full row set', () => {
    const stats = computeStats(buildRecommendationRows(committeeCycles()))
    expect(stats.total).toBe(6)
    expect(stats.buy).toBe(3)
    expect(stats.hold).toBe(1)
    expect(stats.avoid).toBe(1)
    expect(stats.avgConfidence).toBeCloseTo(62.8, 5) // (40+88+61+75+50)/5
    expect(stats.avgAgreement).toBeCloseTo(71.4, 5) // (55+90+62+80+70)/5
    expect(stats.newestAt).toBe('2026-07-14T12:00:00')
    expect(stats.oldestAt).toBe('2026-07-01T12:00:00')
  })

  it('withholds averages when there is no data', () => {
    const stats = computeStats([])
    expect(stats.total).toBe(0)
    expect(stats.avgConfidence).toBeNull()
    expect(stats.avgAgreement).toBeNull()
    expect(stats.newestAt).toBeNull()
  })
})

describe('recommendationExplorer — filterRows', () => {
  const rows = buildRecommendationRows(committeeCycles())

  it('filters by ticker search (case-insensitive)', () => {
    expect(filterRows(rows, { ...DEFAULT_FILTERS, ticker: 'aapl' })).toHaveLength(4)
  })

  it('filters by action bucket', () => {
    expect(filterRows(rows, { ...DEFAULT_FILTERS, actions: ['BUY'] })).toHaveLength(3)
  })

  it('filters by minimum confidence, excluding null-confidence rows', () => {
    const result = filterRows(rows, { ...DEFAULT_FILTERS, minConfidence: 70 })
    expect(result.map((r) => r.ticker).sort()).toEqual(['AAPL', 'MSFT']) // 75 and 88
  })

  it('filters by from/to date window', () => {
    expect(filterRows(rows, { ...DEFAULT_FILTERS, from: '2026-07-08' })).toHaveLength(3)
    expect(filterRows(rows, { ...DEFAULT_FILTERS, to: '2026-07-06' })).toHaveLength(3)
  })

  it('returns [] for null input', () => {
    expect(filterRows(null)).toEqual([])
  })
})

describe('recommendationExplorer — sortRows', () => {
  const rows = buildRecommendationRows(committeeCycles())

  it('sorts newest and oldest by timestamp', () => {
    expect(sortRows(rows, 'newest')[0].evaluatedAt).toBe('2026-07-14T12:00:00')
    expect(sortRows(rows, 'oldest')[0].evaluatedAt).toBe('2026-07-01T12:00:00')
  })

  it('sorts by highest and lowest confidence', () => {
    expect(sortRows(rows, 'confidence_desc')[0].ticker).toBe('MSFT') // 88
    const asc = sortRows(rows, 'confidence_asc')
    expect(asc[asc.length - 1].ticker).toBe('MSFT') // highest ends last
    expect(asc[0].confidencePct).toBeNull() // null sorts as lowest, honestly
  })

  it('does not mutate the source array', () => {
    const before = rows.map((r) => r.id)
    sortRows(rows, 'confidence_desc')
    expect(rows.map((r) => r.id)).toEqual(before)
  })

  it('sorts Learning Intelligence fields and keeps unavailable evidence last', () => {
    const learningRows = [
      { ...rows[0], id: 'a', learningIntelligence: { committeeHistoricalAccuracy: 50, engineHistoricalAccuracy: 80, calibrationGap: -5, evaluationMaturity: 20, completionRate: 25 } },
      { ...rows[1], id: 'b', learningIntelligence: { committeeHistoricalAccuracy: 75, engineHistoricalAccuracy: 60, calibrationGap: 10, evaluationMaturity: 80, completionRate: 90 } },
      { ...rows[2], id: 'c', learningIntelligence: null },
    ]
    expect(sortRows(learningRows, 'committee_accuracy_desc')[0].id).toBe('b')
    expect(sortRows(learningRows, 'engine_accuracy_desc')[0].id).toBe('a')
    expect(sortRows(learningRows, 'calibration_gap_desc')[0].id).toBe('b')
    expect(sortRows(learningRows, 'evaluation_maturity_desc')[0].id).toBe('b')
    expect(sortRows(learningRows, 'recommendation_maturity_desc')[0].id).toBe('b')
    expect(sortRows(learningRows, 'completion_rate_desc').at(-1).id).toBe('c')
  })
})

describe('recommendationExplorer — executionStatus & toCardModel', () => {
  it('distinguishes an executed paper position from a recommendation-only ticker', () => {
    const fund = paperFundForExecution()
    expect(executionStatus(fund, 'AAPL')).toEqual({ executed: true, latestReturn: 20 })
    expect(executionStatus(fund, 'MSFT')).toEqual({ executed: false, latestReturn: null })
  })

  it('invents no return when the position carries no unrealized figure', () => {
    const fund = { open_positions: { AAPL: { quantity: 10 } }, virtual_orders: [] }
    expect(executionStatus(fund, 'AAPL')).toEqual({ executed: true, latestReturn: null })
  })

  it('maps a row to the exact drawer card shape', () => {
    const rows = buildRecommendationRows(committeeCycles())
    expect(toCardModel(rowFor(rows, 'AAPL', 'c4'))).toEqual({
      ticker: 'AAPL',
      action: 'AVOID',
      confidence: 0.4,
      agreementPct: 55,
      strength: 'Weak',
      recommendationId: null,
      outcomeEvidence: null,
      learningIntelligence: null,
    })
    expect(toCardModel(null)).toBeNull()
  })
})
