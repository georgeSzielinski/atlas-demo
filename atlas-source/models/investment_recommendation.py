from dataclasses import dataclass, field


@dataclass
class InvestmentRecommendation:
    ticker: str

    action: str

    confidence: int

    reasons: list[str] = field(default_factory=list)

    risks: list[str] = field(default_factory=list)

    score: int = 0

    technical_score: int = 0

    fundamental_score: int = 0

    portfolio_score: int = 0

    risk_score: int = 0

    forecast_score: int = 0

    forecast_direction: str = ""

    forecast_confidence: int = 0

    expected_change: float = 0.0

    overall_score: int = 0

    rating: str = ""

    news_sentiment: str = ""

    news_confidence: int = 0

    headline_count: int = 0

    news_summary: str = ""

    signal_quality_score: int = 0

    signal_label: str = ""

    false_positive_warnings: list[str] = field(default_factory=list)

    evidence_breakdown: list[dict] = field(default_factory=list)

    confidence_metadata: list[dict] = field(default_factory=list)

    validation_status: str = "Pending"

    fusion: dict = field(default_factory=dict)

    overall_conviction: float = 0.0

    fusion_summary: str = ""

    investment_committee: dict = field(default_factory=dict)

    committee_members: list[dict] = field(default_factory=list)

    committee_bull_case: list[str] = field(default_factory=list)

    committee_bear_case: list[str] = field(default_factory=list)

    committee_neutral_case: list[str] = field(default_factory=list)

    committee_agreement: float = 0.0

    bullish_members: list[str] = field(default_factory=list)

    bearish_members: list[str] = field(default_factory=list)

    neutral_members: list[str] = field(default_factory=list)

    strongest_bull_argument: str = ""

    strongest_bear_argument: str = ""

    main_disagreement: str = ""

    final_committee_summary: str = ""

    top_positive_factors: list[str] = field(default_factory=list)

    top_negative_factors: list[str] = field(default_factory=list)

    missing_evidence: list[str] = field(default_factory=list)

    suggested_follow_up_research: list[str] = field(default_factory=list)

    confidence_explanation: str = ""

    evidence_summary: str = ""

    assumptions: list[str] = field(default_factory=list)

    strongest_assumption: str = ""

    weakest_assumption: str = ""

    counterfactuals: list[dict] = field(default_factory=list)

    recommendation_flip_conditions: list[str] = field(default_factory=list)

    confidence_drivers: list[dict] = field(default_factory=list)

    executive_review: dict = field(default_factory=dict)

    executive_status: str = ""

    executive_confidence: int = 0

    executive_summary: str = ""

    executive_warnings: list[str] = field(default_factory=list)

    executive_strengths: list[str] = field(default_factory=list)

    executive_weaknesses: list[str] = field(default_factory=list)

    required_follow_up_research: list[str] = field(default_factory=list)

    stability_score: int = 0

    stability_level: str = ""

    most_sensitive_factor: str = ""

    stability_explanation: str = ""

    knowledge_score: int = 0

    knowledge_level: str = ""

    knowledge_explanation: str = ""

    def summary(self):
        return (
            f"{self.ticker} | "
            f"{self.action} | "
            f"{self.confidence}% Confidence | "
            f"Forecast: {self.forecast_score} | "
            f"Overall: {self.overall_score} | "
            f"{self.rating}"
        )
