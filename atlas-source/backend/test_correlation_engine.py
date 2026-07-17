from datetime import datetime, timedelta

from engines.correlation_engine import CorrelationEngine


REQUIRED_POLICY_KEYS = {
    "read_only",
    "descriptive_only",
    "deterministic",
    "paper_only",
    "broker_integration",
    "real_money",
    "uses_real_price_history_only",
    "does_not_modify_recommendations",
    "does_not_modify_trades",
    "does_not_modify_risk_limits",
    "does_not_place_orders",
    "does_not_feed_risk_gate",
}

REQUIRED_SECTIONS = (
    "coverage",
    "correlation_matrix",
    "high_correlation_pairs",
    "clusters",
    "limit_violations",
    "insufficient_data",
    "data_source",
    "source_counts",
    "policy",
)


# 23 deterministic daily returns -> 24 closes per fully-covered symbol.
GROUP_RETURNS = [
    0.01, -0.02, 0.015, 0.02, -0.01, 0.03, -0.015, 0.02, 0.01, -0.02,
    0.025, -0.01, 0.02, 0.015, -0.025, 0.01, 0.02, -0.015, 0.03, -0.01,
    0.02, -0.02, 0.015,
]


def build_closes(returns, start=100.0):
    closes = [start]
    for value in returns:
        closes.append(closes[-1] * (1 + value))
    return closes


def dates(count, start="2026-01-05"):
    origin = datetime.strptime(start, "%Y-%m-%d")
    return [(origin + timedelta(days=index)).strftime("%Y-%m-%d") for index in range(count)]


GROUP_CLOSES = build_closes(GROUP_RETURNS)
XLE_CLOSES = build_closes([-value for value in GROUP_RETURNS])
DATE_SERIES = dates(len(GROUP_CLOSES))
# ZZZZ has only 5 closes -> 4 returns -> below the 20-observation minimum.
ZZZZ_CLOSES = [100.0, 101.0, 100.0, 102.0, 101.0]


def price_rows():
    rows = []
    for symbol, closes in (
        ("AAPL", GROUP_CLOSES),
        ("MSFT", GROUP_CLOSES),
        ("GOOGL", GROUP_CLOSES),
        ("XLE", XLE_CLOSES),
    ):
        for date, close in zip(DATE_SERIES, closes):
            rows.append({"ticker": symbol, "date": date, "close": close})
    for date, close in zip(DATE_SERIES, ZZZZ_CLOSES):
        rows.append({"ticker": "ZZZZ", "date": date, "close": close})
    return rows


def positions(symbols):
    return {
        symbol: {
            "ticker": symbol,
            "quantity": 10,
            "cost_basis": 100,
            "current_price": 100,
            "current_value": 1000,
        }
        for symbol in symbols
    }


def state_with(symbols):
    return {
        "fund_status": "RUNNING",
        "cash": 500,
        "positions": positions(symbols),
        "updated_at": "2026-02-01T10:15:00",
        "last_update": "2026-02-01T10:15:00",
    }


def snapshot_with(symbols):
    return {
        "as_of": "2026-02-01T10:15:00",
        "date": "2026-02-01T10:15:00",
        "cash": 500,
        "positions": positions(symbols),
        "portfolio_value": 10000,
    }


engine = CorrelationEngine()

SYMBOLS = ["AAPL", "GOOGL", "MSFT", "XLE", "ZZZZ"]


def run(price_history):
    return engine.generate(
        state=state_with(SYMBOLS),
        snapshots=[snapshot_with(SYMBOLS)],
        price_history=price_history,
        limit=100,
    )


# ----------------------------------------------------------------------
# Deterministic, real price-backed evaluation.
# ----------------------------------------------------------------------
history = {"provider": "yahoo", "fallback_used": False, "rows": price_rows()}
report = run(history)
repeated = run(history)

assert report == repeated, "Correlation output must be deterministic."

for section in REQUIRED_SECTIONS:
    assert section in report, section

assert REQUIRED_POLICY_KEYS.issubset(report["policy"].keys())
assert report["policy"]["read_only"] is True
assert report["policy"]["deterministic"] is True
assert report["policy"]["uses_real_price_history_only"] is True
assert report["policy"]["real_money"] is False
assert report["policy"]["broker_integration"] is False
assert report["policy"]["does_not_feed_risk_gate"] is True

# PARTIAL because ZZZZ lacks enough history.
assert report["status"] == "PARTIAL"
assert report["coverage"]["symbols_held"] == 5
assert report["coverage"]["symbols_evaluated"] == 4
assert report["coverage"]["pairs_evaluated"] == 6

