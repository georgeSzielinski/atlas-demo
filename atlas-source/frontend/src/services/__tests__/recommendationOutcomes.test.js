import { describe, expect, it } from 'vitest'
import { buildTimeline } from '../researchMemory'
import {
  OUTCOME_HORIZONS,
  buildDrawerOutcomeModel,
  buildOutcomeEvidence,
  enrichRecommendationRows,
  indexOutcomeRows,
  normalizeOutcomeRow,
  outcomeResult,
  outcomeSourceMeta,
} from '../recommendationOutcomes'

function record(overrides = {}) {
  return {
    recommendation_id: 11,
    run_id: 101,
    ticker: 'AAPL',
    action: 'BUY',
    outcome_id: 501,
    horizon_days: 7,
    evaluation_source: 'paper',
    status: 'Succeeded',
    success: true,
    percentage_return: 4.5,
    entry_at: '2026-07-01T12:00:00',
    evaluation_at: '2026-07-08T12:00:00',
    ...overrides,
  }
}

function payload(records, meta = {}) {
  return {
    recommendation_intelligence_records: records,
    meta: { total: records.length, limit: 10000, truncated: false, read_only: true, ...meta },
  }
}

describe('recommendationOutcomes — exact identity and indexing', () => {
  it('indexes outcomes only by exact recommendation_id and preserves horizons', () => {
    const index = indexOutcomeRows([
      record(),
      record({ outcome_id: 502, horizon_days: 30, status: 'Failed' }),
      record({ recommendation_id: 12, outcome_id: 503, horizon_days: 90 }),
    ])
    expect(index.get(11).map((row) => row.horizonDays)).toEqual([7, 30])
    expect(index.get(12).map((row) => row.horizonDays)).toEqual([90])
  })

  it('never links by ticker alone when the exact run/ticker identity is absent', () => {
    const rows = [
      { id: 'same-run', runId: 101, ticker: 'AAPL' },
      { id: 'other-run', runId: 999, ticker: 'AAPL' },
    ]
    const enriched = enrichRecommendationRows(rows, payload([record()]))
    expect(enriched[0].recommendationId).toBe(11)
    expect(enriched[0].outcomeEvidence.latestResult).toBe('Correct')
    expect(enriched[1].recommendationId).toBeNull()
    expect(enriched[1].outcomeEvidence.latestResult).toBe('Unavailable')
  })

  it('does not guess when a run/ticker identity maps to multiple recommendations', () => {
    const source = payload([
      record(),
      record({ recommendation_id: 99, outcome_id: 999 }),
    ])
    const [enriched] = enrichRecommendationRows([{ runId: 101, ticker: 'AAPL' }], source)
    expect(enriched.recommendationId).toBeNull()
    expect(enriched.outcomeEvidence.outcomeStatus).toBe('Unavailable')
  })
})

describe('recommendationOutcomes — status and latest-completed semantics', () => {
  it('selects latest completed deterministically by evaluation time then outcome id', () => {
    const rows = [
      record(),
      record({ outcome_id: 502, horizon_days: 30, status: 'Failed', evaluation_at: '2026-07-31T12:00:00' }),
      record({ outcome_id: 503, horizon_days: 90, status: 'Succeeded', evaluation_at: '2026-07-31T12:00:00' }),
    ]
    const evidence = buildOutcomeEvidence(11, indexOutcomeRows(rows))
    expect(evidence.latestCompletedHorizon).toBe(90)
    expect(evidence.latestCompletedResult).toBe('Correct')
    expect(evidence.counts.completed).toBe(3)
  })

  it('derives Correct and Incorrect only from stored Succeeded and Failed statuses', () => {
    expect(outcomeResult('Succeeded')).toBe('Correct')
    expect(outcomeResult('Failed')).toBe('Incorrect')
    expect(outcomeResult('Pending')).toBe('Pending')
    expect(outcomeResult('Deferred')).toBe('Deferred')
    expect(outcomeResult('Expired')).toBe('Expired')
  })

  it('never labels Pending, Deferred, or Expired as incorrect', () => {
    for (const [status, expected] of [
      ['Pending', 'Pending'],
      ['Deferred', 'Deferred'],
      ['Expired', 'Expired'],
    ]) {
      const evidence = buildOutcomeEvidence(
        11,
        indexOutcomeRows([record({ status, success: false, percentage_return: null })]),
      )
      expect(evidence.latestResult).toBe(expected)
      expect(evidence.latestResult).not.toBe('Incorrect')
    }
  })

  it('keeps a successful AVOID negative return raw and interpretable', () => {
    const normalized = normalizeOutcomeRow(record({ action: 'AVOID', percentage_return: -8 }))
    const evidence = buildOutcomeEvidence(11, indexOutcomeRows([record({ action: 'AVOID', percentage_return: -8 })]))
    expect(normalized.action).toBe('AVOID')
    expect(normalized.rawReturn).toBe(-8)
    expect(evidence.latestResult).toBe('Correct')
    expect(evidence.latestRawReturn).toBe(-8)
  })

  it('returns Not evaluated for an exact recommendation record with no outcomes', () => {
    const emptyRecord = record({ outcome_id: null, horizon_days: null, status: null, percentage_return: null, evaluation_at: null })
    const [enriched] = enrichRecommendationRows([{ runId: 101, ticker: 'AAPL' }], payload([emptyRecord]))
    expect(enriched.recommendationId).toBe(11)
    expect(enriched.outcomeEvidence.hasOutcomes).toBe(false)
    expect(enriched.outcomeEvidence.latestResult).toBe('Not evaluated')
    expect(enriched.outcomeEvidence.latestRawReturn).toBeNull()
  })
})

