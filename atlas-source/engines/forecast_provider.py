class ForecastProvider:

    def forecast(self, stock):
        raise NotImplementedError(
            "Forecast providers must implement forecast()."
        )
