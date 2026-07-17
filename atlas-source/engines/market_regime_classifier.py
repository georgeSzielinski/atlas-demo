import math


class MarketRegimeClassifier:
    """Deterministic, read-only classifier of the current market environment.

    Given daily closes for broad-market gauges (SPY as the market proxy, QQQ as
    a growth/risk confirmation, and ^VIX as an implied-volatility gauge), this
    engine describes *what kind of market we are in right now* across three
    orthogonal axes:

    * Trend regime  - Strong Bull / Bull / Sideways / Weak / Bear, from where
      price sits relative to its 50- and 200-day moving averages plus recent
      returns and the golden/death-cross relationship of the two averages.
    * Volatility regime - High / Normal / Low Volatility, from the VIX level
      when available, otherwise from SPY realized (annualized) volatility.
    * Risk posture - Risk-On / Neutral / Risk-Off, from a deterministic score
      combining trend, volatility, and QQQ-vs-SPY relative momentum.

    The nine milestone regime labels map onto these three axes, so the headline
    reports all three together.

    Guarantees: the classification is a pure function of the supplied closes -
    no randomness, no LLM, no network side effects in the math. The engine is
    read-only: it never writes rows and never changes paper-fund, recommendation,
    risk, broker, or order behavior. When the supplied data is insufficient
    (e.g. fewer than 200 SPY closes, so the 200-day average is undefined) the
    affected section - and, when the market proxy itself is missing, the whole
    result - is returned as ``NOT_EVALUATED`` with a human-readable reason and
    whatever supporting metrics could still be computed. Nothing is fabricated.
    """

    MARKET_PROXY = "SPY"
    GROWTH_PROXY = "QQQ"
    VOLATILITY_GAUGE = "^VIX"
    SYMBOLS = (MARKET_PROXY, GROWTH_PROXY, VOLATILITY_GAUGE)

    # Trading-day windows.
    SHORT_WINDOW = 50
    LONG_WINDOW = 200
    RETURN_1M = 21
    RETURN_3M = 63
    VOL_WINDOW = 21
    TRADING_DAYS = 252

    # Trend thresholds (percent).
    STRONG_BULL_RETURN = 8.0
    SIDEWAYS_RETURN_BAND = 1.5
    SIDEWAYS_MONTH_BAND = 2.0

    # Volatility thresholds.
    VIX_HIGH = 25.0
    VIX_LOW = 15.0
    REALIZED_VOL_HIGH = 20.0
    REALIZED_VOL_LOW = 10.0

    # Risk-posture score cutoffs.
    RISK_ON_SCORE = 2
    RISK_OFF_SCORE = -2

    def __init__(self, provider=None):
        self._provider = provider

    # ------------------------------------------------------------------
    # Assembly
    # ------------------------------------------------------------------
    def generate(self, closes=None):
        loaded = self._load(closes)
        histories = loaded["histories"]

        spy = self._metrics(histories.get(self.MARKET_PROXY))
        qqq = self._metrics(histories.get(self.GROWTH_PROXY))
        vix = self._vix_metrics(histories.get(self.VOLATILITY_GAUGE))

        inputs = {
            "symbols_requested": list(self.SYMBOLS),
            "symbols_available": sorted(
                symbol for symbol in self.SYMBOLS if histories.get(symbol)
            ),
            "symbols_missing": sorted(
                symbol for symbol in self.SYMBOLS if not histories.get(symbol)
            ),
            "data_source": loaded["data_source"],
            "provider_error": loaded["provider_error"],
        }

        if spy["status"] != "EVALUATED":
            return {
                "generated_at": spy.get("as_of"),
                "status": "NOT_EVALUATED",
                "reason": spy["reason"],
                "trend_regime": self._not_evaluated(spy["reason"]),
                "volatility_regime": self._not_evaluated(spy["reason"]),
                "risk_posture": self._not_evaluated(spy["reason"]),
                "headline": "NOT_EVALUATED",
                "metrics": {"spy": spy, "qqq": qqq, "vix": vix},
                "signals": [],
                "inputs": inputs,
                "possible_regimes": self._possible_regimes(),
                "policy": self.policy(),
            }

        trend = self._trend_regime(spy)
        volatility = self._volatility_regime(spy, vix)
        risk = self._risk_posture(spy, qqq, vix, trend, volatility)
        signals = self._signals(spy, qqq, vix)

        headline = " · ".join([
            trend["label"],
            volatility["label"],
            risk["label"],
        ])

        return {
            "generated_at": spy.get("as_of"),
            "status": "EVALUATED",
            "reason": None,
            "trend_regime": trend,
            "volatility_regime": volatility,
            "risk_posture": risk,
            "headline": headline,
            "metrics": {"spy": spy, "qqq": qqq, "vix": vix},
            "signals": signals,
            "inputs": inputs,
            "possible_regimes": self._possible_regimes(),
            "policy": self.policy(),
        }

    # ------------------------------------------------------------------
    # Trend regime
    # ------------------------------------------------------------------
    def _trend_regime(self, spy):
        above_50 = spy["price_vs_50ma_pct"] >= 0
        above_200 = spy["price_vs_200ma_pct"] >= 0
        golden = spy["golden_cross"]
        return_3m = spy["return_3m_pct"]
        return_1m = spy["return_1m_pct"]

        if above_200 and above_50:
            if golden and return_3m >= self.STRONG_BULL_RETURN and return_1m >= 0:
                label = "Strong Bull"
                reason = (
                    "Price is above both the 50- and 200-day averages with a "
                    f"golden cross and a strong 3-month return "
                    f"({return_3m}%)."
                )
            elif (
                abs(return_3m) <= self.SIDEWAYS_RETURN_BAND
                and abs(return_1m) <= self.SIDEWAYS_MONTH_BAND
            ):
                label = "Sideways"
                reason = (
                    "Price is near its moving averages and recent returns are "
                    f"flat (3-month {return_3m}%, 1-month {return_1m}%)."
                )
            else:
                label = "Bull"
                reason = (
                    "Price is above both moving averages with positive "
                    f"momentum (3-month {return_3m}%)."
                )
        elif above_200 and not above_50:
            label = "Weak"
            reason = (
                "Price is below the 50-day average but still above the 200-day "
                "average: the long-term uptrend is intact but losing momentum "
                f"(3-month {return_3m}%)."
            )
        elif not above_200 and above_50:
            label = "Sideways"
            reason = (
                "Price is above the 50-day but below the 200-day average: "
                "mixed, transitional signals."
            )
        else:
            label = "Bear"
            reason = (
                "Price is below both the 50- and 200-day averages"
                + (" with a death cross" if not golden else "")
                + f" (3-month {return_3m}%)."
            )

        return {
            "status": "EVALUATED",
            "label": label,
            "reason": reason,
            "supporting": {
                "price_vs_50ma_pct": spy["price_vs_50ma_pct"],
                "price_vs_200ma_pct": spy["price_vs_200ma_pct"],
                "golden_cross": golden,
                "return_1m_pct": return_1m,
                "return_3m_pct": return_3m,
            },
        }

    # ------------------------------------------------------------------
    # Volatility regime
    # ------------------------------------------------------------------
    def _volatility_regime(self, spy, vix):
        if vix["status"] == "EVALUATED":
            level = vix["level"]
            if level >= self.VIX_HIGH:
                label, note = "High Volatility", "elevated fear"
            elif level <= self.VIX_LOW:
                label, note = "Low Volatility", "calm conditions"
            else:
                label, note = "Normal Volatility", "typical conditions"
            return {
                "status": "EVALUATED",
                "label": label,
                "reason": f"VIX at {level} indicates {note}.",
                "basis": "vix",
                "vix_level": level,
                "realized_vol_annualized_pct": spy["realized_vol_annualized_pct"],
            }

        realized = spy["realized_vol_annualized_pct"]
        if realized is None:
            return self._not_evaluated(
                "Neither VIX nor enough SPY history is available to gauge "
                "volatility."
            )
        if realized >= self.REALIZED_VOL_HIGH:
            label, note = "High Volatility", "turbulent"
        elif realized <= self.REALIZED_VOL_LOW:
            label, note = "Low Volatility", "calm"
        else:
            label, note = "Normal Volatility", "typical"
        return {
            "status": "EVALUATED",
            "label": label,
            "reason": (
                f"VIX unavailable; SPY realized volatility of {realized}% "
                f"(annualized) indicates {note} conditions."
            ),
            "basis": "realized",
            "vix_level": None,
            "realized_vol_annualized_pct": realized,
        }

    # ------------------------------------------------------------------
    # Risk posture
    # ------------------------------------------------------------------
    def _risk_posture(self, spy, qqq, vix, trend, volatility):
        components = []
        score = 0

        def add(points, label):
            nonlocal score
            score += points
            components.append({"factor": label, "points": points})

        add(1 if spy["price_vs_200ma_pct"] >= 0 else -1, "price_vs_200ma")
        add(1 if spy["golden_cross"] else -1, "golden_cross")
        add(1 if spy["return_3m_pct"] > 0 else -1, "return_3m")

        if qqq["status"] == "EVALUATED":
            leadership = qqq["return_1m_pct"] >= spy["return_1m_pct"]
            add(1 if leadership else -1, "qqq_leadership")
        else:
            components.append({"factor": "qqq_leadership", "points": 0,
                               "note": "QQQ history unavailable."})

        vol_label = volatility.get("label")
        if vol_label == "High Volatility":
            add(-2, "volatility")
        elif vol_label == "Low Volatility":
            add(1, "volatility")

        if score >= self.RISK_ON_SCORE:
            label = "Risk-On"
            reason = (
                "Trend, breadth, and volatility signals lean toward risk-taking "
                f"(risk score {score})."
            )
        elif score <= self.RISK_OFF_SCORE:
            label = "Risk-Off"
            reason = (
                "Trend, breadth, and volatility signals lean defensive "
                f"(risk score {score})."
            )
        else:
            label = "Neutral"
            reason = f"Risk signals are mixed (risk score {score})."

        return {
            "status": "EVALUATED",
            "label": label,
            "reason": reason,
            "score": score,
            "components": components,
        }

    # ------------------------------------------------------------------
    # Signals summary
    # ------------------------------------------------------------------
    def _signals(self, spy, qqq, vix):
        signals = [
            {
                "signal": "50/200-day cross",
                "value": "Golden cross" if spy["golden_cross"] else "Death cross",
                "interpretation": (
                    "50-day average above 200-day average (bullish)."
                    if spy["golden_cross"]
                    else "50-day average below 200-day average (bearish)."
                ),
            },
            {
                "signal": "Price vs 200-day average",
                "value": f"{spy['price_vs_200ma_pct']}%",
                "interpretation": (
                    "Above long-term trend."
                    if spy["price_vs_200ma_pct"] >= 0
                    else "Below long-term trend."
                ),
            },
            {
                "signal": "3-month return",
                "value": f"{spy['return_3m_pct']}%",
                "interpretation": (
                    "Positive momentum." if spy["return_3m_pct"] > 0
                    else "Negative momentum."
                ),
            },
        ]
        if vix["status"] == "EVALUATED":
            signals.append({
                "signal": "VIX",
                "value": vix["level"],
                "interpretation": (
                    "Risk-off / elevated fear." if vix["level"] >= self.VIX_HIGH
                    else "Risk-on / calm." if vix["level"] <= self.VIX_LOW
                    else "Neutral volatility."
                ),
            })
        if qqq["status"] == "EVALUATED":
            leadership = qqq["return_1m_pct"] >= spy["return_1m_pct"]
            signals.append({
                "signal": "QQQ vs SPY (1-month)",
                "value": f"{qqq['return_1m_pct']}% vs {spy['return_1m_pct']}%",
                "interpretation": (
                    "Growth leadership (risk-on)." if leadership
                    else "Growth lagging (risk-off)."
                ),
            })
        return signals

    # ------------------------------------------------------------------
    # Metric derivation
    # ------------------------------------------------------------------
    def _metrics(self, history):
        closes, dates = self._series(history)
        as_of = dates[-1] if dates else None
        if len(closes) < self.LONG_WINDOW:
            return {
                "status": "NOT_EVALUATED",
                "reason": (
                    f"At least {self.LONG_WINDOW} daily closes are required for "
                    f"the 200-day average; {len(closes)} were available."
                ),
                "as_of": as_of,
                "sample_size": len(closes),
                # Whatever is still computable is surfaced for transparency.
                "close": round(closes[-1], 4) if closes else None,
                "ma_50": self._sma(closes, self.SHORT_WINDOW),
                "return_1m_pct": self._window_return(closes, self.RETURN_1M),
                "realized_vol_annualized_pct": self._realized_vol(closes),
            }

        close = closes[-1]
        ma_50 = self._sma(closes, self.SHORT_WINDOW)
        ma_200 = self._sma(closes, self.LONG_WINDOW)
        return {
            "status": "EVALUATED",
            "as_of": as_of,
            "sample_size": len(closes),
            "close": round(close, 4),
            "ma_50": ma_50,
            "ma_200": ma_200,
            "price_vs_50ma_pct": self._percent(close, ma_50),
            "price_vs_200ma_pct": self._percent(close, ma_200),
            "ma_50_vs_200_pct": self._percent(ma_50, ma_200),
            "golden_cross": ma_50 >= ma_200,
            "return_1m_pct": self._window_return(closes, self.RETURN_1M),
            "return_3m_pct": self._window_return(closes, self.RETURN_3M),
            "realized_vol_annualized_pct": self._realized_vol(closes),
        }

    def _vix_metrics(self, history):
        closes, dates = self._series(history)
        if not closes:
            return self._not_evaluated(
                "No ^VIX history is available; volatility falls back to SPY "
                "realized volatility."
            )
        return {
            "status": "EVALUATED",
            "as_of": dates[-1] if dates else None,
            "level": round(closes[-1], 4),
            "sample_size": len(closes),
        }

    # ------------------------------------------------------------------
    # Math helpers (pure)
    # ------------------------------------------------------------------
    def _series(self, history):
        if not history:
            return [], []
        ordered = sorted(
            (row for row in history if row.get("close") is not None),
            key=lambda row: str(row.get("date", "")),
        )
        closes = [float(row["close"]) for row in ordered]
        dates = [str(row.get("date", "")) for row in ordered]
        return closes, dates

    def _sma(self, closes, window):
        if len(closes) < window:
            return None
        window_values = closes[-window:]
        return round(sum(window_values) / window, 4)

    def _window_return(self, closes, window):
        if len(closes) <= window:
            return None
        previous = closes[-1 - window]
        if not previous:
            return None
        return round((closes[-1] - previous) / previous * 100, 4)

    def _realized_vol(self, closes):
        if len(closes) <= self.VOL_WINDOW:
            return None
        window = closes[-(self.VOL_WINDOW + 1):]
        daily_returns = [
            (window[i] - window[i - 1]) / window[i - 1]
            for i in range(1, len(window))
            if window[i - 1]
        ]
        if len(daily_returns) < 2:
            return None
        mean = sum(daily_returns) / len(daily_returns)
        variance = sum((value - mean) ** 2 for value in daily_returns) / len(
            daily_returns
        )
        return round(math.sqrt(variance) * math.sqrt(self.TRADING_DAYS) * 100, 4)

    def _percent(self, current, base):
        if not base:
            return 0
        return round((current - base) / base * 100, 4)

    # ------------------------------------------------------------------
    # Data loading (read-only market gauges; never a trade candidate)
    # ------------------------------------------------------------------
    def _load(self, closes):
        if closes is not None:
            return {
                "histories": {
                    symbol: closes.get(symbol) or [] for symbol in self.SYMBOLS
                },
                "data_source": "injected",
                "provider_error": "",
            }

        provider = self._provider
        if provider is None:
            from market.index_history_provider import IndexHistoryProvider

            provider = IndexHistoryProvider()

        histories = {}
        provider_error = ""
        try:
            histories = provider.get_daily_closes(list(self.SYMBOLS)) or {}
            provider_error = getattr(provider, "last_error", "") or ""
        except Exception as error:  # pragma: no cover - defensive
            provider_error = f"provider failed: {error}"
            histories = {}

        return {
            "histories": {
                symbol: histories.get(symbol) or [] for symbol in self.SYMBOLS
            },
            "data_source": getattr(provider, "provider_name", "unknown"),
            "provider_error": provider_error,
        }

    # ------------------------------------------------------------------
    # Static descriptors
    # ------------------------------------------------------------------
    def _possible_regimes(self):
        return {
            "trend": ["Strong Bull", "Bull", "Sideways", "Weak", "Bear"],
            "volatility": ["High Volatility", "Normal Volatility", "Low Volatility"],
            "risk": ["Risk-On", "Neutral", "Risk-Off"],
        }

    def policy(self):
        return {
            "read_only": True,
            "deterministic": True,
            "descriptive_only": True,
            "changes_trading_behavior": False,
            "changes_recommendation_behavior": False,
            "changes_paper_fund_behavior": False,
            "uses_llm": False,
            "broker_integration": False,
            "real_money": False,
        }

    def _not_evaluated(self, reason):
        return {"status": "NOT_EVALUATED", "reason": reason}
