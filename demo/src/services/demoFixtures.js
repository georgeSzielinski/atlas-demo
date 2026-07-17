import {
  committeeCycles,
  dashboardV2,
  institutionalReportPayload,
} from './__tests__/fixtures'

function clone(value) {
  return JSON.parse(JSON.stringify(value))
}

function history() {
  const cycles = committeeCycles().map((cycle) => ({
    ...cycle,
    evaluations: cycle.evaluations.map((evaluation, index) => ({
      ...evaluation,
      recommendation_id: cycle.run_id * 100 + index + 1,
      provider: 'fixture',
    })),
  }))
  return { cycles }
}

function outcomeRecords() {
  return {
    recommendation_intelligence_records: [
      {
        recommendation_id: 401,
        run_id: 4,
        ticker: 'AAPL',
        outcome_id: 'fixture-aapl-7d',
        horizon_days: 7,
        status: 'EVALUATED',
        percentage_return: -1.2,
        evaluation_at: '2026-07-15T12:00:00Z',
        evaluation_source: 'fixture',
      },
      {
        recommendation_id: 402,
        run_id: 4,
        ticker: 'MSFT',
        outcome_id: 'fixture-msft-7d',
        horizon_days: 7,
        status: 'EVALUATED',
        percentage_return: 2.4,
        evaluation_at: '2026-07-15T12:00:00Z',
        evaluation_source: 'fixture',
      },
      {
        recommendation_id: 301,
        run_id: 3,
        ticker: 'AAPL',
        outcome_id: 'fixture-aapl-14d',
        horizon_days: 14,
        status: 'EVALUATED',
        percentage_return: 1.1,
        evaluation_at: '2026-07-17T12:00:00Z',
        evaluation_source: 'fixture',
      },
    ],
    meta: {
      read_only: true,
      truncated: false,
      analyzed_row_count: 3,
      source_total_row_count: 3,
    },
  }
}

function learningCenter() {
  return {
    status: 'EVALUATED',
    generated_at: '2026-07-16T12:00:00Z',
    deterministic: true,
    paper_only: true,
    summary: {
      overall_recommendation_accuracy: 0.67,
      recommendation_volume: 6,
      completed_evaluations: 3,
      pending_evaluations: 3,
      deferred_evaluations: 0,
      expired_evaluations: 0,
      outcome_completion_rate: 0.5,
      recommendation_coverage: 0.5,
      data_maturity: 'PARTIAL',
      average_return: 0.77,
      return_sample_size: 3,
    },
    recommendation_metrics: [
      {
        recommendation_id: 401,
        committee: 'fixture committee',
        committee_historical_accuracy: 0.67,
        primary_engine: 'fixture evidence pipeline',
        engine_historical_accuracy: 0.67,
        calibration_gap: 0.12,
        evaluation_maturity: 1,
        recommendation_maturity: 'EVALUATED',
        outcome_maturity: 1,
        evaluation_coverage: 1,
        completion_rate: 1,
      },
      {
        recommendation_id: 402,
        committee: 'fixture committee',
        committee_historical_accuracy: 0.67,
        primary_engine: 'fixture evidence pipeline',
        engine_historical_accuracy: 0.67,
        calibration_gap: -0.04,
        evaluation_maturity: 1,
        recommendation_maturity: 'EVALUATED',
        outcome_maturity: 1,
        evaluation_coverage: 1,
        completion_rate: 1,
      },
    ],
    confidence_calibration: { status: 'EVALUATED', buckets: [] },
    outcome_distribution: [
      { label: 'Positive', count: 2 },
      { label: 'Negative', count: 1 },
    ],
    evaluation_maturity_by_horizon: [
      { horizon_days: 7, evaluated: 2, pending: 1 },
      { horizon_days: 14, evaluated: 1, pending: 2 },
    ],
    committee_intelligence: { status: 'EVALUATED', rows: [] },
    engine_intelligence: { status: 'EVALUATED', rows: [] },
    best_recommendations: [
      { ticker: 'MSFT', percentage_return: 2.4, horizon_days: 7 },
    ],
    worst_recommendations: [
      { ticker: 'AAPL', percentage_return: -1.2, horizon_days: 7 },
    ],
    historical_recommendation_volume: [
      { date: '2026-07-01', count: 2 },
      { date: '2026-07-10', count: 2 },
      { date: '2026-07-14', count: 2 },
    ],
    rolling_accuracy: [
      { date: '2026-07-10', accuracy: 0.5 },
      { date: '2026-07-16', accuracy: 0.67 },
    ],
    system_health: { status: 'EVALUATED', notes: ['Fixture data only'] },
    data: {
      truncated: false,
      analyzed_row_count: 3,
      source_total_row_count: 3,
      warning: null,
    },
  }
}

function learningStatus() {
  return {
    learning_center_status: {
      status: 'EVALUATED',
      deterministic: true,
      paper_only: true,
      summary: {
        overall_recommendation_accuracy: 0.67,
        completed_evaluations: 3,
        pending_evaluations: 3,
        outcome_completion_rate: 0.5,
        recommendation_coverage: 0.5,
        data_maturity: 'PARTIAL',
      },
      rolling_accuracy: 0.67,
      committee_analytics_health: 'EVALUATED',
      engine_analytics_health: 'EVALUATED',
      calibration_health: 'EVALUATED',
      data_freshness: '2026-07-16T12:00:00Z',
    },
  }
}

function reportFor(ticker) {
  const report = institutionalReportPayload()
  report.ticker = ticker
  report.metadata = { ...report.metadata, active_providers: ['fixture'] }
  report.policy = { deterministic: true, uses_llm: false, read_only: true, fixture_only: true }
  return report
}

function outcomesFor(recommendationId) {
  const records = outcomeRecords().recommendation_intelligence_records.filter(
    (row) => String(row.recommendation_id) === String(recommendationId),
  )
  return {
    meta: { recommendation_id: recommendationId, read_only: true, fixture_only: true },
    recommendation_outcomes: records,
  }
}

export function resolveDemoRequest(path, options = {}) {
  const method = (options.method ?? 'GET').toUpperCase()
  if (method !== 'GET') {
    throw new Error('Static Atlas demo is read-only: mutation routes are disabled.')
  }

  const url = new URL(path, 'https://atlas.demo')
  const routes = {
    '/dashboard/v2': dashboardV2,
    '/learning-center/status': learningStatus,
    '/recommendations/history': history,
    '/recommendation-intelligence/records': outcomeRecords,
    '/learning-center': learningCenter,
  }

  if (routes[url.pathname]) return clone(routes[url.pathname]())

  const reportMatch = url.pathname.match(/^\/institutional-report\/(AAPL|MSFT|NVDA)$/)
  if (reportMatch) return clone(reportFor(reportMatch[1]))

  const outcomeMatch = url.pathname.match(/^\/recommendations\/(\d+)\/outcomes$/)
  if (outcomeMatch) return clone(outcomesFor(outcomeMatch[1]))

  throw new Error(`Static Atlas demo has no fixture for ${url.pathname}.`)
}
