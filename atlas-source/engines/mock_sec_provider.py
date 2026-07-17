from core.settings import APPROVED_TICKERS
from engines.sec_provider import SecProvider


class MockSecProvider(SecProvider):
    provider_name = "mock"

    COMPANIES = {
        "AAPL": "Apple Inc.",
        "MSFT": "Microsoft Corporation",
        "NVDA": "NVIDIA Corporation",
        "AMZN": "Amazon.com, Inc.",
        "GOOGL": "Alphabet Inc.",
        "COST": "Costco Wholesale Corporation",
    }

    def __init__(self):
        self.supported_tickers = list(APPROVED_TICKERS)
        self.fallback_used = False
        self.last_error = ""

    def get_filings(self, tickers=None, filing_types=None):
        tickers = tickers or self.supported_tickers[:3]
        filing_types = filing_types or self.FILING_TYPES
        self._validate(tickers, filing_types)
        filings = []

        for ticker in sorted(tickers):
            for index, form_type in enumerate(self.FILING_TYPES, start=1):
                if form_type not in filing_types:
                    continue

                filings.append(self.normalize_filing({
                    "filing_date": f"2024-0{index}-15",
                    "form_type": form_type,
                    "company": self.COMPANIES.get(ticker, f"{ticker} Corporation"),
                    "ticker": ticker,
                    "sections_available": self._sections(form_type),
                    "filing_url": (
                        "https://www.sec.gov/Archives/mock/"
                        f"{ticker}/{form_type.replace(' ', '-')}.html"
                    ),
                    "summaries": self._summaries(ticker, form_type),
                }))

        return filings

    def health_check(self):
        return {
            "provider": self.provider_name,
            "status": "Mock",
            "healthy": True,
            "fallback_used": self.fallback_used,
            "filing_types": self.FILING_TYPES,
            "supports_offline": True,
            "requires_api_key": False,
            "failure_message": self.last_error,
        }

    def _validate(self, tickers, filing_types):
        unsupported_tickers = [
            ticker for ticker in tickers
            if ticker not in self.supported_tickers
        ]
        if unsupported_tickers:
            raise ValueError(
                "Unsupported SEC ticker(s): "
                f"{', '.join(sorted(unsupported_tickers))}."
            )

        unsupported_forms = [
            form_type for form_type in filing_types
            if form_type not in self.FILING_TYPES
        ]
        if unsupported_forms:
            raise ValueError(
                "Unsupported SEC filing type(s): "
                f"{', '.join(sorted(unsupported_forms))}."
            )

    def _sections(self, form_type):
        if form_type == "8-K":
            return ["Management Guidance", "Legal Proceedings"]

        if form_type == "DEF 14A":
            return ["Business", "Legal Proceedings"]

        return list(self.SUMMARY_SECTIONS)

    def _summaries(self, ticker, form_type):
        return {
            section: (
                f"Mock {form_type} {section} summary for {ticker}. "
                "Deterministic SEC intelligence placeholder."
            )
            for section in self.SUMMARY_SECTIONS
        }
