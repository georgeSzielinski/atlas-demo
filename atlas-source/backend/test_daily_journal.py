import os
import tempfile

import database.connection as connection
from api.main import daily_journal_dashboard, latest_daily_journal_dashboard
from database.repository import get_daily_journals, get_latest_daily_journal
from database.setup import setup_database
from engines.daily_cycle_engine import DailyCycleEngine
from engines.daily_journal_engine import DailyJournalEngine


recommendations = [
    {
        "ticker": "AAPL",
        "action": "BUY",
        "confidence": 91,
        "overall_conviction": 88,
        "forecast_score": 72,
        "committee_agreement": 0.82,
        "evidence_breakdown": [
            {"source": "Technical", "score": 9},
            {"source": "Fundamental", "score": 7},
        ],
        "reason": "Paper journal test entry.",
        "sector": "Technology",
    },
    {
        "ticker": "MSFT",
        "action": "HOLD",
        "confidence": 74,
        "forecast_score": 66,
        "committee_agreement": 0.7,
        "evidence_breakdown": [
            {"source": "Forecast", "score": 6},
            {"source": "News", "score": 4},
        ],
        "reason": "Paper journal test hold.",
        "sector": "Technology",
    },
    {
        "ticker": "TSLA",
        "action": "AVOID",
        "confidence": 63,
        "forecast_score": 41,
        "committee_agreement": 0.58,
        "evidence_breakdown": [
            {"source": "Risk", "score": 8},
        ],
        "reason": "Paper journal test avoid.",
        "sector": "Consumer Cyclical",
    },
]

cycle = DailyCycleEngine().run_phase(
    "market_close",
    cycle_date="2026-07-02",
    recommendations=recommendations,
    market_prices={"AAPL": 100, "MSFT": 200, "TSLA": 250},
    benchmark_returns={
        "S&P 500": 0.2,
        "NASDAQ-100": 0.3,
        "Equal Weight Placeholder": 0.1,
    },
)
journal = DailyJournalEngine().build(cycle=cycle)

assert journal["date"] == "2026-07-02"
assert journal["policy"]["paper_only"] is True
assert journal["policy"]["broker_integration"] is False
assert journal["policy"]["changes_recommendation_behavior"] is False
assert journal["recommendation_summary"]["recommendations_today"] == 3
assert journal["recommendation_summary"]["buy_count"] == 1
assert journal["recommendation_summary"]["hold_count"] == 1
assert journal["recommendation_summary"]["avoid_count"] == 1
assert journal["recommendation_summary"]["sell_count"] == 0
assert journal["recommendation_summary"]["highest_conviction"]["ticker"] == "AAPL"
assert journal["performance_summary"]["portfolio_value"] == 100000
assert journal["performance_summary"]["open_positions"] == 1
assert len(journal["benchmark_comparison"]) == 3
assert journal["lessons_learned"]["most_useful_evidence_today"] == "Technical"
assert "Compare similar historical cases before the next cycle." in journal[
    "research_tasks"
]

original_database_path = connection.DATABASE_PATH
with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as database_file:
    database_path = database_file.name

try:
    connection.DATABASE_PATH = database_path
    setup_database()

    persisted_cycle = DailyCycleEngine().run_phase(
        "market_close",
        cycle_date="2026-07-03",
        recommendations=recommendations,
        market_prices={"AAPL": 105, "MSFT": 205, "TSLA": 245},
        benchmark_returns={
            "S&P 500": 0.4,
            "NASDAQ-100": 0.5,
            "Equal Weight Placeholder": 0.2,
        },
        persist=True,
    )
    journals = get_daily_journals(limit=10)
    latest = get_latest_daily_journal()

    assert persisted_cycle["status"] == "COMPLETED"
    assert len(journals) == 1
    assert latest["date"] == "2026-07-03"
    assert latest["runtime_state"]["status"] == "COMPLETED"
    assert latest["recommendation_summary"]["buy_count"] == 1
    assert latest["performance_summary"]["portfolio_value"] == 100000
    assert latest["policy"]["automatic_execution"] is False
    assert latest["policy"]["real_money"] is False

    api_journals = daily_journal_dashboard()
    assert len(api_journals["daily_journals"]) == 1
    assert api_journals["policy"]["broker_integration"] is False

    api_latest = latest_daily_journal_dashboard()
    assert api_latest["latest_daily_journal"]["journal_id"] == latest["journal_id"]
    assert api_latest["policy"]["permanent_research_record"] is True
finally:
    connection.DATABASE_PATH = original_database_path
    if os.path.exists(database_path):
        os.remove(database_path)

print("DailyJournalEngine test passed.")
