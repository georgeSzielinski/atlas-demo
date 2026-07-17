from engines.catalyst_provider import CatalystProvider


class MockCatalystProvider(CatalystProvider):
    provider_name = "mock"

    def get_events(self, tickers=None, as_of_date=None):
        requested = {ticker.upper() for ticker in (tickers or [])}
        events = [
            self._event("AAPL", "Company", "Earnings", "2026-07-15", 92, 86, "High", "High", 78),
            self._event("AAPL", "Company", "Product Launch", "2026-08-05", 72, 74, "Medium", "Medium", 58),
            self._event("MSFT", "Company", "Dividend", "2026-07-10", 54, 88, "Low", "Low", 42),
            self._event("MSFT", "Company", "Investor Day", "2026-09-01", 76, 73, "Medium", "Medium", 64),
            self._event("NVDA", "Company", "Guidance Update", "2026-07-22", 88, 80, "High", "High", 75),
            self._event("AMZN", "Company", "SEC Filing", "2026-07-08", 62, 82, "Medium", "Medium", 50),
            self._event("COST", "Company", "Earnings", "2026-07-18", 84, 82, "Medium", "Medium", 70),
            self._event("GOOGL", "Company", "Investor Day", "2026-08-18", 74, 70, "Medium", "Medium", 60),
            self._event(None, "Macro", "CPI", "2026-07-11", 95, 90, "High", "High", 82),
            self._event(None, "Macro", "PPI", "2026-07-12", 80, 86, "Medium", "Medium", 66),
            self._event(None, "Macro", "Jobs Report", "2026-07-03", 86, 88, "High", "High", 72),
            self._event(None, "Macro", "FOMC", "2026-07-30", 98, 90, "High", "High", 88),
            self._event(None, "Macro", "GDP", "2026-07-25", 82, 84, "Medium", "Medium", 68),
            self._event(None, "Macro", "Retail Sales", "2026-07-16", 74, 80, "Medium", "Medium", 55),
            self._event(None, "Market", "Options Expiration", "2026-07-17", 78, 92, "Medium", "High", 60),
            self._event(None, "Market", "Index Rebalance", "2026-09-20", 70, 78, "Medium", "Medium", 52),
        ]

        if not requested:
            return events

        return [
            event for event in events
            if event["ticker"] is None or event["ticker"] in requested
        ]

    def _event(
        self,
        ticker,
        catalyst_group,
        event_type,
        event_date,
        importance,
        confidence,
        risk_level,
        volatility_level,
        historical_relevance,
    ):
        return {
            "ticker": ticker,
            "catalyst_group": catalyst_group,
            "event_type": event_type,
            "event_date": event_date,
            "importance": importance,
            "confidence": confidence,
            "risk_level": risk_level,
            "potential_volatility_level": volatility_level,
            "historical_relevance_placeholder": historical_relevance,
            "provider": self.provider_name,
        }
