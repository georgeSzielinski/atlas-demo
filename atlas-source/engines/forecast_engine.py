import logging

from core.settings import FORECAST_PROVIDER
from engines.kronos_forecast_provider import (
    KronosForecastProvider,
    KronosUnavailableError,
)
from engines.mock_forecast_provider import MockForecastProvider


logger = logging.getLogger(__name__)


class ForecastEngine:

    def __init__(self, provider=None, forecast_provider=None):
        selected_provider = forecast_provider or FORECAST_PROVIDER
        self.provider = provider or self._select_provider(selected_provider)

    def forecast(self, stock):
        try:
            return self.provider.forecast(stock)
        except KronosUnavailableError as error:
            logger.warning(
                "Kronos forecast failed: %s Falling back to "
                "MockForecastProvider.",
                error
            )
            return MockForecastProvider().forecast(stock)

    def _select_provider(self, forecast_provider):
        if forecast_provider == "kronos":
            if KronosForecastProvider.is_available():
                return KronosForecastProvider()

            logger.warning(
                "Kronos forecast provider selected but unavailable. "
                "Falling back to MockForecastProvider."
            )
            return MockForecastProvider()

        if forecast_provider != "mock":
            logger.warning(
                "Unknown forecast_provider '%s'. Falling back to "
                "MockForecastProvider.",
                forecast_provider
            )

        return MockForecastProvider()
