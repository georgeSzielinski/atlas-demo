"""Additive response contracts for public Learning Intelligence APIs."""

from typing import Any

from pydantic import BaseModel, ConfigDict


Metric = int | float


class ContractModel(BaseModel):
    """Validate stable contract fields without coercing serialized values."""

    model_config = ConfigDict(extra="forbid", strict=True)


class ExtensionModel(ContractModel):
    """Preserve partially modeled analytics and stored-evidence fields."""

    model_config = ConfigDict(extra="allow", strict=True)


class LearningCenterSummary(ContractModel):
    overall_recommendation_accuracy: Metric | None
    recommendation_volume: int
    completed_evaluations: int
    pending_evaluations: int
    deferred_evaluations: int
    expired_evaluations: int
    outcome_completion_rate: Metric | None
    recommendation_coverage: Metric | None
    data_maturity: str
    average_return: Metric | None
    accuracy_scope: str | None = None
    multiple_horizons_weight_separately: bool | None = None
    unique_recommendation_accuracy: str | None = None
    accuracy_evaluations: int | None = None
    return_sample_size: int | None = None


class LearningCenterCalibration(ExtensionModel):
    status: str
    expected_confidence: Metric | None
    observed_accuracy: Metric | None
    calibration_gap: Metric | None
    sample_size: int
    minimum_sample_size: int
    minimum_sample_warning: str | None
    reliability_buckets: list[dict[str, Any]]


class RecommendationLearningMetric(ContractModel):
    recommendation_id: int
    committee: str | None
    committee_historical_accuracy: Metric | None
    primary_engine: str | None
    engine_historical_accuracy: Metric | None
    calibration_gap: Metric | None
    evaluation_maturity: Metric | None
    recommendation_maturity: str
    outcome_maturity: Metric | None
    evaluation_coverage: Metric | None
    completion_rate: Metric | None


class LearningLeaderboardSection(ExtensionModel):
    status: str
    leaderboard: list[dict[str, Any]]
    data: dict[str, Any]


class LearningSignalIntelligence(ContractModel):
    status: str
    groups: list[dict[str, Any]]
    unavailable: list[dict[str, Any]]


class LearningDimensionIntelligence(ContractModel):
    status: str
    reason: str | None
    groups: list[dict[str, Any]]


class LearningSystemHealth(ContractModel):
    calibration: str
    committee_analytics: str
    data_freshness: str | None
    data_maturity: str
    deterministic_status: str
    engine_analytics: str
    outcome_evidence: str
    paper_only_status: str
    read_only_status: str


class LearningEvidenceQuality(ContractModel):
    status: str
    evaluation_source_coverage: Metric | None
    price_lineage_coverage: Metric | None
    sample_size: int


class LearningCenterSourceData(ExtensionModel):
    analyzed_row_count: int
    selected_recommendation_count: int
    source_total_row_count: int
    limit: int | None
    truncated: bool
    warning: str | None


class LearningCenterPolicy(ContractModel):
    deterministic: bool
    read_only: bool
    paper_only: bool
    uses_ai: bool
    writes: bool
    automatic_execution: bool
    changes_recommendation_behavior: bool
    changes_committee_behavior: bool
    changes_scheduler_behavior: bool
    changes_trading_behavior: bool


class LearningCenterReport(ContractModel):
    generated_at: str
    version: str
    status: str
    reason: str | None
    summary: LearningCenterSummary
    rolling_accuracy: list[dict[str, Any]]
    best_recommendations: list[dict[str, Any]]
    worst_recommendations: list[dict[str, Any]]
    outcome_distribution: list[dict[str, Any]]
    historical_recommendation_volume: list[dict[str, Any]]
    evaluation_maturity_by_horizon: list[dict[str, Any]]
    confidence_calibration: LearningCenterCalibration
    committee_intelligence: LearningLeaderboardSection
    engine_intelligence: LearningLeaderboardSection
    signal_intelligence: LearningSignalIntelligence
    sector_intelligence: LearningDimensionIntelligence
    regime_intelligence: LearningDimensionIntelligence
    system_health: LearningSystemHealth
    evidence_quality: LearningEvidenceQuality
    recommendation_metrics: list[RecommendationLearningMetric]
    selectors: dict[str, Any]
    data: LearningCenterSourceData
    policy: LearningCenterPolicy


class LearningCenterResponse(ContractModel):
    learning_center: LearningCenterReport


class LearningCenterStatus(ContractModel):
    status: str
    reason: str | None
    summary: LearningCenterSummary
    committee_analytics_health: str
    engine_analytics_health: str
    truncated: bool
    warning: str | None
    policy: LearningCenterPolicy
    committee_leader: dict[str, Any] | None = None
    engine_leader: dict[str, Any] | None = None
    calibration_health: str | None = None
    rolling_accuracy: Metric | None = None
    data_freshness: str | None = None
    analyzed_row_count: int | None = None
    source_total_row_count: int | None = None
    deterministic: bool | None = None
    paper_only: bool | None = None


class LearningCenterStatusResponse(ContractModel):
    learning_center_status: LearningCenterStatus


class RecommendationIntelligenceFilters(ContractModel):
    ticker: str | None
    action: str | None
    horizon: int | None
    evaluation_source: str | None


class BoundedRecommendationRecordsMetadata(ContractModel):
    total: int
    limit: int
    truncated: bool
    filters: RecommendationIntelligenceFilters
    read_only: bool


class RecommendationIntelligenceRecord(ExtensionModel):
    recommendation_id: int
    run_id: int | None
    ticker: str | None
    action: str | None
    confidence: Metric | None
    recommendation_at: str | None
    entry_at: str | None
    outcome_id: int | None
    horizon_days: int | None
    evaluation_source: str | None
    status: str | None
    success: bool | None
    percentage_return: Metric | None
    evaluation_at: str | None
    committee_members: list[Any]
    evidence_breakdown: list[Any]


class RecommendationIntelligenceRecordsResponse(ContractModel):
    recommendation_intelligence_records: list[RecommendationIntelligenceRecord]
    meta: BoundedRecommendationRecordsMetadata


class RecommendationOutcome(ExtensionModel):
    id: int
    recommendation_id: int
    ticker: str | None
    recommendation: str | None
    recommendation_timestamp: str | None
    evaluation_timestamp: str | None
    horizon_days: int | None
    percentage_return: Metric | None
    success: bool | int | None
    status: str | None
    evaluation_source: str | None


class RecommendationOutcomesMetadata(ContractModel):
    recommendation_id: int
    count: int
    read_only: bool


class RecommendationOutcomesResponse(ContractModel):
    recommendation_outcomes: list[RecommendationOutcome]
    meta: RecommendationOutcomesMetadata
