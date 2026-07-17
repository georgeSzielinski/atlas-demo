import math

import market.index_history_provider as index_history_provider
from engines.market_regime_classifier import MarketRegimeClassifier

REQUIRED_POLICY_KEYS = {
    "read_only",
    "deterministic",
    "descriptive_only",
    "changes_trading_behavior",
    "changes_recommendation_behavior",
    "changes_paper_fund_behavior",
    "uses_llm",
    "broker_integration",
    "real_money",
}

REQUIRED_KEYS = {
    "generated_at",
    "status",
    "trend_regime",
    "volatility_regime",
    "risk_posture",
    "headline",
    "metrics",
    "signals",
    "inputs",
    "possible_regimes",
    "policy",
}


def series(fn, n):
    return [{"date": f"2026-{i:05d}", "close": fn(i)} for i in range(n)]


# Deterministic synthetic gauge histories (verified against the engine rules).
BULL = series(lambda i: 100 + 0.5 * i, 220)          # steady uptrend
BEAR = series(lambda i: 200 - 0.5 * i, 220)          # steady downtrend
QQQ_STRONG = series(lambda i: 100 + 0.7 * i, 220)    # leads SPY
QQQ_WEAK = series(lambda i: 200 - 0.7 * i, 220)      # lags SPY


def weak_fn(i):
    if i < 200:
        return 100 + 0.6 * i
    return 100 + 0.6 * 199 - 1.2 * (i - 199)


WEAK = series(weak_fn, 214)


def sideways_fn(i):
    if i < 150:
        return 100 + 0.5 * i
    return 175.0 + 0.02 * ((i % 5) - 2)


SIDEWAYS = series(sideways_fn, 230)

HIGH_VOL = series(lambda i: 150 + 0.2 * i + 12 * math.sin(i), 220)


def vix(level):
    return series(lambda i: level, 220)


engine = MarketRegimeClassifier()

# ----------------------------------------------------------------------
# Determinism + shape.
# ----------------------------------------------------------------------
report = engine.generate(closes={"SPY": BULL, "QQQ": QQQ_STRONG, "^VIX": vix(12)})
repeated = engine.generate(closes={"SPY": BULL, "QQQ": QQQ_STRONG, "^VIX": vix(12)})
assert report == repeated, "Classification must be deterministic."
assert REQUIRED_KEYS.issubset(report.keys())
assert REQUIRED_POLICY_KEYS.issubset(report["policy"].keys())
assert report["policy"]["read_only"] is True
assert report["policy"]["deterministic"] is True
assert report["policy"]["changes_trading_behavior"] is False
assert report["policy"]["uses_llm"] is False

# ----------------------------------------------------------------------
# Strong Bull, low VIX, QQQ leadership -> Risk-On, Low Volatility.
# ----------------------------------------------------------------------
assert report["status"] == "EVALUATED"
assert report["trend_regime"]["label"] == "Strong Bull"
assert report["volatility_regime"]["label"] == "Low Volatility"
assert report["volatility_regime"]["basis"] == "vix"
assert report["risk_posture"]["label"] == "Risk-On"
assert report["risk_posture"]["score"] >= 2
spy = report["metrics"]["spy"]
assert spy["status"] == "EVALUATED"
assert spy["golden_cross"] is True
assert spy["price_vs_200ma_pct"] > 0
assert report["metrics"]["vix"]["status"] == "EVALUATED"
assert report["metrics"]["qqq"]["status"] == "EVALUATED"
assert "Strong Bull" in report["headline"]
assert report["inputs"]["symbols_missing"] == []

# ----------------------------------------------------------------------
# Bear, high VIX, QQQ lagging -> Risk-Off, High Volatility.
# ----------------------------------------------------------------------
bear = engine.generate(closes={"SPY": BEAR, "QQQ": QQQ_WEAK, "^VIX": vix(31)})
assert bear["trend_regime"]["label"] == "Bear"
assert bear["metrics"]["spy"]["golden_cross"] is False
assert bear["volatility_regime"]["label"] == "High Volatility"
assert bear["risk_posture"]["label"] == "Risk-Off"
assert bear["risk_posture"]["score"] <= -2

