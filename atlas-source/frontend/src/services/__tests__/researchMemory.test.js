import { describe, it, expect } from 'vitest'
import {
  buildRecommendationRows,
  indexByTicker,
  tickersWithHistory,
  buildTimeline,
  filterTimeline,
  computeTrendSummary,
  changeTone,
  eventSummary,
} from '../researchMemory'
import { committeeCycles } from './fixtures'

const rows = () => buildRecommendationRows(committeeCycles())

describe('researchMemory — ticker indexing', () => {
  it('groups rows by ticker and orders the directory by activity then name', () => {
    const index = indexByTicker(rows())
    expect(index.get('AAPL')).toHaveLength(4)
    const directory = tickersWithHistory(rows())
    expect(directory.map((t) => t.ticker)).toEqual(['AAPL', 'MSFT', 'NVDA'])
    expect(directory[0]).toMatchObject({ ticker: 'AAPL', count: 4 })
    expect(directory[0].lastAt).toBe(Date.parse('2026-07-14T12:00:00'))
  })

  it('is safe on empty/null input', () => {
    expect(indexByTicker(null).size).toBe(0)
    expect(tickersWithHistory([])).toEqual([])
  })
})

describe('researchMemory — buildTimeline', () => {
  const timeline = buildTimeline(rows(), 'AAPL')

  it('returns AAPL events newest-first', () => {
    expect(timeline.map((e) => e.action)).toEqual(['AVOID', 'HOLD', 'BUY', 'BUY'])
    expect(timeline[0].evaluatedAt).toBe('2026-07-14T12:00:00')
  })

  it('detects BUY → HOLD and HOLD → AVOID transitions', () => {
    expect(timeline[0]).toMatchObject({ action: 'AVOID', actionChanged: true, previousBucket: 'HOLD' })
    expect(timeline[1]).toMatchObject({ action: 'HOLD', actionChanged: true, previousBucket: 'BUY' })
  })

  it('flags an unchanged recommendation and the first (initial) event', () => {
    expect(timeline[2]).toMatchObject({ action: 'BUY', actionChanged: false, previousBucket: 'BUY' })
    expect(timeline[3]).toMatchObject({ isFirst: true, previousBucket: null, confidenceDelta: null })
  })

  it('reports confidence and agreement changes in percentage points', () => {
    expect(timeline[0].confidenceDelta).toBe(-21) // 40 - 61
    expect(timeline[0].agreementDelta).toBe(-7) // 55 - 62
    expect(timeline[2].confidenceDelta).toBe(25) // 75 - 50
    expect(timeline[2].agreementDelta).toBe(10) // 80 - 70
  })

  it('returns [] for missing ticker or empty rows', () => {
    expect(buildTimeline(rows(), null)).toEqual([])
    expect(buildTimeline([], 'AAPL')).toEqual([])
    expect(buildTimeline(rows(), 'ZZZZ')).toEqual([])
  })

  it('preserves recommendation chronology when learning metrics are attached', () => {
    const enriched = rows().map((row, index) => ({
      ...row,
      learningIntelligence: { evaluationMaturity: index * 20 },
    }))
    const timeline = buildTimeline(enriched, 'AAPL')
    expect(timeline.map((event) => event.evaluatedAt)).toEqual([
      '2026-07-14T12:00:00',
      '2026-07-10T12:00:00',
      '2026-07-05T12:00:00',
      '2026-07-01T12:00:00',
    ])
    expect(timeline.every((event) => event.learningIntelligence)).toBe(true)
  })
})

describe('researchMemory — filterTimeline (date window)', () => {
  it('keeps only in-window events and preserves order', () => {
    const timeline = buildTimeline(rows(), 'AAPL')
    const win = filterTimeline(timeline, { from: '2026-07-05', to: '2026-07-11' })
    expect(win).toHaveLength(2)
    expect(win.map((e) => e.evaluatedAt)).toEqual(['2026-07-10T12:00:00', '2026-07-05T12:00:00'])
  })

  it('returns the full list when no window is set, [] on null', () => {
    const timeline = buildTimeline(rows(), 'AAPL')
    expect(filterTimeline(timeline, {})).toHaveLength(4)
    expect(filterTimeline(null, {})).toEqual([])
  })
})

describe('researchMemory — computeTrendSummary', () => {
  const summary = computeTrendSummary(buildTimeline(rows(), 'AAPL'))

  it('summarizes totals, current vs previous, and change count', () => {
    expect(summary.total).toBe(4)
    expect(summary.currentAction).toBe('AVOID')
    expect(summary.previousAction).toBe('HOLD')
    expect(summary.recommendationChanges).toBe(2)
    expect(summary.buy).toBe(2)
    expect(summary.hold).toBe(1)
    expect(summary.avoid).toBe(1)
  })

  it('computes confidence stats with dates', () => {
    expect(summary.avgConfidence).toBeCloseTo(56.5, 5) // (50+75+61+40)/4
    expect(summary.highestConfidence).toEqual({ value: 75, at: '2026-07-05T12:00:00' })
    expect(summary.lowestConfidence).toEqual({ value: 40, at: '2026-07-14T12:00:00' })
    expect(summary.largestIncrease).toEqual({ delta: 25, at: '2026-07-05T12:00:00', fromAt: '2026-07-01T12:00:00' })
    expect(summary.largestDecrease).toMatchObject({ delta: -21, at: '2026-07-14T12:00:00' })
  })

  it('reports first versus most-recent recommendation', () => {
    expect(summary.firstAction).toBe('BUY')
    expect(summary.firstAt).toBe('2026-07-01T12:00:00')
    expect(summary.mostRecentAction).toBe('AVOID')
    expect(summary.mostRecentAt).toBe('2026-07-14T12:00:00')
  })

  it('returns null for empty or null timelines', () => {
    expect(computeTrendSummary([])).toBeNull()
    expect(computeTrendSummary(null)).toBeNull()
  })
})

describe('researchMemory — small helpers', () => {
  it('changeTone reflects the destination action', () => {
    expect(changeTone('BUY')).toBe('positive')
    expect(changeTone('AVOID')).toBe('negative')
    expect(changeTone('HOLD')).toBe('neutral')
  })

  it('eventSummary restates stored metrics, never invents prose', () => {
    const timeline = buildTimeline(rows(), 'AAPL')
    expect(eventSummary(timeline[0])).toBe('AVOID · 40% confidence · 55% agreement · Weak')
  })
})
