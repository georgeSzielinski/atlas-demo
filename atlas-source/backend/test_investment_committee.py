import os
import tempfile

import database.connection as connection
from database.repository import get_recommendations_for_run, save_recommendations
from database.setup import setup_database
from engines.investment_committee_engine import InvestmentCommitteeEngine
from models.investment_recommendation import InvestmentRecommendation


def run_tests():
    original_database_path = connection.DATABASE_PATH

    with tempfile.NamedTemporaryFile(delete=False) as database_file:
        test_database_path = database_file.name

    try:
        connection.DATABASE_PATH = test_database_path
        setup_database()

        evidence = [
            {
                "category": "Technical",
                "score": 82,
                "confidence": 80,
                "summary": "Technical score 82 with high confidence.",
                "reason": "Technical evidence supports the recommendation.",
            },
            {
                "category": "Fundamental",
                "score": 72,
                "confidence": 68,
                "summary": "Fundamental score 72 with medium confidence.",
            },
            {
                "category": "Forecast",
                "score": 44,
                "confidence": 48,
                "summary": "Forecast score 44 with low confidence.",
                "reason": "Forecast evidence is a weaker input.",
            },
            {
                "category": "News",
                "score": 55,
                "confidence": 52,
                "summary": "News score 55 with medium confidence.",
            },
            {
                "category": "Portfolio",
                "score": 75,
                "confidence": 70,
                "summary": "Portfolio score 75 with medium confidence.",
            },
            {
                "category": "Risk",
                "score": 40,
                "confidence": 45,
                "summary": "Risk score 40 with low confidence.",
            },
            {
                "category": "Validation",
                "score": 50,
                "confidence": 50,
                "summary": "Validation is pending.",
            },
        ]
        fusion = {
            "fusion_summary": "Fusion conviction is 64/100.",
        }

        engine = InvestmentCommitteeEngine()
        committee = engine.evaluate(evidence=evidence, fusion=fusion)

        assert len(committee["members"]) == 8
        assert committee["members"][0]["member"] == "Technical Analyst"
        assert committee["members"][0]["stance"] == "Bullish"
        assert committee["members"][2]["stance"] == "Bearish"
        assert committee["members"][7]["stance"] == "Missing"
        assert committee["committee_agreement"] == 42.86
        assert committee["bullish_members"] == [
            "Technical Analyst",
            "Fundamental Analyst",
            "Portfolio Manager",
        ]
        assert committee["bearish_members"] == [
            "Forecast Analyst",
            "Risk Manager",
        ]
        assert "Technical Analyst" in committee["strongest_bull_argument"]
        assert "Forecast Analyst" in committee["strongest_bear_argument"]
        assert "disagrees with" in committee["main_disagreement"]
        assert "8 specialists" in committee["final_committee_summary"]

        recommendation = InvestmentRecommendation(
            ticker="AAPL",
            action="HOLD",
            confidence=65,
            score=3,
            technical_score=82,
            fundamental_score=72,
            portfolio_score=75,
            risk_score=40,
            forecast_score=44,
            news_confidence=55,
            evidence_breakdown=evidence,
            fusion=fusion,
            fusion_summary=fusion["fusion_summary"],
            investment_committee=committee,
            committee_members=committee["members"],
            committee_bull_case=committee["bull_case"],
            committee_bear_case=committee["bear_case"],
            committee_neutral_case=committee["neutral_case"],
            committee_agreement=committee["committee_agreement"],
            bullish_members=committee["bullish_members"],
            bearish_members=committee["bearish_members"],
            neutral_members=committee["neutral_members"],
            strongest_bull_argument=committee["strongest_bull_argument"],
            strongest_bear_argument=committee["strongest_bear_argument"],
            main_disagreement=committee["main_disagreement"],
            final_committee_summary=committee["final_committee_summary"],
        )

        save_recommendations(1, [recommendation])
        saved = get_recommendations_for_run(1)[0]

        assert saved["committee_members"] == committee["members"]
        assert saved["committee_bull_case"] == committee["bull_case"]
        assert saved["committee_bear_case"] == committee["bear_case"]
        assert saved["committee_neutral_case"] == committee["neutral_case"]
        assert saved["committee_agreement"] == committee["committee_agreement"]
        assert saved["bullish_members"] == committee["bullish_members"]
        assert saved["bearish_members"] == committee["bearish_members"]
        assert saved["neutral_members"] == committee["neutral_members"]
        assert saved["strongest_bull_argument"] == (
            committee["strongest_bull_argument"]
        )
        assert saved["strongest_bear_argument"] == (
            committee["strongest_bear_argument"]
        )
        assert saved["main_disagreement"] == committee["main_disagreement"]
        assert saved["final_committee_summary"] == (
            committee["final_committee_summary"]
        )

        print("InvestmentCommitteeEngine tests passed.")
    finally:
        connection.DATABASE_PATH = original_database_path
        if os.path.exists(test_database_path):
            os.remove(test_database_path)


if __name__ == "__main__":
    run_tests()
