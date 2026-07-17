import os
import tempfile
import atexit

import database.connection as connection
from api.main import (
    analytics_benchmarks_dashboard,
    analytics_calibration_dashboard,
    analytics_dashboard,
    analytics_equity_dashboard,
    analytics_research_dashboard,
    latest_monthly_report_dashboard,
)
from database.repository import (
    get_latest_monthly_report,
    save_monthly_report,
)
from database.migrator import run_migrations
from database.setup import setup_database
from engines.daily_journal_engine import DailyJournalEngine
from engines.performance_analytics_engine import PerformanceAnalyticsEngine
from engines.performance_observatory import PerformanceObservatory
from engines.research_lab_engine import ResearchLabEngine


# ------------------------------------------------------------------
# Deterministic fixtures
# ------------------------------------------------------------------
history = [
    {"date": "2026-06-01", "portfolio_value": 100000, "daily_return": 0.0, "total_return": 0.0},
    {"date": "2026-06-02", "portfolio_value": 100500, "daily_return": 0.5, "total_return": 0.5},
    {"date": "2026-06-03", "portfolio_value": 101000, "daily_return": 0.4975, "total_return": 1.0},
    {"date": "2026-06-04", "portfolio_value": 100800, "daily_return": -0.198, "total_return": 0.8},
    {"date": "2026-06-05", "portfolio_value": 101500, "daily_return": 0.694, "total_return": 1.5},
    {"date": "2026-06-08", "portfolio_value": 102200, "daily_return": 0.6897, "total_return": 2.2},
]

performance_reports = [
    {
        "date": "2026-06-08",
        "performance": {
            "sharpe": 0.9,
            "sortino": 1.2,
            "volatility": 0.4,
            "max_drawdown": -0.7,
            "total_return": 2.2,
            "benchmark_comparison": [
                {"benchmark": "S&P 500", "benchmark_return": 1.5, "paper_return": 2.2, "alpha": 0.7},
                {"benchmark": "NASDAQ-100", "benchmark_return": 2.0, "paper_return": 2.2, "alpha": 0.2},
                {"benchmark": "Equal Weight Placeholder", "benchmark_return": 1.0, "paper_return": 2.2, "alpha": 1.2},
            ],
        },
    },
    {
        "date": "2026-06-05",
        "performance": {
            "sharpe": 0.6,
            "sortino": 0.8,
            "volatility": 0.5,
            "max_drawdown": -0.9,
            "total_return": 1.5,
            "benchmark_comparison": [
                {"benchmark": "S&P 500", "benchmark_return": 1.4, "paper_return": 1.5, "alpha": 0.1},
                {"benchmark": "NASDAQ-100", "benchmark_return": 1.8, "paper_return": 1.5, "alpha": -0.3},
                {"benchmark": "Equal Weight Placeholder", "benchmark_return": 1.1, "paper_return": 1.5, "alpha": 0.4},
            ],
        },
    },
]

experiments = ResearchLabEngine().default_experiments()

validations = [
    {"adoption_decision": "ADOPT", "scientific_result": "Improved"},
    {"adoption_decision": "REJECT", "scientific_result": "Regression"},
    {"adoption_decision": "RETEST", "scientific_result": "Neutral"},
]

journals = [
    {
        "date": "2026-06-05",
        "performance_summary": {"win_rate": 55, "alpha_vs_sp": 0.1, "drawdown": -0.9},
        "lessons_learned": {
            "most_useful_evidence_today": "Forecast evidence led performance.",
            "performance_observation": "Paper alpha vs S&P: 0.1.",
            "macro_influence": "Bull regime with risk score 40.",
        },
        "research_tasks": ["Review probability calibration."],
    },
    {
        "date": "2026-06-08",
        "performance_summary": {"win_rate": 60, "alpha_vs_sp": 0.7, "drawdown": -0.7},
        "lessons_learned": {
            "most_useful_evidence_today": "Committee agreement was decisive.",
            "performance_observation": "Paper alpha vs S&P: 0.7.",
            "macro_influence": "Bull regime with risk score 38.",
        },
        "research_tasks": ["Study macro sensitivity."],
    },
]

