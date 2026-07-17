from core.settings import FUNDAMENTAL_PROVIDER
from api.main import _fundamental_provider_health
from backend.status import fundamental_provider_status
from engines.fundamental_engine import FundamentalEngine
from engines.mock_fundamental_provider import MockFundamentalProvider
from engines.yahoo_fundamental_provider import YahooFundamentalProvider


engine = FundamentalEngine()
result = engine.analyze("AAPL")

assert FUNDAMENTAL_PROVIDER == "mock"
assert isinstance(engine.provider, MockFundamentalProvider)
assert result["provider"] == "mock"
assert result["revenue"] > 0
assert result["eps"] > 0
assert result["pe_ratio"] == 30
assert result["debt"] > 0
assert result["cash"] > 0
assert result["market_cap"] > 0
assert result["profit_margin"] == 24
assert result["roe"] == 150
assert result["confidence"] > 0
assert engine.health_check()["healthy"] is True

status_health = fundamental_provider_status()
api_health = _fundamental_provider_health()

assert status_health["active_provider"] == "mock"
assert status_health["healthy"] is True
assert status_health["data_availability"] is True
assert status_health["failure_message"] == ""
assert api_health["active_provider"] == "mock"
assert api_health["healthy"] is True
assert api_health["data_availability"] is True
assert api_health["failure_message"] == ""

legacy_result = engine.analyze({
    "earnings_growth": 12,
    "revenue_growth": 8,
    "debt_to_equity": 0.4,
    "profit_margin": 20,
    "pe_ratio": 25,
})

assert legacy_result["score"] == 100
assert legacy_result["provider"] == "mock"

invalid_engine = FundamentalEngine(fundamental_provider="invalid")
invalid_result = invalid_engine.analyze("MSFT")

assert isinstance(invalid_engine.provider, MockFundamentalProvider)
assert invalid_result["provider"] == "mock"
assert invalid_result["revenue"] > 0

yahoo_provider = YahooFundamentalProvider()


def unavailable_info(ticker):
    raise OSError("yahoo unavailable")


yahoo_provider._get_info = unavailable_info

fallback_profile = yahoo_provider.get_company_profile("AAPL")
fallback_fundamentals = yahoo_provider.get_fundamentals("AAPL")

assert fallback_profile["ticker"] == "AAPL"
assert fallback_fundamentals["revenue"] > 0
assert yahoo_provider.health_check()["healthy"] is True

yahoo_engine = FundamentalEngine(fundamental_provider="yahoo")
yahoo_engine.provider._get_info = unavailable_info
yahoo_result = yahoo_engine.analyze("AAPL")

assert yahoo_result["provider"] == "yahoo"
assert yahoo_result["revenue"] > 0
assert yahoo_result["confidence"] > 0

print("FundamentalEngine provider test passed.")
