import os
import sqlite3
import tempfile

import database.connection as connection
from database.migrator import run_migrations
from database.repository import (
    add_paper_fund_learning,
    save_paper_fund_order,
    save_paper_fund_snapshot,
    save_risk_decision,
)
from engines.self_learning_analytics_engine import SelfLearningAnalyticsEngine


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
        "paper_fund_learning",
        "paper_fund_orders",
        "paper_fund_snapshots",
        "risk_decisions",
    ):
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        counts[table] = cursor.fetchone()[0]
    database.close()
    return counts


def seed_history():
    policy = {
        "paper_only": True,
        "broker_integration": False,
        "real_money": False,
        "human_approval_required_for_real_trading": True,
    }
    learning_policy = {
        "descriptive_only": True,
        "does_not_modify_recommendations": True,
        "does_not_modify_trades": True,
        "paper_only": True,
        "real_money": False,
    }

    add_paper_fund_learning({
        "at": "2026-07-01T10:05:00",
        "cycle_id": "cycle-1",
        "lesson": "Initial simulated cycle.",
        "details": {
            "learning_summary": {
                "recommended_symbols": ["AAPL", "MSFT", "ZZZZ"],
                "construction_targets": [
                    {
                        "ticker": "AAPL",
                        "sector": "Technology",
                        "suggested_allocation": 20,
                    },
                    {
                        "ticker": "MSFT",
                        "sector": "Technology",
                        "suggested_allocation": 15,
                    },
                ],
                "bought_symbols": ["AAPL"],
                "sold_symbols": [],
                "rejected_orders": [
                    {
                        "symbol": "MSFT",
                        "side": "BUY",
                        "quantity": 5,
                        "reasons": ["Buy order value exceeds available cash."],
                    }
                ],
                "policy": learning_policy,
            },
        },
    })
    add_paper_fund_learning({
        "at": "2026-07-02T10:05:00",
        "cycle_id": "cycle-2",
        "lesson": "Second simulated cycle.",
        "details": {
            "learning_summary": {
                "recommended_symbols": ["AAPL", "MSFT"],
                "construction_targets": [
                    {
                        "ticker": "AAPL",
                        "sector": "Technology",
                        "suggested_allocation": 20,
                    },
                    {
                        "ticker": "MSFT",
                        "sector": "Technology",
                        "suggested_allocation": 15,
                    },
                ],
                "bought_symbols": [],
                "sold_symbols": [],
                "rejected_orders": [
                    {
                        "symbol": "MSFT",
                        "side": "BUY",
                        "quantity": 6,
                        "reasons": ["Buy order value exceeds available cash."],
                    }
                ],
                "policy": learning_policy,
            },
        },
    })

    save_paper_fund_order({
        "order_id": "cycle-1-BUY-AAPL",
        "cycle_id": "cycle-1",
        "ticker": "AAPL",
        "side": "BUY",
        "quantity": 10,
        "status": "FILLED_SIMULATED",
        "created_at": "2026-07-01T10:01:00",
        "filled_at": "2026-07-01T10:01:00",
        "fill_price": 100,
        "price_source": "test_live_prices",
        "validated": True,
        "simulated": True,
        "reason": "PortfolioConstructionEngine rebalance.",
        "policy": policy,
    })

    save_paper_fund_snapshot({
        "as_of": "2026-07-01T10:10:00",
        "cycle_id": "cycle-1",
        "cash": 9000,
        "positions": {
            "AAPL": {
                "ticker": "AAPL",
                "quantity": 10,
                "cost_basis": 100,
                "current_price": 100,
                "current_value": 1000,
                "unrealized_pl": 0,
            },
        },
        "current_value": 1000,
        "realized_pl": 0,
        "unrealized_pl": 0,
        "portfolio_value": 10000,
        "daily_return": 0,
        "total_return": 0,
        "price_source": "test_live_prices",
        "policy": policy,
    })
    save_paper_fund_snapshot({
        "as_of": "2026-07-02T10:10:00",
        "cycle_id": "cycle-2",
        "cash": 9000,
        "positions": {
            "AAPL": {
                "ticker": "AAPL",
                "quantity": 10,
                "cost_basis": 100,
                "current_price": 110,
                "current_value": 1100,
                "unrealized_pl": 100,
            },
        },
        "current_value": 1100,
        "realized_pl": 0,
        "unrealized_pl": 100,
        "portfolio_value": 10100,
        "daily_return": 1,
        "total_return": 1,
        "price_source": "test_live_prices",
        "policy": policy,
    })

    save_risk_decision({
        "decision_id": "risk-approved-aapl",
        "cycle_id": "cycle-1",
        "symbol": "AAPL",
        "side": "BUY",
        "quantity": 10,
        "verdict": "APPROVED",
        "checks": {
            "checks": [
                {
                    "rule": "affordability",
                    "status": "APPROVED",
                    "limit": 10000,
                    "measured": 1000,
                    "reason": "Buy order value is within available cash.",
                }
            ],
            "rejections": [],
            "reasons": [],
        },
        "policy": policy,
        "created_at": "2026-07-01T10:01:00",
    })
    for index, quantity in enumerate((5, 6), start=1):
        save_risk_decision({
            "decision_id": f"risk-rejected-msft-{index}",
            "cycle_id": f"cycle-{index}",
            "symbol": "MSFT",
            "side": "BUY",
            "quantity": quantity,
            "verdict": "REJECTED",
            "checks": {
                "checks": [],
                "rejections": [
                    {
                        "rule": "affordability",
                        "status": "REJECTED",
                        "limit": 500,
                        "measured": 1000,
                        "reason": "Buy order value exceeds available cash.",
                    }
                ],
                "reasons": ["Buy order value exceeds available cash."],
            },
            "policy": policy,
            "created_at": f"2026-07-0{index}T10:02:00",
        })


