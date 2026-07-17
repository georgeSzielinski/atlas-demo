class HistoricalDataAdapter:
    provider_name = "base"
    fallback_used = False
    last_error = ""

    def get_ohlcv(self, tickers, start_date, end_date):
        raise NotImplementedError

    def get_supported_tickers(self):
        raise NotImplementedError

    def health_metadata(self):
        return {
            "provider": self.provider_name,
            "fallback_used": self.fallback_used,
            "last_error": self.last_error,
        }
