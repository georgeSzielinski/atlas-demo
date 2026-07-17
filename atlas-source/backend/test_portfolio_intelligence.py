import os
import sqlite3
import tempfile

import database.connection as connection
from database.migrator import run_migrations
from database.repository import (
    add_paper_fund_activity,
    add_paper_fund_learning,
    save_paper_fund_snapshot,
    save_paper_fund_state,
    save_risk_decision,
)
from engines.portfolio_intelligence_engine import PortfolioIntelligenceEngine


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
        "paper_fund_states",
        "paper_fund_snapshots",
        "paper_fund_learning",
        "paper_fund_activity",
        "risk_decisions",
    ):
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        counts[table] = cursor.fetchone()[0]
    database.close()
    return counts


def seed_portfolio_history():
    policy = {
        "paper_only": True,
        "broker_integration": False,
        "broker_disabled": True,
        "real_money": False,
        "execution": "simulated_only",
        "automatic_execution": False,
        "changes_recommendation_behavior": False,
        "human_approval_required_for_real_trading": True,
    }
    learning_policy = {
        "descriptive_only": True,
        "does_not_modify_recommendations": True,
        "does_not_modify_trades": True,
        "paper_only": True,
        "real_money": False,
    }
    positions = {
        "AAPL": {
            "ticker": "AAPL",
            "quantity": 50,
            "cost_basis": 90,
            "current_price": 100,
            "current_value": 5000,
            "unrealized_pl": 500,
        },
        "MSFT": {
            "ticker": "MSFT",
            "quantity": 20,
            "cost_basis": 95,
            "current_price": 100,
            "current_value": 2000,
            "unrealized_pl": 100,
        },
        "XLE": {
            "ticker": "XLE",
            "quantity": 20,
            "cost_basis": 100,
            "current_price": 100,
            "current_value": 2000,
            "unrealized_pl": 0,
        },
        "ZZZZ": {
            "ticker": "ZZZZ",
            "quantity": 5,
            "cost_basis": 100,
            "current_price": 100,
            "current_value": 500,
            "unrealized_pl": 0,
        },
    }

    save_paper_fund_state({
        "updated_at": "2026-07-03T10:15:00",
        "fund_status": "RUNNING",
        "watchlist": ["AAPL", "MSFT", "XLE", "ZZZZ"],
        "starting_cash": 10000,
        "cash": 500,
        "positions": positions,
        "realized_pl": 0,
        "interval_minutes": 30,
        "last_update": "2026-07-03T10:15:00",
        "next_update": "2026-07-03T10:45:00",
        "last_error": None,
        "price_provider": "test_live_prices",
        "policy": policy,
    })
    save_paper_fund_snapshot({
        "as_of": "2026-07-03T10:15:00",
        "cycle_id": "cycle-3",
        "cash": 500,
        "positions": positions,
        "current_value": 9500,
        "realized_pl": 0,
        "unrealized_pl": 600,
        "portfolio_value": 10000,
        "daily_return": 0.5,
        "total_return": 0,
        "price_source": "test_live_prices",
        "policy": policy,
    })

    construction_targets = [
        {"ticker": "AAPL", "sector": "Technology", "suggested_allocation": 30},
        {"ticker": "MSFT", "sector": "Technology", "suggested_allocation": 20},
        {"ticker": "XLE", "sector": "Energy", "suggested_allocation": 20},
    ]
    add_paper_fund_learning({
        "at": "2026-07-03T10:16:00",
        "cycle_id": "cycle-3",
        "lesson": "Portfolio intelligence seed.",
        "details": {
            "learning_summary": {
                "recommended_symbols": ["AAPL", "MSFT", "XLE", "ZZZZ"],
                "construction_targets": construction_targets,
                "policy": learning_policy,
            },
        },
    })
    add_paper_fund_activity({
        "at": "2026-07-03T10:12:00",
        "cycle_id": "cycle-3",
        "activity_type": "CONSTRUCTION_BUILT",
        "message": "Construction summary built.",
        "details": {
            "construction_summary": {
                "recommended_allocations": construction_targets,
            },
        },
    })

    save_risk_decision({
        "decision_id": "risk-approved-aapl",
        "cycle_id": "cycle-3",
        "symbol": "AAPL",
        "side": "BUY",
        "quantity": 5,
        "verdict": "APPROVED",
        "checks": {
            "checks": [
                {
                    "rule": "max_position_size",
                    "status": "APPROVED",
                    "limit": 0.25,
                    "measured": 0.2,
                    "reason": "Position size is within limit.",
                }
            ],
            "rejections": [],
            "reasons": [],
        },
        "policy": policy,
        "created_at": "2026-07-03T10:10:00",
    })
    save_risk_decision({
        "decision_id": "risk-rejected-msft-1",
        "cycle_id": "cycle-3",
        "symbol": "MSFT",
        "side": "BUY",
        "quantity": 20,
        "verdict": "REJECTED",
        "checks": {
            "checks": [],
            "rejections": [
                {
                    "rule": "affordability",
                    "status": "REJECTED",
                    "limit": 1000,
                    "measured": 1500,
                    "reason": "Buy order value exceeds available cash.",
                },
                {
                    "rule": "max_position_size",
                    "status": "REJECTED",
                    "limit": 0.25,
                    "measured": 0.5,
                    "reason": "Post-order position exceeds max size.",
                },
            ],
            "reasons": [
                "Buy order value exceeds available cash.",
                "Post-order position exceeds max size.",
            ],
        },
        "policy": policy,
        "created_at": "2026-07-03T10:11:00",
    })
    save_risk_decision({
        "decision_id": "risk-rejected-msft-2",
        "cycle_id": "cycle-3",
        "symbol": "MSFT",
        "side": "BUY",
        "quantity": 10,
        "verdict": "REJECTED",
        "checks": {
            "checks": [],
            "rejections": [
                {
                    "rule": "affordability",
                    "status": "REJECTED",
                    "limit": 1000,
                    "measured": 1400,
                    "reason": "Buy order value exceeds available cash.",
                }
            ],
            "reasons": ["Buy order value exceeds available cash."],
        },
        "policy": policy,
        "created_at": "2026-07-03T10:12:00",
    })


