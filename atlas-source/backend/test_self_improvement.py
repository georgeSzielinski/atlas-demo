from engines.self_improvement_engine import SelfImprovementEngine

REQUIRED_POLICY_KEYS = {
    "read_only",
    "research_only",
    "deterministic",
    "uses_llm",
    "uses_randomness",
    "changes_strategies",
    "changes_weights",
    "changes_committee",
    "changes_trading_behavior",
    "changes_risk_limits",
    "real_money",
}

REQUIRED_FINDING_KEYS = {
    "id",
    "category",
    "title",
    "status",
    "confidence",
    "confidence_label",
    "sample_size",
    "statistics",
    "explanation",
    "recommendation",
    "policy",
}


def _committee(*actions):
    return [
        {"member_id": f"strat_{i}", "member_name": f"Strategy {i}", "action": action}
        for i, action in enumerate(actions)
    ]


def _trade(ticker, pl, exit_date, snapshot, holding=5, exit_price=100):
    return {
        "trade_id": f"T-{ticker}-{exit_date}",
        "ticker": ticker,
        "action": "BUY",
        "entry_date": "2026-05-25",
        "entry_price": 90,
        "exit_date": exit_date,
        "exit_price": exit_price,
        "holding_period": holding,
        "quantity": 10,
        "profit_loss": pl,
        "recommendation_snapshot": snapshot,
    }


def _snap(strategy, sector, regime, forecast, rsi, votes, technical=None):
    snapshot = {
        "strategy": strategy,
        "sector": sector,
        "market_regime": regime,
        "forecast_score": forecast,
        "rsi": rsi,
        "committee_members": votes,
    }
    if technical is not None:
        snapshot["technical_score"] = technical
    return snapshot


# Momentum wins in Bull/Technology; Quality loses in Bear. Forecast stays
# predictive throughout; RSI is strongly predictive in the older half and loses
# its edge in the recent half (so it must surface as "less predictive").
TRADES = [
    # --- older half (winners RSI high, losers RSI low) ---
    _trade("AAPL", 500, "2026-06-01",
           _snap("Momentum", "Technology", "Bull", 80, 80, _committee("BUY", "BUY", "HOLD")), holding=12),
    _trade("MSFT", 400, "2026-06-02",
           _snap("Momentum", "Technology", "Bull", 78, 75, _committee("BUY", "BUY", "BUY")), holding=11),
    _trade("PFE", -200, "2026-06-03",
           _snap("Quality", "Healthcare", "Bear", 40, 35, _committee("BUY", "AVOID", "AVOID")), holding=5, exit_price=80),
    _trade("MRK", -300, "2026-06-04",
           _snap("Quality", "Healthcare", "Bear", 42, 30, _committee("BUY", "AVOID", "SELL")), holding=4, exit_price=75),
    _trade("NVDA", 300, "2026-06-05",
           _snap("Momentum", "Technology", "Bull", 76, 78, _committee("BUY", "BUY", "BUY")), holding=10),
    _trade("XOM", -150, "2026-06-06",
           _snap("Quality", "Energy", "Bear", 45, 38, _committee("BUY", "AVOID", "AVOID")), holding=6, exit_price=85),
    # --- recent half (winners and losers have similar RSI -> edge gone) ---
    _trade("GOOG", 350, "2026-06-07",
           _snap("Momentum", "Technology", "Bull", 82, 50, _committee("BUY", "BUY", "HOLD")), holding=9),
    _trade("ABBV", -250, "2026-06-08",
           _snap("Quality", "Healthcare", "Bear", 38, 52, _committee("BUY", "AVOID", "SELL")), holding=4, exit_price=78),
    _trade("META", 450, "2026-06-09",
           _snap("Momentum", "Technology", "Bull", 85, 48, _committee("BUY", "BUY", "BUY")), holding=13),
    _trade("CVX", -180, "2026-06-10",
           _snap("Quality", "Energy", "Bear", 41, 51, _committee("BUY", "AVOID", "AVOID")), holding=6, exit_price=82),
    _trade("AMD", 250, "2026-06-11",
           _snap("Momentum", "Technology", "Bull", 79, 49, _committee("BUY", "BUY", "BUY")), holding=8),
    _trade("BMY", -220, "2026-06-12",
           _snap("Quality", "Healthcare", "Bear", 39, 50, _committee("BUY", "AVOID", "SELL")), holding=5, exit_price=79),
    # Open trade must be ignored everywhere.
    {"trade_id": "OPEN", "ticker": "TSLA", "action": "BUY", "exit_price": None,
     "profit_loss": 0, "recommendation_snapshot": {}},
]

