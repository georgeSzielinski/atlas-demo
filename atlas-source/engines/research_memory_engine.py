class ResearchMemoryEngine:
    WEIGHTS = {
        "ticker": 8,
        "sector": 8,
        "market_regime": 12,
        "evidence_profile": 14,
        "committee_agreement": 10,
        "executive_review": 8,
        "knowledge_score": 8,
        "stability_score": 8,
        "catalyst_profile": 8,
        "probability_profile": 8,
        "portfolio_strategy": 8,
    }

    def build(self, recommendation=None, source_data=None, limit=5):
        if source_data is None:
            from database.repository import get_discovery_source_data

            source_data = get_discovery_source_data()

        historical_cases = self.historical_cases(source_data)
        target = self._record(recommendation) if recommendation else None
        analogs = self.retrieve(target, historical_cases, limit=limit)
        lessons = self.lessons(target, analogs)

        return {
            "target": self._target_summary(target),
            "similar_historical_cases": analogs,
            "lessons": lessons,
            "observability": self.observability(analogs, historical_cases),
            "policy": {
                "read_only": True,
                "changes_recommendation_behavior": False,
                "automatic_execution": False,
                "requires_human_approval": True,
            },
        }

    def build_many(self, recommendations, source_data=None, limit=5):
        return [
            self.build(recommendation, source_data=source_data, limit=limit)
            for recommendation in recommendations
        ]

    def historical_cases(self, source_data):
        cases = []

        for case in source_data.get("case_studies", []):
            if case.get("return") is None and not case.get("validation"):
                continue

            cases.append(self._case_record(case))

        for recommendation in source_data.get("recommendations", []):
            validation = recommendation.get("validation_result")
            if not isinstance(validation, dict):
                continue

            if validation.get("success") is None and validation.get("hit") is None:
                continue

            cases.append(self._record(recommendation))

        deduped = {}
        for case in cases:
            deduped[case["id"]] = case

        return list(deduped.values())

    def retrieve(self, target, historical_cases, limit=5):
        if target is None:
            rows = [
                self._analog_row(case, case, 100, {
                    key: self.WEIGHTS[key] for key in self.WEIGHTS
                })
                for case in historical_cases
            ]
        else:
            rows = []
            for case in historical_cases:
                if case.get("id") == target.get("id") and target.get("id") is not None:
                    continue

                score, components = self.similarity_score(target, case)
                if score <= 0:
                    continue

                rows.append(self._analog_row(target, case, score, components))

        return sorted(
            rows,
            key=lambda item: (
                item["similarity_score"],
                item.get("return", 0),
                item.get("ticker", ""),
                item.get("case_id", ""),
            ),
            reverse=True,
        )[:limit]

    def similarity_score(self, target, case):
        components = {
            "ticker": self._exact(target.get("ticker"), case.get("ticker"), "ticker"),
            "sector": self._exact(target.get("sector"), case.get("sector"), "sector"),
            "market_regime": self._exact(
                target.get("market_regime"),
                case.get("market_regime"),
                "market_regime",
            ),
            "evidence_profile": self._overlap(
                target.get("evidence_profile", []),
                case.get("evidence_profile", []),
                "evidence_profile",
            ),
            "committee_agreement": self._range(
                target.get("committee_agreement", 0),
                case.get("committee_agreement", 0),
                "committee_agreement",
            ),
            "executive_review": self._exact(
                target.get("executive_status"),
                case.get("executive_status"),
                "executive_review",
            ),
            "knowledge_score": self._range(
                target.get("knowledge_score", 0),
                case.get("knowledge_score", 0),
                "knowledge_score",
            ),
            "stability_score": self._range(
                target.get("stability_score", 0),
                case.get("stability_score", 0),
                "stability_score",
            ),
            "catalyst_profile": self._overlap(
                target.get("catalyst_profile", []),
                case.get("catalyst_profile", []),
                "catalyst_profile",
            ),
            "probability_profile": self._probability_similarity(
                target.get("probability_profile", {}),
                case.get("probability_profile", {}),
            ),
            "portfolio_strategy": self._overlap(
                target.get("portfolio_strategy", []),
                case.get("portfolio_strategy", []),
                "portfolio_strategy",
            ),
        }

        return round(sum(components.values()), 2), components

    def lessons(self, target, analogs):
        returns = [item.get("return") for item in analogs if item.get("return") is not None]
        holding_periods = [
            item.get("holding_period")
            for item in analogs
            if item.get("holding_period") is not None
        ]
        wins = [item for item in analogs if item.get("outcome") == "Win"]
        losses = [item for item in analogs if item.get("outcome") == "Loss"]
        useful_evidence = self._rank_patterns([
            evidence
            for item in wins
            for evidence in item.get("evidence_profile", [])
        ])
        failed_evidence = self._rank_patterns([
            evidence
            for item in losses
            for evidence in item.get("evidence_profile", [])
        ])

        return {
            "similar_historical_cases": [
                {
                    "case_id": item.get("case_id"),
                    "ticker": item.get("ticker"),
                    "similarity_score": item.get("similarity_score"),
                    "outcome": item.get("outcome"),
                    "return": item.get("return"),
                }
                for item in analogs
            ],
            "average_historical_return": self._average(returns),
            "average_holding_period": self._average(holding_periods),
            "win_rate": self._rate(len(wins), len(analogs)),
            "common_successful_patterns": self._successful_patterns(wins),
            "common_failure_patterns": self._failure_patterns(losses),
            "most_useful_evidence": useful_evidence[:5],
            "frequent_catalyst_behavior": self._rank_patterns([
                catalyst
                for item in analogs
                for catalyst in item.get("catalyst_profile", [])
            ])[:5],
            "explanation": self._lesson_explanation(target, analogs),
        }

    def observability(self, analogs, historical_cases):
        scored = [item.get("similarity_score", 0) for item in analogs]
        high_similarity = [
            item for item in analogs
            if item.get("similarity_score", 0) >= 70
        ]
        successful_high_similarity = [
            item for item in high_similarity
            if item.get("outcome") == "Win"
        ]

        return {
            "research_memory_retrieval_accuracy": self._rate(
                len(successful_high_similarity),
                len(high_similarity),
            ),
            "analog_success_rate": self._rate(
                len([item for item in analogs if item.get("outcome") == "Win"]),
                len(analogs),
            ),
            "similarity_score_calibration": {
                "average_similarity": self._average(scored),
                "high_similarity_success_rate": self._rate(
                    len(successful_high_similarity),
                    len(high_similarity),
                ),
                "sample_size": len(analogs),
            },
            "pattern_frequency": self.pattern_frequency(historical_cases),
        }

    def pattern_frequency(self, historical_cases):
        return {
            "evidence": self._rank_patterns([
                evidence
                for case in historical_cases
                for evidence in case.get("evidence_profile", [])
            ])[:10],
            "failures": self._rank_patterns([
                evidence
                for case in historical_cases
                if case.get("outcome") == "Loss"
                for evidence in case.get("evidence_profile", [])
            ])[:10],
            "catalysts": self._rank_patterns([
                catalyst
                for case in historical_cases
                for catalyst in case.get("catalyst_profile", [])
            ])[:10],
        }

    def graph_relationship_summary(self, source_data):
        cases = self.historical_cases(source_data)
        pairs = []

        for index, case in enumerate(cases):
            for other in cases[index + 1:]:
                score, components = self.similarity_score(case, other)
                pairs.append({
                    "source": case["id"],
                    "target": other["id"],
                    "score": score,
                    "components": components,
                    "outcomes": [case.get("outcome"), other.get("outcome")],
                })

        ordered = sorted(
            pairs,
            key=lambda item: (item["score"], item["source"], item["target"]),
            reverse=True,
        )
        failures = [
            item for item in ordered
            if "Loss" in item["outcomes"]
        ]

        return {
            "strongest_analogs": ordered[:5],
            "weakest_analogs": list(reversed(ordered[-5:])),
            "recurring_patterns": self.pattern_frequency(cases)["evidence"][:5],
            "recurring_failures": self.pattern_frequency(cases)["failures"][:5],
            "failure_analogs": failures[:5],
        }

    def _analog_row(self, target, case, score, components):
        return {
            "case_id": case.get("id"),
            "ticker": case.get("ticker"),
            "sector": case.get("sector"),
            "market_regime": case.get("market_regime"),
            "recommendation": case.get("action"),
            "outcome": case.get("outcome"),
            "return": case.get("return"),
            "holding_period": case.get("holding_period"),
            "evidence_profile": case.get("evidence_profile", []),
            "catalyst_profile": case.get("catalyst_profile", []),
            "probability_profile": case.get("probability_profile", {}),
            "portfolio_strategy": case.get("portfolio_strategy", []),
            "similarity_score": score,
            "component_scores": components,
            "explanation": self._explanation(target, case, score, components),
        }

    def _record(self, item):
        if not isinstance(item, dict):
            item = {
                "id": getattr(item, "id", None),
                "ticker": getattr(item, "ticker", ""),
                "sector": getattr(item, "sector", ""),
                "action": getattr(item, "action", ""),
                "market_regime": getattr(item, "market_regime", ""),
                "evidence_breakdown": getattr(item, "evidence_breakdown", []),
                "committee_agreement": getattr(item, "committee_agreement", 0),
                "executive_status": getattr(item, "executive_status", ""),
                "knowledge_score": getattr(item, "knowledge_score", 0),
                "stability_score": getattr(item, "stability_score", 0),
                "catalysts": getattr(item, "catalysts", []),
                "probability_report": getattr(item, "probability_report", {}),
                "portfolio_strategy": getattr(item, "portfolio_strategy", []),
                "validation_result": getattr(item, "validation_result", None),
            }

        validation = item.get("validation_result") or {}
        success = validation.get("success")
        if success is None:
            success = validation.get("hit")

        return {
            "id": f"recommendation:{item.get('id', item.get('ticker', 'unknown'))}",
            "ticker": item.get("ticker", ""),
            "sector": item.get("sector", "Unknown") or "Unknown",
            "action": item.get("action") or item.get("recommendation", ""),
            "market_regime": item.get("market_regime", "Unknown") or "Unknown",
            "evidence_profile": self._evidence_profile(
                item.get("evidence_breakdown", item.get("evidence", []))
            ),
            "committee_agreement": item.get("committee_agreement", 0) or 0,
            "executive_status": item.get("executive_status", ""),
            "knowledge_score": item.get("knowledge_score", 0) or 0,
            "stability_score": item.get("stability_score", 0) or 0,
            "catalyst_profile": self._catalyst_profile(item.get("catalysts", [])),
            "probability_profile": self._probability_profile(
                item.get("probability_report", {})
            ),
            "portfolio_strategy": self._portfolio_strategy(item),
            "outcome": "Win" if success is True else "Loss" if success is False else "",
            "return": validation.get("percentage_return"),
            "holding_period": validation.get("holding_period"),
        }

    def _case_record(self, case):
        return {
            "id": f"case_study:{case.get('case_id', case.get('ticker', 'unknown'))}",
            "ticker": case.get("ticker", ""),
            "sector": case.get("sector", "Unknown") or "Unknown",
            "action": case.get("recommendation", ""),
            "market_regime": case.get("market_regime", "Unknown") or "Unknown",
            "evidence_profile": self._evidence_profile(case.get("evidence", [])),
            "committee_agreement": case.get("committee", {}).get("agreement", 0),
            "executive_status": case.get("executive_review", {}).get("status", ""),
            "knowledge_score": case.get("knowledge_score", 0) or 0,
            "stability_score": case.get("stability_score", 0) or 0,
            "catalyst_profile": self._catalyst_profile(case.get("catalysts", [])),
            "probability_profile": self._probability_profile(
                case.get("probability_report", {})
            ),
            "portfolio_strategy": self._portfolio_strategy(case),
            "outcome": case.get("outcome", ""),
            "return": case.get("return", 0),
            "holding_period": case.get("holding_period", 0),
        }

    def _evidence_profile(self, evidence):
        return sorted({
            item.get("category") or item.get("name")
            for item in evidence
            if isinstance(item, dict)
            and (item.get("category") or item.get("name"))
            and item.get("score", 0) >= 60
        })

    def _catalyst_profile(self, catalysts):
        return sorted({
            item.get("event_type")
            for item in catalysts
            if isinstance(item, dict) and item.get("event_type")
        })

    def _probability_profile(self, report):
        probabilities = report.get("probabilities", {}) if isinstance(report, dict) else {}
        expected = report.get("expected_outcome", {}) if isinstance(report, dict) else {}

        return {
            "outperformance": probabilities.get("outperformance", 0),
            "market_performance": probabilities.get("market_performance", 0),
            "underperformance": probabilities.get("underperformance", 0),
            "expected_return": expected.get("expected_return", 0),
        }

    def _portfolio_strategy(self, item):
        strategy = item.get("portfolio_strategy") or item.get("portfolio_strategy_profile")
        if isinstance(strategy, list):
            return sorted([str(value) for value in strategy])

        if isinstance(strategy, dict):
            values = []
            for key, value in strategy.items():
                if isinstance(value, (str, int, float)):
                    values.append(f"{key}:{value}")
            return sorted(values)

        action = item.get("portfolio_action") or item.get("action")
        return [action] if action else []

    def _exact(self, first, second, key):
        if not first or not second:
            return 0

        return self.WEIGHTS[key] if first == second else 0

    def _range(self, first, second, key):
        distance = abs((first or 0) - (second or 0))
        return round(max(0, self.WEIGHTS[key] - distance / 100 * self.WEIGHTS[key]), 2)

    def _overlap(self, first, second, key):
        if not first or not second:
            return 0

        first_set = set(first)
        second_set = set(second)
        overlap = len(first_set & second_set)
        denominator = max(len(first_set), len(second_set))

        return round(overlap / denominator * self.WEIGHTS[key], 2)

    def _probability_similarity(self, first, second):
        if not first or not second:
            return 0

        distances = [
            abs(first.get("outperformance", 0) - second.get("outperformance", 0)),
            abs(first.get("market_performance", 0) - second.get("market_performance", 0)),
            abs(first.get("underperformance", 0) - second.get("underperformance", 0)),
            min(100, abs(first.get("expected_return", 0) - second.get("expected_return", 0)) * 10),
        ]
        distance = sum(distances) / len(distances)

        return round(max(0, self.WEIGHTS["probability_profile"] - distance / 100 * self.WEIGHTS["probability_profile"]), 2)

    def _successful_patterns(self, wins):
        patterns = []
        for item in wins:
            if item.get("committee_agreement", 0) >= 75:
                patterns.append("High committee agreement")
            if item.get("knowledge_score", 0) >= 80:
                patterns.append("High knowledge score")
            if item.get("stability_score", 0) >= 75:
                patterns.append("Stable recommendation")
            patterns.extend(item.get("evidence_profile", []))

        return self._rank_patterns(patterns)[:5]

    def _failure_patterns(self, losses):
        patterns = []
        for item in losses:
            if item.get("committee_agreement", 0) < 60:
                patterns.append("Low committee agreement")
            if item.get("stability_score", 0) < 60:
                patterns.append("Low stability score")
            patterns.extend(item.get("evidence_profile", []))

        return self._rank_patterns(patterns)[:5]

    def _rank_patterns(self, values):
        counts = {}
        for value in values:
            if not value:
                continue
            counts[value] = counts.get(value, 0) + 1

        return [
            {"pattern": key, "count": value}
            for key, value in sorted(
                counts.items(),
                key=lambda item: (-item[1], item[0]),
            )
        ]

    def _explanation(self, target, case, score, components):
        strongest = [
            key for key, value in sorted(
                components.items(),
                key=lambda item: item[1],
                reverse=True,
            )
            if value > 0
        ][:3]

        return (
            f"{case.get('ticker')} is a {score}% analog based on "
            f"{', '.join(strongest) or 'limited shared evidence'}."
        )

    def _lesson_explanation(self, target, analogs):
        if not analogs:
            return "No validated historical analogs are available yet."

        return (
            f"Lessons are derived from {len(analogs)} deterministic analogs "
            "and are evidence only, not recommendation rules."
        )

    def _target_summary(self, target):
        if target is None:
            return {"mode": "all_historical_cases"}

        return {
            "ticker": target.get("ticker"),
            "sector": target.get("sector"),
            "market_regime": target.get("market_regime"),
            "evidence_profile": target.get("evidence_profile", []),
        }

    def _average(self, values):
        values = [value for value in values if value is not None]
        if not values:
            return 0

        return round(sum(values) / len(values), 2)

    def _rate(self, numerator, denominator):
        if denominator == 0:
            return 0

        return round(numerator / denominator * 100, 2)
