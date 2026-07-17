from core.settings import NEWS_PROVIDER
from api.main import _news_provider_health
from backend.status import news_provider_status
from engines.fake_news_provider import FakeNewsProvider
from engines.news_engine import NewsEngine
from engines.rss_news_provider import RSSNewsProvider


engine = NewsEngine()
result = engine.analyze("AAPL")

assert NEWS_PROVIDER == "fake"
assert isinstance(engine.provider, FakeNewsProvider)
assert result["sentiment"] == "neutral"
assert result["confidence"] == 50
assert isinstance(result["headline_count"], int)
assert result["headline_count"] == 3
assert isinstance(result["headlines"], list)
assert isinstance(result["top_headlines"], list)
assert result["headlines"] == result["top_headlines"]
assert len(result["top_headlines"]) <= 5
assert "AAPL" in result["summary"]
assert result["provider"] == "fake"
assert engine.health_check()["healthy"] is True

status_health = news_provider_status()
api_health = _news_provider_health()

assert status_health["active_provider"] == "fake"
assert status_health["healthy"] is True
assert status_health["headline_availability"] is True
assert status_health["failure_message"] == ""
assert api_health["active_provider"] == "fake"
assert api_health["healthy"] is True
assert api_health["headline_availability"] is True
assert api_health["failure_message"] == ""

invalid_engine = NewsEngine(news_provider="invalid")
invalid_result = invalid_engine.analyze("MSFT")

assert isinstance(invalid_engine.provider, FakeNewsProvider)
assert invalid_result["provider"] == "fake"
assert invalid_result["headline_count"] == 3

rss_provider = RSSNewsProvider()


def unavailable_headlines(ticker):
    raise OSError("network unavailable")


rss_provider._fetch_headlines = unavailable_headlines

fallback_headlines = rss_provider.get_headlines("MSFT")

assert fallback_headlines == []
assert rss_provider.health_check()["healthy"] is True

rss_engine = NewsEngine(news_provider="rss")
rss_engine.provider._fetch_headlines = unavailable_headlines
fallback_result = rss_engine.analyze("MSFT")

assert fallback_result["sentiment"] == "neutral"
assert fallback_result["confidence"] == 0
assert fallback_result["headline_count"] == 0
assert fallback_result["headlines"] == []
assert fallback_result["top_headlines"] == []
assert "MSFT" in fallback_result["summary"]
assert fallback_result["provider"] == "rss"

print("NewsEngine provider test passed.")
