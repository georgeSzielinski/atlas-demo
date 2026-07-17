from engines.evidence_engine import EvidenceEngine
from engines.discovery_engine import DiscoveryEngine
from engines.performance_observatory import PerformanceObservatory
from engines.research_engine import ResearchEngine
from models.investment_recommendation import InvestmentRecommendation


recommendation = InvestmentRecommendation(
    ticker="AAPL",
    action="BUY",
    confidence=80,
    technical_score=85,
    fundamental_score=70,
    forecast_score=65,
    news_confidence=50,
    portfolio_score=75,
    risk_score=80,
    signal_quality_score=8,
)

evidence = EvidenceEngine().build(recommendation)
names = [item["name"] for item in evidence]

assert names == [
    "Technical",
    "Fundamental",
    "Forecast",
    "News",
    "Portfolio",
    "Risk",
    "Validation",
    "Benchmark",
]

for item in evidence:
    assert set(item.keys()) == {
        "name",
        "category",
        "score",
        "confidence",
        "weight",
        "label",
        "reason",
        "summary",
        "confidence_metadata",
    }
    assert 0 <= item["score"] <= 100
    assert 0 <= item["confidence"] <= 100
    assert item["weight"] > 0
    assert item["label"]
    assert item["reason"]
    assert item["summary"]

historical_recommendations = [
    {
        "ticker": "AAA",
        "date": "2026-01-01",
        "committee_agreement": 82,
        "executive_status": "READY",
        "executive_confidence": 60,
        "discovery_score": 60,
        "evidence_breakdown": [
            {"category": "Technical", "score": 82, "confidence": 80},
            {"category": "Fundamental", "score": 100, "confidence": 100},
            {"category": "Forecast", "score": 45, "confidence": 45},
            {"category": "News", "score": 50, "confidence": 50},
            {"category": "Portfolio", "score": 60, "confidence": 60},
            {"category": "Risk", "score": 60, "confidence": 60},
            {"category": "Validation", "score": 60, "confidence": 60},
        ],
        "validation_result": {
            "success": True,
            "hit": True,
            "percentage_return": 10,
        },
    },
    {
        "ticker": "BBB",
        "date": "2026-02-01",
        "committee_agreement": 78,
        "executive_status": "READY",
        "executive_confidence": 60,
        "discovery_score": 60,
        "evidence_breakdown": [
            {"category": "Technical", "score": 78, "confidence": 78},
            {"category": "Fundamental", "score": 100, "confidence": 100},
            {"category": "Forecast", "score": 48, "confidence": 48},
            {"category": "News", "score": 52, "confidence": 52},
            {"category": "Portfolio", "score": 60, "confidence": 60},
            {"category": "Risk", "score": 60, "confidence": 60},
            {"category": "Validation", "score": 60, "confidence": 60},
        ],
        "validation_result": {
            "success": True,
            "hit": True,
            "percentage_return": 8,
        },
    },
    {
        "ticker": "CCC",
        "date": "2026-03-01",
        "committee_agreement": 42,
        "executive_status": "NEEDS_REVIEW",
        "executive_confidence": 40,
        "discovery_score": 50,
        "evidence_breakdown": [
            {"category": "Technical", "score": 45, "confidence": 45},
            {"category": "Fundamental", "score": 55, "confidence": 55},
            {"category": "Forecast", "score": 75, "confidence": 75},
            {"category": "News", "score": 82, "confidence": 82},
            {"category": "Portfolio", "score": 48, "confidence": 48},
            {"category": "Risk", "score": 50, "confidence": 50},
            {"category": "Validation", "score": 45, "confidence": 45},
        ],
        "validation_result": {
            "success": False,
            "hit": False,
            "percentage_return": -4,
        },
    },
    {
        "ticker": "DDD",
        "date": "2026-04-01",
        "committee_agreement": 48,
        "executive_status": "CAUTION",
        "executive_confidence": 55,
        "discovery_score": 55,
        "evidence_breakdown": [
            {"category": "Technical", "score": 52, "confidence": 52},
            {"category": "Fundamental", "score": 58, "confidence": 58},
            {"category": "Forecast", "score": 88, "confidence": 88},
            {"category": "News", "score": 78, "confidence": 78},
            {"category": "Portfolio", "score": 45, "confidence": 45},
            {"category": "Risk", "score": 44, "confidence": 44},
            {"category": "Validation", "score": 42, "confidence": 42},
        ],
        "validation_result": {
            "success": True,
            "hit": True,
            "percentage_return": 12,
        },
    },
    {
        "ticker": "EEE",
        "date": "2026-05-01",
        "committee_agreement": 50,
        "executive_status": "NEEDS_REVIEW",
        "executive_confidence": 45,
        "discovery_score": 45,
        "evidence_breakdown": [
            {"category": "Forecast", "score": 80, "confidence": 80},
        ],
        "validation_result": {
            "success": True,
            "hit": True,
            "percentage_return": 8,
        },
    },
    {
        "ticker": "FFF",
        "date": "2026-06-01",
        "committee_agreement": 52,
        "executive_status": "NEEDS_REVIEW",
        "executive_confidence": 45,
        "discovery_score": 45,
        "evidence_breakdown": [
            {"category": "Forecast", "score": 82, "confidence": 82},
        ],
        "validation_result": {
            "success": True,
            "hit": True,
            "percentage_return": 9,
        },
    },
]