HISTORY = [
    {"id": 1, "date": "2026-06-01", "portfolio_value": 100000},
    {"id": 2, "date": "2026-06-02", "portfolio_value": 102000},
    {"id": 3, "date": "2026-06-03", "portfolio_value": 101000},
    {"id": 4, "date": "2026-06-04", "portfolio_value": 99000},
    {"id": 5, "date": "2026-06-05", "portfolio_value": 100500},
    {"id": 6, "date": "2026-06-06", "portfolio_value": 103000},
]

RISK_DECISIONS = [
    {"decision_id": "d1", "symbol": "AAPL", "side": "BUY", "verdict": "APPROVED", "checks": {}},
    {"decision_id": "d2", "symbol": "MSFT", "side": "BUY", "verdict": "APPROVED", "checks": {}},
    {"decision_id": "d3", "symbol": "NVDA", "side": "BUY", "verdict": "REJECTED",
     "checks": {"rejections": [{"reason": "Buy order value exceeds available cash"}]}},
    {"decision_id": "d4", "symbol": "NVDA", "side": "BUY", "verdict": "REJECTED",
     "checks": {"rejections": [{"reason": "Buy order value exceeds available cash"}]}},
    {"decision_id": "d5", "symbol": "META", "side": "BUY", "verdict": "REJECTED",
     "checks": {"rejections": [{"reason": "Correlation with held position exceeds limit"}]}},
    {"decision_id": "d6", "symbol": "AMD", "side": "SELL", "verdict": "REJECTED",
     "checks": {"rejections": [{"reason": "Sell quantity exceeds current holdings"}]}},
]

CONSTRUCTION_REPORTS = [
    {"id": 1, "date": "2026-06-01", "diversification": {"diversification_score": 70, "concentration_score": 40},
     "risk_summary": {"risk_budget": "Moderate"}},
    {"id": 2, "date": "2026-06-02", "diversification": {"diversification_score": 72, "concentration_score": 38},
     "risk_summary": {"risk_budget": "Moderate"}},
    {"id": 3, "date": "2026-06-03", "diversification": {"diversification_score": 78, "concentration_score": 33},
     "risk_summary": {"risk_budget": "Low"}},
]


engine = SelfImprovementEngine()
report = engine.generate(
    trades=TRADES,
    history=HISTORY,
    risk_decisions=RISK_DECISIONS,
    construction_reports=CONSTRUCTION_REPORTS,
)
repeated = engine.generate(
    trades=TRADES,
    history=HISTORY,
    risk_decisions=RISK_DECISIONS,
    construction_reports=CONSTRUCTION_REPORTS,
)

# --- Determinism ---
assert report == repeated, "SelfImprovementEngine must be deterministic."

# --- Policy: research only, never changes live behavior ---
assert REQUIRED_POLICY_KEYS.issubset(report["policy"].keys())
assert report["policy"]["read_only"] is True
assert report["policy"]["research_only"] is True
assert report["policy"]["uses_llm"] is False
assert report["policy"]["uses_randomness"] is False
for key in (
    "changes_strategies",
    "changes_weights",
    "changes_committee",
    "changes_trading_behavior",
    "changes_risk_limits",
):
    assert report["policy"][key] is False

# --- Every domain evaluated with this rich evidence ---
domains = report["domains"]
for name in SelfImprovementEngine.DOMAINS:
    assert name in domains, f"missing domain {name}"
    assert domains[name]["status"] == "EVALUATED", (name, domains[name])
assert report["not_evaluated"] == []
assert report["status"] == "EVALUATED"

# --- Findings well-formed and ranked by confidence (desc) ---
findings = report["findings"]
assert len(findings) >= 9
for finding in findings:
    assert REQUIRED_FINDING_KEYS.issubset(finding.keys()), finding.keys()
    assert 0.0 <= finding["confidence"] <= 1.0
    assert finding["confidence_label"] in {"Low", "Moderate", "High"}
    assert finding["sample_size"] >= 1
    assert finding["explanation"] and finding["recommendation"]
    assert finding["status"] == "EVALUATED"
confidences = [finding["confidence"] for finding in findings]
assert confidences == sorted(confidences, reverse=True), "findings must rank by confidence"

# Opportunities mirror findings.
assert len(report["opportunities"]) == len(findings)
assert {o["id"] for o in report["opportunities"]} == {f["id"] for f in findings}

by_id = {finding["id"]: finding for finding in findings}

# --- Strategy performance: Momentum outperforms Quality ---
strategy = by_id["strategy-outperformance"]["statistics"]
assert strategy["best_strategy"] == "Momentum"
assert strategy["worst_strategy"] == "Quality"
assert strategy["best_average_pl"] > strategy["worst_average_pl"]

