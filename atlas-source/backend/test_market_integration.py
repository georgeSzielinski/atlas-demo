import os
import tempfile

import database.connection as connection
from api.main import (
    market_cache_dashboard,
    market_health_dashboard,
    market_provider_dashboard,
    market_status_dashboard,
)
from database.repository import (
    get_latest_market_data_snapshot,
    save_market_data_snapshot,
)
from database.setup import setup_database
from engines.paper_trading_engine import PaperTradingEngine
from market.data_cache import MarketDataCache
from market.data_validator import MarketDataValidator
from market.market_data_manager import MarketDataManager
from market.provider_health import data_freshness


# ------------------------------------------------------------------
# Part 3 - Validation
# ------------------------------------------------------------------
validator = MarketDataValidator()

good_rows = [
    {"date": "2024-01-01", "open": 100, "high": 105, "low": 99, "close": 104},
    {"date": "2024-01-02", "open": 104, "high": 108, "low": 103, "close": 107},
    {"date": "2024-01-03", "open": 107, "high": 110, "low": 106, "close": 109},
]
good = validator.validate_rows(good_rows, ticker="AAPL", supported_tickers=["AAPL"])
assert good["valid"] is True
assert good["row_count"] == 3
assert any(check["check"] == "corporate_action_awareness" for check in good["checks"])
assert any(check["check"] == "market_calendar" for check in good["checks"])

unknown_ticker = validator.validate_rows(good_rows, ticker="ZZZZ", supported_tickers=["AAPL"])
assert unknown_ticker["valid"] is False

unordered = validator.validate_rows(
    [
        {"date": "2024-01-03", "open": 107, "high": 110, "low": 106, "close": 109},
        {"date": "2024-01-01", "open": 100, "high": 105, "low": 99, "close": 104},
    ],
    ticker="AAPL",
    supported_tickers=["AAPL"],
)
assert unordered["valid"] is False
assert any(
    check["check"] == "timestamps_ordered" and not check["passed"]
    for check in unordered["checks"]
)

inconsistent = validator.validate_rows(
    [{"date": "2024-01-01", "open": 100, "high": 95, "low": 99, "close": 104}],
    ticker="AAPL",
    supported_tickers=["AAPL"],
)
assert inconsistent["valid"] is False
assert any(
    check["check"] == "ohlc_consistent" and not check["passed"]
    for check in inconsistent["checks"]
)

missing = validator.validate_rows(
    [{"date": "2024-01-01", "open": None, "high": 105, "low": 99, "close": 104}],
    ticker="AAPL",
    supported_tickers=["AAPL"],
)
assert missing["valid"] is False

duplicate = validator.validate_rows(
    [
        {"date": "2024-01-01", "open": 100, "high": 105, "low": 99, "close": 104},
        {"date": "2024-01-01", "open": 100, "high": 105, "low": 99, "close": 104},
    ],
    ticker="AAPL",
    supported_tickers=["AAPL"],
)
assert duplicate["valid"] is False

empty = validator.validate_rows([], ticker="AAPL", supported_tickers=["AAPL"])
assert empty["valid"] is False

assert validator.validate_price(191.25, ticker="AAPL", supported_tickers=["AAPL"])["valid"] is True
assert validator.validate_price(None, ticker="AAPL", supported_tickers=["AAPL"])["valid"] is False
assert validator.validate_price(-5, ticker="AAPL", supported_tickers=["AAPL"])["valid"] is False

# ------------------------------------------------------------------
# Part 4 - Caching
# ------------------------------------------------------------------
clock = {"now": 1000.0}
cache = MarketDataCache(ttl_seconds=300, clock=lambda: clock["now"])
assert cache.get("missing") is None
cache.set("latest:mock:AAPL", 191.25, "mock", fallback_used=False)
hit = cache.get("latest:mock:AAPL")
assert hit is not None
assert hit["value"] == 191.25
assert hit["cache_age"] == 0
clock["now"] = 1120.0
aged = cache.get("latest:mock:AAPL")
assert aged["cache_age"] == 120
clock["now"] = 1400.0  # beyond ttl
assert cache.get("latest:mock:AAPL") is None
stats = cache.stats()
assert stats["size"] == 1
assert stats["ttl_seconds"] == 300

freshness = data_freshness(30)
assert freshness["label"] == "Fresh"
assert data_freshness(600)["is_stale"] is True
assert data_freshness(None)["label"] == "Unknown"

# ------------------------------------------------------------------
# Part 1 + Part 2 - Manager, providers, selection, fallback
# ------------------------------------------------------------------
manager_clock = {"now": 5000.0}
manager = MarketDataManager(
    provider_name="mock",
    cache=MarketDataCache(clock=lambda: manager_clock["now"]),
)
result = manager.latest_price("AAPL")
assert result["provider"] == "mock"
assert result["fallback_used"] is False
assert result["validated"] is True
assert result["cache_hit"] is False
assert isinstance(result["price"], float)

