class ProbabilityEngine:
    OUTPERFORMANCE_THRESHOLD = 1
    UNDERPERFORMANCE_THRESHOLD = -1

    def explain(self, report=None, recommendation=None, history=None, case_studies=None):
        """Read-only explainability view of an existing probability report.

        Reuses saved probability output (or a deterministic estimate when none
        is provided). It does not change probabilities or recommendation
        behavior; it only reformats existing values for the Atlas Brain.
        """
        if not isinstance(report, dict) or not report:
            if recommendation is not None:
                report = self.estimate(
                    recommendation,
                    history=history,
                    case_studies=case_studies,
                )
            else:
                report = {}

        probabilities = report.get("probabilities", {}) or {}
        expected = report.get("expected_outcome", {}) or {}
        quality = report.get("confidence_quality", {}) or {}
        most_likely = (
            max(probabilities, key=probabilities.get)
            if probabilities
            else "unavailable"
        )

        return {
            "probabilities": probabilities,
            "expected_outcome": expected,
            "outperformance_probability": probabilities.get("outperformance", 0),
            "most_likely_outcome": most_likely,
            "uncertainty_level": quality.get("uncertainty_level", "Unknown"),
            "sample_size": quality.get(
                "sample_size",
                expected.get("sample_size", 0),
            ),
            "explanation": report.get(
                "explanation",
                "Probability explanation is unavailable for this ticker.",
            ),
            "similar_historical_cases": report.get(
                "similar_historical_cases",
                [],
            ),
            "calibration_note": (
                "Probabilities are deterministic estimates from historical "
                "analogs. They are measurement only and do not change "
                "recommendation behavior or execute trades."
            ),
            "policy": report.get(
                "policy",
                {
                    "changes_recommendation_behavior": False,
                    "automatic_execution": False,
                    "requires_human_approval": True,
                },
            ),
        }

    def estimate(self, recommendation, history=None, case_studies=None):
        history = history or []
        case_studies = case_studies or []
        target = self._record(recommendation)
        samples = self._validated_samples(history, case_studies)
        similar = self.similar_historical_cases(target, samples)

        if not similar and samples:
            similar = [
                dict(sample) | {"similarity_score": 0}
                for sample in samples
            ]

        outcomes = self._outcome_probabilities(similar)
        expected = self._expected_outcome(similar)
        quality = self._confidence_quality(similar)
        report = {
            "ticker": target.get("ticker", ""),
            "recommendation": target.get("action") or target.get("recommendation", ""),
            "probabilities": outcomes,
            "expected_outcome": expected,
            "confidence_quality": quality,
            "research_memory": self._research_memory_report(
                target,
                history,
                case_studies,
            ),
            "explanation": self._explanation(outcomes, expected, quality),
            "similar_historical_cases": quality["similar_historical_cases"],
            "policy": {
                "changes_recommendation_behavior": False,
                "automatic_execution": False,
                "requires_human_approval": True,
            },
        }

        return report

    def _research_memory_report(self, target, history, case_studies):
        from engines.research_memory_engine import ResearchMemoryEngine

        source_data = {
            "recommendations": history,
            "case_studies": case_studies,
            "benchmark_results": [],
            "provider_results": [],
            "research_experiments": [],
        }

        return ResearchMemoryEngine().build(
            target,
            source_data=source_data,
            limit=5,
        )

    def estimate_many(self, recommendations, history=None, case_studies=None):
        history = history or recommendations

        return [
            self.estimate(
                recommendation,
                history=history,
                case_studies=case_studies,
            )
            for recommendation in recommendations
        ]

    def allocation_probability_adjustment(self, probability_report):
        probabilities = probability_report.get("probabilities", {})
        outperform = probabilities.get("outperformance", 34)
        underperform = probabilities.get("underperformance", 33)

        return {
            "allocation_probability_score": max(0, outperform - underperform + 50),
            "policy": {
                "changes_recommendation_behavior": False,
                "automatic_execution": False,
                "paper_only": True,
            },
        }

    def similar_historical_cases(self, target, samples, limit=10):
        rows = []

        for sample in samples:
            if sample.get("id") == target.get("id") and target.get("id") is not None:
                continue

            score = self._similarity_score(target, sample)
            if score <= 0:
                continue

            rows.append(dict(sample) | {"similarity_score": score})

        return sorted(
            rows,
            key=lambda item: (
                item["similarity_score"],
                item.get("validation_result", {}).get("percentage_return", 0),
                item.get("ticker", ""),
            ),
            reverse=True,
        )[:limit]

    def calibration_report(self, recommendations):
        rows = [
            item for item in recommendations
            if isinstance(item.get("probability_report"), dict)
            and isinstance(item.get("validation_result"), dict)
        ]
        if not rows:
            return {
                "sample_size": 0,
                "probability_calibration": 0,
                "expected_vs_actual_return": 0,
                "expected_vs_actual_holding_period": 0,
                "probability_accuracy": 0,
                "uncertainty_distribution": {},
            }

        probability_errors = []
        return_errors = []
        holding_errors = []
        accurate = 0
        uncertainty = {}

        for row in rows:
            report = row["probability_report"]
            validation = row["validation_result"]
            actual_category = self._outcome_category(
                validation.get("percentage_return", 0),
            )
            predicted_category = self._predicted_category(report)
            actual_probability = report["probabilities"].get(actual_category, 0)
            probability_errors.append(abs(100 - actual_probability))
            return_errors.append(
                abs(
                    report["expected_outcome"].get("expected_return", 0)
                    - validation.get("percentage_return", 0)
                )
            )
            holding_errors.append(
                abs(
                    report["expected_outcome"].get("expected_holding_period", 0)
                    - validation.get("holding_period", 0)
                )
            )
            if predicted_category == actual_category:
                accurate += 1

            level = report["confidence_quality"].get(
                "uncertainty_level",
                "Unknown",
            )
            uncertainty[level] = uncertainty.get(level, 0) + 1

        return {
            "sample_size": len(rows),
            "probability_calibration": round(
                max(0, 100 - self._average(probability_errors)),
                2,
            ),
            "expected_vs_actual_return": round(self._average(return_errors), 2),
            "expected_vs_actual_holding_period": round(
                self._average(holding_errors),
                2,
            ),
            "probability_accuracy": self._rate(accurate, len(rows)),
            "uncertainty_distribution": uncertainty,
        }

    def _validated_samples(self, history, case_studies):
        samples = []

        for item in history:
            record = self._record(item)
            validation = record.get("validation_result")
            if not isinstance(validation, dict):
                continue

            if validation.get("percentage_return") is None:
                continue

            samples.append(record)

        for case in case_studies:
            validation = case.get("validation", {})
            samples.append({
                "id": case.get("case_id"),
                "ticker": case.get("ticker"),
                "action": case.get("recommendation"),
                "market_regime": case.get("market_regime"),
                "evidence_breakdown": case.get("evidence", []),
                "committee_agreement": case.get("committee", {}).get(
                    "agreement",
                    0,
                ),
                "executive_status": case.get("executive_review", {}).get(
                    "status",
                    "",
                ),
                "knowledge_score": case.get("knowledge_score", 0),
                "stability_score": case.get("stability_score", 0),
                "catalysts": case.get("catalysts", []),
                "validation_result": {
                    "success": case.get("outcome") == "Win",
                    "percentage_return": case.get("return", 0),
                    "holding_period": case.get(
                        "holding_period",
                        validation.get("holding_period", 0),
                    ),
                },
            })

        return samples

    def _outcome_probabilities(self, samples):
        counts = {
            "outperformance": 0,
            "market_performance": 0,
            "underperformance": 0,
        }
        for sample in samples:
            category = self._outcome_category(
                sample.get("validation_result", {}).get("percentage_return", 0),
            )
            counts[category] += 1

        total = sum(counts.values())
        if total == 0:
            return {
                "outperformance": 34,
                "market_performance": 33,
                "underperformance": 33,
            }

        out = round(counts["outperformance"] / total * 100)
        market = round(counts["market_performance"] / total * 100)
        under = 100 - out - market

        return {
            "outperformance": out,
            "market_performance": market,
            "underperformance": under,
        }

    def _expected_outcome(self, samples):
        returns = [
            sample.get("validation_result", {}).get("percentage_return")
            for sample in samples
            if sample.get("validation_result", {}).get("percentage_return")
            is not None
        ]
        holding_periods = [
            sample.get("validation_result", {}).get("holding_period")
            for sample in samples
            if sample.get("validation_result", {}).get("holding_period")
            is not None
        ]
        ordered = sorted(returns)

        return {
            "expected_return": self._average(returns),
            "expected_holding_period": self._average(holding_periods),
            "best_case": max(returns) if returns else 0,
            "base_case": self._median(ordered),
            "worst_case": min(returns) if returns else 0,
        }

    def _confidence_quality(self, samples):
        sample_size = len(samples)
        average_similarity = self._average([
            sample.get("similarity_score", 0)
            for sample in samples
        ])
        confidence = round(
            min(95, sample_size * 8 + average_similarity * 0.45),
            2,
        )

        return {
            "sample_size": sample_size,
            "similar_historical_cases": [
                {
                    "id": sample.get("id"),
                    "ticker": sample.get("ticker"),
                    "action": sample.get("action"),
                    "market_regime": sample.get("market_regime"),
                    "return": sample.get("validation_result", {}).get(
                        "percentage_return",
                    ),
                    "similarity_score": sample.get("similarity_score", 0),
                }
                for sample in samples[:5]
            ],
            "probability_confidence": confidence,
            "uncertainty_level": self._uncertainty_level(sample_size),
        }

    def _similarity_score(self, target, sample):
        score = 0

        if target.get("ticker") == sample.get("ticker"):
            score += 15

        if (target.get("action") or target.get("recommendation")) == (
            sample.get("action") or sample.get("recommendation")
        ):
            score += 10

        if target.get("market_regime") == sample.get("market_regime"):
            score += 15

        score += self._range_similarity(
            target.get("committee_agreement", 0),
            sample.get("committee_agreement", 0),
            15,
        )
        if target.get("executive_status") == sample.get("executive_status"):
            score += 10

        score += self._range_similarity(
            target.get("knowledge_score", 0),
            sample.get("knowledge_score", 0),
            15,
        )
        score += self._range_similarity(
            target.get("stability_score", 0),
            sample.get("stability_score", 0),
            10,
        )
        score += self._overlap_score(
            self._evidence_categories(target),
            self._evidence_categories(sample),
            10,
        )
        score += self._overlap_score(
            self._catalyst_types(target),
            self._catalyst_types(sample),
            10,
        )

        return round(min(100, score), 2)

    def _record(self, item):
        if isinstance(item, dict):
            return item

        return {
            "id": getattr(item, "id", None),
            "ticker": getattr(item, "ticker", ""),
            "action": getattr(item, "action", ""),
            "market_regime": getattr(item, "market_regime", ""),
            "evidence_breakdown": getattr(item, "evidence_breakdown", []),
            "committee_agreement": getattr(item, "committee_agreement", 0),
            "executive_status": getattr(item, "executive_status", ""),
            "knowledge_score": getattr(item, "knowledge_score", 0),
            "stability_score": getattr(item, "stability_score", 0),
            "catalysts": getattr(item, "catalysts", []),
            "validation_result": getattr(item, "validation_result", None),
        }

    def _outcome_category(self, percentage_return):
        if percentage_return > self.OUTPERFORMANCE_THRESHOLD:
            return "outperformance"

        if percentage_return < self.UNDERPERFORMANCE_THRESHOLD:
            return "underperformance"

        return "market_performance"

    def _predicted_category(self, report):
        probabilities = report.get("probabilities", {})

        return max(
            probabilities,
            key=lambda key: (probabilities[key], key),
        )

    def _uncertainty_level(self, sample_size):
        if sample_size >= 10:
            return "Very Low"

        if sample_size >= 6:
            return "Low"

        if sample_size >= 4:
            return "Moderate"

        if sample_size >= 2:
            return "High"

        return "Very High"

    def _range_similarity(self, first, second, weight):
        distance = abs((first or 0) - (second or 0))

        return max(0, weight - distance / 100 * weight)

    def _overlap_score(self, first, second, weight):
        if not first or not second:
            return 0

        overlap = len(set(first) & set(second))
        denominator = max(len(set(first)), len(set(second)))

        return round(overlap / denominator * weight, 2)

    def _evidence_categories(self, record):
        return [
            item.get("category", item.get("name"))
            for item in record.get("evidence_breakdown", [])
            if isinstance(item, dict) and item.get("score", 0) >= 60
        ]

    def _catalyst_types(self, record):
        return [
            item.get("event_type")
            for item in record.get("catalysts", [])
            if isinstance(item, dict) and item.get("event_type")
        ]

    def _explanation(self, probabilities, expected, quality):
        return (
            "Probability estimate uses similar validated Atlas history. "
            f"Sample size {quality['sample_size']} produces "
            f"{quality['uncertainty_level']} uncertainty. Expected return is "
            f"{expected['expected_return']}%, and probabilities sum to "
            f"{sum(probabilities.values())}%."
        )

    def _average(self, values):
        values = [value for value in values if value is not None]

        if not values:
            return 0

        return round(sum(values) / len(values), 2)

    def _median(self, values):
        if not values:
            return 0

        midpoint = len(values) // 2
        if len(values) % 2:
            return values[midpoint]

        return round((values[midpoint - 1] + values[midpoint]) / 2, 2)

    def _rate(self, numerator, denominator):
        if denominator == 0:
            return 0

        return round(numerator / denominator * 100, 2)