observatory = PerformanceObservatory()
report = observatory.evidence_contribution_report(historical_recommendations)
categories = {item["category"]: item for item in report["categories"]}

assert set(categories.keys()) == {
    "Technical",
    "Fundamentals",
    "Forecast",
    "News",
    "Portfolio",
    "Risk",
    "Committee",
    "Executive Review",
    "Validation",
    "Discovery",
}
assert categories["Fundamentals"]["sample_size"] == 2
assert categories["Fundamentals"]["average_return"] == 9
assert categories["Fundamentals"]["hit_rate"] == 100
assert categories["News"]["average_return"] == 4
assert categories["Forecast"]["sample_size"] == 4
assert categories["Forecast"]["average_return"] == 6.25
assert report["strongest_evidence_category"] == "Fundamentals"
assert report["weakest_evidence_category"] in {"News", "Forecast"}
assert report["automatic_behavior_changes"] is False
assert report["evidence_rankings"][0]["category"] == "Fundamentals"

source_data = {"recommendations": historical_recommendations}
discoveries = DiscoveryEngine().analyze(
    source_data=source_data,
    discovery_date="2026-06-29T12:00:00",
)
descriptions = [item["description"] for item in discoveries]
assert any(
    "Fundamentals outperforms News by 5.0%" in description
    or "Fundamentals outperforms Forecast by 5.0%" in description
    for description in descriptions
)
assert any(
    "Forecast contribution has increased over time" in description
    for description in descriptions
)

research_report = ResearchEngine().evidence_ranking_report(
    historical_recommendations
)
assert research_report["strongest_evidence_category"] == "Fundamentals"
markdown = ResearchEngine().generate_markdown_report({
    "experiment": ResearchEngine().create_experiment(
        title="Evidence Ranking Test",
        description="Rank evidence categories.",
        dataset="unit-test-history",
        ticker_list=["AAA"],
        experiment_date="2026-06-29T12:05:00",
    ),
    "strategy_results": [],
    "provider_results": [],
    "hypothesis_analysis": {},
    "executive_analysis": {},
    "evidence_ranking_report": research_report,
    "knowledge_graph": {},
    "executive_summary": "Evidence ranking report generated.",
    "recommendations": [],
    "next_experiments": [],
    "future_work": [],
})
assert "## Evidence Ranking Report" in markdown
assert "Fundamentals" in markdown

print("EvidenceEngine test passed.")
