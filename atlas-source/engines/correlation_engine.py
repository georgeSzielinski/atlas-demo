import math
from datetime import datetime, timedelta

from engines.portfolio_intelligence_engine import PortfolioIntelligenceEngine
from engines.risk_management_engine import RiskManagementEngine


class CorrelationEngine:
    """Deterministic, read-only correlation analytics for the Live Paper Fund.

    The engine measures how the fund's current paper positions move together.
    It answers which holdings are correlated, which pairs are highly correlated,
    which clusters look like the same trade, whether the portfolio breaches the
    correlation limit, and which symbols still need more price history before
    they can be evaluated.

    It uses only real, validated, price-backed history. If the configured market
    data provider is mock, the history fetch falls back, no rows are returned, or
    too few observations exist, the relevant output is ``NOT_EVALUATED`` with a
    human-readable reason. Correlations are never fabricated. The engine reads
    persisted paper-fund evidence and market prices only; it never writes
    database rows and never modifies recommendations, trades, risk limits,
    orders, the scheduler, or broker state.

    The descriptive ``generate`` report never feeds the risk gate. The separate
    ``risk_matrix`` method exposes the same real, price-backed correlations to
    the risk gate as evidence in the nested ``{symbol: {peer: correlation}}``
    format ``RiskManagementEngine`` expects, still using real price history only
    and still never fabricating values (unavailable history is ``NOT_EVALUATED``
    with empty correlations).
    """

    DEFAULT_LIMIT = 200
    LOOKBACK_DAYS = 180
    MIN_OBSERVATIONS = 20
    MOCK_PROVIDERS = {"mock"}

    def __init__(self):
        self.intelligence = PortfolioIntelligenceEngine()
        # Read (never modify) the shared correlation limit so this engine and the
        # risk gate describe "highly correlated" the same way.
        self.max_correlation = float(
            RiskManagementEngine.DEFAULT_LIMITS["max_correlation"]
        )
        self.cluster_threshold = self.max_correlation

    # ------------------------------------------------------------------
    # Entry point
    # ------------------------------------------------------------------
    def generate(
        self,
        state=None,
        snapshots=None,
        price_history=None,
        limit=None,
        lookback_days=None,
        as_of=None,
    ):
        limit = limit or self.DEFAULT_LIMIT
        lookback_days = lookback_days or self.LOOKBACK_DAYS

        state, latest_snapshot, portfolio = self._load_portfolio(
            state, snapshots, limit
        )
        generated_at = self._generated_at(state, latest_snapshot)
        symbols = self._held_symbols(portfolio)

        if len(symbols) < 2:
            return self._not_evaluated(
                generated_at,
                symbols,
                lookback_days,
                reason=(
                    "At least two held paper-fund positions are required to "
                    "measure correlation."
                ),
                data_source=self._data_source(
                    provider=None,
                    price_backed=False,
                    fallback_used=False,
                    rows=0,
                    symbols=symbols,
                ),
            )

        resolved = self._resolve_price_history(
            symbols, latest_snapshot, state, lookback_days, price_history, as_of
        )
        if not resolved["price_backed"]:
            return self._not_evaluated(
                generated_at,
                symbols,
                lookback_days,
                reason=resolved["reason"],
                data_source=resolved["data_source"],
            )

        return self._evaluate(
            generated_at,
            symbols,
            lookback_days,
            resolved["rows"],
            resolved["data_source"],
        )

    # ------------------------------------------------------------------
    # Risk-gate evidence
    # ------------------------------------------------------------------
    def risk_matrix(
        self,
        symbols,
        state=None,
        snapshots=None,
        price_history=None,
        lookback_days=None,
        as_of=None,
    ):
        """Real, price-backed correlation evidence for the risk gate.

        Returns the nested ``{symbol: {peer: correlation}}`` format
        ``RiskManagementEngine`` consumes as ``market_data["correlations"]``,
        built over an explicit ``symbols`` universe (held positions plus
        candidate order symbols) so a not-yet-held BUY can still be evaluated
        against existing holdings.

        Only evaluated pairs are included, and the matrix is symmetric. If real
        price-backed history is unavailable (mock provider, fallback rows, no
        rows, or too few overlapping observations) the result is
        ``NOT_EVALUATED`` with empty correlations; values are never fabricated.
        """
        lookback_days = lookback_days or self.LOOKBACK_DAYS
        universe = self._normalize_symbols(symbols)
        state = state or {}
        latest_snapshot = (
            self.intelligence._latest_snapshot(snapshots)
            if snapshots is not None
            else None
        )

        if len(universe) < 2:
            return self._risk_matrix_not_evaluated(
                universe,
                "At least two symbols are required to measure correlation.",
                self._data_source(
                    provider=None,
                    price_backed=False,
                    fallback_used=False,
                    rows=0,
                    symbols=universe,
                ),
            )

        resolved = self._resolve_price_history(
            universe, latest_snapshot, state, lookback_days, price_history, as_of
        )
        if not resolved["price_backed"]:
            return self._risk_matrix_not_evaluated(
                universe, resolved["reason"], resolved["data_source"]
            )

        returns_by_symbol = self._returns_by_symbol(universe, resolved["rows"])
        evaluable = [
            symbol for symbol in universe
            if len(returns_by_symbol.get(symbol, {})) >= self.MIN_OBSERVATIONS
        ]
        pairs = (
            self._pairwise(evaluable, returns_by_symbol)
            if len(evaluable) >= 2 else []
        )
        evaluated_pairs = [pair for pair in pairs if pair["status"] == "EVALUATED"]

        correlations = {}
        for pair in evaluated_pairs:
            first, second = pair["symbols"]
            correlations.setdefault(first, {})[second] = pair["correlation"]
            correlations.setdefault(second, {})[first] = pair["correlation"]

        if not correlations:
            return self._risk_matrix_not_evaluated(
                universe,
                "No symbol pair had enough overlapping real price history to "
                "measure correlation.",
                resolved["data_source"],
            )

        fully_evaluated = (
            len(evaluable) == len(universe)
            and len(evaluated_pairs) == len(pairs)
        )
        return {
            "status": "EVALUATED" if fully_evaluated else "PARTIAL",
            "reason": (
                None if fully_evaluated
                else "Some symbols do not yet have enough overlapping real "
                "price history; only evaluated pairs are included."
            ),
            "correlations": correlations,
            "threshold": self.max_correlation,
            "symbols_requested": list(universe),
            "symbols_evaluated": sorted(evaluable),
            "pairs_evaluated": len(evaluated_pairs),
            "min_observations": self.MIN_OBSERVATIONS,
            "data_source": resolved["data_source"],
            "policy": self._risk_matrix_policy(),
        }

    def _risk_matrix_not_evaluated(self, universe, reason, data_source):
        return {
            "status": "NOT_EVALUATED",
            "reason": reason,
            "correlations": {},
            "threshold": self.max_correlation,
            "symbols_requested": list(universe),
            "symbols_evaluated": [],
            "pairs_evaluated": 0,
            "min_observations": self.MIN_OBSERVATIONS,
            "data_source": data_source,
            "policy": self._risk_matrix_policy(),
        }

    def _risk_matrix_policy(self):
        return {
            "read_only": True,
            "deterministic": True,
            "uses_real_price_history_only": True,
            "feeds_risk_gate": True,
            "does_not_fabricate_values": True,
        }

    def _normalize_symbols(self, symbols):
        seen = []
        for symbol in symbols or []:
            ticker = str(symbol or "").strip().upper()
            if ticker and ticker not in seen:
                seen.append(ticker)
        return sorted(seen)

    # ------------------------------------------------------------------
    # Evaluation
    # ------------------------------------------------------------------
    def _evaluate(self, generated_at, symbols, lookback_days, rows, data_source):
        returns_by_symbol = self._returns_by_symbol(symbols, rows)

        insufficient_items = []
        evaluable = []
        for symbol in symbols:
            observations = len(returns_by_symbol.get(symbol, {}))
            if observations < self.MIN_OBSERVATIONS:
                insufficient_items.append({
                    "symbol": symbol,
                    "status": "NEEDS_MORE_DATA",
                    "observations": observations,
                    "required_observations": self.MIN_OBSERVATIONS,
                    "reason": (
                        "Only {found} of {required} required return "
                        "observations are available for this symbol.".format(
                            found=observations,
                            required=self.MIN_OBSERVATIONS,
                        )
                    ),
                })
            else:
                evaluable.append(symbol)

        insufficient_section = {
            "status": "EVALUATED" if evaluable else "NOT_EVALUATED",
            "min_observations": self.MIN_OBSERVATIONS,
            "items": insufficient_items,
        }

        if len(evaluable) < 2:
            reason = (
                "Fewer than two held symbols have enough price history to "
                "measure correlation."
            )
            report = self._not_evaluated(
                generated_at,
                symbols,
                lookback_days,
                reason=reason,
                data_source=data_source,
            )
            report["insufficient_data"] = insufficient_section
            report["coverage"]["symbols_evaluated"] = 0
            return report

        pairs = self._pairwise(evaluable, returns_by_symbol)

        matrix_items = [self._matrix_item(pair) for pair in pairs]
        evaluated_pairs = [p for p in pairs if p["status"] == "EVALUATED"]

        high_pairs = [
            self._pair_view(pair)
            for pair in evaluated_pairs
            if pair["correlation"] >= self.max_correlation
        ]
        high_pairs.sort(key=lambda row: (-row["correlation"], row["symbols"]))

        violations = [
            {
                "symbols": pair["symbols"],
                "correlation": pair["correlation"],
                "limit": self.max_correlation,
                "exceeded_by": round(pair["correlation"] - self.max_correlation, 6),
                "observations": pair["observations"],
            }
            for pair in evaluated_pairs
            if pair["correlation"] > self.max_correlation
        ]
        violations.sort(key=lambda row: (-row["correlation"], row["symbols"]))

        clusters = self._clusters(evaluable, evaluated_pairs)

        matrix_status = "EVALUATED" if evaluated_pairs else "NOT_EVALUATED"
        status = "PARTIAL" if insufficient_items else "EVALUATED"

        return {
            "generated_at": generated_at,
            "status": status,
            "reason": (
                "Some held symbols do not yet have enough price history."
                if insufficient_items else None
            ),
            "coverage": {
                "symbols_held": len(symbols),
                "symbols_evaluated": len(evaluable),
                "pairs_evaluated": len(evaluated_pairs),
                "lookback_days": lookback_days,
                "min_observations": self.MIN_OBSERVATIONS,
            },
            "correlation_matrix": {
                "status": matrix_status,
                "reason": (
                    None if evaluated_pairs
                    else "No symbol pair had enough overlapping observations."
                ),
                "items": matrix_items,
            },
            "high_correlation_pairs": {
                "status": "EVALUATED" if evaluated_pairs else "NOT_EVALUATED",
                "threshold": self.max_correlation,
                "items": high_pairs,
                "reason": (
                    None if evaluated_pairs
                    else "No pair could be evaluated for high correlation."
                ),
            },
            "clusters": {
                "status": "EVALUATED" if evaluated_pairs else "NOT_EVALUATED",
                "threshold": self.cluster_threshold,
                "items": clusters,
                "reason": (
                    "Clusters group symbols whose correlation meets or exceeds "
                    "the threshold and therefore behave like the same trade."
                ),
            },
            "limit_violations": {
                "status": "EVALUATED" if evaluated_pairs else "NOT_EVALUATED",
                "limit": self.max_correlation,
                "items": violations,
                "reason": (
                    "Pairs whose correlation exceeds the maximum correlation "
                    "limit; descriptive only and not fed into the risk gate."
                ),
            },
            "insufficient_data": insufficient_section,
            "data_source": data_source,
            "source_counts": {
                "symbols_held": len(symbols),
                "symbols_evaluated": len(evaluable),
                "pairs_evaluated": len(evaluated_pairs),
                "price_rows": data_source.get("rows", 0),
            },
            "policy": self.policy(),
        }

    # ------------------------------------------------------------------
    # Correlation math
    # ------------------------------------------------------------------
    def _returns_by_symbol(self, symbols, rows):
        closes_by_symbol = {symbol: [] for symbol in symbols}
        wanted = set(symbols)
        for row in rows:
            ticker = str(
                row.get("ticker") or row.get("symbol") or row.get("Ticker") or ""
            ).upper()
            if ticker not in wanted:
                continue
            date = str(row.get("date") or row.get("timestamp") or "")
            close = row.get("close")
            if close is None:
                close = row.get("Close")
            if not date or close is None:
                continue
            closes_by_symbol[ticker].append((date, self._number(close)))

        returns_by_symbol = {}
        for symbol, series in closes_by_symbol.items():
            series.sort(key=lambda item: item[0])
            returns = {}
            previous_close = None
            for date, close in series:
                if previous_close is not None and previous_close != 0:
                    returns[date] = close / previous_close - 1
                previous_close = close
            returns_by_symbol[symbol] = returns
        return returns_by_symbol

    def _pairwise(self, evaluable, returns_by_symbol):
        pairs = []
        for index, first in enumerate(evaluable):
            for second in evaluable[index + 1:]:
                pairs.append(
                    self._correlation(
                        first,
                        second,
                        returns_by_symbol[first],
                        returns_by_symbol[second],
                    )
                )
        return pairs

    def _correlation(self, first, second, returns_a, returns_b):
        common_dates = sorted(set(returns_a) & set(returns_b))
        observations = len(common_dates)
        if observations < self.MIN_OBSERVATIONS:
            return {
                "symbols": [first, second],
                "status": "NOT_EVALUATED",
                "observations": observations,
                "correlation": None,
                "reason": (
                    "Only {found} overlapping observations are available; "
                    "{required} are required.".format(
                        found=observations,
                        required=self.MIN_OBSERVATIONS,
                    )
                ),
            }

        series_a = [returns_a[date] for date in common_dates]
        series_b = [returns_b[date] for date in common_dates]
        mean_a = sum(series_a) / observations
        mean_b = sum(series_b) / observations
        sum_aa = sum((value - mean_a) ** 2 for value in series_a)
        sum_bb = sum((value - mean_b) ** 2 for value in series_b)
        sum_ab = sum(
            (series_a[i] - mean_a) * (series_b[i] - mean_b)
            for i in range(observations)
        )

        if sum_aa == 0 or sum_bb == 0:
            return {
                "symbols": [first, second],
                "status": "NOT_EVALUATED",
                "observations": observations,
                "correlation": None,
                "reason": (
                    "At least one symbol has zero return variance over the "
                    "window, so correlation is undefined."
                ),
            }

        correlation = sum_ab / math.sqrt(sum_aa * sum_bb)
        return {
            "symbols": [first, second],
            "status": "EVALUATED",
            "observations": observations,
            "correlation": round(correlation, 6),
        }

    def _clusters(self, evaluable, evaluated_pairs):
        parent = {symbol: symbol for symbol in evaluable}

        def find(symbol):
            while parent[symbol] != symbol:
                parent[symbol] = parent[parent[symbol]]
                symbol = parent[symbol]
            return symbol

        def union(first, second):
            root_a, root_b = find(first), find(second)
            if root_a == root_b:
                return
            low, high = sorted((root_a, root_b))
            parent[high] = low

        edges = [
            pair for pair in evaluated_pairs
            if pair["correlation"] >= self.cluster_threshold
        ]
        for pair in edges:
            union(pair["symbols"][0], pair["symbols"][1])

        groups = {}
        for symbol in evaluable:
            groups.setdefault(find(symbol), []).append(symbol)

        edge_pairs = {tuple(pair["symbols"]): pair for pair in edges}
        clusters = []
        for members in groups.values():
            if len(members) < 2:
                continue
            members = sorted(members)
            member_correlations = [
                edge_pairs[(a, b)]["correlation"]
                for i, a in enumerate(members)
                for b in members[i + 1:]
                if (a, b) in edge_pairs
            ]
            clusters.append({
                "symbols": members,
                "size": len(members),
                "average_correlation": (
                    round(sum(member_correlations) / len(member_correlations), 6)
                    if member_correlations else None
                ),
                "max_correlation": (
                    round(max(member_correlations), 6)
                    if member_correlations else None
                ),
                "reason": (
                    "These symbols move together above the correlation "
                    "threshold and behave like the same trade."
                ),
            })

        clusters.sort(key=lambda row: (-row["size"], row["symbols"]))
        return clusters

    def _matrix_item(self, pair):
        item = {
            "symbols": pair["symbols"],
            "status": pair["status"],
            "observations": pair["observations"],
            "correlation": pair["correlation"],
        }
        if pair["status"] == "EVALUATED":
            item["relationship"] = self._relationship(pair["correlation"])
        else:
            item["reason"] = pair.get("reason")
        return item

    def _pair_view(self, pair):
        return {
            "symbols": pair["symbols"],
            "correlation": pair["correlation"],
            "observations": pair["observations"],
            "relationship": self._relationship(pair["correlation"]),
        }

    def _relationship(self, correlation):
        if correlation >= self.max_correlation:
            return "MOVES_TOGETHER"
        if correlation <= -self.max_correlation:
            return "MOVES_OPPOSITE"
        return "WEAK"

    # ------------------------------------------------------------------
    # Loading / price history resolution
    # ------------------------------------------------------------------
    def _load_portfolio(self, state, snapshots, limit):
        if state is None:
            from database.repository import get_latest_paper_fund_state

            state = get_latest_paper_fund_state()
        if snapshots is None:
            from database.repository import get_paper_fund_snapshots

            snapshots = get_paper_fund_snapshots(limit=limit)

        state = state or {}
        snapshots = snapshots or []
        latest_snapshot = self.intelligence._latest_snapshot(snapshots)
        portfolio = self.intelligence._portfolio(state, latest_snapshot)
        return state, latest_snapshot, portfolio

    def _held_symbols(self, portfolio):
        positions = portfolio.get("positions", {})
        return sorted(
            symbol for symbol, position in positions.items()
            if self._number(position.get("quantity")) > 0
        )

    def _resolve_price_history(
        self, symbols, latest_snapshot, state, lookback_days, price_history, as_of
    ):
        if price_history is not None:
            rows = price_history.get("rows") or []
            fallback_used = bool(price_history.get("fallback_used", False))
            provider = price_history.get("provider")
            if "price_backed" in price_history:
                price_backed = bool(price_history["price_backed"]) and bool(rows)
            else:
                price_backed = (
                    bool(rows)
                    and not fallback_used
                    and (provider is None or provider not in self.MOCK_PROVIDERS)
                )
            return {
                "rows": rows,
                "price_backed": price_backed,
                "reason": self._price_reason(rows, fallback_used, provider),
                "data_source": self._data_source(
                    provider=provider,
                    price_backed=price_backed,
                    fallback_used=fallback_used,
                    rows=len(rows),
                    symbols=symbols,
                ),
            }

        from market.market_data_manager import MarketDataManager

        manager = MarketDataManager()
        provider = manager.provider_name
        if provider in self.MOCK_PROVIDERS:
            return {
                "rows": [],
                "price_backed": False,
                "reason": (
                    "The configured market data provider is 'mock'; real "
                    "price-backed history is required (set "
                    "MARKET_DATA_PROVIDER=yahoo)."
                ),
                "data_source": self._data_source(
                    provider=provider,
                    price_backed=False,
                    fallback_used=False,
                    rows=0,
                    symbols=symbols,
                ),
            }

        window = self._window(latest_snapshot, state, lookback_days, as_of)
        if window is None:
            return {
                "rows": [],
                "price_backed": False,
                "reason": (
                    "No parseable as-of date is available to build the price "
                    "history window."
                ),
                "data_source": self._data_source(
                    provider=provider,
                    price_backed=False,
                    fallback_used=False,
                    rows=0,
                    symbols=symbols,
                ),
            }

        payload = manager.historical_prices(symbols, window[0], window[1])
        rows = payload.get("rows") or []
        fallback_used = bool(payload.get("fallback_used", False))
        price_backed = bool(rows) and not fallback_used
        return {
            "rows": rows,
            "price_backed": price_backed,
            "reason": self._price_reason(rows, fallback_used, provider),
            "data_source": self._data_source(
                provider=(provider if price_backed else "mock"),
                price_backed=price_backed,
                fallback_used=fallback_used,
                rows=len(rows),
                symbols=symbols,
            ),
        }

    def _price_reason(self, rows, fallback_used, provider):
        if not rows:
            return "No price history rows are available for the held symbols."
        if fallback_used:
            return (
                "Price history fell back to non-real data; correlation requires "
                "real price-backed history."
            )
        if provider is not None and provider in self.MOCK_PROVIDERS:
            return (
                "Price history came from the mock provider; real price-backed "
                "history is required."
            )
        return None

    def _window(self, latest_snapshot, state, lookback_days, as_of):
        end = self._as_of_date(as_of, latest_snapshot, state)
        if end is None:
            return None
        start = end - timedelta(days=lookback_days)
        return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")

    def _as_of_date(self, as_of, latest_snapshot, state):
        candidates = [
            as_of,
            (latest_snapshot or {}).get("as_of"),
            (latest_snapshot or {}).get("date"),
            state.get("updated_at"),
            state.get("last_update"),
        ]
        for candidate in candidates:
            if not candidate:
                continue
            text = str(candidate)
            for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
                try:
                    return datetime.strptime(text[:len(fmt) + 2].strip(), fmt)
                except ValueError:
                    continue
            try:
                return datetime.fromisoformat(text)
            except ValueError:
                continue
        return None

    # ------------------------------------------------------------------
    # Not-evaluated skeleton and helpers
    # ------------------------------------------------------------------
    def _not_evaluated(
        self, generated_at, symbols, lookback_days, reason, data_source
    ):
        return {
            "generated_at": generated_at,
            "status": "NOT_EVALUATED",
            "reason": reason,
            "coverage": {
                "symbols_held": len(symbols),
                "symbols_evaluated": 0,
                "pairs_evaluated": 0,
                "lookback_days": lookback_days,
                "min_observations": self.MIN_OBSERVATIONS,
            },
            "correlation_matrix": {
                "status": "NOT_EVALUATED",
                "reason": reason,
                "items": [],
            },
            "high_correlation_pairs": {
                "status": "NOT_EVALUATED",
                "threshold": self.max_correlation,
                "reason": reason,
                "items": [],
            },
            "clusters": {
                "status": "NOT_EVALUATED",
                "threshold": self.cluster_threshold,
                "reason": reason,
                "items": [],
            },
            "limit_violations": {
                "status": "NOT_EVALUATED",
                "limit": self.max_correlation,
                "reason": reason,
                "items": [],
            },
            "insufficient_data": {
                "status": "NOT_EVALUATED",
                "min_observations": self.MIN_OBSERVATIONS,
                "items": [],
            },
            "data_source": data_source,
            "source_counts": {
                "symbols_held": len(symbols),
                "symbols_evaluated": 0,
                "pairs_evaluated": 0,
                "price_rows": data_source.get("rows", 0),
            },
            "policy": self.policy(),
        }

    def _data_source(self, provider, price_backed, fallback_used, rows, symbols):
        return {
            "provider": provider,
            "price_backed": bool(price_backed),
            "fallback_used": bool(fallback_used),
            "rows": rows,
            "symbols_requested": list(symbols),
        }

    def _generated_at(self, state, latest_snapshot):
        return (
            (latest_snapshot or {}).get("as_of")
            or state.get("updated_at")
            or state.get("last_update")
            or ""
        )

    def policy(self):
        return {
            "read_only": True,
            "descriptive_only": True,
            "deterministic": True,
            "paper_only": True,
            "broker_integration": False,
            "real_money": False,
            "uses_real_price_history_only": True,
            "does_not_modify_recommendations": True,
            "does_not_modify_trades": True,
            "does_not_modify_risk_limits": True,
            "does_not_place_orders": True,
            "does_not_feed_risk_gate": True,
        }

    def _number(self, value):
        if value is None:
            return 0
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0