describe('recommendationOutcomes — malformed, duplicate, and bounded sources', () => {
  it('deduplicates exact outcome rows and safely ignores malformed identities', () => {
    const partial = record({ outcome_id: 700, percentage_return: null })
    const complete = record({ outcome_id: 700, percentage_return: 3.25 })
    const index = indexOutcomeRows([
      partial,
      complete,
      { recommendation_id: null, status: 'Succeeded' },
      { recommendation_id: true, status: 'Failed' },
      'malformed',
      null,
    ])
    expect(index.get(11)).toHaveLength(1)
    expect(index.get(11)[0].rawReturn).toBe(3.25)
    expect(index.size).toBe(1)
  })

  it('surfaces source totals and an explicit truncation warning', () => {
    const meta = outcomeSourceMeta(payload([record()], { total: 25000, limit: 10000, truncated: true }))
    expect(meta.truncated).toBe(true)
    expect(meta.analyzedRowCount).toBe(1)
    expect(meta.sourceTotalRowCount).toBe(25000)
    expect(meta.warning).toContain('1 of 25000 source rows')
    expect(meta.warning).toContain('may be incomplete')
  })

  it('marks absent horizon badges Unavailable when the source is truncated', () => {
    const [enriched] = enrichRecommendationRows(
      [{ runId: 101, ticker: 'AAPL' }],
      payload([record()], { total: 20000, truncated: true }),
    )
    expect(enriched.outcomeEvidence.horizonBadges.find((badge) => badge.horizonDays === 30).result)
      .toBe('Unavailable')
  })
})

describe('recommendationOutcomes — Explorer, Memory, drawer, and badges', () => {
  it('enriches Explorer rows with exact outcome evidence', () => {
    const [row] = enrichRecommendationRows(
      [{ id: 'explorer-row', runId: 101, ticker: 'AAPL', action: 'BUY' }],
      payload([record()]),
    )
    expect(row.recommendationId).toBe(11)
    expect(row.outcomeEvidence).toMatchObject({
      outcomeStatus: 'Succeeded',
      latestCompletedHorizon: 7,
      latestResult: 'Correct',
      latestRawReturn: 4.5,
    })
  })

  it('enriches Research Memory without changing recommendation chronology', () => {
    const rows = [
      { id: 'new', runId: 102, ticker: 'AAPL', at: Date.parse('2026-07-10'), evaluatedAt: '2026-07-10', confidencePct: 80, agreementPct: 80, bucket: 'BUY' },
      { id: 'old', runId: 101, ticker: 'AAPL', at: Date.parse('2026-07-01'), evaluatedAt: '2026-07-01', confidencePct: 70, agreementPct: 70, bucket: 'BUY' },
    ]
    const source = payload([
      record({ evaluation_at: '2026-12-31T12:00:00' }),
      record({ recommendation_id: 12, run_id: 102, outcome_id: 502, evaluation_at: '2026-07-17T12:00:00' }),
    ])
    const timeline = buildTimeline(enrichRecommendationRows(rows, source), 'AAPL')
    expect(timeline.map((event) => event.id)).toEqual(['new', 'old'])
    expect(timeline[1].outcomeEvidence.latestEvaluationAt).toBe('2026-12-31T12:00:00')
  })

  it('builds the drawer model from the per-recommendation outcome payload', () => {
    const model = buildDrawerOutcomeModel({
      recommendation_outcomes: [
        {
          id: 501,
          recommendation_id: 11,
          ticker: 'AAPL',
          recommendation: 'BUY',
          recommendation_timestamp: '2026-07-01T12:00:00',
          evaluation_timestamp: '2026-07-08T12:00:00',
          horizon_days: 7,
          percentage_return: 4.5,
          status: 'Succeeded',
          evaluation_source: 'paper',
        },
      ],
      meta: { recommendation_id: 11, count: 1, read_only: true },
    })
    expect(model).toMatchObject({
      recommendationId: 11,
      latestCompletedResult: 'Correct',
      latestRawReturn: 4.5,
      entryAt: '2026-07-01T12:00:00',
      evaluationSource: 'paper',
    })
  })

  it('handles null and partial drawer payloads without invented evidence', () => {
    expect(buildDrawerOutcomeModel(null).latestResult).toBe('Unavailable')
    const partial = buildDrawerOutcomeModel({
      recommendation_outcomes: null,
      meta: { recommendation_id: 11 },
    })
    expect(partial.recommendationId).toBe(11)
    expect(partial.latestResult).toBe('Unavailable')
    expect(partial.latestRawReturn).toBeNull()
  })

  it('maps exactly the 7/30/90/180/365 compact badge horizons', () => {
    const rows = OUTCOME_HORIZONS.map((horizon, index) => record({
      outcome_id: 600 + index,
      horizon_days: horizon,
      evaluation_at: `2026-${String(index + 1).padStart(2, '0')}-10T12:00:00`,
    }))
    const evidence = buildOutcomeEvidence(11, indexOutcomeRows(rows))
    expect(evidence.horizonBadges.map((badge) => badge.horizonDays)).toEqual([7, 30, 90, 180, 365])
    expect(evidence.horizonBadges.map((badge) => badge.label)).toEqual(['7d', '30d', '90d', '180d', '365d'])
  })
})
