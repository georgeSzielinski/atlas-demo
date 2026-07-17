import os
import tempfile

import database.connection as connection
from api.main import institutional_report
from database.migrator import run_migrations
from engines.institutional_report_engine import InstitutionalReportEngine
from engines.markdown_report_engine import MarkdownReportEngine


recommendation = {
    "id": 1,
    "ticker": "AAPL",
    "action": "BUY",
    "confidence": 82,
    "score": 5,
    "rating": "Strong",
    "technical_score": 84,
    "fundamental_score": 88,
    "portfolio_score": 70,
    "risk_score": 66,
    "forecast_score": 78,
    "forecast_direction": "Up",
    "forecast_confidence": 74,
    "expected_change": 3.5,
    "overall_score": 83,
    "news_sentiment": "Positive",
    "news_confidence": 71,
    "headline_count": 4,
    "news_summary": "Mock positive product and earnings headlines.",
    "signal_quality_score": 8,
    "signal_label": "Strong",
    "false_positive_warnings": ["Valuation sensitivity"],
    "evidence_breakdown": [
        {"category": "Fundamentals", "score": 88, "confidence": 85},
        {"category": "Forecast", "score": 78, "confidence": 74},
        {"category": "Technical", "score": 84, "confidence": 80},
    ],
    "validation_status": "Succeeded",
    "overall_conviction": 81,
    "bull_case": ["Strong fundamentals", "Positive forecast"],
    "bear_case": ["Valuation risk"],
    "committee_bull_case": ["Committee supports upside"],
    "committee_bear_case": ["Risk manager flags valuation"],
    "committee_agreement": 86,
    "bullish_members": ["Fundamental Analyst", "Forecast Analyst"],
    "bearish_members": ["Risk Manager"],
    "neutral_members": ["Portfolio Manager"],
    "final_committee_summary": "Committee agreement is high.",
    "confidence_explanation": "Confidence is supported by strong evidence.",
    "assumptions": ["Fundamentals remain stable"],
    "counterfactuals": [{"scenario": "Revenue miss", "impact": "Lower confidence"}],
    "recommendation_flip_conditions": ["Risk score falls below threshold"],
    "executive_status": "READY",
    "executive_confidence": 84,
    "executive_summary": "Executive review is ready.",
    "executive_warnings": ["Monitor valuation"],
    "stability_score": 79,
    "stability_level": "Stable",
    "most_sensitive_factor": "Fundamental score",
    "stability_explanation": "Recommendation is stable across major inputs.",
    "knowledge_score": 91,
    "knowledge_level": "High",
    "knowledge_explanation": "Atlas has strong evidence depth.",
    "catalysts": [
        {
            "event_type": "Earnings",
            "event_date": "2026-07-25",
            "description": "Mock earnings catalyst.",
        }
    ],
    "risks": ["Valuation compression"],
    "probability_report": {
        "probabilities": {
            "outperformance": 65,
            "market_performance": 25,
            "underperformance": 10,
        },
        "expected_outcome": {
            "expected_return": 6.5,
            "expected_holding_period": 45,
            "best_case": 12,
            "base_case": 6,
            "worst_case": -4,
        },
        "confidence_quality": {
            "sample_size": 2,
            "uncertainty_level": "High",
        },
    },
    "validation_result": {
        "success": True,
        "hit": True,
        "percentage_return": 8,
        "holding_period": 45,
        "status": "Succeeded",
    },
}

history = [
    recommendation,
    {
        **recommendation,
        "id": 2,
        "ticker": "MSFT",
        "validation_result": {
            "success": False,
            "hit": False,
            "percentage_return": -3,
            "holding_period": 30,
            "status": "Failed",
        },
    },
]
source_data = {
    "recommendations": history,
    "case_studies": [],
    "benchmark_results": [],
    "provider_results": [],
    "research_experiments": [],
}

report = InstitutionalReportEngine().generate(
    "AAPL",
    source_data=source_data,
    generation_time="2026-06-30T17:00:00",
)

assert report["ticker"] == "AAPL"
assert report["metadata"]["generation_time"] == "2026-06-30T17:00:00"
assert report["metadata"]["report_version"] == "1.0"
assert "ProviderRegistry" in report["metadata"]["data_sources_used"]
assert report["metadata"]["provider_health_snapshot"]["total_providers"] > 0
assert report["policy"]["uses_llm"] is False
assert report["policy"]["changes_recommendation_behavior"] is False
assert report["pdf_placeholder"]["available"] is False
assert report["html_placeholder"]["available"] is False

section_titles = [section["title"] for section in report["sections"]]
assert section_titles == InstitutionalReportEngine.SECTION_ORDER
assert len(section_titles) == 24
assert report["sections"][0]["title"] == "Executive Summary"
assert report["sections"][1]["data"]["action"] == "BUY"
assert report["sections"][2]["data"]["outperformance"] == 65
assert report["sections"][11]["title"] == "SEC Highlights"
assert report["sections"][11]["data"]["filing_count"] == 5
assert report["sections"][17]["title"] == "Historical Analogs"
assert report["sections"][22]["title"] == "Research Memory"
assert report["sections"][23]["title"] == "Appendix"

chart_names = [chart["name"] for chart in report["charts"]]
assert chart_names == [
    "Probability Distribution",
    "Evidence Breakdown",
    "Catalyst Timeline",
    "Historical Return Distribution",
    "Committee Agreement",
]
assert report["charts"][0]["data"][0] == {
    "label": "outperformance",
    "value": 65,
}
assert report["charts"][4]["data"][0]["value"] == 86

markdown = MarkdownReportEngine().institutional_markdown(report)
assert markdown == report["markdown"]
assert "# Atlas Institutional Research Report: AAPL" in markdown
assert "## Executive Summary" in markdown
assert "## Appendix" in markdown
assert "## Structured Data Placeholders" in markdown
assert "Future PDF renderer placeholder" in markdown

original_database_path = connection.DATABASE_PATH
with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as database_file:
    database_path = database_file.name

try:
    connection.DATABASE_PATH = database_path
    connection._wal_initialized_paths.discard(database_path)
    run_migrations()
    api_report = institutional_report("AAPL")
    assert api_report["ticker"] == "AAPL"
    assert [section["title"] for section in api_report["sections"]] == (
        InstitutionalReportEngine.SECTION_ORDER
    )
    assert api_report["policy"]["changes_recommendation_behavior"] is False
finally:
    connection.DATABASE_PATH = original_database_path
    connection._wal_initialized_paths.discard(database_path)
    for candidate in (database_path, f"{database_path}-wal", f"{database_path}-shm"):
        if os.path.exists(candidate):
            os.remove(candidate)

assert recommendation["action"] == "BUY"

print("InstitutionalReportEngine test passed.")
