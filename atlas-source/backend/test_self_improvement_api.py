import os
import sqlite3
import tempfile

import database.connection as connection
from database.migrator import run_migrations
from database.repository import (
    save_paper_trading_report,
    save_portfolio_construction_report,
    save_risk_decision,
)

from api.main import self_improvement

REQUIRED_POLICY_KEYS = {
    "read_only",
    "research_only",
    "deterministic",
    "uses_llm",
    "uses_randomness",
    "changes_strategies",
    "changes_weights",
    "changes_committee",
    "changes_trading_behavior",
    "changes_risk_limits",
    "real_money",
}

REQUIRED_SECTIONS = (
    "findings",
    "opportunities",
    "domains",
    "not_evaluated",
    "source_counts",
    "policy",
    "status",
)

POLICY = {
    "read_only": True,
    "deterministic": True,
    "paper_only": True,
    "broker_integration": False,
    "real_money": False,
}


def cleanup_database(path):
    connection._wal_initialized_paths.discard(path)
    for candidate in (path, f"{path}-wal", f"{path}-shm"):
        if os.path.exists(candidate):
            os.remove(candidate)


def table_counts(path):
    database = sqlite3.connect(path)
    cursor = database.cursor()
    counts = {}
    for table in (
        "paper_portfolio_snapshots",
        "paper_trades",
        "paper_performance_reports",
        "risk_decisions",
        "portfolio_construction_reports",
    ):
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        counts[table] = cursor.fetchone()[0]
    database.close()
    return counts


def _committee(*actions):
    return [
        {"member_id": f"strat_{i}", "member_name": f"Strategy {i}", "action": action}
        for i, action in enumerate(actions)
    ]


def _snap(strategy, sector, regime, forecast, votes):
    return {
        "strategy": strategy,
        "sector": sector,
        "market_regime": regime,
        "forecast_score": forecast,
        "committee_members": votes,
    }


def _trade(ticker, pl, exit_date, snapshot, exit_price=100):
    return {
        "trade_id": f"T-{ticker}",
        "ticker": ticker,
        "action": "BUY",
        "entry_date": "2026-05-25",
        "entry_price": 90,
        "exit_date": exit_date,
        "exit_price": exit_price,
        "holding_period": 8,
        "quantity": 10,
        "profit_loss": pl,
        "recommendation_snapshot": snapshot,
    }


def seed():
    replay_history = [
        {"date": "2026-06-01", "cash": 0, "positions": {}, "current_value": 100000,
         "realized_pl": 0, "unrealized_pl": 0, "portfolio_value": 100000,
         "daily_return": 0.0, "total_return": 0.0},
        {"date": "2026-06-02", "cash": 0, "positions": {}, "current_value": 102000,
         "realized_pl": 0, "unrealized_pl": 0, "portfolio_value": 102000,
         "daily_return": 2.0, "total_return": 2.0},
        {"date": "2026-06-03", "cash": 0, "positions": {}, "current_value": 99000,
         "realized_pl": 0, "unrealized_pl": 0, "portfolio_value": 99000,
         "daily_return": -2.9, "total_return": -1.0},
        {"date": "2026-06-04", "cash": 0, "positions": {}, "current_value": 103000,
         "realized_pl": 0, "unrealized_pl": 0, "portfolio_value": 103000,
         "daily_return": 4.0, "total_return": 3.0},
    ]
    trades = [
        _trade("AAPL", 500, "2026-06-01",
               _snap("Momentum", "Technology", "Bull", 80, _committee("BUY", "BUY", "HOLD"))),
        _trade("MSFT", 400, "2026-06-02",
               _snap("Momentum", "Technology", "Bull", 78, _committee("BUY", "BUY", "BUY"))),
        _trade("NVDA", 300, "2026-06-03",
               _snap("Momentum", "Technology", "Bull", 76, _committee("BUY", "BUY", "BUY"))),
        _trade("PFE", -200, "2026-06-04",
               _snap("Quality", "Healthcare", "Bear", 40, _committee("BUY", "AVOID", "AVOID")), exit_price=80),
        _trade("MRK", -300, "2026-06-05",
               _snap("Quality", "Healthcare", "Bear", 42, _committee("BUY", "AVOID", "SELL")), exit_price=75),
        _trade("ABBV", -150, "2026-06-06",
               _snap("Quality", "Healthcare", "Bear", 45, _committee("BUY", "AVOID", "AVOID")), exit_price=85),
    ]
    report = {
        "price_backed": True,
        "portfolio": {"date": "2026-06-04", "portfolio_value": 103000},
        "replay_history": replay_history,
        "trades": trades,
        "performance": {},
        "research": {},
        "policy": POLICY,
        "metadata": {"price_backed": True, "run_id": 1},
    }
    save_paper_trading_report(report)

    for index, verdict in enumerate(
        ["APPROVED", "APPROVED", "REJECTED", "REJECTED", "REJECTED"], start=1
    ):
        checks = {}
        if verdict == "REJECTED":
            checks = {"rejections": [{"reason": "Buy order value exceeds available cash"}]}
        save_risk_decision({
            "decision_id": f"risk-{index}",
            "symbol": "NVDA",
            "side": "BUY",
            "quantity": 10,
            "verdict": verdict,
            "checks": checks,
            "policy": POLICY,
            "created_at": f"2026-06-0{index}T10:00:00",
        })

    for score in (70, 74, 80):
        save_portfolio_construction_report({
            "diversification": {"diversification_score": score, "concentration_score": 40},
            "risk_summary": {"risk_budget": "Moderate"},
            "policy": POLICY,
        })


