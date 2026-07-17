from engines.paper_trading_engine import PaperTradingEngine


class PerformanceLabEngine:
    """Deterministic, read-only performance attribution for the paper fund.

    The Performance Lab explains *why* the paper fund makes or loses money by
    composing four attribution domains from persisted paper-trading evidence:

    * Portfolio analytics - equity curve, alpha vs benchmark, beta, drawdown,
      Sharpe, Sortino, Calmar, and volatility.
    * Trade analytics - win rate, average winner/loser, profit factor,
      expectancy, holding period, and the best/worst trade.
    * Committee attribution - which committee members and strategies voted
      correctly, plus rolling committee accuracy over time.
    * Research attribution - which research signals (technical, fundamental,
      forecast, news) separated winning trades from losing trades.

    The engine reads persisted paper evidence only. It never writes database
    rows and never changes recommendations, trades, risk limits, orders, broker
    state, or portfolio construction. Every section returns ``NOT_EVALUATED``
    with a human-readable reason when the stored evidence is insufficient, and
    no metric is ever fabricated. All arithmetic is deterministic: identical
    inputs always produce identical output.
    """

    DEFAULT_LIMIT = 200

    # Minimum paired samples before a research signal or beta is judged.
    MIN_SIGNAL_SAMPLES = 3
    MIN_RETURN_SAMPLES = 2

    # Rolling committee-accuracy window (trades).
    ROLLING_WINDOW = 5

    BENCHMARK = "S&P 500"

    # Recommendation-snapshot fields carrying committee votes, in priority
    # order. Each entry is a list of per-member vote dicts.
    COMMITTEE_VOTE_KEYS = ("committee_members", "committee_votes")

    # Research signal field -> human label. Order is stable for output.
    RESEARCH_SIGNALS = (
        ("technical_score", "Technical"),
        ("fundamental_score", "Fundamental"),
        ("forecast_score", "Forecast"),
        ("news_confidence", "News"),
    )

    # Vote actions grouped by directional stance. Neutral/unknown actions are
    # excluded from scoring rather than guessed.
    BULLISH_ACTIONS = {"BUY", "STRONG BUY", "ADD", "ACCUMULATE", "OVERWEIGHT"}
    BEARISH_ACTIONS = {"SELL", "AVOID", "REDUCE", "TRIM", "EXIT", "UNDERWEIGHT"}

    def __init__(self, paper_engine=None):
        self.math = paper_engine or PaperTradingEngine()

    # ------------------------------------------------------------------
    # Assembly
    # ------------------------------------------------------------------
    def generate(
        self,
        history=None,
        trades=None,
        performance_reports=None,
        benchmark_returns=None,
        limit=None,
    ):
        limit = limit or self.DEFAULT_LIMIT
        data = self._load(history, trades, performance_reports, limit)
        history = data["history"]
        trades = data["trades"]
        performance_reports = data["performance_reports"]

        portfolio = self.portfolio_analytics(
            history, performance_reports, benchmark_returns
        )
        trade = self.trade_analytics(trades)
        committee = self.committee_attribution(trades)
        research = self.research_attribution(trades)

        return {
            "generated_at": self._generated_at(history, performance_reports),
            "demo_data": data["demo"],
            "portfolio_analytics": portfolio,
            "trade_analytics": trade,
            "committee_attribution": committee,
            "research_attribution": research,
            "not_evaluated": self._not_evaluated_summary(
                portfolio, trade, committee, research
            ),
            "source_counts": {
                "portfolio_history": len(history),
                "closed_trades": len(self._closed(trades)),
                "total_trades": len(trades),
                "performance_reports": len(performance_reports),
            },
            "policy": self.policy(),
        }

    # ------------------------------------------------------------------
    # Domain 1 - Portfolio analytics
    # ------------------------------------------------------------------
    def portfolio_analytics(self, history, performance_reports, benchmark_returns):
        ordered = self._ordered_history(history)
        points = [
            {
                "date": self._short_date(item.get("date")),
                "portfolio_value": self._number(item.get("portfolio_value")),
                "daily_return": self._number(item.get("daily_return")),
                "cumulative_return": self._number(item.get("total_return")),
            }
            for item in ordered
        ]
        equity_curve = {
            "points": points,
            "sample_size": len(points),
            "start_value": points[0]["portfolio_value"] if points else None,
            "latest_value": points[-1]["portfolio_value"] if points else None,
            "cumulative_return": points[-1]["cumulative_return"] if points else 0,
        }

        if len(ordered) < self.MIN_RETURN_SAMPLES:
            return {
                "status": "NOT_EVALUATED",
                "reason": (
                    "At least two portfolio-history snapshots are required to "
                    "compute return-based analytics."
                ),
                "equity_curve": equity_curve,
                "risk_adjusted": self._not_evaluated(
                    "Return-based risk metrics need at least two snapshots."
                ),
                "benchmark": self._not_evaluated(
                    "Benchmark comparison needs at least two snapshots."
                ),
            }

        values = [point["portfolio_value"] for point in points]
        daily_returns = [point["daily_return"] for point in points]
        cumulative_return = equity_curve["cumulative_return"]
        max_drawdown = self.math._max_drawdown(values)
        volatility = self.math._standard_deviation(daily_returns)

        risk_adjusted = {
            "status": "EVALUATED",
            "sharpe": self.math._sharpe(daily_returns),
            "sortino": self.math._sortino(daily_returns),
            "calmar": self._calmar(cumulative_return, max_drawdown),
            "volatility": volatility,
            "max_drawdown": max_drawdown,
            "best_day": max(daily_returns),
            "worst_day": min(daily_returns),
            "sample_size": len(daily_returns),
        }

        return {
            "status": "EVALUATED",
            "equity_curve": equity_curve,
            "risk_adjusted": risk_adjusted,
            "benchmark": self._benchmark_analytics(
                performance_reports,
                cumulative_return,
                daily_returns,
                benchmark_returns,
                history,
            ),
        }

    def _benchmark_analytics(
        self,
        performance_reports,
        cumulative_return,
        daily_returns,
        benchmark_returns,
        history,
    ):
        alpha = self._benchmark_alpha(performance_reports, cumulative_return)
        beta = self._beta(daily_returns, benchmark_returns, history)
        if alpha is None and beta["status"] != "EVALUATED":
            return self._not_evaluated(
                "No stored benchmark return series is available for alpha or "
                "beta; benchmark attribution is not fabricated."
            )
        return {
            "status": "EVALUATED",
            "benchmark": self.BENCHMARK,
            "paper_return": cumulative_return,
            "alpha": (
                alpha["value"] if alpha
                else None
            ),
            "benchmark_return": (
                alpha["benchmark_return"] if alpha else None
            ),
            "alpha_status": "EVALUATED" if alpha else "NOT_EVALUATED",
            "alpha_reason": (
                None if alpha
                else "No stored benchmark comparison to compute alpha."
            ),
            "beta": beta,
        }

    def _benchmark_alpha(self, performance_reports, cumulative_return):
        performances = [
            report.get("performance", report)
            for report in (performance_reports or [])
        ]
        for performance in performances:
            for item in performance.get("benchmark_comparison", []):
                if item.get("benchmark") == self.BENCHMARK:
                    benchmark_return = self._number(item.get("benchmark_return"))
                    if item.get("alpha") is not None:
                        alpha_value = self._number(item.get("alpha"))
                    else:
                        alpha_value = round(cumulative_return - benchmark_return, 4)
                    return {
                        "value": alpha_value,
                        "benchmark_return": benchmark_return,
                    }
        return None

    def _beta(self, daily_returns, benchmark_returns, history):
        # A benchmark daily-return series aligned to the portfolio daily
        # returns is required. It may be supplied explicitly or carried on the
        # history rows; otherwise beta is NOT_EVALUATED rather than guessed.
        series = benchmark_returns
        if series is None:
            series = [
                item.get("benchmark_return")
                for item in self._ordered_history(history)
            ]
            if all(value is None for value in series):
                series = None

        if series is None:
            return self._not_evaluated(
                "No aligned benchmark daily-return series is stored, so beta "
                "cannot be computed without fabricating market returns."
            )
        if len(series) != len(daily_returns):
            return self._not_evaluated(
                "The benchmark daily-return series does not align with the "
                "portfolio history length, so beta is not computed."
            )

        pairs = [
            (self._number(port), self._number(bench))
            for port, bench in zip(daily_returns, series)
            if bench is not None
        ]
        if len(pairs) < self.MIN_RETURN_SAMPLES:
            return self._not_evaluated(
                "At least two aligned benchmark observations are required to "
                "compute beta."
            )

        bench_values = [bench for _, bench in pairs]
        bench_mean = sum(bench_values) / len(bench_values)
        variance = sum((bench - bench_mean) ** 2 for bench in bench_values)
        if variance == 0:
            return self._not_evaluated(
                "Benchmark returns have zero variance, so beta is undefined."
            )
        port_values = [port for port, _ in pairs]
        port_mean = sum(port_values) / len(port_values)
        covariance = sum(
            (port - port_mean) * (bench - bench_mean)
            for port, bench in pairs
        )
        return {
            "status": "EVALUATED",
            "value": round(covariance / variance, 4),
            "sample_size": len(pairs),
        }

    # ------------------------------------------------------------------
    # Domain 2 - Trade analytics
    # ------------------------------------------------------------------
    def trade_analytics(self, trades):
        closed = self._closed(trades)
        if not closed:
            return self._not_evaluated(
                "No closed paper trades are available; trade analytics need at "
                "least one exited position."
            )

        wins = [t for t in closed if self._pl(t) > 0]
        losses = [t for t in closed if self._pl(t) < 0]
        breakeven = [t for t in closed if self._pl(t) == 0]
        gross_profit = round(sum(self._pl(t) for t in wins), 4)
        gross_loss = round(abs(sum(self._pl(t) for t in losses)), 4)

        holding_periods = [
            self._number(t.get("holding_period"))
            for t in closed
            if t.get("holding_period") is not None
        ]

        return {
            "status": "EVALUATED",
            "closed_trades": len(closed),
            "wins": len(wins),
            "losses": len(losses),
            "breakeven": len(breakeven),
            "win_rate": self.math._rate(len(wins), len(closed)),
            "average_winner": self.math._average(
                [self._pl(t) for t in wins]
            ) if wins else None,
            "average_loser": self.math._average(
                [self._pl(t) for t in losses]
            ) if losses else None,
            "gross_profit": gross_profit,
            "gross_loss": gross_loss,
            "profit_factor": self._profit_factor(gross_profit, gross_loss),
            "expectancy": self.math._average([self._pl(t) for t in closed]),
            "payoff_ratio": self._payoff_ratio(wins, losses),
            "average_holding_period": (
                self.math._average(holding_periods)
                if holding_periods else None
            ),
            "holding_period_status": (
                "EVALUATED" if holding_periods else "NOT_EVALUATED"
            ),
            "best_trade": self._trade_digest(
                max(closed, key=lambda t: (self._pl(t), t.get("ticker", "")))
            ),
            "worst_trade": self._trade_digest(
                min(closed, key=lambda t: (self._pl(t), t.get("ticker", "")))
            ),
        }

    def _profit_factor(self, gross_profit, gross_loss):
        if gross_loss <= 0:
            return {
                "status": "NOT_EVALUATED",
                "reason": (
                    "No losing trades are recorded, so profit factor is "
                    "undefined (division by zero gross loss)."
                ),
            }
        return {"status": "EVALUATED", "value": round(gross_profit / gross_loss, 4)}

    def _payoff_ratio(self, wins, losses):
        if not wins or not losses:
            return {
                "status": "NOT_EVALUATED",
                "reason": "Both winning and losing trades are required.",
            }
        avg_win = self.math._average([self._pl(t) for t in wins])
        avg_loss = abs(self.math._average([self._pl(t) for t in losses]))
        if avg_loss == 0:
            return {
                "status": "NOT_EVALUATED",
                "reason": "Average loss is zero, so payoff ratio is undefined.",
            }
        return {"status": "EVALUATED", "value": round(avg_win / avg_loss, 4)}

    # ------------------------------------------------------------------
    # Domain 3 - Committee attribution
    # ------------------------------------------------------------------
    def committee_attribution(self, trades):
        scored = []  # (trade, ordered list of {member_id, member_name, action})
        for trade in self._closed(trades):
            votes = self._committee_votes(trade)
            if votes:
                scored.append((trade, votes))

        if not scored:
            return self._not_evaluated(
                "No closed trade carries committee-member votes, so member and "
                "strategy accuracy cannot be attributed."
            )

        members = {}
        for trade, votes in scored:
            result = self._trade_result(trade)
            if result is None:
                continue
            for vote in votes:
                correct = self._vote_correct(vote["action"], result)
                if correct is None:
                    continue
                key = vote["member_id"]
                entry = members.setdefault(key, {
                    "member_id": key,
                    "member_name": vote["member_name"],
                    "evaluated": 0,
                    "correct": 0,
                })
                entry["evaluated"] += 1
                entry["correct"] += 1 if correct else 0

        member_rows = [
            {
                **entry,
                "accuracy": self.math._rate(entry["correct"], entry["evaluated"]),
            }
            for entry in members.values()
            if entry["evaluated"] > 0
        ]
        member_rows.sort(
            key=lambda row: (-row["accuracy"], -row["evaluated"], row["member_id"])
        )

        if not member_rows:
            return self._not_evaluated(
                "Committee votes exist but none had a directional stance that "
                "could be judged against a win or loss."
            )

        return {
            "status": "EVALUATED",
            "trades_with_votes": len(scored),
            "members": member_rows,
            "strategies": member_rows,
            "most_accurate": member_rows[0],
            "least_accurate": member_rows[-1],
            "rolling_accuracy": self._rolling_committee_accuracy(scored),
            "note": (
                "A bullish vote is scored correct on a winning trade and a "
                "bearish/avoid vote is scored correct on a losing trade; "
                "neutral or unknown votes are excluded, never guessed."
            ),
        }

    def _rolling_committee_accuracy(self, scored):
        per_trade = []
        for trade, votes in sorted(
            scored, key=lambda pair: self._sort_key(pair[0])
        ):
            result = self._trade_result(trade)
            if result is None:
                continue
            judged = [
                self._vote_correct(vote["action"], result)
                for vote in votes
            ]
            judged = [value for value in judged if value is not None]
            if not judged:
                continue
            per_trade.append({
                "date": self._short_date(trade.get("exit_date")),
                "ticker": trade.get("ticker"),
                "trade_accuracy": self.math._rate(
                    sum(1 for value in judged if value), len(judged)
                ),
                "votes_judged": len(judged),
            })

        if not per_trade:
            return self._not_evaluated(
                "No committee vote could be judged against trade outcomes."
            )

        points = []
        window = self.ROLLING_WINDOW
        for index, row in enumerate(per_trade):
            window_rows = per_trade[max(0, index - window + 1): index + 1]
            accuracies = [item["trade_accuracy"] for item in window_rows]
            points.append({
                **row,
                "rolling_accuracy": round(sum(accuracies) / len(accuracies), 2),
                "window": len(window_rows),
            })
        return {"status": "EVALUATED", "window": window, "points": points}

    def _committee_votes(self, trade):
        snapshot = trade.get("recommendation_snapshot") or {}
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
            action = str(item.get("action", "")).strip().upper()
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
                    item.get("member_name")
                    or item.get("name")
                    or member_id
                ),
                "action": action,
            })
        return votes

    def _vote_correct(self, action, result):
        if action in self.BULLISH_ACTIONS:
            return result == "WIN"
        if action in self.BEARISH_ACTIONS:
            return result == "LOSS"
        return None

    # ------------------------------------------------------------------
    # Domain 4 - Research attribution
    # ------------------------------------------------------------------
    def research_attribution(self, trades):
        closed = self._closed(trades)
        signals = []
        for field, label in self.RESEARCH_SIGNALS:
            signals.append(self._signal_attribution(closed, field, label))

        evaluated = [row for row in signals if row["status"] == "EVALUATED"]
        if not evaluated:
            return {
                "status": "NOT_EVALUATED",
                "reason": (
                    "No research signal had enough winning and losing trades "
                    "carrying that signal to measure predictiveness."
                ),
                "signals": signals,
                "most_predictive": None,
            }

        ranked = sorted(evaluated, key=lambda row: (-row["lift"], row["signal"]))
        return {
            "status": "EVALUATED",
            "signals": signals,
            "most_predictive": ranked[0],
            "note": (
                "A signal is predictive when its average value on winning "
                "trades exceeds its average on losing trades (positive lift)."
            ),
        }

    def _signal_attribution(self, closed, field, label):
        pairs = []
        for trade in closed:
            snapshot = trade.get("recommendation_snapshot") or {}
            score = snapshot.get(field)
            if score is None:
                continue
            pairs.append((self._number(score), self._pl(trade)))

        winners = [score for score, pl in pairs if pl > 0]
        losers = [score for score, pl in pairs if pl < 0]

        if (
            len(pairs) < self.MIN_SIGNAL_SAMPLES
            or not winners
            or not losers
        ):
            return {
                "signal": label,
                "field": field,
                "status": "NOT_EVALUATED",
                "reason": (
                    "Needs at least "
                    f"{self.MIN_SIGNAL_SAMPLES} trades carrying this signal "
                    "with both a winner and a loser present."
                ),
                "sample_size": len(pairs),
                "winners": len(winners),
                "losers": len(losers),
            }

        winner_avg = round(sum(winners) / len(winners), 4)
        loser_avg = round(sum(losers) / len(losers), 4)
        lift = round(winner_avg - loser_avg, 4)
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
            "verdict": "PREDICTIVE" if lift > 0 else "NOT_PREDICTIVE",
        }

    # ------------------------------------------------------------------
    # Cross-cutting
    # ------------------------------------------------------------------
    def _not_evaluated_summary(self, portfolio, trade, committee, research):
        areas = []
        for name, section in (
            ("portfolio_analytics", portfolio),
            ("trade_analytics", trade),
            ("committee_attribution", committee),
            ("research_attribution", research),
        ):
            if section.get("status") != "EVALUATED":
                areas.append({
                    "area": name,
                    "reason": section.get("reason", "Insufficient data."),
                })
        return areas

    def policy(self):
        return {
            "read_only": True,
            "descriptive_only": True,
            "deterministic": True,
            "paper_only": True,
            "broker_integration": False,
            "real_money": False,
            "does_not_modify_recommendations": True,
            "does_not_modify_trades": True,
            "does_not_modify_risk_limits": True,
            "does_not_place_orders": True,
        }

    # ------------------------------------------------------------------
    # Data loading (repository with deterministic demo fallback)
    # ------------------------------------------------------------------
    def _load(self, history, trades, performance_reports, limit):
        demo = False
        if history is None:
            from database.repository import (
                get_demo_paper_portfolio_history,
                get_paper_portfolio_history,
            )

            history = get_paper_portfolio_history(limit=limit)
            if not history:
                history = get_demo_paper_portfolio_history(limit=limit)
                demo = True
        if trades is None:
            from database.repository import (
                get_demo_paper_trades,
                get_paper_trades,
            )

            trades = get_paper_trades(limit=limit)
            if not trades:
                trades = get_demo_paper_trades(limit=limit)
        if performance_reports is None:
            from database.repository import (
                get_demo_paper_performance_reports,
                get_paper_performance_reports,
            )

            performance_reports = get_paper_performance_reports(limit=limit)
            if not performance_reports:
                performance_reports = get_demo_paper_performance_reports(
                    limit=limit
                )

        return {
            "history": history or [],
            "trades": trades or [],
            "performance_reports": performance_reports or [],
            "demo": demo,
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _closed(self, trades):
        return [
            trade for trade in (trades or [])
            if trade.get("exit_price") is not None
        ]

    def _trade_result(self, trade):
        pl = self._pl(trade)
        if pl > 0:
            return "WIN"
        if pl < 0:
            return "LOSS"
        return None

    def _pl(self, trade):
        return self._number(trade.get("profit_loss"))

    def _trade_digest(self, trade):
        return {
            "ticker": trade.get("ticker"),
            "action": trade.get("action"),
            "profit_loss": round(self._pl(trade), 4),
            "holding_period": trade.get("holding_period"),
            "entry_date": self._short_date(trade.get("entry_date")),
            "exit_date": self._short_date(trade.get("exit_date")),
            "result": self._pl_result(self._pl(trade)),
        }

    def _calmar(self, cumulative_return, max_drawdown):
        if not max_drawdown:
            return {
                "status": "NOT_EVALUATED",
                "reason": (
                    "Max drawdown is zero, so Calmar (return over drawdown) is "
                    "undefined."
                ),
            }
        return {
            "status": "EVALUATED",
            "value": round(cumulative_return / abs(max_drawdown), 4),
        }

    def _ordered_history(self, history):
        return sorted(
            history or [],
            key=lambda item: (self._short_date(item.get("date")), item.get("id", 0)),
        )

    def _generated_at(self, history, performance_reports):
        ordered = self._ordered_history(history)
        if ordered:
            return self._short_date(ordered[-1].get("date"))
        return ""

    def _sort_key(self, trade):
        return (
            self._short_date(trade.get("exit_date")),
            str(trade.get("trade_id", "")),
        )

    def _pl_result(self, value):
        if value > 0:
            return "WIN"
        if value < 0:
            return "LOSS"
        return "FLAT"

    def _not_evaluated(self, reason):
        return {"status": "NOT_EVALUATED", "reason": reason}

    def _short_date(self, value):
        return str(value or "")[:10]

    def _number(self, value):
        if value is None:
            return 0
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0
