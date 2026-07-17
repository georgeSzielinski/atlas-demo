class CatalystProvider:
    provider_name = "base"

    def get_events(self, tickers=None, as_of_date=None):
        raise NotImplementedError

    def health_check(self, tickers=None, as_of_date=None):
        try:
            events = self.get_events(tickers=tickers, as_of_date=as_of_date)
            dates = sorted([
                event.get("event_date")
                for event in events
                if event.get("event_date")
            ])

            return {
                "provider": self.provider_name,
                "healthy": True,
                "events_available": len(events),
                "date_range": {
                    "start_date": dates[0] if dates else None,
                    "end_date": dates[-1] if dates else None,
                },
                "failure_message": "",
            }
        except Exception as error:
            return {
                "provider": self.provider_name,
                "healthy": False,
                "events_available": 0,
                "date_range": {"start_date": None, "end_date": None},
                "failure_message": str(error),
            }
