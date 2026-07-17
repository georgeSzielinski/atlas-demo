from datetime import datetime

from engines.case_study_engine import CaseStudyEngine
from engines.probability_engine import ProbabilityEngine
from engines.research_memory_engine import ResearchMemoryEngine
from engines.sec_engine import SecEngine
from market.provider_registry import ProviderRegistry


class InstitutionalReportEngine:
    REPORT_VERSION = "1.0"
    SECTION_ORDER = [
        "Executive Summary",
        "Recommendation",
        "Probability Distribution",
        "Confidence",
        "Knowledge",
        "Stability",
        "Executive Review",
        "Investment Committee",
        "Bull Case",
        "Bear Case",
        "Catalyst Timeline",
        "SEC Highlights",
        "Fundamental Analysis",
        "Technical Analysis",
        "Forecast Analysis",
        "News Summary",
        "Portfolio Impact",
        "Historical Analogs",
        "Case Studies",
        "Risk Assessment",
        "Expected Return",
        "Scenario Analysis",
        "Research Memory",
        "Appendix",
    ]

    def generate(self, ticker, source_data=None, generation_time=None):
        ticker = (ticker or "").upper()
        if source_data is None:
            from database.repository import get_discovery_source_data

            source_data = get_discovery_source_data()

        recommendation = self._recommendation(ticker, source_data)
        probability = self._probability_report(recommendation, source_data)
        memory = ResearchMemoryEngine().build(
            recommendation,
            source_data=source_data,
        )
        sec = SecEngine().analyze(tickers=[ticker] if ticker else None)
        case_studies = self._case_studies(recommendation, source_data)
        metadata = self._metadata(generation_time)
        sections = self._sections(
            ticker,
            recommendation,
            probability,
            memory,
            sec,
            case_studies,
        )
        charts = self._charts(recommendation, probability, memory)
        report = {
            "metadata": metadata,
            "ticker": ticker,
            "sections": sections,
            "charts": charts,
            "markdown": "",
            "pdf_placeholder": {
                "available": False,
                "format": "PDF",
                "message": "Future PDF renderer placeholder.",
            },
            "html_placeholder": {
                "available": False,
                "format": "HTML",
                "message": "Future HTML renderer placeholder.",
            },
            "policy": {
                "deterministic": True,
                "uses_llm": False,
                "changes_recommendation_behavior": False,
                "automatic_execution": False,
            },
        }
        report["markdown"] = self.to_markdown(report)

        return report

    def to_markdown(self, report):
        lines = [
            f"# Atlas Institutional Research Report: {report['ticker']}",
            "",
            f"Report Version: {report['metadata']['report_version']}",
            f"Generation Time: {report['metadata']['generation_time']}",
            "",
        ]

        for section in report["sections"]:
            lines.extend([
                f"## {section['title']}",
                "",
                section["summary"],
                "",
            ])
            data = section.get("data")
            if isinstance(data, dict):
                for key in sorted(data):
                    lines.append(f"- {key}: {data[key]}")
                lines.append("")
            elif isinstance(data, list):
                if data:
                    for item in data:
                        lines.append(f"- {item}")
                else:
                    lines.append("- None")
                lines.append("")

        lines.extend([
            "## Structured Data Placeholders",
            "",
        ])
        for chart in report["charts"]:
            lines.append(
                f"- {chart['name']}: {chart['type']} "
                f"({len(chart.get('data', []))} rows)"
            )

        lines.extend([
            "",
            "## Output Placeholders",
            "",
            f"- PDF: {report['pdf_placeholder']['message']}",
            f"- HTML: {report['html_placeholder']['message']}",
            "",
        ])

        return "\n".join(lines)

    def _sections(self, ticker, recommendation, probability, memory, sec, case_studies):
        section_data = {
            "Executive Summary": self._section(
                "Executive Summary",
                self._executive_summary(ticker, recommendation),
                {
                    "ticker": ticker,
                    "action": recommendation.get("action", "Unavailable"),
                    "confidence": recommendation.get("confidence", 0),
                    "sec_filings": sec["summary"]["filing_count"],
                },
            ),
            "Recommendation": self._section(
                "Recommendation",
                "Recommendation is reported from existing Atlas output.",
                {
                    "action": recommendation.get("action", "Unavailable"),
                    "rating": recommendation.get("rating", "Unavailable"),
                    "overall_score": recommendation.get("overall_score", 0),
                    "validation_status": recommendation.get(
                        "validation_status",
                        "Unavailable",
                    ),
                },
            ),
            "Probability Distribution": self._section(
                "Probability Distribution",
                "Probability values come from ProbabilityEngine or saved probability output.",
                probability.get("probabilities", {}),
            ),
            "Confidence": self._section(
                "Confidence",
                recommendation.get("confidence_explanation")
                or "Confidence is derived from saved Atlas recommendation fields.",
                {
                    "confidence": recommendation.get("confidence", 0),
                    "signal_quality_score": recommendation.get(
                        "signal_quality_score",
                        0,
                    ),
                    "signal_label": recommendation.get("signal_label", ""),
                },
            ),
            "Knowledge": self._section(
                "Knowledge",
                recommendation.get("knowledge_explanation")
                or "Knowledge score unavailable in saved recommendation.",
                {
                    "knowledge_score": recommendation.get("knowledge_score", 0),
                    "knowledge_level": recommendation.get("knowledge_level", ""),
                },
            ),
            "Stability": self._section(
                "Stability",
                recommendation.get("stability_explanation")
                or "Stability score unavailable in saved recommendation.",
                {
                    "stability_score": recommendation.get("stability_score", 0),
                    "stability_level": recommendation.get("stability_level", ""),
                    "most_sensitive_factor": recommendation.get(
                        "most_sensitive_factor",
                        "",
                    ),
                },
            ),
            "Executive Review": self._section(
                "Executive Review",
                recommendation.get("executive_summary")
                or "Executive review unavailable.",
                {
                    "status": recommendation.get("executive_status", ""),
                    "confidence": recommendation.get("executive_confidence", 0),
                    "warnings": recommendation.get("executive_warnings", []),
                },
            ),
            "Investment Committee": self._section(
                "Investment Committee",
                recommendation.get("final_committee_summary")
                or "Committee summary unavailable.",
                {
                    "agreement": recommendation.get("committee_agreement", 0),
                    "bullish_members": recommendation.get("bullish_members", []),
                    "bearish_members": recommendation.get("bearish_members", []),
                    "neutral_members": recommendation.get("neutral_members", []),
                },
            ),
            "Bull Case": self._section(
                "Bull Case",
                "Bull case comes from existing committee and fusion output.",
                recommendation.get("bull_case")
                or recommendation.get("committee_bull_case", []),
            ),
            "Bear Case": self._section(
                "Bear Case",
                "Bear case comes from existing committee and fusion output.",
                recommendation.get("bear_case")
                or recommendation.get("committee_bear_case", []),
            ),
            "Catalyst Timeline": self._section(
                "Catalyst Timeline",
                "Catalysts are existing Atlas catalyst records for this recommendation.",
                recommendation.get("catalysts", []),
            ),
            "SEC Highlights": self._section(
                "SEC Highlights",
                "SEC highlights come from SecEngine normalized filing output.",
                {
                    "filing_count": sec["summary"]["filing_count"],
                    "form_type_counts": sec["summary"]["form_type_counts"],
                    "section_coverage": sec["summary"]["section_coverage"],
                },
            ),
            "Fundamental Analysis": self._section(
                "Fundamental Analysis",
                "Fundamental analysis comes from saved Atlas scores.",
                {
                    "fundamental_score": recommendation.get("fundamental_score", 0),
                    "strongest_positive_factor": recommendation.get(
                        "strongest_positive_factor",
                        {},
                    ),
                },
            ),
            "Technical Analysis": self._section(
                "Technical Analysis",
                "Technical analysis comes from saved Atlas scores.",
                {
                    "technical_score": recommendation.get("technical_score", 0),
                    "score": recommendation.get("score", 0),
                },
            ),
            "Forecast Analysis": self._section(
                "Forecast Analysis",
                "Forecast analysis comes from saved Atlas forecast fields.",
                {
                    "forecast_score": recommendation.get("forecast_score", 0),
                    "forecast_direction": recommendation.get(
                        "forecast_direction",
                        "",
                    ),
                    "forecast_confidence": recommendation.get(
                        "forecast_confidence",
                        0,
                    ),
                    "expected_change": recommendation.get("expected_change", 0),
                },
            ),
            "News Summary": self._section(
                "News Summary",
                recommendation.get("news_summary") or "News summary unavailable.",
                {
                    "news_sentiment": recommendation.get("news_sentiment", ""),
                    "news_confidence": recommendation.get("news_confidence", 0),
                    "headline_count": recommendation.get("headline_count", 0),
                },
            ),
            "Portfolio Impact": self._section(
                "Portfolio Impact",
                "Portfolio impact comes from saved portfolio score and strategy context.",
                {
                    "portfolio_score": recommendation.get("portfolio_score", 0),
                    "overall_conviction": recommendation.get(
                        "overall_conviction",
                        0,
                    ),
                },
            ),
            "Historical Analogs": self._section(
                "Historical Analogs",
                "Historical analogs come from ResearchMemoryEngine.",
                memory["similar_historical_cases"],
            ),
            "Case Studies": self._section(
                "Case Studies",
                "Case studies come from existing validated Atlas cases.",
                case_studies,
            ),
            "Risk Assessment": self._section(
                "Risk Assessment",
                "Risk assessment comes from saved Atlas risk fields.",
                {
                    "risk_score": recommendation.get("risk_score", 0),
                    "risks": recommendation.get("risks", []),
                    "false_positive_warnings": recommendation.get(
                        "false_positive_warnings",
                        [],
                    ),
                },
            ),
            "Expected Return": self._section(
                "Expected Return",
                "Expected return comes from probability output and forecast fields.",
                probability.get("expected_outcome", {}),
            ),
            "Scenario Analysis": self._section(
                "Scenario Analysis",
                "Scenario analysis comes from hypothesis and counterfactual output.",
                {
                    "assumptions": recommendation.get("assumptions", []),
                    "counterfactuals": recommendation.get("counterfactuals", []),
                    "flip_conditions": recommendation.get(
                        "recommendation_flip_conditions",
                        [],
                    ),
                },
            ),
            "Research Memory": self._section(
                "Research Memory",
                memory["lessons"].get("explanation", ""),
                memory["lessons"],
            ),
            "Appendix": self._section(
                "Appendix",
                "Appendix contains source metadata and raw evidence references.",
                {
                    "evidence_breakdown": recommendation.get("evidence_breakdown", []),
                    "missing_evidence": recommendation.get("missing_evidence", []),
                    "sec_provider": sec["provider"],
                },
            ),
        }

        return [section_data[title] for title in self.SECTION_ORDER]

    def _charts(self, recommendation, probability, memory):
        return [
            {
                "name": "Probability Distribution",
                "type": "bar",
                "data": [
                    {"label": key, "value": value}
                    for key, value in probability.get("probabilities", {}).items()
                ],
            },
            {
                "name": "Evidence Breakdown",
                "type": "table",
                "data": recommendation.get("evidence_breakdown", []),
            },
            {
                "name": "Catalyst Timeline",
                "type": "timeline",
                "data": recommendation.get("catalysts", []),
            },
            {
                "name": "Historical Return Distribution",
                "type": "histogram",
                "data": [
                    {
                        "ticker": analog.get("ticker"),
                        "return": analog.get("return"),
                    }
                    for analog in memory.get("similar_historical_cases", [])
                ],
            },
            {
                "name": "Committee Agreement",
                "type": "gauge",
                "data": [
                    {
                        "label": "agreement",
                        "value": recommendation.get("committee_agreement", 0),
                    }
                ],
            },
        ]

    def _metadata(self, generation_time):
        registry = ProviderRegistry()

        return {
            "generation_time": generation_time or datetime.now().isoformat(),
            "report_version": self.REPORT_VERSION,
            "data_sources_used": [
                "RecommendationEngine output",
                "ProbabilityEngine",
                "ResearchMemoryEngine",
                "CaseStudyEngine",
                "SecEngine",
                "ProviderRegistry",
            ],
            "provider_health_snapshot": registry.health()["summary"],
            "active_providers": registry.active_providers(),
        }

    def _recommendation(self, ticker, source_data):
        recommendations = source_data.get("recommendations", [])
        found = next(
            (
                item for item in recommendations
                if item.get("ticker", "").upper() == ticker
            ),
            None,
        )

        return found or {
            "ticker": ticker,
            "action": "Unavailable",
            "confidence": 0,
            "evidence_breakdown": [],
            "catalysts": [],
            "risks": [],
        }

    def _probability_report(self, recommendation, source_data):
        report = recommendation.get("probability_report")
        if isinstance(report, dict) and report:
            return report

        return ProbabilityEngine().estimate(
            recommendation,
            history=source_data.get("recommendations", []),
            case_studies=source_data.get("case_studies", []),
        )

    def _case_studies(self, recommendation, source_data):
        cases = [
            case for case in source_data.get("case_studies", [])
            if case.get("ticker", "").upper()
            == recommendation.get("ticker", "").upper()
        ]
        built = CaseStudyEngine().build_case_study(recommendation)
        if built is not None:
            cases.append(built)

        return cases

    def _executive_summary(self, ticker, recommendation):
        action = recommendation.get("action", "Unavailable")
        confidence = recommendation.get("confidence", 0)

        return (
            f"{ticker} institutional report uses existing Atlas intelligence. "
            f"Current saved action is {action} with {confidence}% confidence."
        )

    def _section(self, title, summary, data):
        return {
            "title": title,
            "summary": summary,
            "data": data,
        }