original_database_path = connection.DATABASE_PATH
with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as database_file:
    database_path = database_file.name

try:
    connection.DATABASE_PATH = database_path
    connection._wal_initialized_paths.discard(database_path)
    run_migrations()
    seed_history()

    counts_before = table_counts(database_path)
    engine = SelfLearningAnalyticsEngine()
    report = engine.generate(limit=100)
    repeated_report = engine.generate(limit=100)
    counts_after = table_counts(database_path)

    assert report == repeated_report
    assert counts_before == counts_after

    assert report["policy"] == {
        "read_only": True,
        "descriptive_only": True,
        "does_not_modify_recommendations": True,
        "does_not_modify_trades": True,
        "does_not_modify_risk_limits": True,
        "paper_only": True,
        "real_money": False,
    }
    assert report["source_counts"] == {
        "paper_fund_learning": 2,
        "paper_fund_orders": 1,
        "paper_fund_snapshots": 2,
        "risk_decisions": 3,
    }

    outcomes = {
        item["symbol"]: item
        for item in report["recommendation_outcomes"]["items"]
    }
    assert outcomes["AAPL"]["result"] == "HELPED"
    assert outcomes["ZZZZ"]["status"] == "NOT_EVALUATED"
    assert "no order" in outcomes["ZZZZ"]["reason"]

    trade_items = report["trade_impact"]["items"]
    assert len(trade_items) == 1
    assert trade_items[0]["symbol"] == "AAPL"
    assert trade_items[0]["impact_status"] == "EVALUATED"
    assert trade_items[0]["impact"]["value"] == 100

    blockers = report["risk_blockers"]
    affordability = [
        item for item in blockers["by_rule"]
        if item["rule"] == "affordability"
    ][0]
    assert affordability["count"] == 2
    assert affordability["symbols"] == ["MSFT"]

    watch = report["watch_patterns"]["items"]
    assert any(
        item.get("symbol") == "MSFT"
        and "Buy order value exceeds available cash." in item.get("reasons", [])
        for item in watch
    )
    assert any(
        item["type"] == "REPEATED_RISK_BLOCKER"
        and item["rule"] == "affordability"
        and item["count"] == 2
        for item in watch
    )

    symbol_items = {
        item["symbol"]: item
        for item in report["symbol_performance"]["items"]
    }
    assert symbol_items["AAPL"]["result"] == "HELPED"
    assert symbol_items["MSFT"]["status"] == "NOT_EVALUATED"

    sector = report["sector_performance"]
    assert sector["status"] == "PARTIAL"
    assert sector["items"][0]["sector"] == "Technology"
    assert sector["items"][0]["unrealized_pl"] == 100
    assert sector["missing_sector"] == [
        {
            "symbol": "ZZZZ",
            "status": "NOT_EVALUATED",
            "reason": "Sector metadata is unavailable for this symbol.",
        }
    ]

    from api.main import app, learning_analytics

    assert any(
        route.path == "/learning/analytics"
        and "GET" in route.methods
        for route in app.routes
    )

    api_counts_before = table_counts(database_path)
    api_report = learning_analytics(limit=100)
    api_counts_after = table_counts(database_path)

    assert api_counts_before == api_counts_after
    assert api_report["policy"] == report["policy"]
    for section in (
        "recommendation_outcomes",
        "trade_impact",
        "risk_blockers",
        "symbol_performance",
        "sector_performance",
        "watch_patterns",
    ):
        assert section in api_report

    api_outcomes = {
        item["symbol"]: item
        for item in api_report["recommendation_outcomes"]["items"]
    }
    assert api_outcomes["AAPL"]["result"] == "HELPED"
    assert api_outcomes["MSFT"]["rejection_count"] == 2
    api_blocker = [
        item for item in api_report["risk_blockers"]["by_rule"]
        if item["rule"] == "affordability"
    ][0]
    assert api_blocker["count"] == 2
finally:
    connection.DATABASE_PATH = original_database_path
    cleanup_database(database_path)


print("SelfLearningAnalyticsEngine test passed.")