engine = PortfolioIntelligenceEngine()

cash_pass = engine.generate(
    state={"fund_status": "RUNNING", "cash": 2500, "positions": {}},
    snapshots=[{"as_of": "2026-07-01", "cash": 2500, "portfolio_value": 10000}],
    risk_decisions=[],
    learning=[],
    activity=[],
)["cash_reserve_status"]
cash_warn = engine.generate(
    state={"fund_status": "RUNNING", "cash": 1000, "positions": {}},
    snapshots=[{"as_of": "2026-07-01", "cash": 1000, "portfolio_value": 10000}],
    risk_decisions=[],
    learning=[],
    activity=[],
)["cash_reserve_status"]
cash_fail = engine.generate(
    state={"fund_status": "RUNNING", "cash": 400, "positions": {}},
    snapshots=[{"as_of": "2026-07-01", "cash": 400, "portfolio_value": 10000}],
    risk_decisions=[],
    learning=[],
    activity=[],
)["cash_reserve_status"]
assert cash_pass["status"] == "PASS"
assert cash_warn["status"] == "WARN"
assert cash_fail["status"] == "FAIL"

missing_sector = engine.generate(
    state={"fund_status": "RUNNING", "cash": 9000, "positions": {}},
    snapshots=[{
        "as_of": "2026-07-01",
        "cash": 9000,
        "portfolio_value": 10000,
        "positions": {
            "ZZZZ": {
                "ticker": "ZZZZ",
                "quantity": 10,
                "current_price": 100,
                "current_value": 1000,
            }
        },
    }],
    risk_decisions=[],
    learning=[],
    activity=[],
)["sector_exposure_summary"]
assert missing_sector["status"] == "NOT_EVALUATED"
assert missing_sector["missing_sector"][0]["status"] == "NOT_EVALUATED"


original_database_path = connection.DATABASE_PATH
with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as database_file:
    database_path = database_file.name