# --- Deterministic correlation math ---
matrix = {tuple(item["symbols"]): item for item in report["correlation_matrix"]["items"]}
assert report["correlation_matrix"]["status"] == "EVALUATED"
# Identical return streams correlate at exactly 1.0.
assert matrix[("AAPL", "GOOGL")]["correlation"] == 1.0
assert matrix[("AAPL", "MSFT")]["correlation"] == 1.0
assert matrix[("GOOGL", "MSFT")]["correlation"] == 1.0
# Mirrored return stream correlates strongly negative.
assert matrix[("AAPL", "XLE")]["correlation"] < 0
assert matrix[("AAPL", "XLE")]["correlation"] <= -0.99
assert matrix[("AAPL", "XLE")]["relationship"] == "MOVES_OPPOSITE"
assert matrix[("AAPL", "GOOGL")]["relationship"] == "MOVES_TOGETHER"
assert matrix[("AAPL", "GOOGL")]["observations"] == len(GROUP_RETURNS)

# --- High-correlation pair detection ---
high = report["high_correlation_pairs"]
assert high["threshold"] == 0.80
high_pairs = {tuple(item["symbols"]) for item in high["items"]}
assert high_pairs == {("AAPL", "GOOGL"), ("AAPL", "MSFT"), ("GOOGL", "MSFT")}
# Negatively correlated pairs are not "moving together".
assert ("AAPL", "XLE") not in high_pairs

# --- Cluster grouping (same-trade detection) ---
clusters = report["clusters"]["items"]
assert len(clusters) == 1
assert clusters[0]["symbols"] == ["AAPL", "GOOGL", "MSFT"]
assert clusters[0]["size"] == 3
assert clusters[0]["max_correlation"] == 1.0
# The opposite-moving symbol is not grouped into the cluster.
assert "XLE" not in clusters[0]["symbols"]

# --- Limit violations vs max_correlation ---
violations = report["limit_violations"]
assert violations["limit"] == 0.80
violation_pairs = {tuple(item["symbols"]) for item in violations["items"]}
assert violation_pairs == {("AAPL", "GOOGL"), ("AAPL", "MSFT"), ("GOOGL", "MSFT")}
assert all(item["correlation"] > 0.80 for item in violations["items"])
assert violations["items"][0]["exceeded_by"] == round(1.0 - 0.80, 6)

# --- Insufficient-data handling ---
insufficient = report["insufficient_data"]
assert insufficient["status"] == "EVALUATED"
assert insufficient["min_observations"] == 20
insufficient_symbols = {item["symbol"] for item in insufficient["items"]}
assert insufficient_symbols == {"ZZZZ"}
assert insufficient["items"][0]["status"] == "NEEDS_MORE_DATA"
assert insufficient["items"][0]["observations"] == 4

# --- Data source is flagged real / price-backed ---
assert report["data_source"]["price_backed"] is True
assert report["data_source"]["provider"] == "yahoo"
assert report["data_source"]["fallback_used"] is False


# ----------------------------------------------------------------------
# Mock / fallback / empty history -> NOT_EVALUATED (never fabricated).
# ----------------------------------------------------------------------
mock_report = run({"provider": "mock", "rows": price_rows()})
assert mock_report["status"] == "NOT_EVALUATED"
assert mock_report["data_source"]["price_backed"] is False
assert "mock" in mock_report["reason"].lower()
for section in ("correlation_matrix", "high_correlation_pairs", "clusters", "limit_violations"):
    assert mock_report[section]["status"] == "NOT_EVALUATED"
    assert mock_report[section]["items"] == []

fallback_report = run({"provider": "yahoo", "fallback_used": True, "rows": price_rows()})
assert fallback_report["status"] == "NOT_EVALUATED"
assert fallback_report["data_source"]["fallback_used"] is True
assert "real price-backed" in fallback_report["reason"].lower()

empty_report = run({"provider": "yahoo", "rows": []})
assert empty_report["status"] == "NOT_EVALUATED"
assert empty_report["correlation_matrix"]["items"] == []
assert REQUIRED_POLICY_KEYS.issubset(empty_report["policy"].keys())


# ----------------------------------------------------------------------
# Fewer than two positions -> NOT_EVALUATED.
# ----------------------------------------------------------------------
single = engine.generate(
    state=state_with(["AAPL"]),
    snapshots=[snapshot_with(["AAPL"])],
    price_history={"provider": "yahoo", "rows": price_rows()},
    limit=100,
)
assert single["status"] == "NOT_EVALUATED"
assert "two held" in single["reason"].lower()
for section in REQUIRED_SECTIONS:
    assert section in single, section


