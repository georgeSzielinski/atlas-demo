from datetime import date, datetime

from core.settings import CATALYST_PROVIDER, SUPPORTED_CATALYST_PROVIDERS
from engines.calendar_provider import CalendarProvider
from engines.mock_catalyst_provider import MockCatalystProvider


class CatalystProviderFactory:
    @staticmethod
    def create(provider_name=None):
        requested = provider_name or CATALYST_PROVIDER

        if requested == "mock":
            return MockCatalystProvider()

        if requested in SUPPORTED_CATALYST_PROVIDERS:
            return CalendarProvider(provider_name=requested)

        return MockCatalystProvider()


class CatalystEngine:
    def __init__(self, provider=None, provider_name=None):
        self.provider = provider or CatalystProviderFactory.create(provider_name)

    def analyze(self, tickers=None, as_of_date=None):
        tickers = [ticker.upper() for ticker in (tickers or ["AAPL"])]
        as_of = self._date(as_of_date)
        events = [
            self._enrich_event(event, as_of)
            for event in self.provider.get_events(tickers=tickers, as_of_date=str(as_of))
        ]
        upcoming = [
            event for event in events
            if event["days_until_event"] >= 0
        ]
        contexts = {
            ticker: self._context_for_ticker(ticker, upcoming)
            for ticker in tickers
        }

        return {
            "provider": self.provider.provider_name,
            "as_of_date": str(as_of),
            "events": upcoming,
            "recommendation_contexts": contexts,
            "summary": self.summarize_events(upcoming),
            "controlled_behavior": {
                "changes_recommendation_actions": False,
                "automatic_execution": False,
                "requires_human_approval": True,
            },
        }

    def recommendation_context(self, ticker, as_of_date=None):
        return self.analyze([ticker], as_of_date=as_of_date)[
            "recommendation_contexts"
        ][ticker.upper()]

    def health_check(self, tickers=None, as_of_date=None):
        health = self.provider.health_check(
            tickers=tickers or ["AAPL"],
            as_of_date=as_of_date,
        )
        health["active_provider"] = self.provider.provider_name
        health["healthy"] = bool(health["healthy"]) and (
            health["events_available"] > 0
            or self.provider.provider_name != "mock"
        )

        return health

    def summarize_events(self, events):
        if not events:
            return {
                "event_count": 0,
                "most_common_catalyst": None,
                "highest_importance_event": None,
                "highest_volatility_event": None,
            }

        counts = {}
        for event in events:
            event_type = event["event_type"]
            counts[event_type] = counts.get(event_type, 0) + 1

        return {
            "event_count": len(events),
            "most_common_catalyst": sorted(
                counts.items(),
                key=lambda item: (-item[1], item[0]),
            )[0][0],
            "highest_importance_event": max(
                events,
                key=lambda item: (
                    item["importance"],
                    -item["days_until_event"],
                    item["event_type"],
                ),
            ),
            "highest_volatility_event": max(
                events,
                key=lambda item: (
                    self._volatility_rank(item["potential_volatility_level"]),
                    item["importance"],
                    item["event_type"],
                ),
            ),
        }

    def _context_for_ticker(self, ticker, events):
        rows = [
            event for event in events
            if event["ticker"] in {ticker, None}
        ]

        return sorted(
            rows,
            key=lambda item: (
                item["days_until_event"],
                -item["importance"],
                item["event_type"],
            ),
        )

    def _enrich_event(self, event, as_of):
        enriched = dict(event)
        event_date = self._date(event["event_date"])
        enriched["days_until_event"] = (event_date - as_of).days
        enriched["historical_relevance_placeholder"] = event.get(
            "historical_relevance_placeholder",
            0,
        )

        return enriched

    def _date(self, value):
        if value is None:
            return date(2026, 6, 30)

        if isinstance(value, date):
            return value

        return datetime.fromisoformat(str(value)[:10]).date()

    def _volatility_rank(self, level):
        return {"Low": 1, "Medium": 2, "High": 3}.get(level, 0)
