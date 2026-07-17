from engines.mock_sec_provider import MockSecProvider
from engines.sec_provider import SecProvider


class EdgarProvider(SecProvider):
    provider_name = "edgar"

    def __init__(self):
        self.fallback_provider = MockSecProvider()
        self.fallback_used = False
        self.last_error = ""

    def get_filings(self, tickers=None, filing_types=None):
        try:
            raise RuntimeError(
                "EDGAR provider is registered for future integration and "
                "is not active in offline mode."
            )
        except Exception as error:
            self.fallback_used = True
            self.last_error = str(error)

            return self.fallback_provider.get_filings(
                tickers=tickers,
                filing_types=filing_types,
            )

    def health_check(self):
        return {
            "provider": self.provider_name,
            "status": "Experimental",
            "healthy": False,
            "fallback_used": self.fallback_used,
            "filing_types": self.FILING_TYPES,
            "supports_offline": False,
            "requires_api_key": False,
            "failure_message": self.last_error
            or "EDGAR provider is not active in offline mode.",
        }
