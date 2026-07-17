import { describe, expect, it } from 'vitest'
import {
  buildDrawerLearningModel,
  buildLearningCenterModel,
  buildLearningStatusModel,
  enrichRowsWithLearning,
  indexRecommendationLearning,
  learningSourceMeta,
} from '../learningIntelligence'

function payload() {
  return {
    learning_center: {
      status: 'EVALUATED',
      generated_at: '2026-07-15T12:00:00',
      summary: {
        overall_recommendation_accuracy: 62.5,
        recommendation_volume: 8,
        completed_evaluations: 10,
        pending_evaluations: 2,
        deferred_evaluations: 1,
        expired_evaluations: 1,
        outcome_completion_rate: 71.43,
        recommendation_coverage: 75,
        data_maturity: 'LIMITED',
        average_return: 3.2,
        return_sample_size: 8,
      },
      confidence_calibration: {
        status: 'INSUFFICIENT_SAMPLE',
        expected_confidence: 70,
        observed_accuracy: 62.5,
        calibration_gap: 7.5,
        sample_size: 8,
        minimum_sample_size: 20,
        minimum_sample_warning: 'INSUFFICIENT_SAMPLE',
        reliability_buckets: [{ bucket: '70-79', sample_size: 8 }],
      },
      recommendation_metrics: [
        {
          recommendation_id: 42,
          committee: 'Investment Committee',
          committee_historical_accuracy: 62.5,
          primary_engine: 'Technical',
          engine_historical_accuracy: 70,
          calibration_gap: 7.5,
          evaluation_maturity: 40,
          recommendation_maturity: '30d completed',
          outcome_maturity: 40,
          evaluation_coverage: 40,
          completion_rate: 66.67,
        },
        // Duplicate exact id is ignored deterministically.
        { recommendation_id: 42, committee_historical_accuracy: 0 },
        { recommendation_id: null, committee_historical_accuracy: 100 },
      ],
      committee_intelligence: { leaderboard: [{ committee: 'Investment Committee', accuracy: 62.5 }] },
      engine_intelligence: {
        leaderboard: [{ engine: 'Technical', accuracy: 70 }],
        data: { association_notice: 'Association only.' },
      },
      system_health: { deterministic_status: 'CONFIRMED' },
      evidence_quality: { status: 'EVALUATED', price_lineage_coverage: 80 },
      data: {
        truncated: true,
        analyzed_row_count: 10000,
        source_total_row_count: 12000,
        warning: 'Source projection was truncated; analytics may be incomplete.',
      },
      policy: { read_only: true, paper_only: true },
    },
  }
}

describe('learningIntelligence selectors', () => {
  it('indexes only exact recommendation ids and handles duplicates safely', () => {
    const index = indexRecommendationLearning(payload())
    expect(index.size).toBe(1)
    expect(index.get('42')).toMatchObject({
      committeeHistoricalAccuracy: 62.5,
      primaryEngine: 'Technical',
      recommendationMaturity: '30d completed',
    })
  })

  it('never links by ticker alone', () => {
    const rows = enrichRowsWithLearning([
      { id: 'exact', ticker: 'AAPL', recommendationId: 42 },
      { id: 'ticker-only', ticker: 'AAPL', recommendationId: null },
      { id: 'wrong-id', ticker: 'AAPL', recommendationId: 43 },
    ], payload())
    expect(rows[0].learningIntelligence?.engineHistoricalAccuracy).toBe(70)
    expect(rows[1].learningIntelligence).toBeNull()
    expect(rows[2].learningIntelligence).toBeNull()
  })

  it('builds Learning Center and truncation models without zero-filling missing evidence', () => {
    const model = buildLearningCenterModel(payload())
    expect(model.summary.accuracy).toBe(62.5)
    expect(model.summary.pending).toBe(2)
    expect(model.summary.deferred).toBe(1)
    expect(model.calibration.status).toBe('INSUFFICIENT_SAMPLE')
    expect(model.engineAssociationNotice).toBe('Association only.')
    expect(model.source).toEqual({
      truncated: true,
      analyzedRowCount: 10000,
      sourceTotalRowCount: 12000,
      warning: 'Source projection was truncated; analytics may be incomplete.',
    })
    expect(learningSourceMeta(null)).toEqual({
      truncated: false,
      analyzedRowCount: 0,
      sourceTotalRowCount: 0,
      warning: null,
    })
  })

  it('builds the Institutional Report learning model from exact context', () => {
    const model = buildDrawerLearningModel(payload(), 42)
    expect(model.status).toBe('EVALUATED')
    expect(model.historicalAccuracy).toBe(62.5)
    expect(model.context.evaluationCoverage).toBe(40)
    expect(model.evidenceQuality.status).toBe('EVALUATED')
    expect(buildDrawerLearningModel(payload(), 999).status).toBe('NOT_EVALUATED')
  })

  it('handles null and partial payloads honestly', () => {
    const model = buildLearningCenterModel(null)
    expect(model.status).toBe('NOT_EVALUATED')
    expect(model.summary.accuracy).toBeNull()
    expect(model.summary.averageReturn).toBeNull()
    expect(model.summary.completed).toBe(0)
    expect(model.committeeLeaderboard).toEqual([])
    expect(indexRecommendationLearning({ recommendation_metrics: 'bad' }).size).toBe(0)
  })

  it('normalizes Mission and Operations status without fabricating percentages', () => {
    const model = buildLearningStatusModel({
      learning_center_status: {
        status: 'EVALUATED',
        rolling_accuracy: 55,
        summary: {
          overall_recommendation_accuracy: null,
          completed_evaluations: 0,
          pending_evaluations: 3,
          recommendation_coverage: null,
          data_maturity: 'OUTCOMES_PENDING',
        },
        deterministic: true,
        paper_only: true,
      },
    })
    expect(model.accuracy).toBeNull()
    expect(model.rollingAccuracy).toBe(55)
    expect(model.coverage).toBeNull()
    expect(model.pending).toBe(3)
    expect(model.deterministic).toBe(true)
  })
})