original_database_path = connection.DATABASE_PATH

# ----------------------------------------------------------------------
# Seeded database: endpoint proposes research and writes nothing.
# ----------------------------------------------------------------------
with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as database_file:
    database_path = database_file.name

try:
    connection.DATABASE_PATH = database_path
    connection._wal_initialized_paths.discard(database_path)
    run_migrations()
    seed()

    counts_before = table_counts(database_path)
    report = self_improvement(limit=100)
    repeated = self_improvement(limit=100)
    counts_after = table_counts(database_path)

    # Read-only + deterministic over repository reads.
    assert counts_before == counts_after, "engine must not write to the database"
    assert report == repeated, "endpoint must be deterministic"

    for section in REQUIRED_SECTIONS:
        assert section in report, f"missing section {section}"
    assert REQUIRED_POLICY_KEYS.issubset(report["policy"].keys())
    assert report["policy"]["research_only"] is True
    assert report["policy"]["changes_trading_behavior"] is False

    assert report["status"] == "EVALUATED"
    assert len(report["findings"]) >= 1
    by_id = {finding["id"]: finding for finding in report["findings"]}

    # Strategy, sector, regime, committee, signal, risk, construction all
    # derive from the seeded evidence.
    assert by_id["strategy-outperformance"]["statistics"]["best_strategy"] == "Momentum"
    assert by_id["sector-dominance"]["statistics"]["leading_sector"] == "Technology"
    assert by_id["regime-best"]["statistics"]["best_regime"] == "Bull"
    assert by_id["signal-forecast_score"]["statistics"]["verdict"] == "PREDICTIVE"
    assert by_id["risk-rejection-rate"]["statistics"]["rejected"] == 3
    assert by_id["construction-diversification-trend"]["statistics"]["direction"] == "improving"

    # Findings ranked by confidence, and every finding is research-only.
    confidences = [finding["confidence"] for finding in report["findings"]]
    assert confidences == sorted(confidences, reverse=True)
    for finding in report["findings"]:
        assert finding["policy"]["does_not_change_live_behavior"] is True
finally:
    connection.DATABASE_PATH = original_database_path
    cleanup_database(database_path)


# ----------------------------------------------------------------------
# Empty database: well-formed, every domain NOT_EVALUATED, nothing written.
# ----------------------------------------------------------------------
with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as empty_database_file:
    empty_database_path = empty_database_file.name

try:
    connection.DATABASE_PATH = empty_database_path
    connection._wal_initialized_paths.discard(empty_database_path)
    run_migrations()

    empty_counts_before = table_counts(empty_database_path)
    empty_report = self_improvement(limit=100)
    empty_counts_after = table_counts(empty_database_path)

    assert empty_counts_before == empty_counts_after
    for section in REQUIRED_SECTIONS:
        assert section in empty_report
    assert REQUIRED_POLICY_KEYS.issubset(empty_report["policy"].keys())

    # No evidence -> no fabricated findings; every domain NOT_EVALUATED.
    assert empty_report["status"] == "NOT_EVALUATED"
    assert empty_report["findings"] == []
    assert empty_report["opportunities"] == []
    assert len(empty_report["not_evaluated"]) == 9
finally:
    connection.DATABASE_PATH = original_database_path
    cleanup_database(empty_database_path)


print("SelfImprovement API test passed.")
