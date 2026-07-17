class HypothesisEngine:
    """Build deterministic recommendation assumptions and counterfactuals."""

    def generate(self, recommendation):
        evidence = self._evidence(recommendation)
        key_assumptions = [
            self._assumption(item, "key")
            for item in evidence
            if item["score"] >= 60
        ]
        supporting_assumptions = [
            self._assumption(item, "supporting")
            for item in evidence
            if 50 <= item["score"] < 60
        ]
        weakest_assumptions = [
            self._assumption(item, "weak")
            for item in sorted(evidence, key=lambda item: item["score"])
            if item["score"] < 60
        ]
        evidence_dependencies = [
            {
                "source": item["name"],
                "score": item["score"],
                "confidence": item["confidence"],
                "dependency": item["reason"],
            }
            for item in evidence
        ]
        confidence_drivers = self._confidence_drivers(recommendation, evidence)
        counterfactuals = self._counterfactuals(recommendation, evidence)

        if not key_assumptions:
            key_assumptions.append(
                "Atlas assumes mixed evidence is sufficient for a neutral recommendation."
            )

        strongest = max(
            key_assumptions + supporting_assumptions + weakest_assumptions,
            key=lambda item: self._score_from_text(item),
            default="No strong assumption available.",
        )
        weakest = (
            weakest_assumptions[0]
            if weakest_assumptions
            else "No fragile assumption identified from current evidence."
        )

        return {
            "key_assumptions": key_assumptions[:5],
            "supporting_assumptions": supporting_assumptions[:5],
            "weakest_assumptions": weakest_assumptions[:5],
            "evidence_dependencies": evidence_dependencies,
            "confidence_drivers": confidence_drivers,
            "strongest_assumption": strongest,
            "weakest_assumption": weakest,
            "counterfactuals": counterfactuals,
            "recommendation_flip_conditions": self._flip_conditions(
                recommendation,
                counterfactuals,
            ),
        }

    def _evidence(self, recommendation):
        evidence = getattr(recommendation, "evidence_breakdown", []) or []

        return [
            {
                "name": item.get("name") or item.get("category") or "Unknown",
                "score": self._number(item.get("score")),
                "confidence": self._number(item.get("confidence")),
                "weight": self._number(item.get("weight")),
                "reason": item.get("reason") or item.get("summary") or "",
            }
            for item in evidence
            if isinstance(item, dict)
        ]

    def _assumption(self, item, category):
        prefix = {
            "key": "Atlas assumes",
            "supporting": "Atlas partly assumes",
            "weak": "Atlas is vulnerable if",
        }[category]

        if category == "weak":
            return (
                f"{prefix} {item['name'].lower()} evidence remains weak "
                f"(score {item['score']})."
            )

        return (
            f"{prefix} {item['name'].lower()} evidence remains valid "
            f"(score {item['score']})."
        )

    def _confidence_drivers(self, recommendation, evidence):
        drivers = [
            {
                "source": item["name"],
                "score": item["score"],
                "confidence": item["confidence"],
                "weight": item["weight"],
                "effect": "strengthens" if item["score"] >= 60 else "weakens",
            }
            for item in evidence
        ]
        drivers.sort(
            key=lambda item: (item["weight"], item["score"], item["confidence"]),
            reverse=True,
        )

        return drivers[:5]

    def _counterfactuals(self, recommendation, evidence):
        scenarios = [
            ("Technical", "If technical score falls", -20),
            ("Forecast", "If forecast improves", 15),
            ("Fundamental", "If valuation decreases", 12),
            ("Risk", "If risk increases", -20),
            ("News", "If news sentiment reverses", -15),
        ]
        current_action = getattr(recommendation, "action", "HOLD")
        current_confidence = self._number(getattr(recommendation, "confidence", 0))
        current_conviction = self._number(
            getattr(recommendation, "overall_conviction", 0)
        )

        rows = []
        for source, scenario, delta in scenarios:
            item = self._find_evidence(evidence, source)
            confidence_delta = self._scaled_delta(delta, item)
            conviction_delta = self._scaled_delta(delta, item, conviction=True)
            possible_action = self._possible_action(
                current_action,
                current_confidence + confidence_delta,
            )

            rows.append({
                "scenario": scenario,
                "evidence_source": source,
                "effect_on_confidence": confidence_delta,
                "effect_on_conviction": conviction_delta,
                "possible_recommendation_change": possible_action,
                "rationale": self._rationale(
                    source,
                    item,
                    current_action,
                    possible_action,
                    current_conviction + conviction_delta,
                ),
            })

        return rows

    def _find_evidence(self, evidence, source):
        return next(
            (item for item in evidence if item["name"].lower() == source.lower()),
            {"name": source, "score": 0, "confidence": 0, "weight": 0},
        )

    def _scaled_delta(self, delta, item, conviction=False):
        multiplier = item["weight"] if item["weight"] else 0.1
        if conviction:
            multiplier += 0.05

        return round(delta * multiplier, 2)

    def _possible_action(self, current_action, adjusted_confidence):
        if adjusted_confidence >= 80:
            possible = "BUY"
        elif adjusted_confidence >= 55:
            possible = "HOLD"
        else:
            possible = "AVOID"

        if possible == current_action:
            return f"Likely remains {current_action}"

        return f"Could move from {current_action} to {possible}"

    def _rationale(
        self,
        source,
        item,
        current_action,
        possible_action,
        adjusted_conviction,
    ):
        return (
            f"{source} currently has score {item['score']} and confidence "
            f"{item['confidence']}; this deterministic scenario compares the "
            f"adjusted confidence threshold with the current {current_action} "
            f"action and estimated conviction {round(adjusted_conviction, 2)}."
        )

    def _flip_conditions(self, recommendation, counterfactuals):
        flips = [
            item for item in counterfactuals
            if item["possible_recommendation_change"].startswith("Could move")
        ]

        if flips:
            return [
                f"{item['scenario']}: {item['possible_recommendation_change']}."
                for item in flips
            ]

        return [
            "No single deterministic counterfactual crosses an action threshold."
        ]

    def _score_from_text(self, text):
        digits = "".join(character for character in text if character.isdigit())

        return int(digits) if digits else 0

    def _number(self, value):
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0