# Second call hits the cache (clock unchanged).
cached_result = manager.latest_price("AAPL")
assert cached_result["cache_hit"] is True
assert cached_result["price"] == result["price"]

# Deterministic: a fresh manager returns the same mock price.
assert MarketDataManager(provider_name="mock").latest_price("AAPL")["price"] == result["price"]

# Fallback: unavailable providers gracefully fall back to mock.
for provider_name in ["polygon", "alpaca"]:
    fallback_manager = MarketDataManager(provider_name=provider_name)
    fallback = fallback_manager.latest_price("MSFT")
    assert fallback["fallback_used"] is True
    assert fallback["provider"] == "mock"
    assert fallback["validated"] is True
    assert fallback["price"] > 0

# Unsupported provider name defaults to mock (offline/demo default).
assert MarketDataManager(provider_name="does-not-exist").provider_name == "mock"
assert MarketDataManager().provider_name in MarketDataManager.SUPPORTED_PROVIDERS

# latest_prices batch
batch = manager.latest_prices(["AAPL", "MSFT", "GOOGL"])
assert set(batch["prices"].keys()) == {"AAPL", "MSFT", "GOOGL"}
assert batch["validated"] is True

# ------------------------------------------------------------------
# Part 5 - Market status, provider summary, health
# ------------------------------------------------------------------
weekend = manager.market_status("2026-06-28T10:00:00")  # Sunday
assert weekend["is_open"] is False
weekday_open = manager.market_status("2026-06-29T10:00:00")  # Monday 10:00
assert weekday_open["is_open"] is True
after_hours = manager.market_status("2026-06-29T18:00:00")  # Monday 18:00
assert after_hours["is_open"] is False
# Backed by a real exchange calendar now, not the naive placeholder.
assert weekday_open["market_calendar_placeholder"] is False
assert weekday_open["available"] is True
assert weekday_open["timezone"] == "America/New_York"
# US market holiday (New Year's Day) is closed even though it is a weekday.
holiday = manager.market_status("2026-01-01T10:00:00")  # Thursday holiday
assert holiday["is_open"] is False
assert holiday["is_holiday"] is True
# Early close (day after Thanksgiving) closes at 13:00 ET.
early_before = manager.market_status("2026-11-27T12:00:00")
assert early_before["is_open"] is True
assert early_before["is_early_close"] is True
early_after = manager.market_status("2026-11-27T13:30:00")
assert early_after["is_open"] is False
assert early_after["is_early_close"] is True
# A date beyond the calendar's coverage fails loudly rather than guessing.
uncovered = manager.market_status("2099-06-29T10:00:00")
assert uncovered["is_open"] is False
assert uncovered["available"] is False
assert uncovered["session"] == "unavailable"

summary = manager.provider_summary()
assert summary["current_provider"] == "mock"
assert summary["default_provider"] == "mock"
assert set(summary["supported_providers"]) == set(MarketDataManager.SUPPORTED_PROVIDERS)
assert any(detail["current"] for detail in summary["provider_details"])

health = manager.health()
assert health["active_provider"] == "mock"
assert health["healthy"] is True
assert health["fallback_used"] is False
assert isinstance(health["providers"], list)

# Policy invariants - safety
for section in (batch, health, summary, weekend):
    assert section["policy"]["broker_integration"] is False
    assert section["policy"]["automatic_execution"] is False
    assert section["policy"]["changes_recommendation_behavior"] is False

# ------------------------------------------------------------------
# Part 6 - Paper trading consumes validated prices (no execution change)
# ------------------------------------------------------------------
paper = PaperTradingEngine()
paper_prices = paper.market_prices(["AAPL", "MSFT"], manager=MarketDataManager())
assert set(paper_prices["prices"].keys()) == {"AAPL", "MSFT"}
assert paper_prices["validated"] is True
assert paper_prices["policy"]["broker_integration"] is False
assert paper_prices["policy"]["data_source"] == "MarketDataManager"

