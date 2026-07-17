from engines.paper_trading_engine import PaperTradingEngine


class SelfImprovementEngine:
    """Deterministic, read-only research-opportunity engine.

    The Self-Improvement Engine studies persisted historical evidence and
    proposes *research opportunities* — it NEVER changes live behavior. It does
    not modify strategies, weights, the committee, risk limits, orders, or
    trades; it calls no LLM and uses no randomness. Identical inputs always
    produce identical output.

    It analyzes nine evidence domains from stored paper-trading records:

      1. strategy_performance     - per-strategy realized P/L on closed trades
      2. committee_performance    - per-member directional vote accuracy
      3. signal_predictive_power  - research-signal lift (winners vs losers),
                                    including whether a signal is *degrading*
      4. sector_performance       - realized P/L concentration by sector
      5. regime_performance       - realized P/L by market regime
      6. portfolio_construction   - diversification / concentration trend
      7. risk_decisions           - approval / rejection rate and top reasons
      8. drawdowns                - peak-to-trough equity drawdown
      9. trade_quality            - winners vs losers (win rate, holding edge)

    Each *finding* carries the fields the milestone requires: ``confidence``
    (deterministic 0-1 with a band label), ``statistics`` (the supporting
    numbers), ``sample_size``, a plain-language ``explanation``, and a research
    ``recommendation``. A domain with insufficient evidence is returned as
    ``NOT_EVALUATED`` with a human-readable reason, never fabricated.
    """

    DEFAULT_LIMIT = 200

    # Evidence thresholds. Below these a domain (or group) is NOT_EVALUATED
    # rather than judged on too little data.
    MIN_TRADES_PER_GROUP = 3
    MIN_GROUPS = 2
    MIN_SIGNAL_SAMPLES = 3
    MIN_RISK_DECISIONS = 5
    MIN_CONSTRUCTION_REPORTS = 3
    MIN_DRAWDOWN_POINTS = 3
    MIN_CLOSED_TRADES = 3

    # Deterministic confidence model. Confidence blends how much evidence
    # exists (sample vs saturation) with how large the measured effect is
    # (|effect| vs its normalizer), each clamped to [0, 1].
    CONFIDENCE_SATURATION = 30
    SAMPLE_WEIGHT = 0.5
    EFFECT_WEIGHT = 0.5
    LOW_BAND = 0.40
    HIGH_BAND = 0.70

    # Signal lift (in score points) needed to call a signal predictive, and the
    # recent-vs-older drop that flags a signal as degrading.
    LIFT_PREDICTIVE = 2.0
    LIFT_DEGRADE_MARGIN = 5.0
    SIGNAL_EFFECT_NORM = 20.0

    # Research signal field -> label. Order is stable for deterministic output.
    RESEARCH_SIGNALS = (
        ("technical_score", "Technical"),
        ("fundamental_score", "Fundamental"),
        ("forecast_score", "Forecast"),
        ("news_confidence", "News"),
        ("signal_quality_score", "Signal Quality"),
        ("rsi", "RSI"),
    )

    # Snapshot keys carrying committee votes, in priority order.
    COMMITTEE_VOTE_KEYS = ("committee_members", "committee_votes")
    # Snapshot keys for the strategy tag and market regime tag.
    STRATEGY_KEYS = ("strategy", "strategy_name")
    REGIME_KEYS = ("market_regime", "regime")
    SECTOR_KEYS = ("sector",)

    BULLISH_ACTIONS = {"BUY", "STRONG BUY", "ADD", "ACCUMULATE", "OVERWEIGHT"}
    BEARISH_ACTIONS = {"SELL", "AVOID", "REDUCE", "TRIM", "EXIT", "UNDERWEIGHT"}

    # Persisted order statuses that count as executed fills for round-trip
    # accounting. The live paper fund records simulated executions as
    # FILLED_SIMULATED; anything outside this set (rejected, proposed,
    # unfilled) is never treated as a fill.
    LIVE_FUND_FILL_STATUSES = frozenset({"FILLED", "FILLED_SIMULATED"})

    DOMAINS = (
        "strategy_performance",
        "committee_performance",
        "signal_predictive_power",
        "sector_performance",
        "regime_performance",
        "portfolio_construction",
        "risk_decisions",
        "drawdowns",
        "trade_quality",
    )

    def __init__(self, math_engine=None):
        self.math = math_engine or PaperTradingEngine()

    # ------------------------------------------------------------------
    # Assembly
    # ------------------------------------------------------------------
    def generate(
        self,
        trades=None,
        history=None,
        risk_decisions=None,
        construction_reports=None,
        limit=None,
    ):
        limit = limit or self.DEFAULT_LIMIT
        data = self._load(trades, history, risk_decisions, construction_reports, limit)
        trades = data["trades"]
        history = data["history"]
        risk_decisions = data["risk_decisions"]
        construction_reports = data["construction_reports"]
        closed = self._closed(trades)

        domains = {
            "strategy_performance": self.strategy_performance(closed),
            "committee_performance": self.committee_performance(closed),
            "signal_predictive_power": self.signal_predictive_power(closed),
            "sector_performance": self.sector_performance(closed),
            "regime_performance": self.regime_performance(closed),
            "portfolio_construction": self.portfolio_construction(construction_reports),
            "risk_decisions": self.risk_decisions(risk_decisions),
            "drawdowns": self.drawdowns(history),
            "trade_quality": self.trade_quality(closed),
        }

        findings = []
        not_evaluated = []
        for name in self.DOMAINS:
            section = domains[name]
            findings.extend(section.get("findings", []))
            if section.get("status") != "EVALUATED":
                not_evaluated.append({
                    "domain": name,
                    "reason": section.get("reason", "Insufficient evidence."),
                })

        findings = self._rank(findings)
        return {
            "generated_at": self._generated_at(history, closed),
            "status": "EVALUATED" if findings else "NOT_EVALUATED",
            "headline": self._headline(findings, not_evaluated),
            "findings": findings,
            "opportunities": [self._opportunity(item) for item in findings],
            "domains": domains,
            "not_evaluated": not_evaluated,
            "source_counts": {
                "trades": len(trades),
                "closed_trades": len(closed),
                "portfolio_history": len(history),
                "risk_decisions": len(risk_decisions),
                "construction_reports": len(construction_reports),
            },
            "policy": self.policy(),
        }

    # ------------------------------------------------------------------
    # Domain 1 - strategy performance
    # ------------------------------------------------------------------
    def strategy_performance(self, closed):
        groups = self._group_pl(closed, self.STRATEGY_KEYS)
        qualified = self._qualified_groups(groups)
        if len(qualified) < self.MIN_GROUPS:
            return self._domain_not_evaluated(
                "strategy_performance",
                "At least two strategies each with "
                f"{self.MIN_TRADES_PER_GROUP} closed trades are required to "
                "compare strategy performance.",
            )

        ranked = sorted(
            qualified, key=lambda row: (-row["average_pl"], row["key"])
        )
        best, worst = ranked[0], ranked[-1]
        separation = round(best["average_pl"] - worst["average_pl"], 4)
        sample = best["count"] + worst["count"]
        confidence = self._confidence(
            sample, separation, self._pl_norm(best, worst), self.MIN_GROUPS
        )
        finding = self._finding(
            finding_id="strategy-outperformance",
            category="strategy_performance",
            title=(
                f"{best['key']} has outperformed {worst['key']} across recent "
                "closed trades"
            ),
            confidence=confidence,
            sample_size=sample,
            statistics={
                "best_strategy": best["key"],
                "best_average_pl": best["average_pl"],
                "best_win_rate": best["win_rate"],
                "best_trades": best["count"],
                "worst_strategy": worst["key"],
                "worst_average_pl": worst["average_pl"],
                "worst_win_rate": worst["win_rate"],
                "worst_trades": worst["count"],
                "average_pl_separation": separation,
                "strategies": [self._group_digest(row) for row in ranked],
            },
            explanation=(
                f"{best['key']} averaged {best['average_pl']} P/L over "
                f"{best['count']} closed trades ({best['win_rate']}% win rate) "
                f"versus {worst['key']} at {worst['average_pl']} over "
                f"{worst['count']} trades ({worst['win_rate']}%). Separation is "
                f"{separation} average P/L per trade."
            ),
            recommendation=(
                f"Research why {best['key']} outperforms {worst['key']}: review "
                "the setups, holding periods, and regimes behind the gap before "
                "any strategy change. Research only; no weights are altered."
            ),
        )
        return self._domain([finding])

    # ------------------------------------------------------------------
    # Domain 2 - committee member performance
    # ------------------------------------------------------------------
    def committee_performance(self, closed):
        members = {}
        judged_trades = 0
        for trade in closed:
            result = self._trade_result(trade)
            votes = self._committee_votes(trade)
            if result is None or not votes:
                continue
            counted = False
            for vote in votes:
                correct = self._vote_correct(vote["action"], result)
                if correct is None:
                    continue
                counted = True
                entry = members.setdefault(vote["member_id"], {
                    "key": vote["member_id"],
                    "member_name": vote["member_name"],
                    "evaluated": 0,
                    "correct": 0,
                })
                entry["evaluated"] += 1
                entry["correct"] += 1 if correct else 0
            if counted:
                judged_trades += 1

        rows = [
            {**entry, "accuracy": self.math._rate(entry["correct"], entry["evaluated"])}
            for entry in members.values()
            if entry["evaluated"] >= self.MIN_TRADES_PER_GROUP
        ]
        if not rows:
            return self._domain_not_evaluated(
                "committee_performance",
                "No committee member has at least "
                f"{self.MIN_TRADES_PER_GROUP} directionally judged votes on "
                "closed trades, so member accuracy cannot be attributed.",
            )

        rows.sort(key=lambda row: (-row["accuracy"], -row["evaluated"], row["key"]))
        best = rows[0]
        edge = round(best["accuracy"] - 50.0, 4)
        confidence = self._confidence(
            best["evaluated"], edge, 50.0, self.MIN_TRADES_PER_GROUP
        )
        finding = self._finding(
            finding_id="committee-top-member",
            category="committee_performance",
            title=f"Committee member {best['member_name']} has the highest accuracy",
            confidence=confidence,
            sample_size=best["evaluated"],
            statistics={
                "top_member": best["member_name"],
                "top_member_id": best["key"],
                "accuracy": best["accuracy"],
                "correct": best["correct"],
                "evaluated": best["evaluated"],
                "edge_over_coin_flip": edge,
                "trades_with_votes": judged_trades,
                "members": [self._member_digest(row) for row in rows],
            },
            explanation=(
                f"{best['member_name']} voted correctly on {best['correct']} of "
                f"{best['evaluated']} directionally judged votes "
                f"({best['accuracy']}%), an edge of {edge} points over a 50% "
                "coin flip. A bullish vote is correct on a winning trade and a "
                "bearish vote is correct on a losing trade; neutral votes are "
                "excluded."
            ),
            recommendation=(
                f"Research the rationale behind {best['member_name']}'s calls and "
                "the misses of the lowest-accuracy members. Research only; the "
                "committee and its weights are unchanged."
            ),
        )
        return self._domain([finding])

    # ------------------------------------------------------------------
    # Domain 3 - signal predictive power
    # ------------------------------------------------------------------
    def signal_predictive_power(self, closed):
        findings = []
        evaluated_any = False
        reasons = []
        for field, label in self.RESEARCH_SIGNALS:
            row = self._signal_row(closed, field, label)
            if row["status"] != "EVALUATED":
                reasons.append(f"{label}: {row['reason']}")
                continue
            evaluated_any = True
            findings.append(self._signal_finding(row))

        if not evaluated_any:
            return self._domain_not_evaluated(
                "signal_predictive_power",
                "No research signal had at least "
                f"{self.MIN_SIGNAL_SAMPLES} closed trades carrying it with both "
                "a winner and a loser present. " + "; ".join(reasons),
            )
        return self._domain(findings)

    def _signal_row(self, closed, field, label):
        pairs = []
        for trade in closed:
            score = self._snapshot(trade).get(field)
            if score is None:
                continue
            pairs.append((
                self._number(score),
                self._pl(trade),
                self._sort_key(trade),
            ))
        winners = [score for score, pl, _ in pairs if pl > 0]
        losers = [score for score, pl, _ in pairs if pl < 0]
        if len(pairs) < self.MIN_SIGNAL_SAMPLES or not winners or not losers:
            return {
                "signal": label,
                "field": field,
                "status": "NOT_EVALUATED",
                "reason": (
                    f"needs {self.MIN_SIGNAL_SAMPLES}+ trades with a winner and a "
                    f"loser (have {len(pairs)}, {len(winners)}W/{len(losers)}L)"
                ),
            }

        winner_avg = round(sum(winners) / len(winners), 4)
        loser_avg = round(sum(losers) / len(losers), 4)
        lift = round(winner_avg - loser_avg, 4)
        trend = self._signal_trend(pairs)
        return {
            "signal": label,
            "field": field,
            "status": "EVALUATED",
            "sample_size": len(pairs),
            "winners": len(winners),
            "losers": len(losers),
            "winner_average": winner_avg,
            "loser_average": loser_avg,
            "lift": lift,
            "trend": trend,
        }

    def _signal_trend(self, pairs):
        # Split chronologically into older and recent halves; report the lift in
        # each so a shrinking edge surfaces as "less predictive". NOT_EVALUATED
        # unless both halves have a winner and a loser.
        ordered = sorted(pairs, key=lambda item: item[2])
        half = len(ordered) // 2
        older = self._half_lift(ordered[:half])
        recent = self._half_lift(ordered[half:])
        if older is None or recent is None:
            return {"status": "NOT_EVALUATED"}
        drop = round(older - recent, 4)
        return {
            "status": "EVALUATED",
            "older_lift": older,
            "recent_lift": recent,
            "lift_drop": drop,
            "degrading": drop >= self.LIFT_DEGRADE_MARGIN,
        }

    def _half_lift(self, half):
        winners = [score for score, pl, _ in half if pl > 0]
        losers = [score for score, pl, _ in half if pl < 0]
        if not winners or not losers:
            return None
        return round(sum(winners) / len(winners) - sum(losers) / len(losers), 4)

    def _signal_finding(self, row):
        label = row["signal"]
        lift = row["lift"]
        trend = row.get("trend", {})
        degrading = trend.get("status") == "EVALUATED" and trend.get("degrading")
        confidence = self._confidence(
            row["sample_size"], lift, self.SIGNAL_EFFECT_NORM, self.MIN_SIGNAL_SAMPLES
        )
        if degrading:
            title = f"{label} has become less predictive"
            verdict = "DEGRADING"
            recommendation = (
                f"Research why {label}'s edge shrank from {trend['older_lift']} to "
                f"{trend['recent_lift']} lift; consider whether it needs "
                "recalibration in future research. Research only."
            )
        elif lift >= self.LIFT_PREDICTIVE:
            title = f"{label} scores separate winners from losers"
            verdict = "PREDICTIVE"
            recommendation = (
                f"Research prioritizing {label} — winners scored "
                f"{row['winner_average']} vs {row['loser_average']} on losers. "
                "Research only; no weights change."
            )
        else:
            title = f"{label} shows weak predictive power"
            verdict = "WEAK"
            recommendation = (
                f"Research whether {label} deserves less emphasis; its "
                f"winner/loser separation is only {lift}. Research only."
            )
        explanation = (
            f"{label} averaged {row['winner_average']} on {row['winners']} winning "
            f"trades versus {row['loser_average']} on {row['losers']} losing trades "
            f"(lift {lift}) across {row['sample_size']} closed trades carrying the "
            "signal."
        )
        if trend.get("status") == "EVALUATED":
            explanation += (
                f" Older-half lift {trend['older_lift']} vs recent-half "
                f"{trend['recent_lift']} (drop {trend['lift_drop']})."
            )
        statistics = {
            "signal": label,
            "field": row["field"],
            "verdict": verdict,
            "winner_average": row["winner_average"],
            "loser_average": row["loser_average"],
            "lift": lift,
            "winners": row["winners"],
            "losers": row["losers"],
            "trend": trend,
        }
        return self._finding(
            finding_id=f"signal-{row['field']}",
            category="signal_predictive_power",
            title=title,
            confidence=confidence,
            sample_size=row["sample_size"],
            statistics=statistics,
            explanation=explanation,
            recommendation=recommendation,
        )

    # ------------------------------------------------------------------
    # Domain 4 - sector performance
    # ------------------------------------------------------------------
    def sector_performance(self, closed):
        groups = self._group_pl(closed, self.SECTOR_KEYS)
        qualified = self._qualified_groups(groups)
        if len(qualified) < self.MIN_GROUPS:
            return self._domain_not_evaluated(
                "sector_performance",
                "At least two sectors each with "
                f"{self.MIN_TRADES_PER_GROUP} closed trades are required to "
                "attribute sector performance.",
            )

        ranked = sorted(qualified, key=lambda row: (-row["total_pl"], row["key"]))
        best = ranked[0]
        total_abs = sum(abs(row["total_pl"]) for row in ranked) or 1
        dominance = round(best["total_pl"] / total_abs, 4)
        sample = sum(row["count"] for row in ranked)
        confidence = self._confidence(
            sample, dominance * 100, 100.0, self.MIN_GROUPS
        )
        finding = self._finding(
            finding_id="sector-dominance",
            category="sector_performance",
            title=f"{best['key']} sector currently dominates paper performance",
            confidence=confidence,
            sample_size=best["count"],
            statistics={
                "leading_sector": best["key"],
                "leading_total_pl": best["total_pl"],
                "leading_average_pl": best["average_pl"],
                "leading_win_rate": best["win_rate"],
                "dominance_share": dominance,
                "sectors": [self._group_digest(row) for row in ranked],
            },
            explanation=(
                f"{best['key']} produced {best['total_pl']} total P/L across "
                f"{best['count']} closed trades ({best['win_rate']}% win rate), "
                f"a {round(dominance * 100, 2)}% share of gross sector P/L."
            ),
            recommendation=(
                f"Research the {best['key']} concentration: is the edge durable or "
                "crowding risk? Study diversification in future research. No "
                "positions or limits are changed."
            ),
        )
        return self._domain([finding])

    # ------------------------------------------------------------------
    # Domain 5 - market regime performance
    # ------------------------------------------------------------------
    def regime_performance(self, closed):
        groups = self._group_pl(closed, self.REGIME_KEYS)
        qualified = self._qualified_groups(groups)
        if len(qualified) < self.MIN_GROUPS:
            return self._domain_not_evaluated(
                "regime_performance",
                "At least two market regimes each with "
                f"{self.MIN_TRADES_PER_GROUP} closed trades are required to "
                "compare regime performance.",
            )

        ranked = sorted(qualified, key=lambda row: (-row["average_pl"], row["key"]))
        best, worst = ranked[0], ranked[-1]
        separation = round(best["average_pl"] - worst["average_pl"], 4)
        sample = best["count"] + worst["count"]
        confidence = self._confidence(
            sample, separation, self._pl_norm(best, worst), self.MIN_GROUPS
        )
        best_strategy = self._best_strategy_in_regime(closed, best["key"])
        title = f"Paper trades perform best during {best['key']} regimes"
        if best_strategy:
            title = (
                f"{best_strategy['key']} performs best during {best['key']} regimes"
            )
        finding = self._finding(
            finding_id="regime-best",
            category="regime_performance",
            title=title,
            confidence=confidence,
            sample_size=sample,
            statistics={
                "best_regime": best["key"],
                "best_average_pl": best["average_pl"],
                "best_win_rate": best["win_rate"],
                "worst_regime": worst["key"],
                "worst_average_pl": worst["average_pl"],
                "average_pl_separation": separation,
                "best_regime_top_strategy": best_strategy,
                "regimes": [self._group_digest(row) for row in ranked],
            },
            explanation=(
                f"{best['key']} regimes averaged {best['average_pl']} P/L over "
                f"{best['count']} trades versus {worst['average_pl']} in "
                f"{worst['key']} regimes (separation {separation})."
                + (
                    f" Within {best['key']}, {best_strategy['key']} led at "
                    f"{best_strategy['average_pl']} avg P/L."
                    if best_strategy else ""
                )
            ),
            recommendation=(
                f"Research which setups drive the {best['key']} edge and why "
                f"{worst['key']} lags, to inform future regime-aware research. "
                "Research only."
            ),
        )
        return self._domain([finding])

    def _best_strategy_in_regime(self, closed, regime):
        in_regime = [
            trade for trade in closed
            if self._first(self._snapshot(trade), self.REGIME_KEYS) == regime
        ]
        groups = self._qualified_groups(
            self._group_pl(in_regime, self.STRATEGY_KEYS)
        )
        if not groups:
            return None
        best = sorted(groups, key=lambda row: (-row["average_pl"], row["key"]))[0]
        return self._group_digest(best)

    # ------------------------------------------------------------------
    # Domain 6 - portfolio construction decisions
    # ------------------------------------------------------------------
    def portfolio_construction(self, reports):
        scores = []
        for report in self._ordered_reports(reports):
            diversification = report.get("diversification") or {}
            score = diversification.get("diversification_score")
            if score is None:
                continue
            scores.append({
                "date": self._short_date(report.get("date")),
                "diversification_score": self._number(score),
                "concentration_score": self._number(
                    diversification.get("concentration_score")
                ),
                "risk_budget": (report.get("risk_summary") or {}).get("risk_budget"),
            })

        if len(scores) < self.MIN_CONSTRUCTION_REPORTS:
            return self._domain_not_evaluated(
                "portfolio_construction",
                f"At least {self.MIN_CONSTRUCTION_REPORTS} construction reports "
                "with a diversification score are required to assess the "
                "construction trend.",
            )

        values = [row["diversification_score"] for row in scores]
        latest = values[-1]
        average = round(sum(values) / len(values), 4)
        drift = round(latest - average, 4)
        direction = "improving" if drift > 0 else "weakening" if drift < 0 else "flat"
        confidence = self._confidence(
            len(scores), drift, 25.0, self.MIN_CONSTRUCTION_REPORTS
        )
        finding = self._finding(
            finding_id="construction-diversification-trend",
            category="portfolio_construction",
            title=f"Portfolio construction diversification is {direction}",
            confidence=confidence,
            sample_size=len(scores),
            statistics={
                "latest_diversification": latest,
                "average_diversification": average,
                "drift_vs_average": drift,
                "direction": direction,
                "latest_concentration": scores[-1]["concentration_score"],
                "history": scores,
            },
            explanation=(
                f"The latest diversification score is {latest} versus a "
                f"{len(scores)}-report average of {average} (drift {drift}); the "
                f"construction trend is {direction}."
            ),
            recommendation=(
                "Research whether construction constraints are producing the "
                f"{direction} diversification trend before adjusting any "
                "constraints. Research only; construction is unchanged."
            ),
        )
        return self._domain([finding])

    # ------------------------------------------------------------------
    # Domain 7 - risk decisions
    # ------------------------------------------------------------------
    def risk_decisions(self, decisions):
        judged = [
            decision for decision in decisions
            if str(decision.get("verdict", "")).upper() in {"APPROVED", "REJECTED"}
        ]
        if len(judged) < self.MIN_RISK_DECISIONS:
            return self._domain_not_evaluated(
                "risk_decisions",
                f"At least {self.MIN_RISK_DECISIONS} risk decisions with a clear "
                "verdict are required to assess the risk gate.",
            )

        rejected = [
            decision for decision in judged
            if str(decision.get("verdict", "")).upper() == "REJECTED"
        ]
        rejection_rate = self.math._rate(len(rejected), len(judged))
        reasons = self._risk_reason_counts(rejected)
        symbols = self._risk_symbol_counts(rejected)
        top_reason = reasons[0] if reasons else None
        confidence = self._confidence(
            len(judged), rejection_rate - 50.0, 50.0, self.MIN_RISK_DECISIONS
        )
        finding = self._finding(
            finding_id="risk-rejection-rate",
            category="risk_decisions",
            title=(
                f"The risk gate rejected {rejection_rate}% of evaluated orders"
            ),
            confidence=confidence,
            sample_size=len(judged),
            statistics={
                "evaluated": len(judged),
                "rejected": len(rejected),
                "approved": len(judged) - len(rejected),
                "rejection_rate": rejection_rate,
                "top_reason": top_reason,
                "reason_counts": reasons,
                "most_rejected_symbols": symbols,
            },
            explanation=(
                f"{len(rejected)} of {len(judged)} evaluated orders were rejected "
                f"({rejection_rate}%)"
                + (
                    f"; the most common reason was \"{top_reason['reason']}\" "
                    f"({top_reason['count']}x)."
                    if top_reason else "."
                )
            ),
            recommendation=(
                "Research whether the risk limits are well-calibrated for the "
                "rejected setups; study the top rejection reasons in future work. "
                "Research only; risk limits are never changed here."
            ),
        )
        return self._domain([finding])

    def _risk_reason_counts(self, rejected):
        counts = {}
        for decision in rejected:
            for reason in self._risk_reasons(decision):
                counts[reason] = counts.get(reason, 0) + 1
        return [
            {"reason": reason, "count": count}
            for reason, count in sorted(
                counts.items(), key=lambda item: (-item[1], item[0])
            )
        ]

    def _risk_reasons(self, decision):
        checks = decision.get("checks")
        reasons = []
        candidates = []
        if isinstance(checks, dict):
            candidates = checks.get("rejections") or checks.get("reasons") or []
            if not candidates:
                for value in checks.values():
                    if isinstance(value, dict) and value.get("passed") is False:
                        candidates.append(value)
        elif isinstance(checks, list):
            candidates = checks
        for item in candidates:
            if isinstance(item, dict):
                reason = item.get("reason") or item.get("message") or item.get("name")
            else:
                reason = item
            if reason:
                reasons.append(str(reason))
        return reasons

    def _risk_symbol_counts(self, rejected):
        counts = {}
        for decision in rejected:
            symbol = decision.get("symbol")
            if symbol:
                counts[symbol] = counts.get(symbol, 0) + 1
        return [
            {"symbol": symbol, "count": count}
            for symbol, count in sorted(
                counts.items(), key=lambda item: (-item[1], item[0])
            )
        ]

    # ------------------------------------------------------------------
    # Domain 8 - drawdowns
    # ------------------------------------------------------------------
    def drawdowns(self, history):
        ordered = self._ordered_history(history)
        values = [
            self._number(row.get("portfolio_value"))
            for row in ordered
            if row.get("portfolio_value") is not None
        ]
        if len(values) < self.MIN_DRAWDOWN_POINTS:
            return self._domain_not_evaluated(
                "drawdowns",
                f"At least {self.MIN_DRAWDOWN_POINTS} portfolio-history snapshots "
                "are required to measure drawdowns.",
            )

        max_drawdown = self.math._max_drawdown(values)
        peak = values[0]
        for value in values:
            peak = max(peak, value)
        current_drawdown = round(
            (values[-1] - peak) / peak * 100, 4
        ) if peak else 0.0
        confidence = self._confidence(
            len(values), max_drawdown, 20.0, self.MIN_DRAWDOWN_POINTS
        )
        finding = self._finding(
            finding_id="drawdown-depth",
            category="drawdowns",
            title=f"Paper equity saw a {abs(round(max_drawdown, 2))}% max drawdown",
            confidence=confidence,
            sample_size=len(values),
            statistics={
                "max_drawdown_percent": max_drawdown,
                "current_drawdown_percent": current_drawdown,
                "peak_value": round(peak, 2),
                "latest_value": round(values[-1], 2),
                "snapshots": len(values),
            },
            explanation=(
                f"Across {len(values)} snapshots the deepest peak-to-trough "
                f"drawdown was {max_drawdown}%; the fund is currently "
                f"{current_drawdown}% from its {round(peak, 2)} peak."
            ),
            recommendation=(
                "Research what preceded the deepest drawdown and whether an "
                "earlier risk-off research signal was available. Research only; "
                "no trading behavior changes."
            ),
        )
        return self._domain([finding])

    # ------------------------------------------------------------------
    # Domain 9 - winning vs losing trades
    # ------------------------------------------------------------------
    def trade_quality(self, closed):
        if len(closed) < self.MIN_CLOSED_TRADES:
            return self._domain_not_evaluated(
                "trade_quality",
                f"At least {self.MIN_CLOSED_TRADES} closed trades are required to "
                "compare winners with losers.",
            )

        wins = [trade for trade in closed if self._pl(trade) > 0]
        losses = [trade for trade in closed if self._pl(trade) < 0]
        if not wins or not losses:
            return self._domain_not_evaluated(
                "trade_quality",
                "Both winning and losing closed trades are required to compare "
                "what separates them.",
            )

        win_rate = self.math._rate(len(wins), len(closed))
        expectancy = self.math._average([self._pl(trade) for trade in closed])
        win_hold = self._avg_holding(wins)
        loss_hold = self._avg_holding(losses)
        hold_edge = (
            round(win_hold - loss_hold, 4)
            if win_hold is not None and loss_hold is not None
            else None
        )
        effect = abs(hold_edge) if hold_edge is not None else abs(win_rate - 50.0)
        norm = 10.0 if hold_edge is not None else 50.0
        confidence = self._confidence(
            len(closed), effect, norm, self.MIN_CLOSED_TRADES
        )
        if hold_edge is not None and hold_edge > 0:
            hold_phrase = (
                f"Winners are held longer ({win_hold}d) than losers ({loss_hold}d)"
            )
        elif hold_edge is not None and hold_edge < 0:
            hold_phrase = (
                f"Losers are held longer ({loss_hold}d) than winners ({win_hold}d)"
            )
        else:
            hold_phrase = "Winners and losers show no holding-period edge"
        finding = self._finding(
            finding_id="trade-quality-holding-edge",
            category="trade_quality",
            title=f"{hold_phrase}",
            confidence=confidence,
            sample_size=len(closed),
            statistics={
                "closed_trades": len(closed),
                "wins": len(wins),
                "losses": len(losses),
                "win_rate": win_rate,
                "expectancy": expectancy,
                "average_winner": self.math._average([self._pl(t) for t in wins]),
                "average_loser": self.math._average([self._pl(t) for t in losses]),
                "winner_avg_holding": win_hold,
                "loser_avg_holding": loss_hold,
                "holding_edge_days": hold_edge,
            },
            explanation=(
                f"Win rate is {win_rate}% over {len(closed)} closed trades with "
                f"expectancy {expectancy} per trade. {hold_phrase}."
            ),
            recommendation=(
                "Research whether holding-period discipline explains the win/loss "
                "gap and whether exits are premature or late. Research only."
            ),
        )
        return self._domain([finding])

    # ------------------------------------------------------------------
    # Finding + confidence primitives
    # ------------------------------------------------------------------
    def _finding(
        self,
        finding_id,
        category,
        title,
        confidence,
        sample_size,
        statistics,
        explanation,
        recommendation,
    ):
        return {
            "id": finding_id,
            "category": category,
            "title": title,
            "status": "EVALUATED",
            "confidence": confidence,
            "confidence_label": self._confidence_label(confidence),
            "sample_size": sample_size,
            "statistics": statistics,
            "explanation": explanation,
            "recommendation": recommendation,
            "policy": self._finding_policy(),
        }

    def _confidence(self, sample_size, effect, effect_norm, min_samples):
        if sample_size < min_samples:
            return 0.0
        sample_component = min(1.0, sample_size / self.CONFIDENCE_SATURATION)
        effect_component = (
            min(1.0, abs(effect) / effect_norm) if effect_norm else 0.0
        )
        return round(
            self.SAMPLE_WEIGHT * sample_component
            + self.EFFECT_WEIGHT * effect_component,
            4,
        )

    def _confidence_label(self, confidence):
        if confidence < self.LOW_BAND:
            return "Low"
        if confidence < self.HIGH_BAND:
            return "Moderate"
        return "High"

    def _rank(self, findings):
        return sorted(
            findings,
            key=lambda item: (-item["confidence"], item["category"], item["id"]),
        )

    def _opportunity(self, finding):
        return {
            "id": finding["id"],
            "category": finding["category"],
            "recommendation": finding["recommendation"],
            "confidence": finding["confidence"],
            "confidence_label": finding["confidence_label"],
        }

    def _headline(self, findings, not_evaluated):
        if findings:
            top = findings[0]
            return (
                f"{len(findings)} research opportunit"
                f"{'y' if len(findings) == 1 else 'ies'} found; highest "
                f"confidence: {top['title']} ({top['confidence_label']})."
            )
        return (
            "No research opportunities yet: "
            f"{len(not_evaluated)} domains lack sufficient evidence."
        )

    # ------------------------------------------------------------------
    # Grouping helpers
    # ------------------------------------------------------------------
    def _group_pl(self, closed, keys):
        groups = {}
        for trade in closed:
            key = self._first(self._snapshot(trade), keys)
            if not key:
                continue
            key = str(key)
            entry = groups.setdefault(key, {"key": key, "pls": []})
            entry["pls"].append(self._pl(trade))
        rows = []
        for entry in groups.values():
            pls = entry["pls"]
            wins = len([value for value in pls if value > 0])
            rows.append({
                "key": entry["key"],
                "count": len(pls),
                "total_pl": round(sum(pls), 4),
                "average_pl": round(sum(pls) / len(pls), 4),
                "win_rate": self.math._rate(wins, len(pls)),
            })
        return rows

    def _qualified_groups(self, rows):
        return [row for row in rows if row["count"] >= self.MIN_TRADES_PER_GROUP]

    def _group_digest(self, row):
        return {
            "key": row["key"],
            "count": row["count"],
            "total_pl": row["total_pl"],
            "average_pl": row["average_pl"],
            "win_rate": row["win_rate"],
        }

    def _member_digest(self, row):
        return {
            "member_id": row["key"],
            "member_name": row["member_name"],
            "evaluated": row["evaluated"],
            "correct": row["correct"],
            "accuracy": row["accuracy"],
        }

    def _pl_norm(self, best, worst):
        return max(abs(best["average_pl"]), abs(worst["average_pl"]), 1.0)

    def _avg_holding(self, trades):
        holds = [
            self._number(trade.get("holding_period"))
            for trade in trades
            if trade.get("holding_period") is not None
        ]
        if not holds:
            return None
        return round(sum(holds) / len(holds), 4)

    # ------------------------------------------------------------------
    # Committee vote parsing
    # ------------------------------------------------------------------
    def _committee_votes(self, trade):
        snapshot = self._snapshot(trade)
        raw = None
        for key in self.COMMITTEE_VOTE_KEYS:
            candidate = snapshot.get(key)
            if isinstance(candidate, list) and candidate:
                raw = candidate
                break
        if raw is None:
            committee = snapshot.get("committee")
            if isinstance(committee, dict):
                candidate = committee.get("votes")
                if isinstance(candidate, list) and candidate:
                    raw = candidate
        if not raw:
            return []

        votes = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            member_id = (
                item.get("member_id")
                or item.get("strategy_id")
                or item.get("member_name")
            )
            if member_id is None:
                continue
            votes.append({
                "member_id": str(member_id),
                "member_name": str(
                    item.get("member_name") or item.get("name") or member_id
                ),
                "action": str(item.get("action", "")).strip().upper(),
            })
        return votes

    def _vote_correct(self, action, result):
        if action in self.BULLISH_ACTIONS:
            return result == "WIN"
        if action in self.BEARISH_ACTIONS:
            return result == "LOSS"
        return None

    # ------------------------------------------------------------------
    # Domain wrappers
    # ------------------------------------------------------------------
    def _domain(self, findings):
        return {"status": "EVALUATED", "findings": findings}

    def _domain_not_evaluated(self, domain, reason):
        return {"status": "NOT_EVALUATED", "reason": reason, "findings": []}

    # ------------------------------------------------------------------
    # Trade helpers
    # ------------------------------------------------------------------
    def _closed(self, trades):
        return [
            trade for trade in (trades or [])
            if trade.get("exit_price") is not None
        ]

    def _snapshot(self, trade):
        snapshot = trade.get("recommendation_snapshot")
        return snapshot if isinstance(snapshot, dict) else {}

    def _trade_result(self, trade):
        pl = self._pl(trade)
        if pl > 0:
            return "WIN"
        if pl < 0:
            return "LOSS"
        return None

    def _pl(self, trade):
        return self._number(trade.get("profit_loss"))

    def _first(self, snapshot, keys):
        for key in keys:
            value = snapshot.get(key)
            if value:
                return value
        return None

    def _sort_key(self, trade):
        return (
            self._short_date(trade.get("exit_date")),
            str(trade.get("trade_id", "")),
        )

    def _ordered_history(self, history):
        return sorted(
            history or [],
            key=lambda item: (self._short_date(item.get("date")), item.get("id", 0)),
        )

    def _ordered_reports(self, reports):
        return sorted(
            reports or [],
            key=lambda item: (self._short_date(item.get("date")), item.get("id", 0)),
        )

    def _generated_at(self, history, closed):
        ordered = self._ordered_history(history)
        if ordered:
            return self._short_date(ordered[-1].get("date"))
        if closed:
            return max(self._short_date(trade.get("exit_date")) for trade in closed)
        return ""

    def _short_date(self, value):
        return str(value or "")[:10]

    def _number(self, value):
        if value is None:
            return 0
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0

    # ------------------------------------------------------------------
    # Data loading (repository reads only; no demo fabrication)
    # ------------------------------------------------------------------
    def _load(self, trades, history, risk_decisions, construction_reports, limit):
        if trades is None:
            from database.repository import get_paper_trades

            trades = get_paper_trades(limit=limit)
            # Live paper-fund fills are evidence too: closed FIFO round-trips
            # derived from persisted simulated orders (real accounting, never
            # fabricated) join the replay trades so the engine learns from
            # what the autonomous loop actually produced.
            trades = list(trades or []) + self._live_fund_round_trips(limit)
        if history is None:
            from database.repository import get_paper_portfolio_history

            # Prefer the live paper fund's own equity curve when it exists;
            # mixing two different funds' values would corrupt drawdown math.
            history = self._live_fund_history(limit)
            if not history:
                history = get_paper_portfolio_history(limit=limit)
        if risk_decisions is None:
            from database.repository import get_recent_risk_decisions

            risk_decisions = get_recent_risk_decisions(limit=limit)
        if construction_reports is None:
            from database.repository import get_portfolio_construction_reports

            construction_reports = get_portfolio_construction_reports(limit=limit)
        return {
            "trades": trades or [],
            "history": history or [],
            "risk_decisions": risk_decisions or [],
            "construction_reports": construction_reports or [],
        }

    def _live_fund_round_trips(self, limit):
        """Deterministic FIFO round-trips from persisted live paper-fund fills.

        Real accounting over stored simulated orders only: BUY fills open
        lots, SELL fills close them first-in-first-out, and only matched
        quantity becomes a closed trade. Open lots produce nothing — no
        fabrication, no estimation.
        """
        try:
            from database.repository import get_paper_fund_orders

            orders = get_paper_fund_orders(limit=limit)
        except Exception:
            return []

        fills = [
            order
            for order in reversed(orders or [])  # reader returns newest first
            if str(order.get("status", "")).upper() in self.LIVE_FUND_FILL_STATUSES
            and order.get("fill_price") is not None
        ]

        open_lots = {}
        trades = []
        for order in fills:
            ticker = order.get("ticker")
            side = str(order.get("side", "")).upper()
            quantity = self._number(order.get("quantity"))
            price = self._number(order.get("fill_price"))
            at = order.get("filled_at") or order.get("created_at")
            if not ticker or quantity <= 0:
                continue

            if side == "BUY":
                open_lots.setdefault(ticker, []).append(
                    {"quantity": quantity, "price": price, "at": at}
                )
                continue
            if side != "SELL":
                continue

            lots = open_lots.get(ticker, [])
            remaining = quantity
            while remaining > 0 and lots:
                lot = lots[0]
                matched = min(remaining, lot["quantity"])
                trades.append({
                    "trade_id": f"live-fund-{ticker}-{len(trades) + 1}",
                    "ticker": ticker,
                    "entry_date": lot["at"],
                    "exit_date": at,
                    "entry_price": lot["price"],
                    "exit_price": price,
                    "quantity": matched,
                    "profit_loss": round((price - lot["price"]) * matched, 2),
                    "holding_period": self._holding_days(lot["at"], at),
                    "recommendation_snapshot": {"strategy": "live_paper_fund"},
                })
                lot["quantity"] -= matched
                remaining -= matched
                if lot["quantity"] <= 0:
                    lots.pop(0)

        return trades

    def _live_fund_history(self, limit):
        """Live paper-fund equity curve mapped to portfolio-history rows."""
        try:
            from database.repository import get_paper_fund_snapshots

            snapshots = get_paper_fund_snapshots(limit=limit)
        except Exception:
            return []

        ordered = list(reversed(snapshots or []))  # reader returns newest first
        return [
            {
                "id": index,
                "date": snapshot.get("as_of"),
                "portfolio_value": snapshot.get("portfolio_value"),
            }
            for index, snapshot in enumerate(ordered, start=1)
            if snapshot.get("portfolio_value") is not None
        ]

    def _holding_days(self, entry_at, exit_at):
        from datetime import datetime

        try:
            start = datetime.fromisoformat(str(entry_at))
            end = datetime.fromisoformat(str(exit_at))
        except (TypeError, ValueError):
            return None
        return round(max(0.0, (end - start).total_seconds()) / 86400, 4)

    # ------------------------------------------------------------------
    # Policy
    # ------------------------------------------------------------------
    def policy(self):
        return {
            "read_only": True,
            "research_only": True,
            "deterministic": True,
            "uses_llm": False,
            "uses_randomness": False,
            "changes_strategies": False,
            "changes_weights": False,
            "changes_committee": False,
            "changes_trading_behavior": False,
            "changes_risk_limits": False,
            "real_money": False,
        }

    def _finding_policy(self):
        return {
            "research_only": True,
            "does_not_change_live_behavior": True,
            "deterministic": True,
        }
