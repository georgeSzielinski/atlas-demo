from engines.catalyst_provider import CatalystProvider


class CalendarProvider(CatalystProvider):
    provider_name = "calendar_placeholder"

    def __init__(self, provider_name=None):
        if provider_name:
            self.provider_name = provider_name

    def get_events(self, tickers=None, as_of_date=None):
        return []
