import os

from core.settings import (
    APPROVED_TICKERS,
    CATALYST_PROVIDER,
    DATA_PROVIDER,
    FORECAST_PROVIDER,
    FUNDAMENTAL_PROVIDER,
    HISTORICAL_DATA_PROVIDER,
    MACRO_PROVIDER,
    NEWS_PROVIDER,
    PORTFOLIO_PROVIDER,
    RESEARCH_PROVIDER,
)
from market.provider_health import (
    EXPERIMENTAL,
    HEALTHY,
    MOCK,
    UNAVAILABLE,
    provider_health,
    summarize_provider_health,
)
from market.provider_metadata import provider_metadata


class ProviderRegistry:
    CATEGORIES = [
        "Market Data",
        "Historical Data",
        "Forecast",
        "News",
        "Fundamentals",
        "SEC Filings",
        "Catalysts",
        "Macro",
        "Portfolio",
        "Research",
    ]

    def __init__(self):
        self._providers = []
        self._register_defaults()

    def providers(self):
        return sorted(
            self._providers,
            key=lambda item: (
                item["category"],
                item["priority"],
                item["name"],
            ),
        )

    def by_category(self, category):
        return [
            provider for provider in self.providers()
            if provider["category"] == category
        ]

    def market_data_providers(self):
        return self.by_category("Market Data")

    def health(self):
        providers = self.providers()

        return {
            "summary": summarize_provider_health(providers),
            "providers": [
                {
                    "name": provider["name"],
                    "category": provider["category"],
                    "status": provider["status"],
                    "health": provider["health"],
                    "supports_offline": provider["supports_offline"],
                    "requires_api_key": provider["requires_api_key"],
                    "deterministic": provider["deterministic"],
                }
                for provider in providers
            ],
        }

    def metadata(self):
        return [
            {
                "name": provider["name"],
                "category": provider["category"],
                "metadata": provider["metadata"],
            }
            for provider in self.providers()
        ]

    def summary(self):
        providers = self.providers()

        return {
            "categories": self.CATEGORIES,
            "provider_count": len(providers),
            "active_providers": self.active_providers(),
            "health_summary": summarize_provider_health(providers),
            "offline_capability": {
                "mock_default": True,
                "offline_tests_supported": True,
                "offline_capable_providers": [
                    provider["name"] for provider in providers
                    if provider["supports_offline"]
                ],
            },
            "experimental_providers": [
                provider["name"] for provider in providers
                if provider["status"] == EXPERIMENTAL
            ],
            "policy": {
                "requires_api_keys_by_default": False,
                "mock_providers_remain_default": True,
                "providers_are_swappable": True,
                "changes_recommendation_behavior": False,
            },
        }

    def active_providers(self):
        return {
            "Market Data": DATA_PROVIDER,
            "Historical Data": HISTORICAL_DATA_PROVIDER,
            "Forecast": FORECAST_PROVIDER,
            "News": NEWS_PROVIDER,
            "Fundamentals": FUNDAMENTAL_PROVIDER,
            "SEC Filings": os.environ.get("SEC_PROVIDER", "mock"),
            "Catalysts": CATALYST_PROVIDER,
            "Macro": MACRO_PROVIDER,
            "Portfolio": PORTFOLIO_PROVIDER,
            "Research": RESEARCH_PROVIDER,
        }

    def register(self, provider):
        if provider["category"] not in self.CATEGORIES:
            raise ValueError(f"Unsupported provider category: {provider['category']}")

        self._providers.append(provider)

    def _register_defaults(self):
        self._register_market_data()
        self._register_historical_data()
        self._register_forecast()
        self._register_news()
        self._register_fundamentals()
        self._register_sec_filings()
        self._register_catalysts()
        self._register_macro()
        self._register_portfolio()
        self._register_research()

    def _provider(
        self,
        name,
        category,
        version,
        status,
        capabilities,
        requires_api_key,
        deterministic,
        supports_offline,
        priority,
        health,
        metadata,
    ):
        return {
            "name": name,
            "category": category,
            "version": version,
            "status": status,
            "capabilities": capabilities,
            "requires_api_key": requires_api_key,
            "deterministic": deterministic,
            "supports_offline": supports_offline,
            "priority": priority,
            "health": health,
            "metadata": metadata,
        }

    def _mock_health(self, message):
        return provider_health(MOCK, healthy=True, message=message)

    def _experimental_health(self, message):
        return provider_health(EXPERIMENTAL, healthy=False, message=message)

    def _unavailable_health(self, message):
        return provider_health(UNAVAILABLE, healthy=False, message=message)

    def _register_market_data(self):
        self.register(self._provider(
            name="mock-market-data",
            category="Market Data",
            version="1.0",
            status=MOCK,
            capabilities=["price_history", "latest_price", "approved_tickers"],
            requires_api_key=False,
            deterministic=True,
            supports_offline=True,
            priority=10,
            health=self._mock_health("Default deterministic market data provider."),
            metadata=provider_metadata(
                supported_tickers=APPROVED_TICKERS,
                coverage="Deterministic synthetic daily close history.",
                earliest_date="offline-generated",
                latest_date="offline-generated",
                update_frequency="On demand",
                known_limitations=["Synthetic prices are not live market data."],
            ),
        ))
        self.register(self._provider(
            name="yahoo-market-data",
            category="Market Data",
            version="experimental",
            status=EXPERIMENTAL,
            capabilities=["price_history", "latest_price"],
            requires_api_key=False,
            deterministic=False,
            supports_offline=False,
            priority=50,
            health=self._experimental_health("Optional yfinance-backed provider with mock fallback."),
            metadata=provider_metadata(
                supported_tickers=APPROVED_TICKERS,
                coverage="Yahoo Finance ticker history when yfinance is available.",
                earliest_date="provider-dependent",
                latest_date="provider-dependent",
                update_frequency="Provider-dependent",
                known_limitations=["Network and package availability are not guaranteed."],
            ),
        ))
        self._register_future_market_provider("polygon-market-data", "Polygon market data candidate.", True)
        self._register_future_market_provider("alpaca-market-data", "Alpaca market data candidate (market data only, no broker).", True)
        self._register_future_market_provider("alpha-vantage-market-data", "Alpha Vantage market data candidate.", True)
        self._register_future_market_provider("finnhub-market-data", "Finnhub market data candidate.", True)
        self._register_future_market_provider("stooq-market-data", "Stooq market data candidate.", False)

    def _register_historical_data(self):
        self.register(self._provider(
            name="mock-historical-data",
            category="Historical Data",
            version="1.0",
            status=MOCK,
            capabilities=["ohlcv", "historical_replay", "approved_tickers"],
            requires_api_key=False,
            deterministic=True,
            supports_offline=True,
            priority=10,
            health=self._mock_health("Default deterministic historical OHLCV provider."),
            metadata=provider_metadata(
                supported_tickers=APPROVED_TICKERS,
                coverage="Synthetic OHLCV rows for approved tickers.",
                earliest_date="2020-01-01",
                latest_date="offline-generated",
                update_frequency="On demand",
                known_limitations=["Synthetic rows are for deterministic research only."],
            ),
        ))
        self.register(self._provider(
            name="yahoo-historical-data",
            category="Historical Data",
            version="experimental",
            status=EXPERIMENTAL,
            capabilities=["ohlcv", "historical_replay"],
            requires_api_key=False,
            deterministic=False,
            supports_offline=False,
            priority=50,
            health=self._experimental_health("Optional yfinance historical provider with mock fallback."),
            metadata=provider_metadata(
                supported_tickers=APPROVED_TICKERS,
                coverage="Yahoo Finance OHLCV history when available.",
                earliest_date="provider-dependent",
                latest_date="provider-dependent",
                update_frequency="Provider-dependent",
                known_limitations=["Network availability and ticker coverage vary."],
            ),
        ))
        for name in ["csv-historical-data", "parquet-historical-data"]:
            self.register(self._provider(
                name=name,
                category="Historical Data",
                version="planned",
                status=EXPERIMENTAL,
                capabilities=["ohlcv", "offline_files"],
                requires_api_key=False,
                deterministic=True,
                supports_offline=True,
                priority=70,
                health=self._experimental_health("Planned offline file-backed historical provider."),
                metadata=provider_metadata(
                    supported_tickers=[],
                    coverage="User-supplied historical files.",
                    earliest_date="file-dependent",
                    latest_date="file-dependent",
                    update_frequency="Manual file refresh",
                    known_limitations=["No loader is active yet."],
                ),
            ))

    def _register_forecast(self):
        self.register(self._provider(
            name="mock-forecast",
            category="Forecast",
            version="1.0",
            status=MOCK,
            capabilities=["deterministic_forecast", "confidence"],
            requires_api_key=False,
            deterministic=True,
            supports_offline=True,
            priority=10,
            health=self._mock_health("Default deterministic forecast provider."),
            metadata=provider_metadata(
                supported_tickers=APPROVED_TICKERS,
                coverage="Approved ticker forecast placeholders.",
                earliest_date="not-applicable",
                latest_date="not-applicable",
                update_frequency="On demand",
                known_limitations=["Forecasts are deterministic research signals."],
            ),
        ))
        self.register(self._provider(
            name="kronos-forecast",
            category="Forecast",
            version="experimental",
            status=EXPERIMENTAL,
            capabilities=["time_series_forecast"],
            requires_api_key=False,
            deterministic=False,
            supports_offline=False,
            priority=60,
            health=self._experimental_health("Optional local Kronos integration candidate."),
            metadata=provider_metadata(
                supported_tickers=APPROVED_TICKERS,
                coverage="Local model availability dependent.",
                earliest_date="model-dependent",
                latest_date="model-dependent",
                update_frequency="On demand",
                known_limitations=["Requires local model assets to be available."],
            ),
        ))

    def _register_news(self):
        self.register(self._provider(
            name="fake-news",
            category="News",
            version="1.0",
            status=MOCK,
            capabilities=["headlines", "sentiment"],
            requires_api_key=False,
            deterministic=True,
            supports_offline=True,
            priority=10,
            health=self._mock_health("Default deterministic news provider."),
            metadata=provider_metadata(
                supported_tickers=APPROVED_TICKERS,
                coverage="Synthetic news headlines for approved tickers.",
                earliest_date="offline-generated",
                latest_date="offline-generated",
                update_frequency="On demand",
                known_limitations=["Synthetic headlines are not live news."],
            ),
        ))
        self.register(self._provider(
            name="rss-news",
            category="News",
            version="experimental",
            status=EXPERIMENTAL,
            capabilities=["rss_headlines", "sentiment"],
            requires_api_key=False,
            deterministic=False,
            supports_offline=False,
            priority=50,
            health=self._experimental_health("Optional no-key RSS provider."),
            metadata=provider_metadata(
                supported_tickers=APPROVED_TICKERS,
                coverage="Provider-dependent public RSS coverage.",
                earliest_date="feed-dependent",
                latest_date="feed-dependent",
                update_frequency="Feed-dependent",
                known_limitations=["RSS feeds can be unavailable or sparse."],
            ),
        ))

    def _register_fundamentals(self):
        self.register(self._provider(
            name="mock-fundamentals",
            category="Fundamentals",
            version="1.0",
            status=MOCK,
            capabilities=["company_fundamentals", "valuation_inputs"],
            requires_api_key=False,
            deterministic=True,
            supports_offline=True,
            priority=10,
            health=self._mock_health("Default deterministic fundamentals provider."),
            metadata=provider_metadata(
                supported_tickers=APPROVED_TICKERS,
                coverage="Synthetic fundamentals for approved tickers.",
                earliest_date="offline-generated",
                latest_date="offline-generated",
                update_frequency="On demand",
                known_limitations=["Synthetic fundamentals are not filings."],
            ),
        ))
        self.register(self._provider(
            name="yahoo-fundamentals",
            category="Fundamentals",
            version="experimental",
            status=EXPERIMENTAL,
            capabilities=["company_fundamentals"],
            requires_api_key=False,
            deterministic=False,
            supports_offline=False,
            priority=50,
            health=self._experimental_health("Optional Yahoo fundamentals provider with fallback."),
            metadata=provider_metadata(
                supported_tickers=APPROVED_TICKERS,
                coverage="Yahoo Finance fundamentals when available.",
                earliest_date="provider-dependent",
                latest_date="provider-dependent",
                update_frequency="Provider-dependent",
                known_limitations=["Coverage varies by ticker."],
            ),
        ))
        self.register(self._provider(
            name="sec-edgar-fundamentals",
            category="Fundamentals",
            version="planned",
            status=EXPERIMENTAL,
            capabilities=["filings", "company_facts"],
            requires_api_key=False,
            deterministic=False,
            supports_offline=False,
            priority=70,
            health=self._experimental_health("Future SEC EDGAR integration candidate."),
            metadata=provider_metadata(
                supported_tickers=[],
                coverage="Public company filings.",
                earliest_date="provider-dependent",
                latest_date="provider-dependent",
                update_frequency="Filing-dependent",
                known_limitations=["Integration is not active yet."],
            ),
        ))

    def _register_catalysts(self):
        self.register(self._provider(
            name="mock-catalysts",
            category="Catalysts",
            version="1.0",
            status=MOCK,
            capabilities=["earnings", "macro_events", "corporate_events"],
            requires_api_key=False,
            deterministic=True,
            supports_offline=True,
            priority=10,
            health=self._mock_health("Default deterministic catalyst provider."),
            metadata=provider_metadata(
                supported_tickers=APPROVED_TICKERS,
                coverage="Synthetic catalyst events.",
                earliest_date="offline-generated",
                latest_date="offline-generated",
                update_frequency="On demand",
                known_limitations=["Synthetic events are not a live calendar."],
            ),
        ))

    def _register_sec_filings(self):
        self.register(self._provider(
            name="mock-sec-filings",
            category="SEC Filings",
            version="1.0",
            status=MOCK,
            capabilities=[
                "10-K",
                "10-Q",
                "8-K",
                "DEF 14A",
                "S-1",
                "section_summaries",
            ],
            requires_api_key=False,
            deterministic=True,
            supports_offline=True,
            priority=10,
            health=self._mock_health("Default deterministic SEC filings provider."),
            metadata=provider_metadata(
                supported_tickers=APPROVED_TICKERS,
                coverage="Synthetic normalized SEC filing records.",
                earliest_date="offline-generated",
                latest_date="offline-generated",
                update_frequency="On demand",
                known_limitations=[
                    "Mock filings are placeholders and not live EDGAR records."
                ],
            ),
        ))
        self.register(self._provider(
            name="sec-edgar-filings",
            category="SEC Filings",
            version="planned",
            status=EXPERIMENTAL,
            capabilities=[
                "10-K",
                "10-Q",
                "8-K",
                "DEF 14A",
                "S-1",
                "filing_urls",
                "section_summaries",
            ],
            requires_api_key=False,
            deterministic=False,
            supports_offline=False,
            priority=60,
            health=self._experimental_health(
                "Future no-key SEC EDGAR filings provider."
            ),
            metadata=provider_metadata(
                supported_tickers=[],
                coverage="Public EDGAR filings when future integration is enabled.",
                earliest_date="provider-dependent",
                latest_date="provider-dependent",
                update_frequency="Filing-dependent",
                known_limitations=[
                    "EDGAR retrieval is not active during offline tests."
                ],
            ),
        ))

    def _register_macro(self):
        self.register(self._provider(
            name="mock-macro",
            category="Macro",
            version="1.0",
            status=MOCK,
            capabilities=[
                "CPI",
                "Fed Funds Rate",
                "Unemployment",
                "GDP Growth",
                "10Y Treasury Yield",
                "Yield Curve Spread",
                "macro_regime",
            ],
            requires_api_key=False,
            deterministic=True,
            supports_offline=True,
            priority=10,
            health=self._mock_health("Default deterministic macro data provider."),
            metadata=provider_metadata(
                supported_tickers=[],
                coverage="Offline FRED-style macro indicators.",
                earliest_date="offline-generated",
                latest_date="offline-generated",
                update_frequency="On demand",
                known_limitations=["Mock macro readings are deterministic placeholders."],
            ),
        ))
        self.register(self._provider(
            name="fred-macro",
            category="Macro",
            version="planned",
            status=EXPERIMENTAL,
            capabilities=[
                "CPI",
                "Fed Funds Rate",
                "Unemployment",
                "GDP Growth",
                "10Y Treasury Yield",
                "Yield Curve Spread",
                "economic_series",
            ],
            requires_api_key=False,
            deterministic=False,
            supports_offline=False,
            priority=70,
            health=self._experimental_health("Future no-key FRED-style integration candidate."),
            metadata=provider_metadata(
                supported_tickers=[],
                coverage="Economic time series.",
                earliest_date="series-dependent",
                latest_date="series-dependent",
                update_frequency="Series-dependent",
                known_limitations=["Integration is not active during offline tests."],
            ),
        ))

    def _register_portfolio(self):
        self.register(self._provider(
            name="local-portfolio",
            category="Portfolio",
            version="1.0",
            status=HEALTHY,
            capabilities=["cash", "positions", "risk_snapshot"],
            requires_api_key=False,
            deterministic=True,
            supports_offline=True,
            priority=10,
            health=provider_health(HEALTHY, healthy=True, message="Local portfolio state only."),
            metadata=provider_metadata(
                supported_tickers=APPROVED_TICKERS,
                coverage="Local Atlas portfolio model.",
                earliest_date="not-applicable",
                latest_date="not-applicable",
                update_frequency="On demand",
                known_limitations=["No broker connection or execution."],
            ),
        ))

    def _register_research(self):
        self.register(self._provider(
            name="local-research",
            category="Research",
            version="1.0",
            status=HEALTHY,
            capabilities=["experiments", "case_studies", "research_memory"],
            requires_api_key=False,
            deterministic=True,
            supports_offline=True,
            priority=10,
            health=provider_health(HEALTHY, healthy=True, message="Local deterministic research storage."),
            metadata=provider_metadata(
                supported_tickers=APPROVED_TICKERS,
                coverage="Local Atlas research records.",
                earliest_date="database-dependent",
                latest_date="database-dependent",
                update_frequency="On demand",
                known_limitations=["Depends on locally persisted research history."],
            ),
        ))

    def _register_future_market_provider(self, name, description, requires_api_key):
        self.register(self._provider(
            name=name,
            category="Market Data",
            version="planned",
            status=EXPERIMENTAL,
            capabilities=["price_history", "latest_price"],
            requires_api_key=requires_api_key,
            deterministic=False,
            supports_offline=False,
            priority=80,
            health=self._unavailable_health(description),
            metadata=provider_metadata(
                supported_tickers=[],
                coverage="Future integration candidate.",
                earliest_date="provider-dependent",
                latest_date="provider-dependent",
                update_frequency="Provider-dependent",
                known_limitations=["Provider is registered but not integrated."],
            ),
        ))