# --- Committee: strat_1 is the most accurate member (100%) ---
committee = by_id["committee-top-member"]["statistics"]
assert committee["top_member_id"] == "strat_1"
assert committee["accuracy"] == 100.0

# --- Signals: Forecast predictive, RSI degrading ---
forecast = by_id["signal-forecast_score"]["statistics"]
assert forecast["verdict"] == "PREDICTIVE"
assert forecast["lift"] > 0
rsi = by_id["signal-rsi"]["statistics"]
assert rsi["verdict"] == "DEGRADING"
assert rsi["trend"]["degrading"] is True
assert rsi["trend"]["older_lift"] > rsi["trend"]["recent_lift"]
assert "less predictive" in by_id["signal-rsi"]["title"]

# --- Sector: Technology dominates ---
sector = by_id["sector-dominance"]["statistics"]
assert sector["leading_sector"] == "Technology"
assert sector["dominance_share"] > 0

# --- Regime: Bull best, Momentum leads within it ---
regime = by_id["regime-best"]["statistics"]
assert regime["best_regime"] == "Bull"
assert regime["worst_regime"] == "Bear"
assert regime["best_regime_top_strategy"]["key"] == "Momentum"
assert "Momentum performs best during Bull" in by_id["regime-best"]["title"]

# --- Construction: diversification improving ---
construction = by_id["construction-diversification-trend"]["statistics"]
assert construction["direction"] == "improving"
assert construction["latest_diversification"] == 78

# --- Risk: rejection rate + top reason ---
risk = by_id["risk-rejection-rate"]["statistics"]
assert risk["evaluated"] == 6
assert risk["rejected"] == 4
assert risk["rejection_rate"] == round(4 / 6 * 100, 2)
assert risk["top_reason"]["reason"] == "Buy order value exceeds available cash"
assert risk["top_reason"]["count"] == 2

# --- Drawdowns: peak-to-trough measured ---
drawdown = by_id["drawdown-depth"]["statistics"]
assert drawdown["snapshots"] == 6
assert drawdown["max_drawdown_percent"] < 0  # 102000 -> 99000

# --- Trade quality: winners vs losers ---
quality = by_id["trade-quality-holding-edge"]["statistics"]
assert quality["closed_trades"] == 12
assert quality["wins"] == 6
assert quality["losses"] == 6
assert quality["win_rate"] == 50.0
assert quality["holding_edge_days"] is not None

# --- Headline mentions the top opportunity ---
assert report["headline"]
assert report["source_counts"]["closed_trades"] == 12

# ----------------------------------------------------------------------
# NOT_EVALUATED discipline: no evidence -> no fabricated findings.
# ----------------------------------------------------------------------
empty = engine.generate(
    trades=[], history=[], risk_decisions=[], construction_reports=[]
)
assert empty["status"] == "NOT_EVALUATED"
assert empty["findings"] == []
assert empty["opportunities"] == []
assert len(empty["not_evaluated"]) == len(SelfImprovementEngine.DOMAINS)
for name in SelfImprovementEngine.DOMAINS:
    assert empty["domains"][name]["status"] == "NOT_EVALUATED"
    assert empty["domains"][name]["reason"]

# Thin evidence: a single strategy / one closed trade never fabricates a group
# comparison, but trade_quality still needs a winner AND a loser.
thin = engine.generate(
    trades=[
        _trade("AAPL", 100, "2026-06-01",
               _snap("Momentum", "Technology", "Bull", 70, 60, _committee("BUY"))),
    ],
    history=[HISTORY[0]],
    risk_decisions=[RISK_DECISIONS[0]],
    construction_reports=[CONSTRUCTION_REPORTS[0]],
)
assert thin["domains"]["strategy_performance"]["status"] == "NOT_EVALUATED"
assert thin["domains"]["sector_performance"]["status"] == "NOT_EVALUATED"
assert thin["domains"]["drawdowns"]["status"] == "NOT_EVALUATED"
assert thin["domains"]["risk_decisions"]["status"] == "NOT_EVALUATED"
assert thin["domains"]["trade_quality"]["status"] == "NOT_EVALUATED"

# ----------------------------------------------------------------------
# Live paper-fund evidence: the fund persists fills as FILLED_SIMULATED,
# and those fills must reach FIFO round-trip accounting. Rejected, proposed,
# and open orders never become closed trades.
# ----------------------------------------------------------------------
import database.repository as repository

assert engine.LIVE_FUND_FILL_STATUSES == {"FILLED", "FILLED_SIMULATED"}


