import os

from engines.edgar_provider import EdgarProvider
from engines.mock_sec_provider import MockSecProvider


class SecEngine:
    DEFAULT_PROVIDER = "mock"

    def __init__(self, provider_name=None, provider=None):
        self.provider_name = provider_name or os.environ.get(
            "SEC_PROVIDER",
            self.DEFAULT_PROVIDER,
        )
        self.provider = provider or self._provider(self.provider_name)

    def filings(self, tickers=None, filing_types=None):
        return self.provider.get_filings(
            tickers=tickers,
            filing_types=filing_types,
        )

    def analyze(self, tickers=None, filing_types=None):
        filings = self.filings(tickers=tickers, filing_types=filing_types)

        return {
            "provider": self.provider.provider_name,
            "filings": filings,
            "summary": self.summary(filings),
            "research_context": self.research_context(filings),
            "observatory": self.observatory_summary(filings),
            "knowledge_graph_context": self.knowledge_graph_context(filings),
            "health": self.health_check(),
            "policy": {
                "read_only": True,
                "mock_default": True,
                "requires_api_key": False,
                "changes_recommendation_behavior": False,
                "automatic_execution": False,
            },
        }

    def summary(self, filings=None):
        filings = filings if filings is not None else self.filings()
        form_counts = {}
        tickers = sorted({filing["ticker"] for filing in filings})
        sections = {}

        for filing in filings:
            form_type = filing["form_type"]
            form_counts[form_type] = form_counts.get(form_type, 0) + 1
            for section in filing.get("sections_available", []):
                sections[section] = sections.get(section, 0) + 1

        return {
            "filing_count": len(filings),
            "tickers": tickers,
            "form_type_counts": form_counts,
            "section_coverage": [
                {"section": section, "count": count}
                for section, count in sorted(sections.items())
            ],
            "supported_filing_types": MockSecProvider.FILING_TYPES,
            "summary_sections": MockSecProvider.SUMMARY_SECTIONS,
        }

    def research_context(self, filings=None):
        filings = filings if filings is not None else self.filings()

        return {
            "research_domain": "SEC Filings",
            "filing_count": len(filings),
            "available_forms": sorted({filing["form_type"] for filing in filings}),
            "research_uses": [
                "Business model review",
                "Risk factor comparison",
                "MD&A trend research",
                "Financial statement context",
                "Management guidance tracking",
                "Legal proceedings monitoring",
            ],
            "controlled_learning": {
                "requires_human_approval": True,
                "automatic_behavior_changes": False,
            },
        }

    def observatory_summary(self, filings=None):
        filings = filings if filings is not None else self.filings()
        health = self.health_check()

        return {
            "provider": health["provider"],
            "status": health["status"],
            "healthy": health["healthy"],
            "fallback_used": health["fallback_used"],
            "filing_count": len(filings),
            "offline_capable": health["supports_offline"],
            "requires_api_key": health["requires_api_key"],
            "policy": (
                "SEC intelligence is read-only and does not change "
                "recommendation behavior."
            ),
        }

    def knowledge_graph_context(self, filings=None):
        filings = filings if filings is not None else self.filings()

        return {
            "nodes": [
                {
                    "id": self._filing_id(filing),
                    "type": "SEC Filing",
                    "label": (
                        f"{filing['ticker']} {filing['form_type']} "
                        f"{filing['filing_date']}"
                    ),
                    "properties": filing,
                }
                for filing in filings
            ],
            "relationships": [
                {
                    "source": f"ticker:{filing['ticker']}",
                    "target": self._filing_id(filing),
                    "type": "filed",
                    "properties": {"form_type": filing["form_type"]},
                }
                for filing in filings
            ],
        }

    def health_check(self):
        return self.provider.health_check()

    def _provider(self, provider_name):
        if provider_name == "edgar":
            return EdgarProvider()

        return MockSecProvider()

    def _filing_id(self, filing):
        form = filing["form_type"].replace(" ", "-")
        return f"sec_filing:{filing['ticker']}:{form}:{filing['filing_date']}"
