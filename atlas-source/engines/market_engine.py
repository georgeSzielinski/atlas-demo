from market.analyzer import MarketAnalyzer


class MarketEngine:

    def __init__(self, market_data_manager=None):
        self.analyzer = MarketAnalyzer()
        self._market_data_manager = market_data_manager

    def analyze_market(self, tickers):
        return self.analyzer.analyze_many(tickers)

    def market_data_manager(self):
        if self._market_data_manager is None:
            from market.market_data_manager import MarketDataManager

            self._market_data_manager = MarketDataManager()

        return self._market_data_manager

    def market_status(self, as_of=None):
        """Validated market status via the Market Data Manager (read-only)."""
        return self.market_data_manager().market_status(as_of)

    def data_snapshot(self, tickers=None, as_of=None):
        """Validated, cached market snapshot via the Market Data Manager."""
        return self.market_data_manager().snapshot(tickers=tickers, as_of=as_of)
