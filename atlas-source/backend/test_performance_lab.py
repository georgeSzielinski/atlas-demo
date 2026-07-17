from engines.performance_lab_engine import PerformanceLabEngine

REQUIRED_POLICY_KEYS = {
    "read_only",
    "descriptive_only",
    "deterministic",
    "paper_only",
    "broker_integration",
    "real_money",
    "does_not_modify_recommendations",
    "does_not_modify_trades",
    "does_not_modify_risk_limits",
    "does_not_place_orders",
}

# Portfolio history: five snapshots with daily and cumulative returns, plus an
# aligned benchmark daily-return series so beta is computable.
HISTORY = [
    {"id": 1, "date": "2026-06-01", "portfolio_value": 100000, "daily_return": 0.0,
     "total_return": 0.0, "benchmark_return": 0.0},
    {"id": 2, "date": "2026-06-02", "portfolio_value": 101000, "daily_return": 1.0,
     "total_return": 1.0, "benchmark_return": 0.5},
    {"id": 3, "date": "2026-06-03", "portfolio_value": 100500, "daily_return": -0.5,
     "total_return": 0.5, "benchmark_return": -0.3},
    {"id": 4, "date": "2026-06-04", "portfolio_value": 102000, "daily_return": 1.5,
     "total_return": 2.0, "benchmark_return": 0.9},
    {"id": 5, "date": "2026-06-05", "portfolio_value": 103500, "daily_return": 1.47,
     "total_return": 3.5, "benchmark_return": 1.1},
]

PERFORMANCE_REPORTS = [{
    "performance": {
        "benchmark_comparison": [
            {"benchmark": "S&P 500", "benchmark_return": 2.2, "alpha": 1.3},
        ],
    },
}]


def _trade(ticker, pl, holding, snapshot, exit_price=100):
    return {
        "trade_id": f"T-{ticker}-{pl}",
        "ticker": ticker,
        "action": "BUY",
        "entry_date": "2026-06-01",
        "exit_date": "2026-06-05",
        "entry_price": 90,
        "exit_price": exit_price,
        "holding_period": holding,
        "quantity": 10,
        "profit_loss": pl,
        "recommendation_snapshot": snapshot,
    }


def _committee(*actions):
    return [
        {"member_id": f"strat_{i}", "member_name": f"Strategy {i}", "action": action}
        for i, action in enumerate(actions)
    ]


# Winners have high technical/fundamental scores and bullish committee votes;
# losers have low scores and (partly) bearish votes. This makes technical a
# predictive signal and strat_0 (always BUY) accurate on winners only.
TRADES = [
    _trade("AAPL", 500, 10, {
        "technical_score": 80, "fundamental_score": 75, "forecast_score": 60,
        "news_confidence": 70,
        "committee_members": _committee("BUY", "BUY", "HOLD"),
    }),
    _trade("MSFT", 300, 6, {
        "technical_score": 78, "fundamental_score": 72, "forecast_score": 55,
        "news_confidence": 65,
        "committee_members": _committee("BUY", "AVOID", "BUY"),
    }),
    _trade("NVDA", 700, 12, {
        "technical_score": 85, "fundamental_score": 80, "forecast_score": 62,
        "news_confidence": 72,
        "committee_members": _committee("BUY", "BUY", "BUY"),
    }),
    _trade("AMD", -200, 8, {
        "technical_score": 40, "fundamental_score": 45, "forecast_score": 58,
        "news_confidence": 50,
        "committee_members": _committee("BUY", "AVOID", "AVOID"),
    }, exit_price=80),
    _trade("INTC", -350, 9, {
        "technical_score": 35, "fundamental_score": 42, "forecast_score": 61,
        "news_confidence": 48,
        "committee_members": _committee("BUY", "AVOID", "SELL"),
    }, exit_price=75),
    # Open trade (no exit) must be ignored everywhere.
    {"trade_id": "OPEN", "ticker": "TSLA", "action": "BUY", "exit_price": None,
     "profit_loss": 0, "recommendation_snapshot": {}},
]


engine = PerformanceLabEngine()
report = engine.generate(
    history=HISTORY,
    trades=TRADES,
    performance_reports=PERFORMANCE_REPORTS,
)
repeated = engine.generate(
    history=HISTORY,
    trades=TRADES,
    performance_reports=PERFORMANCE_REPORTS,
)

# Determinism.
assert report == repeated, "PerformanceLabEngine must be deterministic."

# Policy.
assert REQUIRED_POLICY_KEYS.issubset(report["policy"].keys())
assert report["policy"]["read_only"] is True
assert report["policy"]["paper_only"] is True

# --- Portfolio analytics ---
portfolio = report["portfolio_analytics"]
assert portfolio["status"] == "EVALUATED"
assert portfolio["equity_curve"]["sample_size"] == 5
assert portfolio["equity_curve"]["latest_value"] == 103500
assert portfolio["equity_curve"]["cumulative_return"] == 3.5
risk = portfolio["risk_adjusted"]
assert risk["status"] == "EVALUATED"
for metric in ("sharpe", "sortino", "volatility", "max_drawdown"):
    assert metric in risk
