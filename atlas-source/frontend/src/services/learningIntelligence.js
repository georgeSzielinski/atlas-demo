// Pure selectors for the bounded, read-only Learning Intelligence APIs.

export const LEARNING_RESOURCE_KEY = 'learning-center/default'
export const LEARNING_STATUS_RESOURCE_KEY = 'learning-center/status'
export const LEARNING_RECORD_LIMIT = 10000

function numberOrNull(value) {
  if (value === null || value === undefined || value === '' || typeof value === 'boolean') return null
  const number = Number(value)
  return Number.isFinite(number) ? number : null
}

function directReport(payload) {
  if (!payload || typeof payload !== 'object') return null
  const report = payload.learning_center ?? payload
  return report && typeof report === 'object' ? report : null
}

export function indexRecommendationLearning(payload) {
  const report = directReport(payload)
  const index = new Map()
  const rows = Array.isArray(report?.recommendation_metrics)
    ? report.recommendation_metrics
    : []
  for (const row of rows) {
    if (!row || row.recommendation_id === null || row.recommendation_id === undefined) continue
    const key = String(row.recommendation_id)
    if (index.has(key)) continue
    index.set(key, {
      recommendationId: row.recommendation_id,
      committee: row.committee ?? null,
      committeeHistoricalAccuracy: numberOrNull(row.committee_historical_accuracy),
      primaryEngine: row.primary_engine ?? null,
      engineHistoricalAccuracy: numberOrNull(row.engine_historical_accuracy),
      calibrationGap: numberOrNull(row.calibration_gap),
      evaluationMaturity: numberOrNull(row.evaluation_maturity),
      recommendationMaturity: row.recommendation_maturity ?? 'NOT_EVALUATED',
      outcomeMaturity: numberOrNull(row.outcome_maturity),
      evaluationCoverage: numberOrNull(row.evaluation_coverage),
      completionRate: numberOrNull(row.completion_rate),
    })
  }
  return index
}

export function enrichRowsWithLearning(rows, payload) {
  const list = Array.isArray(rows) ? rows : []
  const index = indexRecommendationLearning(payload)
  return list.map((row) => {
    const recommendationId = row?.recommendationId
    const learningIntelligence = recommendationId === null || recommendationId === undefined
      ? null
      : index.get(String(recommendationId)) ?? null
    return { ...row, learningIntelligence }
  })
}

export function learningSourceMeta(payload) {
  const report = directReport(payload)
  const data = report?.data ?? {}
  return {
    truncated: Boolean(data.truncated),
    analyzedRowCount: numberOrNull(data.analyzed_row_count) ?? 0,
    sourceTotalRowCount: numberOrNull(data.source_total_row_count) ?? 0,
    warning: data.warning ?? null,
  }
}

