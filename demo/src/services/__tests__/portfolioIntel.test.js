import { describe, it, expect } from 'vitest'
import {
  portfolioSummary,
  performanceAttribution,
  portfolioHealth,
  committeePerformance,
  learningStatus,
  portfolioTimeline,
  portfolioIntelligence,
} from '../portfolioIntel'
import { dashboardV2 } from './fixtures'

describe('portfolioIntel — portfolioSummary', () => {
  it('reads a populated portfolio and separates realized vs unrealized P/L', () => {
    const summary = portfolioSummary(dashboardV2())
    expect(summary.available).toBe(true)
    expect(summary.portfolioValue).toBe(20000)
    expect(summary.cash).toBe(5000)
    expect(summary.invested).toBe(15000)
    expect(summary.totalReturn).toBe(12.5)
    expect(summary.realizedPl).toBe(250)
    expect(summary.unrealizedPl).toBe(800)
    expect(summary.openPositions).toBe(2)
    expect(summary.lastUpdate).toBe('2026-07-14T15:30:00')
  })

  it('reports unavailable for an empty portfolio', () => {
    const summary = portfolioSummary({})
    expect(summary.available).toBe(false)
    expect(summary.portfolioValue).toBeNull()
    expect(summary.openPositions).toBe(0)
  })
})

describe('portfolioIntel — performanceAttribution', () => {
  it('maps best/worst symbols and largest contributor/detractor', () => {
    const attr = performanceAttribution(dashboardV2())
    expect(attr.available).toBe(true)
    expect(attr.best).toEqual({ symbol: 'AAPL', unrealizedPl: 1500, contributionPercent: 7.5 })
    expect(attr.worst).toEqual({ symbol: 'MSFT', unrealizedPl: 300, contributionPercent: 1.5 })
    expect(attr.largestContributor).toEqual({ symbol: 'AAPL', value: 1500 })
    expect(attr.largestDetractor).toEqual({ symbol: 'MSFT', value: -200 })
    expect(attr.cashDrag).toEqual({ contribution: -12, weightPercent: 25 })
    expect(attr.sectors).toEqual([{ sector: 'Technology', contribution: 9.0 }])
  })

  it('is unavailable when the backend marks sections NOT_EVALUATED', () => {
    // The engine signals absence with an explicit status, not by omission, so
    // an empty {} still reads as evaluated. Only NOT_EVALUATED withholds.
    const data = { performance: { symbol_contribution: { status: 'NOT_EVALUATED' }, cash_drag: { status: 'NOT_EVALUATED' } } }
    expect(performanceAttribution(data).available).toBe(false)
  })
})

describe('portfolioIntel — portfolioHealth', () => {
  it('reads health, concentration and risk-utilization metrics', () => {
    const health = portfolioHealth(dashboardV2())
    expect(health.available).toBe(true)
    expect(health.score).toBe(82)
    expect(health.cashReserve).toMatchObject({ available: true, percent: 25 })
    expect(health.concentration).toMatchObject({ available: true, percent: 45, symbol: 'AAPL' })
    expect(health.sectors).toEqual([
      { name: 'Technology', value: 60 },
      { name: 'Cash', value: 25 },
    ])
    expect(health.largestSector).toBe('Technology')
    expect(health.riskUtilization).toMatchObject({
      available: true,
      decisions: 10,
      rejected: 2,
      rules: ['max_position', 'sector_cap'],
    })
  })

  it('is unavailable when the health score is marked NOT_EVALUATED', () => {
    const data = { portfolio: { portfolio_health_score: { status: 'NOT_EVALUATED' } } }
    expect(portfolioHealth(data).available).toBe(false)
  })
})

describe('portfolioIntel — committeePerformance', () => {
  it('counts BUY/HOLD/AVOID and averages agreement from committee cards', () => {
    const committee = committeePerformance(dashboardV2())
    expect(committee.available).toBe(true)
    expect(committee.recommendationCount).toBe(3)
    expect(committee.completed).toBe(3)
    expect(committee.buy).toBe(1)
    expect(committee.hold).toBe(1)
    expect(committee.avoid).toBe(1)
    expect(committee.agreementPercent).toBeCloseTo(66.6667, 3) // (90+60+50)/3
    expect(committee.reliabilityGrade).toBe('A')
  })

  it('withholds outcome accuracy until the backend evaluates outcomes', () => {
    expect(committeePerformance(dashboardV2()).outcomesAvailable).toBe(false)
    const withOutcomes = dashboardV2()
    withOutcomes.learning = { recommendation_outcomes: { status: 'EVALUATED', accuracy: 0.6 } }
    expect(committeePerformance(withOutcomes).outcomesAvailable).toBe(true)
  })
})

describe('portfolioIntel — learningStatus', () => {
  it('reads active learning state and confidence coverage', () => {
    const learning = learningStatus(dashboardV2())
    expect(learning.available).toBe(true)
    expect(learning.active).toBe(true)
    expect(learning.entries).toBe(5)
    expect(learning.latestLesson).toBe('Rebalanced tech exposure')
    expect(learning.confidenceLevel).toBe('HIGH')
    expect(learning.coverage).toBe(0.8)
  })

  it('is unavailable with no learning activity', () => {
    expect(learningStatus({}).available).toBe(false)
  })
})

describe('portfolioIntel — portfolioTimeline', () => {
  it('maps known activity types and preserves newest-first order', () => {
    const timeline = portfolioTimeline(dashboardV2())
    expect(timeline.available).toBe(true)
    expect(timeline.events.map((e) => e.title)).toEqual([
      'Paper Trade Executed',
      'Committee Evaluated',
      'Recommendation Generated',
    ])
    expect(timeline.events[0].tone).toBe('positive') // ORDERS_FILLED
  })

  it('is unavailable with no recognized activity, safe on null', () => {
    expect(portfolioTimeline({}).available).toBe(false)
    expect(portfolioTimeline(null).events).toEqual([])
  })
})

describe('portfolioIntel — portfolioIntelligence aggregate', () => {
  it('composes all six sections and tolerates a null payload', () => {
    const model = portfolioIntelligence(dashboardV2())
    expect(Object.keys(model)).toEqual([
      'summary',
      'attribution',
      'health',
      'committee',
      'learning',
      'timeline',
    ])
    expect(() => portfolioIntelligence(null)).not.toThrow()
    expect(portfolioIntelligence(null).summary.available).toBe(false)
  })
})
