import { describe, it, expect } from 'vitest'
import {
  actionTone,
  committeeBoard,
  researchTimeline,
  operationsCells,
  systemIntelligence,
} from '../missionOps'
import { dashboardV2 } from './fixtures'

// Focused on missionOps surface NOT already covered by the portfolioIntel /
// executiveBriefing suites (which exercise committee counts and greetings).

describe('missionOps — actionTone', () => {
  it('maps actions to tones, unknown → muted', () => {
    expect(actionTone('BUY')).toBe('positive')
    expect(actionTone('STRONG_BUY')).toBe('positive')
    expect(actionTone('HOLD')).toBe('neutral')
    expect(actionTone('AVOID')).toBe('negative')
    expect(actionTone('SELL')).toBe('negative')
    expect(actionTone('???')).toBe('muted')
    expect(actionTone(null)).toBe('muted')
  })
})

describe('missionOps — committeeBoard', () => {
  it('projects committee cards with status, timestamp and reason', () => {
    const board = committeeBoard(dashboardV2())
    expect(board.status).toBe('COMPLETED')
    expect(board.at).toBe('2026-07-14T09:05:00')
    expect(board.cards).toHaveLength(3)
    expect(board.cards[0]).toEqual({
      ticker: 'AAPL',
      action: 'BUY',
      strength: 'Strong',
      agreementPct: 90,
      confidence: 0.88,
      evaluated: true,
      reason: 'Momentum + earnings',
    })
  })

  it('degrades to an empty board when the committee stage is missing', () => {
    const board = committeeBoard({})
    expect(board.status).toBe('NOT_EVALUATED')
    expect(board.cards).toEqual([])
  })
})

describe('missionOps — researchTimeline', () => {
  it('maps the five milestones; recorded stages COMPLETE, absent fund stages honest', () => {
    const timeline = researchTimeline(dashboardV2())
    expect(timeline.map((s) => s.label)).toEqual(['Research', 'Committee', 'Risk', 'Portfolio', 'Learning'])
    expect(timeline[0]).toMatchObject({ status: 'COMPLETE', detail: '3 records' })
    expect(timeline[1].status).toBe('COMPLETE')
    // No fund cycle ran in this payload, so those stages must not be faked.
    expect(timeline[2].status).toBe('NOT_EVALUATED')
    expect(timeline[3].status).toBe('NOT_EVALUATED')
    expect(timeline[4].status).toBe('NOT_EVALUATED')
  })
})

describe('missionOps — operationsCells', () => {
  it('projects scheduler / provider / database / fund vitals', () => {
    const cells = operationsCells(dashboardV2())
    expect(cells.map((c) => c.key)).toEqual([
      'scheduler',
      'last_cycle',
      'next_cycle',
      'provider',
      'database',
      'paper_fund',
    ])
    const byKey = Object.fromEntries(cells.map((c) => [c.key, c]))
    expect(byKey.scheduler).toMatchObject({ value: 'RUNNING', status: 'RUNNING' })
    expect(byKey.provider).toMatchObject({ value: 'yahoo', status: 'Healthy' })
    expect(byKey.database).toMatchObject({ value: 'Connected', status: 'Healthy', hint: '20 tables · 100 rows' })
    expect(byKey.paper_fund).toMatchObject({ value: 'RUNNING', hint: 'provider: yahoo' })
    expect(byKey.next_cycle).toMatchObject({ status: 'READY', hint: 'every 5 min' })
  })

  it('projects honest "Unavailable" vitals on an incomplete payload', () => {
    const cells = operationsCells(null)
    expect(cells).toHaveLength(6)
    const scheduler = cells.find((c) => c.key === 'scheduler')
    expect(scheduler.value).toBe('Unavailable')
  })
})

describe('missionOps — systemIntelligence', () => {
  it('projects reliability, learning, recommendation count and provider health', () => {
    const intel = systemIntelligence(dashboardV2())
    expect(intel.warnings).toEqual([])
    expect(intel.reliabilityGrade).toBe('A')
    expect(intel.reliabilityScore).toBe(92)
    expect(intel.warningCount).toBe(1)
    expect(intel.errorCount).toBe(0)
    expect(intel.learning).toEqual({ active: true, entries: 5, latestLesson: 'Rebalanced tech exposure', at: '2026-07-14T15:00:00' })
    expect(intel.recommendationCount).toBe(3)
    expect(intel.provider).toBe('yahoo')
    expect(intel.providerHealthy).toBe(true)
  })

  it('is safe on null/incomplete payloads', () => {
    expect(() => systemIntelligence(null)).not.toThrow()
    expect(() => researchTimeline(null)).not.toThrow()
    expect(() => committeeBoard(null)).not.toThrow()
    expect(systemIntelligence(null).recommendationCount).toBe(0)
  })
})
