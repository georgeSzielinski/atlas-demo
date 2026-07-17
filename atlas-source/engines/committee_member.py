from engines.strategy_registry_engine import StrategyRegistryEngine


class CommitteeMember:
    """One deterministic committee voter backed by a registry strategy spec.

    A member wraps a validated strategy spec from StrategyRegistryEngine and
    scores a single stock record with that spec's weights and action bands.
    Signals are read from the record's whitelisted fields only (dict keys or
    attributes); a missing signal is reported in missing_inputs and excluded
    from the weighted blend — it is never defaulted. Below 50% weight coverage
    the member abstains with NOT_EVALUATED instead of guessing.

    Confidence is a documented deterministic formula, not a model output:
        band_margin = min(25, distance of the score from the nearest action
                          boundary)
        confidence  = clamp(1, 99, round((50 + 2 * band_margin) * coverage))
    so a score sitting exactly on a boundary yields 50 x coverage, and a score
    25+ points inside its band yields up to 99. No LLM, no randomness, no live
    trading involvement.
    """

    MIN_COVERAGE_PCT = 50

    def __init__(self, spec, registry=None):
        registry = registry or StrategyRegistryEngine()
        problems = registry.validate(spec)
        if problems:
            raise ValueError(
                f"Invalid strategy spec for committee member: {problems}"
            )
        self.spec = spec
        self.strategy_id = spec["strategy_id"]
        self.name = spec["name"]
        self.signal_catalog = StrategyRegistryEngine.SIGNAL_INPUTS

    # ------------------------------------------------------------------
    # Voting
    # ------------------------------------------------------------------
    def evaluate(self, stock):
        weights = self.spec["scoring_logic"]["weights"]
        bands = self.spec["scoring_logic"]["action_bands"]

        drivers = []
        missing_inputs = []
        available_weight = 0.0
        weighted_sum = 0.0

        for signal, weight in sorted(weights.items()):
            value = self._number(self._value(stock, signal))
            if value is None:
                missing_inputs.append(signal)
                continue
            scale = self.signal_catalog.get(signal, {}).get("scale", 100)
            normalized = max(0.0, min(100.0, value / scale * 100))
            available_weight += weight
            weighted_sum += normalized * weight
            drivers.append({
                "signal": signal,
                "value": value,
                "normalized": round(normalized, 2),
                "weight": weight,
                "contribution": round(normalized * weight, 2),
            })

        total_weight = sum(weights.values())
        coverage = (
            round(available_weight / total_weight * 100, 2) if total_weight else 0
        )

        if coverage < self.MIN_COVERAGE_PCT:
            return {
                "action": None,
                "confidence": None,
                "score": None,
                "explanation": (
                    f"{self.name} abstained: only {coverage}% of signal weight "
                    f"had stored values (missing {', '.join(missing_inputs)})."
                ),
                "drivers": drivers,
                "missing_inputs": missing_inputs,
                "coverage_pct": coverage,
                "status": "NOT_EVALUATED",
            }

        drivers.sort(key=lambda item: (-item["contribution"], item["signal"]))
        score = round(weighted_sum / available_weight, 2)

        if score >= bands["buy"]:
            action = "BUY"
            band_margin = score - bands["buy"]
        elif score >= bands["hold"]:
            action = "HOLD"
            band_margin = min(score - bands["hold"], bands["buy"] - score)
        else:
            action = "AVOID"
            band_margin = bands["hold"] - score

        confidence = self._confidence(band_margin, coverage)
        top = drivers[0]["signal"] if drivers else "no signal"

        return {
            "action": action,
            "confidence": confidence,
            "score": score,
            "explanation": (
                f"{self.name} votes {action}: score {score} against bands "
                f"buy>={bands['buy']}/hold>={bands['hold']} with {coverage}% "
                f"signal coverage; strongest driver {top}."
            ),
            "drivers": drivers,
            "missing_inputs": missing_inputs,
            "coverage_pct": coverage,
            "status": "EVALUATED" if coverage == 100 else "PARTIAL",
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _confidence(self, band_margin, coverage):
        margin = max(0.0, min(25.0, float(band_margin)))
        raw = (50 + 2 * margin) * coverage / 100
        return int(max(1, min(99, round(raw))))

    def _value(self, stock, key):
        if isinstance(stock, dict):
            return stock.get(key)
        return getattr(stock, key, None)

    def _number(self, value):
        if value is None or isinstance(value, bool):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def policy(self):
        return {
            "research_only": True,
            "read_only": True,
            "deterministic": True,
            "llm_decisions": False,
            "randomness": False,
            "broker_integration": False,
            "real_money": False,
            "modifies_live_paper_fund": False,
            "modifies_portfolio_construction": False,
            "modifies_risk_management": False,
        }