try:
    connection.DATABASE_PATH = database_path
    connection._wal_initialized_paths.discard(database_path)
    run_migrations()
    seed_portfolio_history()

    counts_before = table_counts(database_path)
    report = engine.generate(limit=100)
    repeated = engine.generate(limit=100)
    counts_after = table_counts(database_path)

    assert report == repeated
    assert counts_before == counts_after

    assert report["policy"] == {
        "read_only": True,
        "deterministic": True,
        "descriptive_only": True,
        "does_not_modify_recommendations": True,
        "does_not_modify_trades": True,
        "does_not_modify_risk_limits": True,
        "does_not_place_orders": True,
        "broker_integration": False,
        "paper_only": True,
        "real_money": False,
    }

    score = report["portfolio_health_score"]
    assert score == {
        "score": 35,
        "scale": "0-100",
        "status": "AT_RISK",
        "deterministic": True,
        "reason": (
            "Score starts at 100 and deducts for cash pressure, "
            "concentration, risk rejections, sector concentration, and "
            "negative paper P/L signals."
        ),
    }

    cash = report["cash_reserve_status"]
    assert cash["status"] == "WARN"
    assert cash["cash_percent"] == 5

    concentration = report["largest_position_concentration"]
    assert concentration["status"] == "FAIL"
    assert concentration["symbol"] == "AAPL"
    assert concentration["concentration_percent"] == 50

    utilization = report["risk_utilization"]
    assert utilization["status"] == "EVALUATED"
    assert utilization["decision_count"] == 3
    assert utilization["rejected_decisions"] == 2
    by_rule = {item["rule"]: item for item in utilization["by_rule"]}
    assert by_rule["affordability"]["rejected_count"] == 2
    assert by_rule["affordability"]["max_utilization_percent"] == 150
    assert by_rule["max_position_size"]["max_utilization_percent"] == 200

    sectors = report["sector_exposure_summary"]
    assert sectors["status"] == "PARTIAL"
    by_sector = {item["sector"]: item for item in sectors["items"]}
    assert by_sector["Technology"]["exposure_percent"] == 70
    assert by_sector["Technology"]["status"] == "FAIL"
    assert by_sector["Energy"]["exposure_percent"] == 20
    assert sectors["missing_sector"] == [
        {
            "symbol": "ZZZZ",
            "status": "NOT_EVALUATED",
            "reason": "Sector metadata is unavailable for this position.",
        }
    ]

    risks = report["top_portfolio_risks"]
    assert any(
        item["risk_type"] == "risk_rule_blocker"
        and item["rule"] == "affordability"
        and item["measured"] == 2
        for item in risks
    )
    assert any(
        item["risk_type"] == "position_concentration"
        and item["symbol"] == "AAPL"
        for item in risks
    )

    watch = report["suggested_watch_items"]
    assert any(
        item["type"] == "RISK_RULE"
        and item["rule"] == "affordability"
        and "Buy order value exceeds available cash." in item["reasons"]
        for item in watch
    )
    assert any(
        item["type"] == "MISSING_SECTOR_DATA"
        and item["symbol"] == "ZZZZ"
        for item in watch
    )

    from api.main import app, portfolio_intelligence

    assert any(
        route.path == "/portfolio/intelligence"
        and "GET" in route.methods
        for route in app.routes
    )

    api_counts_before = table_counts(database_path)
    api_report = portfolio_intelligence(limit=100)
    api_counts_after = table_counts(database_path)

    assert api_counts_before == api_counts_after
    for section in (
        "portfolio_health_score",
        "cash_reserve_status",
        "risk_utilization",
        "largest_position_concentration",
        "sector_exposure_summary",
        "top_portfolio_risks",
        "suggested_watch_items",
        "policy",
    ):
        assert section in api_report

    assert api_report["policy"] == report["policy"]
    assert api_report["portfolio_health_score"] == report["portfolio_health_score"]
    assert api_report["cash_reserve_status"]["status"] == "WARN"
    assert api_report["risk_utilization"]["rejected_decisions"] == 2
    assert (
        api_report["largest_position_concentration"]["concentration_percent"]
        == 50
    )
    assert api_report["sector_exposure_summary"]["status"] == "PARTIAL"
    assert any(
        item["risk_type"] == "risk_rule_blocker"
        for item in api_report["top_portfolio_risks"]
    )
    assert any(
        item["type"] == "RISK_RULE"
        for item in api_report["suggested_watch_items"]
    )
finally:
    connection.DATABASE_PATH = original_database_path
    cleanup_database(database_path)


with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as empty_database_file:
    empty_database_path = empty_database_file.name

try:
    connection.DATABASE_PATH = empty_database_path
    connection._wal_initialized_paths.discard(empty_database_path)
    run_migrations()

    from api.main import portfolio_intelligence

    empty_counts_before = table_counts(empty_database_path)
    empty_report = portfolio_intelligence(limit=100)
    empty_counts_after = table_counts(empty_database_path)

    assert empty_counts_before == empty_counts_after
    assert isinstance(empty_report["portfolio_health_score"]["score"], int)
    assert empty_report["portfolio_health_score"]["deterministic"] is True
    assert empty_report["cash_reserve_status"]["status"] == "NOT_EVALUATED"
    assert empty_report["risk_utilization"]["status"] == "NOT_EVALUATED"
    assert (
        empty_report["largest_position_concentration"]["status"]
        == "NOT_EVALUATED"
    )
    assert empty_report["sector_exposure_summary"]["status"] == "NOT_EVALUATED"
    assert empty_report["top_portfolio_risks"] == []
    assert empty_report["policy"]["read_only"] is True
finally:
    connection.DATABASE_PATH = original_database_path
    cleanup_database(empty_database_path)


print("PortfolioIntelligenceEngine test passed.")