export function buildLearningCenterModel(payload) {
  const report = directReport(payload)
  const summary = report?.summary ?? {}
  const calibration = report?.confidence_calibration ?? {}
  const committee = report?.committee_intelligence ?? {}
  const engines = report?.engine_intelligence ?? {}
  return {
    status: report?.status ?? 'NOT_EVALUATED',
    reason: report?.reason ?? 'Learning Intelligence is unavailable.',
    generatedAt: report?.generated_at ?? null,
    summary: {
      accuracy: numberOrNull(summary.overall_recommendation_accuracy),
      recommendationVolume: numberOrNull(summary.recommendation_volume) ?? 0,
      completed: numberOrNull(summary.completed_evaluations) ?? 0,
      pending: numberOrNull(summary.pending_evaluations) ?? 0,
      deferred: numberOrNull(summary.deferred_evaluations) ?? 0,
      expired: numberOrNull(summary.expired_evaluations) ?? 0,
      completionRate: numberOrNull(summary.outcome_completion_rate),
      coverage: numberOrNull(summary.recommendation_coverage),
      dataMaturity: summary.data_maturity ?? 'NOT_EVALUATED',
      averageReturn: numberOrNull(summary.average_return),
      returnSampleSize: numberOrNull(summary.return_sample_size) ?? 0,
    },
    rollingAccuracy: Array.isArray(report?.rolling_accuracy) ? report.rolling_accuracy : [],
    best: Array.isArray(report?.best_recommendations) ? report.best_recommendations : [],
    worst: Array.isArray(report?.worst_recommendations) ? report.worst_recommendations : [],
    distribution: Array.isArray(report?.outcome_distribution) ? report.outcome_distribution : [],
    volume: Array.isArray(report?.historical_recommendation_volume)
      ? report.historical_recommendation_volume
      : [],
    horizonMaturity: Array.isArray(report?.evaluation_maturity_by_horizon)
      ? report.evaluation_maturity_by_horizon
      : [],
    calibration: {
      status: calibration.status ?? 'NOT_EVALUATED',
      expectedConfidence: numberOrNull(calibration.expected_confidence),
      observedAccuracy: numberOrNull(calibration.observed_accuracy),
      gap: numberOrNull(calibration.calibration_gap),
      sampleSize: numberOrNull(calibration.sample_size) ?? 0,
      minimumSample: numberOrNull(calibration.minimum_sample_size),
      warning: calibration.minimum_sample_warning ?? calibration.statistical_warning ?? null,
      buckets: Array.isArray(calibration.reliability_buckets)
        ? calibration.reliability_buckets
        : [],
    },
    committeeLeaderboard: Array.isArray(committee.leaderboard) ? committee.leaderboard : [],
    engineLeaderboard: Array.isArray(engines.leaderboard) ? engines.leaderboard : [],
    engineAssociationNotice: engines.data?.association_notice ?? null,
    signals: report?.signal_intelligence ?? { status: 'NOT_EVALUATED', groups: [], unavailable: [] },
    sectors: report?.sector_intelligence ?? { status: 'NOT_EVALUATED', groups: [] },
    regimes: report?.regime_intelligence ?? { status: 'NOT_EVALUATED', groups: [] },
    systemHealth: report?.system_health ?? {},
    evidenceQuality: report?.evidence_quality ?? { status: 'NOT_EVALUATED' },
    source: learningSourceMeta(report),
    policy: report?.policy ?? {},
  }
}

export function buildDrawerLearningModel(payload, recommendationId) {
  const model = buildLearningCenterModel(payload)
  const index = indexRecommendationLearning(payload)
  const context = recommendationId === null || recommendationId === undefined
    ? null
    : index.get(String(recommendationId)) ?? null
  return {
    status: context ? 'EVALUATED' : 'NOT_EVALUATED',
    context,
    historicalAccuracy: model.summary.accuracy,
    calibrationStatus: model.calibration.status,
    calibrationGap: context?.calibrationGap ?? model.calibration.gap,
    evidenceQuality: model.evidenceQuality,
    source: model.source,
  }
}

export function buildLearningStatusModel(payload) {
  const status = payload?.learning_center_status ?? payload ?? {}
  const summary = status.summary ?? {}
  return {
    status: status.status ?? 'Unavailable',
    accuracy: numberOrNull(summary.overall_recommendation_accuracy),
    rollingAccuracy: numberOrNull(status.rolling_accuracy),
    completed: numberOrNull(summary.completed_evaluations) ?? 0,
    pending: numberOrNull(summary.pending_evaluations) ?? 0,
    coverage: numberOrNull(summary.recommendation_coverage),
    maturity: summary.data_maturity ?? 'NOT_EVALUATED',
    committeeHealth: status.committee_analytics_health ?? 'Unavailable',
    engineHealth: status.engine_analytics_health ?? 'Unavailable',
    committeeLeader: status.committee_leader ?? null,
    engineLeader: status.engine_leader ?? null,
    calibrationHealth: status.calibration_health ?? 'NOT_EVALUATED',
    dataFreshness: status.data_freshness ?? null,
    truncated: Boolean(status.truncated),
    warning: status.warning ?? null,
    deterministic: status.deterministic === true,
    paperOnly: status.paper_only === true,
  }
}
