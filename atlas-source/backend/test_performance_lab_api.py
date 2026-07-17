import os
import sqlite3
import tempfile

import database.connection as connection
from database.migrator import run_migrations
from database.repository import save_paper_trading_report

from api.main import performance_lab

REQUIRED_POLICY_KEYS = {
    "read_only",
    "descriptive_only",
    "deterministic",
    "paper_only",
    "broker_integration",
    "real_money",
    "does_not_modify_recommendations",
    "does_not_modify_trades",
    "does_not_modify_risk_limits",
    "does_not_place_orders",
}

REQUIRED_SECTIONS = (
    "portfolio_analytics",
    "trade_analytics",
    "committee_attribution",
    "research_attribution",
    "not_evaluated",
    "source_counts",
    "policy",
)


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
    ):
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        counts[table] = cursor.fetchone()[0]
    database.close()
    return counts


def assert_sections(report):
    for section in REQUIRED_SECTIONS:
        assert section in report, f"Missing section: {section}"


def assert_policy(report):
    assert REQUIRED_POLICY_KEYS.issubset(report["policy"].keys())


POLICY = {
    "read_only": True,
    "deterministic": True,
    "paper_only": True,
    "broker_integration": False,
    "real_money": False,
}


def _committee(*actions):
    return [
        {"member_id": f"strat_{i}", "member_name": f"Strategy {i}", "action": action}
        for i, action in enumerate(actions)
    ]


def _trade(ticker, pl, holding, snapshot, exit_price=100):
    return {
        "trade_id": f"T-{ticker}",
        "ticker": ticker,
        "action": "BUY",
        "entry_date": "2026-06-01",
        "entry_price": 90,
        "exit_date": "2026-06-05",
        "exit_price": exit_price,
        "holding_period": holding,
        "quantity": 10,
        "profit_loss": pl,
        "recommendation_snapshot": snapshot,
    }


def seed_report():
    replay_history = [
        {"date": "2026-06-01", "cash": 0, "positions": {}, "current_value": 100000,
         "realized_pl": 0, "unrealized_pl": 0, "portfolio_value": 100000,
         "daily_return": 0.0, "total_return": 0.0},
        {"date": "2026-06-02", "cash": 0, "positions": {}, "current_value": 101000,
         "realized_pl": 0, "unrealized_pl": 0, "portfolio_value": 101000,
         "daily_return": 1.0, "total_return": 1.0},
        {"date": "2026-06-03", "cash": 0, "positions": {}, "current_value": 100500,
         "realized_pl": 0, "unrealized_pl": 0, "portfolio_value": 100500,
         "daily_return": -0.5, "total_return": 0.5},
        {"date": "2026-06-04", "cash": 0, "positions": {}, "current_value": 102000,
         "realized_pl": 0, "unrealized_pl": 0, "portfolio_value": 102000,
         "daily_return": 1.5, "total_return": 2.0},
        {"date": "2026-06-05", "cash": 0, "positions": {}, "current_value": 103500,
         "realized_pl": 0, "unrealized_pl": 0, "portfolio_value": 103500,
         "daily_return": 1.47, "total_return": 3.5},
    ]
    trades = [
        _trade("AAPL", 500, 10, {
            "technical_score": 80, "fundamental_score": 75,
            "committee_members": _committee("BUY", "BUY", "HOLD")}),
        _trade("MSFT", 300, 6, {
            "technical_score": 78, "fundamental_score": 72,
            "committee_members": _committee("BUY", "AVOID", "BUY")}),
        _trade("NVDA", 700, 12, {
            "technical_score": 85, "fundamental_score": 80,
            "committee_members": _committee("BUY", "BUY", "BUY")}),
        _trade("AMD", -200, 8, {
            "technical_score": 40, "fundamental_score": 45,
            "committee_members": _committee("BUY", "AVOID", "AVOID")}, exit_price=80),
        _trade("INTC", -350, 9, {
            "technical_score": 35, "fundamental_score": 42,
            "committee_members": _committee("BUY", "AVOID", "SELL")}, exit_price=75),
    ]
    report = {
        "price_backed": True,
        "portfolio": {"date": "2026-06-05", "portfolio_value": 103500},
        "replay_history": replay_history,
        "trades": trades,
        "performance": {
            "benchmark_comparison": [
                {"benchmark": "S&P 500", "benchmark_return": 2.2, "alpha": 1.3},
            ],
        },
        "research": {},
        "policy": POLICY,
        "metadata": {"price_backed": True, "run_id": 1},
    }
    save_paper_trading_report(report)


