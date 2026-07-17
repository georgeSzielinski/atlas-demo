from engines.news_provider import NewsProvider


class FakeNewsProvider(NewsProvider):

    def get_headlines(self, ticker):
        symbol = str(ticker).upper()

        return [
            f"{symbol} market update remains neutral in offline mode",
            f"{symbol} research signal available from fake news provider",
            f"{symbol} headline fixture supports deterministic tests",
        ]

    def get_provider_name(self):
        return "fake"

    def health_check(self):
        return {
            "provider": self.get_provider_name(),
            "healthy": True,
            "message": "Fake news provider is available offline.",
        }
