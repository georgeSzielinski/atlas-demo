class SecProvider:
    provider_name = "base"
    fallback_used = False
    last_error = ""

    FILING_TYPES = ["10-K", "10-Q", "8-K", "DEF 14A", "S-1"]
    SUMMARY_SECTIONS = [
        "Business",
        "Risk Factors",
        "MD&A",
        "Financial Statements",
        "Management Guidance",
        "Legal Proceedings",
    ]

    def get_filings(self, tickers=None, filing_types=None):
        raise NotImplementedError

    def health_check(self):
        raise NotImplementedError

    def normalize_filing(self, filing):
        form_type = filing.get("form_type")
        if form_type not in self.FILING_TYPES:
            raise ValueError(f"Unsupported SEC filing type: {form_type}")

        summaries = filing.get("summaries", {})

        return {
            "filing_date": filing.get("filing_date", ""),
            "form_type": form_type,
            "company": filing.get("company", ""),
            "ticker": filing.get("ticker", ""),
            "sections_available": sorted(filing.get("sections_available", [])),
            "filing_url": filing.get("filing_url", ""),
            "summaries": {
                section: summaries.get(
                    section,
                    f"{section} summary unavailable.",
                )
                for section in self.SUMMARY_SECTIONS
            },
        }

    def normalize_filings(self, filings):
        return sorted(
            [self.normalize_filing(filing) for filing in filings],
            key=lambda item: (
                item["ticker"],
                item["filing_date"],
                item["form_type"],
            ),
        )
