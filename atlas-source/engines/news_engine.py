from core.settings import NEWS_PROVIDER, SUPPORTED_NEWS_PROVIDERS
from engines.fake_news_provider import FakeNewsProvider
from engines.rss_news_provider import RSSNewsProvider


class NewsEngine:
    """Provider-based news intelligence engine."""

    def __init__(self, news_provider=None, timeout=5):
        self.provider = self._select_provider(news_provider, timeout)
        self.timeout = timeout

    def analyze(self, ticker):
        headlines = self.provider.get_headlines(ticker)

        return {
            "sentiment": "neutral",
            "confidence": 50 if headlines else 0,
            "headline_count": len(headlines),
            "headlines": headlines[:5],
            "top_headlines": headlines[:5],
            "summary": self._build_summary(ticker, headlines),
            "provider": self.provider.get_provider_name(),
        }

    def health_check(self):
        return self.provider.health_check()

    def _select_provider(self, news_provider, timeout):
        selected_provider = news_provider or NEWS_PROVIDER

        if selected_provider not in SUPPORTED_NEWS_PROVIDERS:
            return FakeNewsProvider()

        if selected_provider == "rss":
            return RSSNewsProvider(timeout=timeout)

        return FakeNewsProvider()

    def _build_summary(self, ticker, headlines):
        if not headlines:
            return f"No news headlines were available for {ticker}."

        return (
            f"Found {len(headlines)} recent headline"
            f"{'s' if len(headlines) != 1 else ''} for {ticker}."
        )