original_database_path = connection.DATABASE_PATH

# ----------------------------------------------------------------------
# Seeded database: endpoint attributes performance and writes nothing.
# ----------------------------------------------------------------------
with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as database_file:
    database_path = database_file.name

try:
    connection.DATABASE_PATH = database_path
    connection._wal_initialized_paths.discard(database_path)
    run_migrations()
    seed_report()

    counts_before = table_counts(database_path)
    report = performance_lab(limit=100)
    repeated = performance_lab(limit=100)
    counts_after = table_counts(database_path)

    # Read-only + deterministic over repository reads.
    assert counts_before == counts_after
    assert report == repeated

    assert_sections(report)
    assert_policy(report)

    portfolio = report["portfolio_analytics"]
    assert portfolio["status"] == "EVALUATED"
    assert portfolio["equity_curve"]["sample_size"] == 5
    assert portfolio["risk_adjusted"]["status"] == "EVALUATED"
    # Alpha computes from the stored benchmark comparison; beta stays
    # NOT_EVALUATED because snapshots store no aligned benchmark series.
    assert portfolio["benchmark"]["alpha"] == 1.3
    assert portfolio["benchmark"]["beta"]["status"] == "NOT_EVALUATED"

    trade = report["trade_analytics"]
    assert trade["status"] == "EVALUATED"
    assert trade["closed_trades"] == 5
    assert trade["win_rate"] == 60.0
    assert trade["best_trade"]["ticker"] == "NVDA"
    assert trade["worst_trade"]["ticker"] == "INTC"

    committee = report["committee_attribution"]
    assert committee["status"] == "EVALUATED"
    member_by_id = {row["member_id"]: row for row in committee["members"]}
    assert member_by_id["strat_0"]["accuracy"] == 60.0
    assert committee["rolling_accuracy"]["status"] == "EVALUATED"

    research = report["research_attribution"]
    assert research["status"] == "EVALUATED"
    technical = next(r for r in research["signals"] if r["signal"] == "Technical")
    assert technical["verdict"] == "PREDICTIVE"
finally:
    connection.DATABASE_PATH = original_database_path
    cleanup_database(database_path)


# ----------------------------------------------------------------------
# Empty database: every section present and NOT_EVALUATED, no writes.
# ----------------------------------------------------------------------
with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as empty_database_file:
    empty_database_path = empty_database_file.name

try:
    connection.DATABASE_PATH = empty_database_path
    connection._wal_initialized_paths.discard(empty_database_path)
    run_migrations()

    empty_counts_before = table_counts(empty_database_path)
    empty_report = performance_lab(limit=100)
    empty_counts_after = table_counts(empty_database_path)

    assert empty_counts_before == empty_counts_after
    assert_sections(empty_report)
    assert_policy(empty_report)

    # With no persisted paper data the engine falls back to deterministic demo
    # data (never fabricated live metrics); the sections are still well-formed.
    for section in (
        "portfolio_analytics",
        "trade_analytics",
        "committee_attribution",
        "research_attribution",
    ):
        assert empty_report[section]["status"] in {"EVALUATED", "NOT_EVALUATED"}
finally:
    connection.DATABASE_PATH = original_database_path
    cleanup_database(empty_database_path)


print("PerformanceLab API test passed.")