# ----------------------------------------------------------------------
# Two positions but one lacks history -> NOT_EVALUATED, insufficient listed.
# ----------------------------------------------------------------------
one_evaluable_rows = [
    {"ticker": "AAPL", "date": date, "close": close}
    for date, close in zip(DATE_SERIES, GROUP_CLOSES)
]
one_evaluable_rows += [
    {"ticker": "ZZZZ", "date": date, "close": close}
    for date, close in zip(DATE_SERIES, ZZZZ_CLOSES)
]
partial = engine.generate(
    state=state_with(["AAPL", "ZZZZ"]),
    snapshots=[snapshot_with(["AAPL", "ZZZZ"])],
    price_history={"provider": "yahoo", "rows": one_evaluable_rows},
    limit=100,
)
assert partial["status"] == "NOT_EVALUATED"
assert partial["coverage"]["symbols_evaluated"] == 0
partial_insufficient = {item["symbol"] for item in partial["insufficient_data"]["items"]}
assert "ZZZZ" in partial_insufficient


# ----------------------------------------------------------------------
# risk_matrix: nested {symbol: {peer: correlation}} evidence for the risk gate.
# ----------------------------------------------------------------------
REAL_HISTORY = {"provider": "yahoo", "fallback_used": False, "rows": price_rows()}

matrix = engine.risk_matrix(SYMBOLS, state=state_with(SYMBOLS), price_history=REAL_HISTORY)
repeated_matrix = engine.risk_matrix(
    SYMBOLS, state=state_with(SYMBOLS), price_history=REAL_HISTORY
)
assert matrix == repeated_matrix, "risk_matrix must be deterministic."

# PARTIAL because ZZZZ lacks enough history and is excluded.
assert matrix["status"] == "PARTIAL"
assert matrix["symbols_evaluated"] == ["AAPL", "GOOGL", "MSFT", "XLE"]
assert matrix["pairs_evaluated"] == 6
assert matrix["threshold"] == 0.80
assert matrix["policy"]["feeds_risk_gate"] is True
assert matrix["policy"]["uses_real_price_history_only"] is True
assert matrix["data_source"]["price_backed"] is True

correlations = matrix["correlations"]
# Nested format and symmetry.
assert correlations["AAPL"]["GOOGL"] == 1.0
assert correlations["GOOGL"]["AAPL"] == 1.0
assert correlations["AAPL"]["MSFT"] == correlations["MSFT"]["AAPL"] == 1.0
assert correlations["XLE"]["AAPL"] <= -0.99
assert correlations["AAPL"]["XLE"] == correlations["XLE"]["AAPL"]
# Unevaluated symbol is omitted entirely -> never fabricated or zero-filled.
assert "ZZZZ" not in correlations
for peers in correlations.values():
    assert "ZZZZ" not in peers

# Fully covered universe -> EVALUATED with no reason.
full_matrix = engine.risk_matrix(
    ["AAPL", "GOOGL", "MSFT", "XLE"],
    state=state_with(["AAPL", "GOOGL", "MSFT", "XLE"]),
    price_history={"provider": "yahoo", "rows": price_rows()},
)
assert full_matrix["status"] == "EVALUATED"
assert full_matrix["reason"] is None

# Mock / fallback / empty history -> NOT_EVALUATED, empty correlations.
for unavailable in (
    {"provider": "mock", "rows": price_rows()},
    {"provider": "yahoo", "fallback_used": True, "rows": price_rows()},
    {"provider": "yahoo", "rows": []},
):
    unavailable_matrix = engine.risk_matrix(
        SYMBOLS, state=state_with(SYMBOLS), price_history=unavailable
    )
    assert unavailable_matrix["status"] == "NOT_EVALUATED"
    assert unavailable_matrix["correlations"] == {}
    assert unavailable_matrix["pairs_evaluated"] == 0
    assert unavailable_matrix["policy"]["feeds_risk_gate"] is True

# Fewer than two symbols -> NOT_EVALUATED.
single_matrix = engine.risk_matrix(
    ["AAPL"], state=state_with(["AAPL"]), price_history=REAL_HISTORY
)
assert single_matrix["status"] == "NOT_EVALUATED"
assert single_matrix["correlations"] == {}

# Symbols are normalized (case-insensitive, de-duplicated).
normalized_matrix = engine.risk_matrix(
    ["aapl", "AAPL", "msft"], state=state_with(SYMBOLS), price_history=REAL_HISTORY
)
assert normalized_matrix["symbols_requested"] == ["AAPL", "MSFT"]
assert normalized_matrix["correlations"]["AAPL"]["MSFT"] == 1.0


print("CorrelationEngine test passed.")