source_data = {
    "recommendations": [
        {"ticker": "AAPL", "action": "BUY", "confidence": 80, "knowledge_score": 82, "stability_score": 80, "validation_result": {"success": True, "percentage_return": 3.2}},
        {"ticker": "MSFT", "action": "BUY", "confidence": 78, "knowledge_score": 79, "stability_score": 77, "validation_result": {"success": False, "percentage_return": -1.1}},
        {"ticker": "NVDA", "action": "HOLD", "confidence": 70, "knowledge_score": 75, "stability_score": 74, "validation_result": {"success": True, "percentage_return": 0.5}},
        {"ticker": "TSLA", "action": "AVOID", "confidence": 65, "knowledge_score": 70, "stability_score": 68, "validation_result": {"success": True, "percentage_return": -2.0}},
    ],
}

real_database_path = connection.DATABASE_PATH
with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as runtime_database_file:
    runtime_database_path = runtime_database_file.name


def cleanup_runtime_database():
    connection.DATABASE_PATH = real_database_path
    connection._wal_initialized_paths.discard(runtime_database_path)
    for candidate in (
        runtime_database_path,
        f"{runtime_database_path}-wal",
        f"{runtime_database_path}-shm",
    ):
        if os.path.exists(candidate):
            os.remove(candidate)


atexit.register(cleanup_runtime_database)
connection.DATABASE_PATH = runtime_database_path
connection._wal_initialized_paths.discard(runtime_database_path)
run_migrations()

paper_trades = [
    {"ticker": "GOOGL", "action": "SELL", "exit_price": 177, "profit_loss": 350, "holding_period": 10, "reason": "Profit take", "recommendation_snapshot": {"sector": "Communication Services"}},
    {"ticker": "AMD", "action": "SELL", "exit_price": 142.5, "profit_loss": -350, "holding_period": 9, "reason": "Risk control", "recommendation_snapshot": {"sector": "Semiconductors"}},
    {"ticker": "AAPL", "action": "BUY", "exit_price": None, "profit_loss": 0, "holding_period": None, "recommendation_snapshot": {"sector": "Technology"}},
]

engine = PerformanceAnalyticsEngine()
analytics = engine.generate(
    portfolio_history=history,
    performance_reports=performance_reports,
    experiments=experiments,
    validations=validations,
    journals=journals,
    source_data=source_data,
    paper_trades=paper_trades,
    as_of_date="2026-06",
)

# Part 1 - Equity curve
equity = analytics["equity_curve"]
assert equity["sample_size"] == 6
assert equity["latest_value"] == 102200
assert equity["cumulative_return"] == 2.2
assert set(equity["points"][0].keys()) == {
    "date",
    "portfolio_value",
    "daily_return",
    "cumulative_return",
}
assert equity["weekly_return"] != 0

# Part 2 - Benchmark comparison
benchmarks = analytics["benchmark_comparison"]
assert [row["benchmark"] for row in benchmarks["benchmarks"]] == engine.BENCHMARKS
sp = next(row for row in benchmarks["benchmarks"] if row["benchmark"] == "S&P 500")
assert sp["alpha"] == round(2.2 - 1.5, 4)
assert sp["outperformance_rate"] == 100.0  # alpha > 0 in both reports
nasdaq = next(row for row in benchmarks["benchmarks"] if row["benchmark"] == "NASDAQ-100")
assert nasdaq["outperformance_rate"] == 50.0  # 0.2 > 0 but -0.3 < 0

# Part 3 - Risk statistics
risk = analytics["risk_statistics"]
assert risk["sharpe"] == 0.9
assert risk["sortino"] == 1.2
assert risk["max_drawdown"] == -0.7
assert risk["best_day"] == 0.694
assert risk["worst_day"] == -0.198
assert risk["calmar"] == round(2.2 / 0.7, 4)

# Part 4 - Recommendation analytics
recommendation = analytics["recommendation_analytics"]
assert recommendation["buy_success_rate"] == 50.0  # 1 of 2 BUY succeeded
assert recommendation["hold_accuracy"] == 100.0
assert recommendation["avoid_accuracy"] == 100.0
assert recommendation["average_holding_period"] == round((10 + 9) / 2, 4)
assert recommendation["recommendation_frequency"]["total"] == 4