# ----------------------------------------------------------------------
# Weak and Sideways trends.
# ----------------------------------------------------------------------
weak = engine.generate(closes={"SPY": WEAK})
assert weak["trend_regime"]["label"] == "Weak"
assert weak["metrics"]["spy"]["price_vs_50ma_pct"] < 0
assert weak["metrics"]["spy"]["price_vs_200ma_pct"] > 0

sideways = engine.generate(closes={"SPY": SIDEWAYS})
assert sideways["trend_regime"]["label"] == "Sideways"

# ----------------------------------------------------------------------
# Volatility falls back to SPY realized vol when VIX is absent.
# ----------------------------------------------------------------------
high_vol = engine.generate(closes={"SPY": HIGH_VOL})
assert high_vol["volatility_regime"]["basis"] == "realized"
assert high_vol["volatility_regime"]["label"] == "High Volatility"
assert high_vol["metrics"]["vix"]["status"] == "NOT_EVALUATED"
# Still EVALUATED overall: VIX and QQQ are optional confirmations.
assert high_vol["status"] == "EVALUATED"

low_vol = engine.generate(closes={"SPY": BULL})
assert low_vol["volatility_regime"]["basis"] == "realized"
assert low_vol["volatility_regime"]["label"] == "Low Volatility"

# VIX thresholds drive the label when present.
assert engine.generate(
    closes={"SPY": BULL, "^VIX": vix(30)}
)["volatility_regime"]["label"] == "High Volatility"
assert engine.generate(
    closes={"SPY": BULL, "^VIX": vix(20)}
)["volatility_regime"]["label"] == "Normal Volatility"

# ----------------------------------------------------------------------
# NOT_EVALUATED: fewer than 200 SPY closes -> overall NOT_EVALUATED, but
# partial metrics are still surfaced and nothing is fabricated.
# ----------------------------------------------------------------------
short = engine.generate(closes={"SPY": BULL[:120]})
assert short["status"] == "NOT_EVALUATED"
assert short["reason"]
assert short["trend_regime"]["status"] == "NOT_EVALUATED"
assert short["volatility_regime"]["status"] == "NOT_EVALUATED"
assert short["risk_posture"]["status"] == "NOT_EVALUATED"
assert short["metrics"]["spy"]["status"] == "NOT_EVALUATED"
assert short["metrics"]["spy"]["ma_50"] is not None  # computable partial metric

# NOT_EVALUATED: market proxy missing entirely.
missing = engine.generate(closes={"QQQ": QQQ_STRONG})
assert missing["status"] == "NOT_EVALUATED"
assert "SPY" in missing["inputs"]["symbols_missing"]

# Empty input -> NOT_EVALUATED, never a crash.
empty = engine.generate(closes={})
assert empty["status"] == "NOT_EVALUATED"


# ----------------------------------------------------------------------
# Provider load path + endpoint wiring, exercised with a fake provider so no
# network call is made and the result stays deterministic.
# ----------------------------------------------------------------------
class FakeProvider:
    provider_name = "fake_yahoo"

    def __init__(self):
        self.last_error = ""

    def get_daily_closes(self, symbols):
        return {"SPY": BULL, "QQQ": QQQ_STRONG, "^VIX": vix(12)}


provider_report = MarketRegimeClassifier(provider=FakeProvider()).generate()
assert provider_report["status"] == "EVALUATED"
assert provider_report["inputs"]["data_source"] == "fake_yahoo"
assert provider_report["trend_regime"]["label"] == "Strong Bull"

# Endpoint returns the same structure when its provider is patched.
original_provider = index_history_provider.IndexHistoryProvider
try:
    index_history_provider.IndexHistoryProvider = FakeProvider
    from api.main import market_regime

    endpoint_report = market_regime()
    assert endpoint_report["status"] == "EVALUATED"
    assert REQUIRED_KEYS.issubset(endpoint_report.keys())
    assert endpoint_report["headline"].startswith("Strong Bull")
finally:
    index_history_provider.IndexHistoryProvider = original_provider


print("MarketRegimeClassifier test passed.")