assert risk["worst_day"] == -0.5
assert risk["best_day"] == 1.5
assert risk["calmar"]["status"] == "EVALUATED"
benchmark = portfolio["benchmark"]
assert benchmark["status"] == "EVALUATED"
assert benchmark["alpha"] == 1.3
assert benchmark["beta"]["status"] == "EVALUATED"
assert benchmark["beta"]["sample_size"] == 5

# --- Trade analytics ---
trade = report["trade_analytics"]
assert trade["status"] == "EVALUATED"
assert trade["closed_trades"] == 5
assert trade["wins"] == 3
assert trade["losses"] == 2
assert trade["win_rate"] == 60.0
assert trade["average_winner"] == 500.0  # (500+300+700)/3
assert trade["average_loser"] == -275.0  # (-200-350)/2
assert trade["gross_profit"] == 1500.0
assert trade["gross_loss"] == 550.0
assert trade["profit_factor"]["status"] == "EVALUATED"
assert trade["profit_factor"]["value"] == round(1500.0 / 550.0, 4)
assert trade["expectancy"] == round((500 + 300 + 700 - 200 - 350) / 5, 4)
assert trade["best_trade"]["ticker"] == "NVDA"
assert trade["worst_trade"]["ticker"] == "INTC"
assert trade["average_holding_period"] == 9.0  # (10+6+12+8+9)/5

# --- Committee attribution ---
committee = report["committee_attribution"]
assert committee["status"] == "EVALUATED"
assert committee["trades_with_votes"] == 5
member_by_id = {row["member_id"]: row for row in committee["members"]}
# strat_0 always votes BUY -> correct only on the 3 winners, wrong on 2 losers.
assert member_by_id["strat_0"]["evaluated"] == 5
assert member_by_id["strat_0"]["correct"] == 3
assert member_by_id["strat_0"]["accuracy"] == 60.0
# strategies mirror members for the milestone's "most accurate strategy".
assert committee["strategies"] == committee["members"]
assert committee["most_accurate"]["accuracy"] >= committee["least_accurate"]["accuracy"]
rolling = committee["rolling_accuracy"]
assert rolling["status"] == "EVALUATED"
assert len(rolling["points"]) == 5

# --- Research attribution ---
research = report["research_attribution"]
assert research["status"] == "EVALUATED"
signal_by_name = {row["signal"]: row for row in research["signals"]}
technical = signal_by_name["Technical"]
assert technical["status"] == "EVALUATED"
assert technical["lift"] > 0  # winners scored higher than losers
assert technical["verdict"] == "PREDICTIVE"
assert research["most_predictive"]["signal"] in {"Technical", "Fundamental"}

# ----------------------------------------------------------------------
# NOT_EVALUATED discipline: empty inputs never fabricate metrics.
# ----------------------------------------------------------------------
empty = engine.generate(history=[], trades=[], performance_reports=[])
assert empty["portfolio_analytics"]["status"] == "NOT_EVALUATED"
assert empty["trade_analytics"]["status"] == "NOT_EVALUATED"
assert empty["committee_attribution"]["status"] == "NOT_EVALUATED"
assert empty["research_attribution"]["status"] == "NOT_EVALUATED"
assert len(empty["not_evaluated"]) == 4

# Single snapshot -> portfolio analytics NOT_EVALUATED but equity curve present.
single = engine.generate(
    history=[HISTORY[0]], trades=[], performance_reports=[]
)
assert single["portfolio_analytics"]["status"] == "NOT_EVALUATED"
assert single["portfolio_analytics"]["equity_curve"]["sample_size"] == 1

# No committee votes -> committee NOT_EVALUATED but trades still analyzed.
no_votes = engine.generate(
    history=HISTORY,
    trades=[_trade("AAPL", 100, 5, {"technical_score": 50})],
    performance_reports=[],
)
assert no_votes["committee_attribution"]["status"] == "NOT_EVALUATED"
assert no_votes["trade_analytics"]["status"] == "EVALUATED"

# Beta is NOT_EVALUATED when no aligned benchmark series is stored.
history_no_bench = [
    {k: v for k, v in row.items() if k != "benchmark_return"}
    for row in HISTORY
]
no_beta = engine.generate(
    history=history_no_bench, trades=[], performance_reports=PERFORMANCE_REPORTS
)
no_beta_benchmark = no_beta["portfolio_analytics"]["benchmark"]
assert no_beta_benchmark["status"] == "EVALUATED"
assert no_beta_benchmark["alpha"] == 1.3
assert no_beta_benchmark["beta"]["status"] == "NOT_EVALUATED"

print("PerformanceLabEngine test passed.")