# Part 5 - Learning curve
learning = analytics["learning_curve"]
assert len(learning["metrics"]) == 5
assert learning["experiment_adoption_rate"] == round(1 / 6 * 100, 2)  # 1 ADOPTED of 6
assert learning["research_completion_rate"] == round(2 / 6 * 100, 2)  # ADOPTED + REJECTED
assert learning["scientific_validation_success_rate"] == round(1 / 3 * 100, 2)
assert len(learning["points"]) == 2

# Part 6 - Research progress
research = analytics["research_progress"]
assert research["adopted"] == 1
assert research["rejected"] == 1
assert set(research["roadmap"].keys()) == {"High", "Medium", "Low"}

# Part 7 - Monthly report
monthly = analytics["monthly_report"]
assert monthly["month"].startswith("2026-06")
assert len(monthly["best_decisions"]) >= 1
assert monthly["best_decisions"][0]["ticker"] == "GOOGL"
assert monthly["largest_mistakes"][0]["ticker"] == "AMD"
assert monthly["validation_summary"]["validation_count"] == 3
assert monthly["major_lessons"]

# Trust assessment is evidence-based, never optimistic-only
trust = analytics["trust_assessment"]
assert trust["verdict"] in {"Improving", "Mixed", "Not Improving", "Not Enough Evidence"}
assert isinstance(trust["evidence"], list)

# Policy invariants
assert analytics["policy"]["changes_recommendation_behavior"] is False
assert analytics["policy"]["broker_integration"] is False
assert analytics["policy"]["human_approval_required"] is True

# Reuse: Observatory delegates to the analytics engine with identical output
observatory_analytics = PerformanceObservatory().performance_analytics(
    portfolio_history=history,
    performance_reports=performance_reports,
    experiments=experiments,
    validations=validations,
    journals=journals,
    source_data=source_data,
    paper_trades=paper_trades,
    as_of_date="2026-06",
)
assert observatory_analytics["equity_curve"]["latest_value"] == 102200

# Reuse: Research Lab learning metrics are deterministic
lab_metrics = ResearchLabEngine().learning_metrics(experiments, validations)
assert lab_metrics["experiment_adoption_rate"] == round(1 / 6 * 100, 2)

# Reuse: Daily Journal monthly summary rolls up lessons
journal_summary = DailyJournalEngine().monthly_summary(journals)
assert journal_summary["journal_count"] == 2
assert journal_summary["major_lessons"]

# ------------------------------------------------------------------
# Persistence + API (empty DB falls back to deterministic demo data)
# ------------------------------------------------------------------
original_database_path = connection.DATABASE_PATH
with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as database_file:
    database_path = database_file.name

try:
    connection.DATABASE_PATH = database_path
    setup_database()

    save_monthly_report(monthly | {"report_date": "2026-06-30"})
    saved = get_latest_monthly_report()
    assert saved["month"] == monthly["month"]
    assert saved["validation_summary"]["validation_count"] == 3
    assert saved["best_decisions"][0]["ticker"] == "GOOGL"

    # API endpoints never crash on an empty database (demo fallback).
    api_analytics = analytics_dashboard()
    assert api_analytics["demo_data"] is True
    assert "equity_curve" in api_analytics
    assert api_analytics["policy"]["changes_recommendation_behavior"] is False

    equity_api = analytics_equity_dashboard()
    assert "equity_curve" in equity_api

    benchmarks_api = analytics_benchmarks_dashboard()
    assert len(benchmarks_api["benchmark_comparison"]["benchmarks"]) == 3

    calibration_api = analytics_calibration_dashboard()
    assert "confidence_calibration" in calibration_api["calibration"]
    assert "probability_calibration" in calibration_api["calibration"]

    research_api = analytics_research_dashboard()
    assert "research_progress" in research_api
    assert "learning_curve" in research_api

    monthly_api = latest_monthly_report_dashboard()
    assert monthly_api["monthly_report"]["month"] == monthly["month"]
    assert monthly_api["policy"]["broker_integration"] is False
finally:
    connection.DATABASE_PATH = original_database_path
    if os.path.exists(database_path):
        os.remove(database_path)

print("PerformanceAnalyticsEngine test passed.")
