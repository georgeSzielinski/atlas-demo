from engines.decision_engine import DecisionEngine
from engines.evidence_engine import EvidenceEngine
from engines.executive_review_engine import ExecutiveReviewEngine
from engines.explainability_engine import ExplainabilityEngine
from engines.forecast_engine import ForecastEngine
from engines.fundamental_engine import FundamentalEngine
from engines.hypothesis_engine import HypothesisEngine
from engines.intelligence_fusion_engine import IntelligenceFusionEngine
from engines.investment_committee_engine import InvestmentCommitteeEngine
from engines.investment_intelligence_engine import InvestmentIntelligenceEngine
from engines.news_engine import NewsEngine
from engines.probability_engine import ProbabilityEngine
from engines.research_memory_engine import ResearchMemoryEngine
from engines.signal_quality_engine import SignalQualityEngine
from market.fundamentals import get_fundamentals


class RecommendationEngine:

    def __init__(self):
        self.decision_engine = DecisionEngine()
        self.forecast_engine = ForecastEngine()
        self.fundamental_engine = FundamentalEngine()
        self.intelligence_engine = InvestmentIntelligenceEngine()
        self.news_engine = NewsEngine()
        self.explainability_engine = ExplainabilityEngine()
        self.signal_quality_engine = SignalQualityEngine()
        self.evidence_engine = EvidenceEngine()
        self.fusion_engine = IntelligenceFusionEngine()
        self.committee_engine = InvestmentCommitteeEngine()
        self.hypothesis_engine = HypothesisEngine()
        self.executive_review_engine = ExecutiveReviewEngine()
        self.probability_engine = ProbabilityEngine()
        self.research_memory_engine = ResearchMemoryEngine()

    PIPELINE_STAGES = [
        ("market_data", "Market Data"),
        ("fundamentals", "Fundamentals"),
        ("technicals", "Technicals"),
        ("forecast", "Forecast"),
        ("news", "News"),
        ("macro", "Macro"),
        ("sec", "SEC"),
        ("catalysts", "Catalysts"),
        ("knowledge_graph", "Knowledge Graph"),
        ("research_memory", "Research Memory"),
        ("committee", "Committee"),
        ("executive_review", "Executive Review"),
        ("probability", "Probability"),
        ("portfolio_construction", "Portfolio Construction"),
        ("final_recommendation", "Final Recommendation"),
    ]

    def explain(self, recommendation):
        """Read-only explainability view of an existing recommendation.

        Composes existing recommendation fields into a reasoning summary,
        confidence breakdown, engine contributions, decision tree, and decision
        flow for the Atlas Brain. It recomputes no scores and changes no
        recommendation behavior.
        """
        rec = recommendation or {}
        evidence = self._brain_evidence_items(rec)
        contributions = self._brain_engine_contributions(evidence)

        return {
            "reasoning_summary": self._brain_reasoning_summary(rec, contributions),
            "confidence_breakdown": self._brain_confidence_breakdown(rec, evidence),
            "engine_contributions": contributions,
            "decision_tree": self._brain_decision_tree(rec, evidence),
            "decision_flow": self._brain_decision_flow(rec, evidence),
            "policy": {
                "read_only": True,
                "changes_recommendation_behavior": False,
                "automatic_execution": False,
            },
        }

    def _brain_get(self, rec, key, default=None):
        if isinstance(rec, dict):
            return rec.get(key, default)

        return getattr(rec, key, default)

    def _brain_evidence_items(self, rec):
        items = []

        for item in self._brain_get(rec, "evidence_breakdown", []) or []:
            if not isinstance(item, dict):
                continue

            items.append({
                "category": item.get("category") or item.get("name") or "Unknown",
                "score": self._brain_number(item.get("score", 0)),
                "weight": self._brain_number(item.get("weight", 0)),
                "confidence": self._brain_number(item.get("confidence", 0)),
                "summary": item.get("summary", ""),
                "disabled": bool(item.get("disabled", False)),
            })

        return items

    def _brain_engine_contributions(self, evidence):
        active = [item for item in evidence if not item["disabled"]]
        raw = []

        for item in active:
            weight = item["weight"] if item["weight"] > 0 else 1
            raw.append((item, item["score"] * weight))

        total = sum(value for _, value in raw)
        contributions = []

        for item, value in raw:
            percent = round(value / total * 100, 2) if total else 0
            contributions.append({
                "engine": item["category"],
                "category": item["category"],
                "percent": percent,
                "score": item["score"],
                "weight": item["weight"],
                "confidence": item["confidence"],
                "summary": item["summary"],
            })

        return sorted(
            contributions,
            key=lambda entry: (entry["percent"], entry["category"]),
            reverse=True,
        )

    def _brain_reasoning_summary(self, rec, contributions):
        action = self._brain_get(rec, "action", "Unavailable")
        confidence = self._brain_number(self._brain_get(rec, "confidence", 0))
        positive = self._brain_get(rec, "top_positive_factors", []) or []
        negative = self._brain_get(rec, "top_negative_factors", []) or []
        committee = self._brain_get(rec, "final_committee_summary", "")
        executive = self._brain_get(rec, "executive_summary", "")
        top = [entry["engine"] for entry in contributions[:3]]

        narrative = (
            f"Atlas reached a {action} conclusion with {confidence}% confidence. "
            f"The strongest contributors were {', '.join(top) or 'no dominant engine'}."
        )
        if committee:
            narrative += f" Committee view: {committee}"

        return {
            "headline": f"{action} · {confidence}% confidence",
            "narrative": narrative.strip(),
            "why": positive[:5] or [
                entry["summary"] for entry in contributions[:3] if entry["summary"]
            ],
            "watch_outs": negative[:5],
            "executive_note": executive,
        }

    def _brain_confidence_breakdown(self, rec, evidence):
        scores = {item["category"]: item["score"] for item in evidence}
        raised = []
        reduced = []

        def score_of(*names):
            for name in names:
                if name in scores:
                    return scores[name]
            return None

        fundamentals = score_of("Fundamentals", "Fundamental")
        technical = score_of("Technical", "Technicals")
        forecast = score_of("Forecast")
        committee_agreement = self._brain_number(
            self._brain_get(rec, "committee_agreement", 0)
        )
        knowledge = self._brain_number(self._brain_get(rec, "knowledge_score", 0))
        stability = self._brain_number(self._brain_get(rec, "stability_score", 0))
        news_confidence = self._brain_number(
            self._brain_get(rec, "news_confidence", 0)
        )

        if fundamentals is not None and fundamentals >= 70:
            raised.append({"factor": "Strong fundamentals", "detail": f"Fundamentals score {fundamentals}."})
        if technical is not None and technical >= 70:
            raised.append({"factor": "Constructive technicals", "detail": f"Technical score {technical}."})
        if forecast is not None and forecast >= 70:
            raised.append({"factor": "Supportive forecast", "detail": f"Forecast score {forecast}."})
        if committee_agreement >= 70:
            raised.append({"factor": "Committee agreement", "detail": f"Committee agreement {committee_agreement}%."})
        if knowledge >= 70:
            raised.append({"factor": "High knowledge score", "detail": f"Knowledge score {knowledge}."})
        if stability >= 70:
            raised.append({"factor": "Stable analogs", "detail": f"Stability score {stability}."})

        if news_confidence and news_confidence < 50:
            reduced.append({"factor": "Weak news agreement", "detail": f"News confidence {news_confidence}."})
        if fundamentals is not None and fundamentals < 50:
            reduced.append({"factor": "Soft fundamentals", "detail": f"Fundamentals score {fundamentals}."})

        macro = score_of("Macro")
        if macro is not None and macro < 55:
            reduced.append({"factor": "Macro uncertainty", "detail": f"Macro score {macro}."})

        if self._brain_upcoming_earnings(rec):
            reduced.append({"factor": "Upcoming earnings", "detail": "An earnings catalyst is near."})

        uncertainty = self._brain_get(
            self._brain_get(rec, "probability_report", {}) or {},
            "confidence_quality",
            {},
        )
        if isinstance(uncertainty, dict) and uncertainty.get("uncertainty_level") in {"High", "Very High"}:
            reduced.append({
                "factor": "High outcome uncertainty",
                "detail": f"Uncertainty level {uncertainty.get('uncertainty_level')}.",
            })

        executive_status = self._brain_get(rec, "executive_status", "")
        if executive_status in {"NEEDS_REVIEW", "INSUFFICIENT_DATA"}:
            reduced.append({"factor": "Executive review caution", "detail": f"Executive status {executive_status}."})

        return {
            "confidence": self._brain_number(self._brain_get(rec, "confidence", 0)),
            "raised": raised or [{"factor": "No dominant positive driver", "detail": "Evidence is balanced."}],
            "reduced": reduced or [{"factor": "No dominant negative driver", "detail": "No major confidence drag detected."}],
        }

    def _brain_decision_tree(self, rec, evidence):
        signal = self._brain_number(self._brain_get(rec, "signal_quality_score", 0))
        strong_evidence = len([item for item in evidence if item["score"] >= 70])
        committee_agreement = self._brain_number(
            self._brain_get(rec, "committee_agreement", 0)
        )
        executive_status = self._brain_get(rec, "executive_status", "")
        outperformance = self._brain_number(
            self._brain_get(
                self._brain_get(
                    self._brain_get(rec, "probability_report", {}) or {},
                    "probabilities",
                    {},
                ),
                "outperformance",
                0,
            )
        )
        action = self._brain_get(rec, "action", "Unavailable")

        branches = [
            self._brain_branch(
                "Signal quality gate",
                "Signal quality score is not weak",
                signal >= 5 or signal == 0,
                f"Signal quality score is {signal}.",
            ),
            self._brain_branch(
                "Evidence strength",
                "At least three strong evidence categories",
                strong_evidence >= 3,
                f"{strong_evidence} evidence categories scored 70 or higher.",
            ),
            self._brain_branch(
                "Committee agreement",
                "Committee agreement is sufficient",
                committee_agreement >= 60,
                f"Committee agreement is {committee_agreement}%.",
            ),
            self._brain_branch(
                "Executive readiness",
                "Executive review is ready or cautious",
                executive_status in {"READY", "CAUTION"},
                f"Executive status is {executive_status or 'Unavailable'}.",
            ),
            self._brain_branch(
                "Probability check",
                "Outperformance probability is favorable",
                outperformance >= 50,
                f"Outperformance probability is {outperformance}%.",
            ),
        ]

        return {
            "branches": branches,
            "final_outcome": action,
            "why": (
                f"Final action is {action} after passing "
                f"{len([b for b in branches if b['passed']])} of {len(branches)} checks."
            ),
        }

    def _brain_decision_flow(self, rec, evidence):
        scores = {item["category"]: item["score"] for item in evidence}

        def score_of(*names, default=0):
            for name in names:
                if name in scores:
                    return scores[name]
            return default

        catalysts = self._brain_get(rec, "catalysts", []) or []
        analogs = self._brain_get(
            self._brain_get(rec, "probability_report", {}) or {},
            "similar_historical_cases",
            [],
        )
        stage_values = {
            "market_data": 100,
            "fundamentals": self._brain_number(self._brain_get(rec, "fundamental_score", score_of("Fundamentals", "Fundamental"))),
            "technicals": self._brain_number(self._brain_get(rec, "technical_score", score_of("Technical", "Technicals"))),
            "forecast": self._brain_number(self._brain_get(rec, "forecast_score", score_of("Forecast"))),
            "news": self._brain_number(self._brain_get(rec, "news_confidence", score_of("News"))),
            "macro": score_of("Macro", default=55),
            "sec": score_of("SEC", default=50),
            "catalysts": min(100, len(catalysts) * 25),
            "knowledge_graph": self._brain_number(self._brain_get(rec, "knowledge_score", 0)),
            "research_memory": min(100, len(analogs) * 20),
            "committee": self._brain_number(self._brain_get(rec, "committee_agreement", 0)),
            "executive_review": self._brain_number(self._brain_get(rec, "executive_confidence", 0)),
            "probability": self._brain_number(
                self._brain_get(
                    self._brain_get(
                        self._brain_get(rec, "probability_report", {}) or {},
                        "probabilities",
                        {},
                    ),
                    "outperformance",
                    0,
                )
            ),
            "portfolio_construction": self._brain_number(self._brain_get(rec, "portfolio_score", 0)),
            "final_recommendation": self._brain_number(self._brain_get(rec, "confidence", 0)),
        }
        summaries = {
            "market_data": "Validated market data ingested via the Market Data Manager.",
            "fundamentals": "Fundamental analysis scored from financial statement signals.",
            "technicals": "Technical indicators evaluated (trend, RSI, MACD).",
            "forecast": "Deterministic forecast direction and confidence.",
            "news": "News sentiment and headline agreement.",
            "macro": "Macro regime and risk context.",
            "sec": "SEC filing intelligence highlights.",
            "catalysts": "Upcoming catalysts and event timing.",
            "knowledge_graph": "Knowledge score across evidence and providers.",
            "research_memory": "Similar historical cases retrieved.",
            "committee": "Investment committee agreement and debate.",
            "executive_review": "Executive readiness review.",
            "probability": "Probability of outperformance from analogs.",
            "portfolio_construction": "Paper portfolio allocation and risk context.",
            "final_recommendation": "Final deterministic recommendation.",
        }

        flow = []
        for key, label in self.PIPELINE_STAGES:
            score = stage_values.get(key, 0)
            flow.append({
                "id": key,
                "label": label,
                "score": score,
                "status": self._brain_stage_status(score),
                "summary": summaries.get(key, ""),
                "detail": self._brain_stage_detail(key, rec, score),
            })

        return flow

    def _brain_stage_status(self, score):
        if score >= 70:
            return "strong"
        if score >= 45:
            return "moderate"
        if score > 0:
            return "weak"
        return "missing"

    def _brain_stage_detail(self, key, rec, score):
        if key == "final_recommendation":
            return f"{self._brain_get(rec, 'action', 'Unavailable')} at {score}% confidence."

        if key == "committee":
            return self._brain_get(rec, "final_committee_summary", "") or f"Agreement {score}%."

        if key == "executive_review":
            return self._brain_get(rec, "executive_summary", "") or f"Executive confidence {score}."

        return f"Score {score}."

    def _brain_branch(self, name, condition, passed, why):
        return {
            "branch": name,
            "condition": condition,
            "passed": bool(passed),
            "outcome": "pass" if passed else "caution",
            "why": why,
        }

    def _brain_upcoming_earnings(self, rec):
        for catalyst in self._brain_get(rec, "catalysts", []) or []:
            if not isinstance(catalyst, dict):
                continue
            event_type = str(catalyst.get("event_type", "")).lower()
            days = catalyst.get("days_until_event")
            if "earnings" in event_type and days is not None and 0 <= days <= 14:
                return True

        return False

    def _brain_number(self, value):
        try:
            return round(float(value), 2)
        except (TypeError, ValueError):
            return 0

    def build_recommendations(self, stocks, experiment_toggles=None):

        recommendations = []

        for stock in stocks:

            recommendation = self.decision_engine.decide(stock)
            technical_score = stock.score * 20
            fundamentals = get_fundamentals(stock.ticker)
            fundamental_analysis = self.fundamental_engine.analyze(
                fundamentals
            )
            fundamental_score = fundamental_analysis["score"]
            portfolio_score = 60
            risk_score = 70
            forecast = self.forecast_engine.forecast(stock)
            forecast_score = forecast["forecast_score"]
            news = self.news_engine.analyze(stock.ticker)
            signal_quality = self.signal_quality_engine.evaluate(
                technical_score=technical_score,
                fundamental_score=fundamental_score,
                forecast_score=forecast_score,
                news_confidence=news["confidence"],
                risk_score=risk_score,
                volatility=getattr(stock, "volatility", 0)
            )

            intelligence = self.intelligence_engine.evaluate(
                technical_score=technical_score,
                fundamental_score=fundamental_score,
                portfolio_health_score=portfolio_score,
                risk_score=risk_score,
                forecast_score=forecast_score
            )

            recommendation.technical_score = technical_score
            recommendation.fundamental_score = fundamental_score
            recommendation.portfolio_score = portfolio_score
            recommendation.risk_score = risk_score
            recommendation.forecast_score = forecast_score
            recommendation.forecast_direction = forecast["direction"]
            recommendation.forecast_confidence = forecast["confidence"]
            recommendation.expected_change = forecast["expected_change"]
            recommendation.overall_score = intelligence["overall_score"]
            recommendation.rating = intelligence["rating"]
            recommendation.news_sentiment = news["sentiment"]
            recommendation.news_confidence = news["confidence"]
            recommendation.headline_count = news["headline_count"]
            recommendation.news_summary = news["summary"]
            recommendation.signal_quality_score = (
                signal_quality["signal_quality_score"]
            )
            recommendation.signal_label = signal_quality["signal_label"]
            recommendation.false_positive_warnings = (
                signal_quality["false_positive_warnings"]
            )

            if recommendation.signal_quality_score < 5:
                recommendation.action = "AVOID"
            elif (
                recommendation.signal_quality_score < 7
                and recommendation.action == "BUY"
            ):
                recommendation.action = "HOLD"

            recommendation.explanation = self.explainability_engine.generate(
                recommendation
            )
            recommendation.evidence_breakdown = self.evidence_engine.build(
                recommendation
            )
            recommendation.fusion = self.fusion_engine.fuse(
                technical=technical_score,
                fundamentals=fundamental_score,
                forecast=forecast_score,
                news=news,
                portfolio=portfolio_score,
                risk=risk_score,
                evidence=recommendation.evidence_breakdown,
                confidence=recommendation.confidence_metadata,
            )
            recommendation.overall_conviction = (
                recommendation.fusion["overall_conviction"]
            )
            recommendation.fusion_summary = (
                recommendation.fusion["fusion_summary"]
            )
            recommendation.investment_committee = (
                self.committee_engine.evaluate(
                    evidence=recommendation.evidence_breakdown,
                    fusion=recommendation.fusion,
                )
            )
            self._attach_committee_context(recommendation)
            self._attach_research_context(recommendation)
            self._attach_hypothesis_context(recommendation)
            self._attach_executive_review(recommendation)
            self._attach_stability_and_knowledge(recommendation)
            recommendation.probability_report = (
                self.probability_engine.estimate(recommendation)
            )
            self._attach_research_memory(recommendation)
            self._attach_experiment_toggle_context(
                recommendation,
                experiment_toggles,
            )

            recommendations.append(recommendation)

        recommendations.sort(
            key=lambda recommendation: recommendation.confidence,
            reverse=True
        )

        return recommendations

    def _attach_committee_context(self, recommendation):
        committee = recommendation.investment_committee

        recommendation.committee_members = committee.get("members", [])
        recommendation.committee_bull_case = committee.get("bull_case", [])
        recommendation.committee_bear_case = committee.get("bear_case", [])
        recommendation.committee_neutral_case = committee.get(
            "neutral_case",
            [],
        )
        recommendation.committee_agreement = committee.get(
            "committee_agreement",
            0,
        )
        recommendation.bullish_members = committee.get("bullish_members", [])
        recommendation.bearish_members = committee.get("bearish_members", [])
        recommendation.neutral_members = committee.get("neutral_members", [])
        recommendation.strongest_bull_argument = committee.get(
            "strongest_bull_argument",
            "",
        )
        recommendation.strongest_bear_argument = committee.get(
            "strongest_bear_argument",
            "",
        )
        recommendation.main_disagreement = committee.get(
            "main_disagreement",
            "",
        )
        recommendation.final_committee_summary = committee.get(
            "final_committee_summary",
            "",
        )

    def _attach_research_context(self, recommendation):
        positive = [
            item for item in recommendation.evidence_breakdown
            if item["score"] >= 70
        ]
        negative = [
            item for item in recommendation.evidence_breakdown
            if item["score"] < 50
        ]
        missing = recommendation.fusion.get("missing_inputs", [])

        recommendation.top_positive_factors = [
            item["summary"] for item in sorted(
                positive,
                key=lambda item: item["score"],
                reverse=True,
            )[:5]
        ]
        recommendation.top_negative_factors = [
            item["summary"] for item in sorted(
                negative,
                key=lambda item: item["score"],
            )[:5]
        ]
        recommendation.missing_evidence = missing
        recommendation.suggested_follow_up_research = (
            self._follow_up_research(recommendation)
        )
        recommendation.confidence_explanation = (
            self._confidence_explanation(recommendation)
        )
        recommendation.evidence_summary = self._evidence_summary(
            recommendation
        )

    def _attach_hypothesis_context(self, recommendation):
        hypothesis = self.hypothesis_engine.generate(recommendation)
        recommendation.assumptions = (
            hypothesis["key_assumptions"]
            + hypothesis["supporting_assumptions"]
            + hypothesis["weakest_assumptions"]
        )
        recommendation.strongest_assumption = (
            hypothesis["strongest_assumption"]
        )
        recommendation.weakest_assumption = hypothesis["weakest_assumption"]
        recommendation.counterfactuals = hypothesis["counterfactuals"]
        recommendation.recommendation_flip_conditions = (
            hypothesis["recommendation_flip_conditions"]
        )
        recommendation.confidence_drivers = hypothesis["confidence_drivers"]

    def _attach_executive_review(self, recommendation):
        review = self.executive_review_engine.review(recommendation)
        recommendation.executive_review = review
        recommendation.executive_status = review["executive_status"]
        recommendation.executive_confidence = review["executive_confidence"]
        recommendation.executive_summary = review["executive_summary"]
        recommendation.executive_warnings = review["executive_warnings"]
        recommendation.executive_strengths = review["executive_strengths"]
        recommendation.executive_weaknesses = review["executive_weaknesses"]
        recommendation.required_follow_up_research = (
            review["required_follow_up_research"]
        )

    def _attach_research_memory(self, recommendation):
        try:
            recommendation.research_memory_report = (
                self.research_memory_engine.build(recommendation)
            )
        except Exception as error:
            recommendation.research_memory_report = {
                "similar_historical_cases": [],
                "lessons": {
                    "similar_historical_cases": [],
                    "average_historical_return": 0,
                    "average_holding_period": 0,
                    "win_rate": 0,
                    "common_successful_patterns": [],
                    "common_failure_patterns": [],
                    "most_useful_evidence": [],
                    "frequent_catalyst_behavior": [],
                    "explanation": "Research memory unavailable for this run.",
                },
                "policy": {
                    "read_only": True,
                    "changes_recommendation_behavior": False,
                    "automatic_execution": False,
                    "error": str(error),
                },
            }

    def _attach_experiment_toggle_context(self, recommendation, toggles):
        if toggles is None:
            return

        evidence_categories = {
            "use_technical": "Technical",
            "use_fundamentals": "Fundamental",
            "use_forecast": "Forecast",
            "use_news": "News",
            "use_portfolio": "Portfolio",
            "use_risk": "Risk",
            "use_committee": "Committee",
            "use_executive_review": "Executive",
            "use_hypothesis": "Hypothesis",
            "use_discovery": "Discovery",
        }
        disabled = [
            category for toggle, category in evidence_categories.items()
            if toggles.get(toggle) is False
        ]

        recommendation.disabled_subsystems = disabled

        for category in disabled:
            recommendation.evidence_breakdown.append({
                "category": category,
                "name": category,
                "score": 0,
                "confidence": 0,
                "weight": 0,
                "enabled": False,
                "disabled": True,
                "summary": (
                    f"{category} disabled by research experiment toggle."
                ),
            })

    def _attach_stability_and_knowledge(self, recommendation):
        stability = self._stability_review(recommendation)
        knowledge = self._knowledge_review(recommendation)

        recommendation.stability_score = stability["score"]
        recommendation.stability_level = stability["level"]
        recommendation.most_sensitive_factor = stability["factor"]
        recommendation.stability_explanation = stability["explanation"]
        recommendation.knowledge_score = knowledge["score"]
        recommendation.knowledge_level = knowledge["level"]
        recommendation.knowledge_explanation = knowledge["explanation"]

    def _stability_review(self, recommendation):
        confidence = self._bounded(recommendation.confidence)
        threshold_distance = min(abs(confidence - 55), abs(confidence - 80))
        threshold_fragility = max(0, 22 - threshold_distance * 2)
        factor_penalties = {
            "technical score": self._weakness_penalty(
                recommendation.technical_score,
                0.22,
            ),
            "fundamental score": self._weakness_penalty(
                recommendation.fundamental_score,
                0.18,
            ),
            "forecast confidence": self._weakness_penalty(
                recommendation.forecast_confidence,
                0.14,
            ),
            "news confidence": self._weakness_penalty(
                recommendation.news_confidence,
                0.10,
            ),
            "risk score": self._weakness_penalty(
                recommendation.risk_score,
                0.14,
            ),
            "committee agreement": self._weakness_penalty(
                recommendation.committee_agreement,
                0.10,
            ),
            "executive confidence": self._weakness_penalty(
                recommendation.executive_confidence,
                0.09,
            ),
        }
        most_sensitive_factor = max(
            factor_penalties,
            key=factor_penalties.get,
        )
        factor_fragility = sum(factor_penalties.values())

        if threshold_fragility > factor_penalties[most_sensitive_factor]:
            most_sensitive_factor = "confidence threshold"

        score = self._bounded(round(100 - threshold_fragility - factor_fragility))
        level = self._stability_level(score)

        return {
            "score": score,
            "level": level,
            "factor": most_sensitive_factor,
            "explanation": (
                f"{level}: confidence is {threshold_distance} points from "
                f"the nearest review threshold; the most sensitive factor is "
                f"{most_sensitive_factor}."
            ),
        }

    def _knowledge_review(self, recommendation):
        evidence_rows = [
            item for item in recommendation.evidence_breakdown
            if isinstance(item, dict)
        ]
        missing_evidence = list(recommendation.missing_evidence or [])
        providers = [
            recommendation.technical_score > 0,
            recommendation.fundamental_score > 0,
            recommendation.forecast_confidence > 0,
            recommendation.news_confidence > 0,
            recommendation.portfolio_score > 0,
            recommendation.risk_score > 0,
        ]
        validation_depth = 15 if (
            recommendation.validation_status
            and recommendation.validation_status != "Pending"
        ) else 0
        benchmark_depth = 10 if any(
            "benchmark" in str(item.get("category", "")).lower()
            or "benchmark" in str(item.get("name", "")).lower()
            for item in evidence_rows
        ) else 0
        historical_depth = min(
            15,
            len(getattr(
                recommendation,
                "similar_historical_recommendations",
                [],
            )) * 5,
        )
        discovery_support = 10 if getattr(
            recommendation,
            "discovery_support",
            [],
        ) else 0
        executive_depth = {
            "READY": 10,
            "CAUTION": 8,
            "NEEDS_REVIEW": 4,
            "INSUFFICIENT_DATA": 0,
        }.get(recommendation.executive_status, 0)

        score = (
            min(30, len(evidence_rows) * 5)
            + validation_depth
            + benchmark_depth
            + historical_depth
            + min(20, sum(1 for provider in providers if provider) * 4)
            + executive_depth
            + discovery_support
            - min(25, len(missing_evidence) * 5)
        )
        score = self._bounded(round(score))
        level = self._knowledge_level(score)

        return {
            "score": score,
            "level": level,
            "explanation": (
                f"{level}: {len(evidence_rows)} evidence items, "
                f"{sum(1 for provider in providers if provider)} provider "
                f"signals, {len(missing_evidence)} missing inputs, and "
                f"executive status {recommendation.executive_status or 'None'}."
            ),
        }

    def _weakness_penalty(self, value, weight):
        return max(0, 70 - self._bounded(value)) * weight

    def _bounded(self, value):
        try:
            number = float(value)
        except (TypeError, ValueError):
            number = 0

        return max(0, min(100, number))

    def _stability_level(self, score):
        if score >= 85:
            return "Very Stable"
        if score >= 70:
            return "Stable"
        if score >= 55:
            return "Moderate"
        if score >= 40:
            return "Fragile"
        return "Highly Fragile"

    def _knowledge_level(self, score):
        if score >= 85:
            return "Deep Knowledge"
        if score >= 70:
            return "Good Knowledge"
        if score >= 50:
            return "Limited Knowledge"
        if score >= 30:
            return "Low Knowledge"
        return "Insufficient Knowledge"

    def _follow_up_research(self, recommendation):
        follow_up = []

        if recommendation.news_confidence < 25:
            follow_up.append("Review recent news and catalysts.")

        if recommendation.fundamental_score < 50:
            follow_up.append("Review fundamentals and upcoming filings.")

        if recommendation.forecast_score < 50:
            follow_up.append("Compare forecast output against alternatives.")

        if recommendation.risk_score < 50:
            follow_up.append("Review risk exposure before acting.")

        if recommendation.missing_evidence:
            follow_up.append("Collect missing evidence inputs.")

        if not follow_up:
            follow_up.append("Monitor validation and benchmark outcomes.")

        return follow_up[:5]

    def _confidence_explanation(self, recommendation):
        high = [
            item for item in recommendation.confidence_metadata
            if item.get("confidence", 0) >= 75
        ]
        low = [
            item for item in recommendation.confidence_metadata
            if item.get("confidence", 0) < 50
        ]

        return (
            f"{len(high)} high-confidence evidence items and "
            f"{len(low)} low-confidence evidence items support "
            f"a recommendation confidence of {recommendation.confidence}%."
        )

    def _evidence_summary(self, recommendation):
        return (
            f"{len(recommendation.top_positive_factors)} positive factors, "
            f"{len(recommendation.top_negative_factors)} negative factors, "
            f"and {len(recommendation.missing_evidence)} missing inputs."
        )