def _live_order(ticker, side, quantity, price, at, status="FILLED_SIMULATED"):
    filled = status in SelfImprovementEngine.LIVE_FUND_FILL_STATUSES
    return {
        "order_id": f"order-{ticker}-{side}-{at}",
        "ticker": ticker,
        "side": side,
        "quantity": quantity,
        "status": status,
        "fill_price": price if filled else None,
        "created_at": at,
        "filled_at": at if filled else None,
    }


# Chronological order below; the repository reader returns newest first.
LIVE_FUND_ORDERS = list(reversed([
    _live_order("AAPL", "BUY", 10, 100.0, "2026-06-01T10:00:00"),
    _live_order("MSFT", "BUY", 5, 200.0, "2026-06-02T10:00:00"),
    _live_order("NVDA", "BUY", 4, 50.0, "2026-06-02T11:00:00", status="REJECTED"),
    _live_order("NVDA", "BUY", 4, 50.0, "2026-06-02T12:00:00", status="PROPOSED"),
    _live_order("AAPL", "SELL", 10, 110.0, "2026-06-03T10:00:00"),
    _live_order("MSFT", "SELL", 5, 180.0, "2026-06-04T10:00:00"),
    _live_order("GOOG", "BUY", 3, 150.0, "2026-06-05T10:00:00"),  # still open
]))

original_get_orders = repository.get_paper_fund_orders
repository.get_paper_fund_orders = lambda limit=None: LIVE_FUND_ORDERS
try:
    round_trips = engine._live_fund_round_trips(limit=50)
finally:
    repository.get_paper_fund_orders = original_get_orders

# One FILLED_SIMULATED BUY+SELL pair per ticker -> one round trip each.
assert len(round_trips) == 2, round_trips
by_ticker = {trip["ticker"]: trip for trip in round_trips}
assert by_ticker["AAPL"]["entry_price"] == 100.0
assert by_ticker["AAPL"]["exit_price"] == 110.0
assert by_ticker["AAPL"]["quantity"] == 10
assert by_ticker["AAPL"]["profit_loss"] == 100.0
assert by_ticker["AAPL"]["holding_period"] == 2
assert by_ticker["MSFT"]["profit_loss"] == -100.0
# Open BUY without a SELL and rejected/proposed orders produce nothing.
assert "GOOG" not in by_ticker
assert "NVDA" not in by_ticker

# ----------------------------------------------------------------------
# End to end: with no replay trades, live-fund fills alone are enough
# evidence for the trade-based domains that apply to them.
# ----------------------------------------------------------------------
RICH_LIVE_FUND_ORDERS = list(reversed([
    _live_order("AAPL", "BUY", 10, 100.0, "2026-06-01T10:00:00"),
    _live_order("MSFT", "BUY", 5, 200.0, "2026-06-01T11:00:00"),
    _live_order("NVDA", "BUY", 8, 50.0, "2026-06-02T10:00:00"),
    _live_order("GOOG", "BUY", 2, 150.0, "2026-06-02T11:00:00"),
    _live_order("AAPL", "SELL", 10, 112.0, "2026-06-08T10:00:00"),
    _live_order("MSFT", "SELL", 5, 188.0, "2026-06-09T10:00:00"),
    _live_order("NVDA", "SELL", 8, 57.0, "2026-06-10T10:00:00"),
    _live_order("GOOG", "SELL", 2, 141.0, "2026-06-11T10:00:00"),
]))

original_get_orders = repository.get_paper_fund_orders
original_get_trades = repository.get_paper_trades
repository.get_paper_fund_orders = lambda limit=None: RICH_LIVE_FUND_ORDERS
repository.get_paper_trades = lambda limit=None: []
try:
    live_report = engine.generate(
        history=HISTORY,
        risk_decisions=RISK_DECISIONS,
        construction_reports=CONSTRUCTION_REPORTS,
    )
finally:
    repository.get_paper_fund_orders = original_get_orders
    repository.get_paper_trades = original_get_trades

# All four closed live-fund round trips arrived as evidence...
assert live_report["source_counts"]["trades"] == 4
assert live_report["source_counts"]["closed_trades"] == 4
assert live_report["status"] == "EVALUATED"
# ...and the trade-based domain with enough evidence (2 winners, 2 losers)
# is actually evaluated from live fills alone.
assert live_report["domains"]["trade_quality"]["status"] == "EVALUATED"
quality_ids = {
    finding["id"] for finding in live_report["domains"]["trade_quality"]["findings"]
}
assert "trade-quality-holding-edge" in quality_ids
live_quality = next(
    finding for finding in live_report["findings"]
    if finding["id"] == "trade-quality-holding-edge"
)
assert live_quality["statistics"]["closed_trades"] == 4
assert live_quality["statistics"]["wins"] == 2
assert live_quality["statistics"]["losses"] == 2

print("SelfImprovementEngine test passed.")