historical_paper = paper.run_historical_price_replay(
    recommendations=[
        {
            "ticker": "AAPL",
            "action": "BUY",
            "reason": "Mocked historical paper entry.",
            "sector": "Technology",
        }
    ],
    historical_rows=[
        {
            "date": "2024-01-02",
            "ticker": "AAPL",
            "open": 100,
            "high": 101,
            "low": 99,
            "close": 100,
            "volume": 1000,
        },
        {
            "date": "2024-01-03",
            "ticker": "AAPL",
            "open": 110,
            "high": 112,
            "low": 109,
            "close": 110,
            "volume": 1000,
        },
    ],
)
historical_trade = historical_paper["trades"][0]
assert historical_paper["replay_status"] == "COMPLETED"
assert historical_paper["metadata"]["mode"] == "historical_price_replay"
assert historical_paper["metadata"]["price_backed"] is True
assert historical_paper["metadata"]["data_source"] == "mocked_historical_prices"
assert historical_paper["dates_tested"] == ["2024-01-02", "2024-01-03"]
assert len(historical_paper["replay_history"]) == 2
assert historical_trade["entry_price"] == 100
assert historical_trade["quantity"] == 100
assert historical_trade["transaction_cost"] == 0
assert historical_trade["slippage"] == 0
assert historical_paper["portfolio"]["positions"]["AAPL"]["current_price"] == 110
assert historical_paper["portfolio"]["positions"]["AAPL"]["current_value"] == 11000
assert historical_paper["portfolio"]["unrealized_pl"] == 1000
assert historical_paper["portfolio"]["portfolio_value"] == 101000
assert historical_paper["policy"]["broker_integration"] is False
assert historical_paper["policy"]["real_money"] is False

missing_historical_paper = paper.run_historical_price_replay(
    recommendations=[
        {
            "ticker": "AAPL",
            "action": "BUY",
            "reason": "Mocked historical paper entry.",
            "sector": "Technology",
        },
        {
            "ticker": "MSFT",
            "action": "BUY",
            "reason": "Missing price should fail replay.",
            "sector": "Technology",
        },
    ],
    tickers=["AAPL", "MSFT"],
    historical_rows=[
        {
            "date": "2024-01-02",
            "ticker": "AAPL",
            "open": 100,
            "high": 101,
            "low": 99,
            "close": 100,
            "volume": 1000,
        },
        {
            "date": "2024-01-03",
            "ticker": "AAPL",
            "open": 110,
            "high": 112,
            "low": 109,
            "close": 110,
            "volume": 1000,
        },
    ],
)
assert missing_historical_paper["replay_status"] == "FAILED"
assert missing_historical_paper["trades"] == []
assert missing_historical_paper["replay_history"] == []
assert missing_historical_paper["policy"]["broker_integration"] is False

# ------------------------------------------------------------------
# Persistence + API (deterministic, offline)
# ------------------------------------------------------------------
original_database_path = connection.DATABASE_PATH
with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as database_file:
    database_path = database_file.name

try:
    connection.DATABASE_PATH = database_path
    setup_database()

    snapshot = MarketDataManager().snapshot(tickers=["AAPL", "MSFT"])
    save_market_data_snapshot(snapshot)
    saved = get_latest_market_data_snapshot()
    assert saved["provider"] == "mock"
    assert saved["ticker_count"] == 2
    assert saved["fallback_used"] is False
    assert set(saved["prices"].keys()) == {"AAPL", "MSFT"}

    status_api = market_status_dashboard()
    assert "market_status" in status_api
    assert status_api["snapshot"]["provider"] == "mock"
    assert status_api["policy"]["broker_integration"] is False

    provider_api = market_provider_dashboard()
    assert provider_api["current_provider"] == "mock"

    health_api = market_health_dashboard()
    assert health_api["health"]["active_provider"] == "mock"
    assert "cache_stats" in health_api

    cache_api = market_cache_dashboard()
    assert cache_api["stats"]["size"] >= 1

    # The historical adapter exposes the fallback signal that price-backed
    # replay relies on, and replay must fail loudly rather than use fallback.
    from market.yahoo_historical_data_adapter import YahooHistoricalDataAdapter

    assert YahooHistoricalDataAdapter().fallback_used is False

    class _FallbackHistoricalAdapter:
        fallback_used = True

        def get_ohlcv(self, tickers, start_date, end_date):
            return [
                {"date": "2024-01-02", "ticker": "AAPL", "open": 100, "high": 101, "low": 99, "close": 100, "volume": 1000},
                {"date": "2024-01-03", "ticker": "AAPL", "open": 110, "high": 111, "low": 109, "close": 110, "volume": 1000},
            ]

    fallback_replay = PaperTradingEngine().run_historical_price_replay(
        recommendations=[{"ticker": "AAPL", "action": "BUY"}],
        tickers=["AAPL"],
        start_date="2024-01-02",
        end_date="2024-01-03",
        historical_adapter=_FallbackHistoricalAdapter(),
    )
    assert fallback_replay["replay_status"] == "FAILED"
    assert fallback_replay["price_backed"] is False
    assert fallback_replay["audit"]["fallback_used"] is True
    assert fallback_replay["trades"] == []
finally:
    connection.DATABASE_PATH = original_database_path
    if os.path.exists(database_path):
        os.remove(database_path)

print("MarketIntegration test passed.")
