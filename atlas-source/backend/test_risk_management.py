from engines.risk_management_engine import RiskManagementEngine


engine = RiskManagementEngine()


def approval(order, portfolio=None, limits=None, market_data=None):
    return engine.evaluate(
        order=order,
        portfolio=portfolio or base_portfolio(),
        limits=limits or base_limits(),
        market_data=market_data,
    )


def base_portfolio():
    return {
        "cash": 5000,
        "positions": {
            "AAPL": {"quantity": 10, "price": 100, "sector": "Technology"},
            "JNJ": {"quantity": 5, "price": 100, "sector": "Healthcare"},
        },
    }


def base_limits():
    return {
        "max_position_size": 0.50,
        "max_portfolio_exposure": 0.80,
        "minimum_cash_reserve": 1000,
        "max_sector_exposure": 0.60,
        "max_position_count": 4,
        "max_correlation": 0.75,
    }


def check(result, rule):
    matches = [item for item in result["checks"] if item["rule"] == rule]
    assert len(matches) == 1
    return matches[0]


def assert_rejection_explained(result, rule):
    item = check(result, rule)
    assert item["status"] == "REJECTED"
    assert item["rule"] == rule
    assert item["limit"] is not None
    assert item["measured"] is not None
    assert isinstance(item["reason"], str)
    assert item["reason"]
    assert item in result["rejections"]


# Approved order includes safety fields and a full check report.
approved = approval({"symbol": "MSFT", "side": "BUY", "quantity": 5, "price": 100, "sector": "Technology"})
assert approved["status"] == "APPROVED"
assert approved["approved"] is True
assert approved["paper_only"] is True
assert approved["broker_integration"] is False
assert approved["real_money"] is False
assert approved["human_approval_required_for_real_trading"] is True
assert len(approved["checks"]) == 8
assert {item["rule"] for item in approved["checks"]} == {
    "affordability",
    "sell_quantity_not_exceeding_holdings",
    "minimum_cash_reserve",
    "max_position_size",
    "max_portfolio_exposure",
    "sector_exposure",
    "max_position_count",
    "correlation",
}

# Correlation exists but is explicitly not evaluated when data is unavailable.
correlation = check(approved, "correlation")
assert correlation["status"] == "NOT_EVALUATED"
assert correlation["measured"] is None
assert "unavailable" in correlation["reason"].lower()

# Max position size pass, fail, and boundary.
position_pass = approval({"symbol": "MSFT", "side": "BUY", "quantity": 5, "price": 100, "sector": "Technology"})
assert check(position_pass, "max_position_size")["status"] == "APPROVED"

position_fail = approval({"symbol": "MSFT", "side": "BUY", "quantity": 40, "price": 100, "sector": "Technology"})
assert position_fail["status"] == "REJECTED"
assert_rejection_explained(position_fail, "max_position_size")

position_boundary = approval({"symbol": "MSFT", "side": "BUY", "quantity": 32.5, "price": 100, "sector": "Technology"}, limits={**base_limits(), "max_position_size": 0.50})
assert check(position_boundary, "max_position_size")["status"] == "APPROVED"

# Max portfolio exposure pass, fail, and boundary.
exposure_pass = approval({"symbol": "MSFT", "side": "BUY", "quantity": 5, "price": 100, "sector": "Technology"})
assert check(exposure_pass, "max_portfolio_exposure")["status"] == "APPROVED"

exposure_fail = approval({"symbol": "MSFT", "side": "BUY", "quantity": 38, "price": 100, "sector": "Industrial"}, limits={**base_limits(), "max_position_size": 1, "max_sector_exposure": 1})
assert exposure_fail["status"] == "REJECTED"
assert_rejection_explained(exposure_fail, "max_portfolio_exposure")

exposure_boundary = approval({"symbol": "MSFT", "side": "BUY", "quantity": 37, "price": 100, "sector": "Industrial"}, limits={**base_limits(), "max_position_size": 1, "max_sector_exposure": 1})
assert check(exposure_boundary, "max_portfolio_exposure")["status"] == "APPROVED"

# Minimum cash reserve pass, fail, and boundary.
reserve_pass = approval({"symbol": "MSFT", "side": "BUY", "quantity": 35, "price": 100, "sector": "Industrial"}, limits={**base_limits(), "max_position_size": 1, "max_sector_exposure": 1, "max_portfolio_exposure": 1})
assert check(reserve_pass, "minimum_cash_reserve")["status"] == "APPROVED"

reserve_fail = approval({"symbol": "MSFT", "side": "BUY", "quantity": 41, "price": 100, "sector": "Industrial"}, limits={**base_limits(), "max_position_size": 1, "max_sector_exposure": 1, "max_portfolio_exposure": 1})
assert reserve_fail["status"] == "REJECTED"
assert_rejection_explained(reserve_fail, "minimum_cash_reserve")

reserve_boundary = approval({"symbol": "MSFT", "side": "BUY", "quantity": 40, "price": 100, "sector": "Industrial"}, limits={**base_limits(), "max_position_size": 1, "max_sector_exposure": 1, "max_portfolio_exposure": 1})
assert check(reserve_boundary, "minimum_cash_reserve")["status"] == "APPROVED"

# Sector exposure pass, fail, and boundary.
sector_pass = approval({"symbol": "MSFT", "side": "BUY", "quantity": 5, "price": 100, "sector": "Technology"})
assert check(sector_pass, "sector_exposure")["status"] == "APPROVED"

sector_fail = approval({"symbol": "MSFT", "side": "BUY", "quantity": 30, "price": 100, "sector": "Technology"}, limits={**base_limits(), "max_position_size": 1, "max_portfolio_exposure": 1, "minimum_cash_reserve": 0})
assert sector_fail["status"] == "REJECTED"
assert_rejection_explained(sector_fail, "sector_exposure")

sector_boundary = approval({"symbol": "MSFT", "side": "BUY", "quantity": 29, "price": 100, "sector": "Technology"}, limits={**base_limits(), "max_position_size": 1, "max_portfolio_exposure": 1, "minimum_cash_reserve": 0})
assert check(sector_boundary, "sector_exposure")["status"] == "APPROVED"

# Max position count pass, fail, and boundary.
count_pass = approval({"symbol": "MSFT", "side": "BUY", "quantity": 1, "price": 100, "sector": "Technology"})
assert check(count_pass, "max_position_count")["status"] == "APPROVED"

count_fail = approval(
    {"symbol": "MSFT", "side": "BUY", "quantity": 1, "price": 100, "sector": "Technology"},
    portfolio={
        "cash": 5000,
        "positions": {
            "AAPL": {"quantity": 1, "price": 100, "sector": "Technology"},
            "JNJ": {"quantity": 1, "price": 100, "sector": "Healthcare"},
            "PG": {"quantity": 1, "price": 100, "sector": "Consumer"},
            "XOM": {"quantity": 1, "price": 100, "sector": "Energy"},
        },
    },
    limits={**base_limits(), "max_position_size": 1, "max_sector_exposure": 1, "max_portfolio_exposure": 1},
)
assert count_fail["status"] == "REJECTED"
assert_rejection_explained(count_fail, "max_position_count")

count_boundary = approval(
    {"symbol": "MSFT", "side": "BUY", "quantity": 1, "price": 100, "sector": "Technology"},
    portfolio={
        "cash": 5000,
        "positions": {
            "AAPL": {"quantity": 1, "price": 100, "sector": "Technology"},
            "JNJ": {"quantity": 1, "price": 100, "sector": "Healthcare"},
            "PG": {"quantity": 1, "price": 100, "sector": "Consumer"},
        },
    },
)
assert check(count_boundary, "max_position_count")["status"] == "APPROVED"

# Affordability rejects unaffordable buys without clipping.
unaffordable = approval({"symbol": "MSFT", "side": "BUY", "quantity": 51, "price": 100, "sector": "Industrial"}, limits={**base_limits(), "max_position_size": 1, "max_sector_exposure": 1, "max_portfolio_exposure": 1, "minimum_cash_reserve": 0})
assert unaffordable["status"] == "REJECTED"
assert unaffordable["order"]["requested_quantity"] == 51
assert unaffordable["order"]["quantity"] == 51
assert_rejection_explained(unaffordable, "affordability")

# Oversells reject without clipping.
oversell = approval({"symbol": "AAPL", "side": "SELL", "quantity": 11, "price": 100, "sector": "Technology"})
assert oversell["status"] == "REJECTED"
assert oversell["order"]["requested_quantity"] == 11
assert oversell["order"]["quantity"] == 11
assert_rejection_explained(oversell, "sell_quantity_not_exceeding_holdings")

# Correlation can pass or fail when data is available.
correlation_pass = approval(
    {"symbol": "MSFT", "side": "BUY", "quantity": 1, "price": 100, "sector": "Technology"},
    market_data={"correlations": {"MSFT": {"AAPL": 0.60}}},
)
assert check(correlation_pass, "correlation")["status"] == "APPROVED"

correlation_fail = approval(
    {"symbol": "MSFT", "side": "BUY", "quantity": 1, "price": 100, "sector": "Technology"},
    market_data={"correlations": {"MSFT": {"AAPL": 0.90}}},
)
assert correlation_fail["status"] == "REJECTED"
assert_rejection_explained(correlation_fail, "correlation")

# Same input produces the same output.
same_order = {"symbol": "MSFT", "side": "BUY", "quantity": 5, "price": 100, "sector": "Technology"}
same_portfolio = base_portfolio()
same_limits = base_limits()
assert engine.evaluate(same_order, same_portfolio, same_limits) == engine.evaluate(
    same_order,
    same_portfolio,
    same_limits,
)

# Deterministic sizing output with full derivation.
sizing_recommendations = [
    {
        "symbol": "MSFT",
        "action": "BUY",
        "confidence": 80,
        "base_target_weight": 0.20,
        "sector": "Technology",
    }
]
sizing_portfolio = {
    "cash": 10000,
    "positions": {},
}
sizing_market_data = {
    "prices": {"MSFT": 100},
    "volatility": {"MSFT": 0.20},
    "risk_budget": {"MSFT": {"multiplier": 0.50}},
}
sizing_policy = {"target_volatility": 0.10}
sizing_one = engine.size_positions(
    sizing_recommendations,
    portfolio=sizing_portfolio,
    market_data=sizing_market_data,
    sizing_policy=sizing_policy,
)
sizing_two = engine.size_positions(
    sizing_recommendations,
    portfolio=sizing_portfolio,
    market_data=sizing_market_data,
    sizing_policy=sizing_policy,
)
assert sizing_one == sizing_two
assert sizing_one["paper_only"] is True
assert sizing_one["broker_integration"] is False
assert sizing_one["real_money"] is False
assert sizing_one["human_approval_required_for_real_trading"] is True

sized = sizing_one["orders"][0]
assert sized["status"] == "VALID"
assert sized["order"] == {
    "symbol": "MSFT",
    "side": "BUY",
    "quantity": 4.0,
    "price": 100.0,
    "sector": "Technology",
}
derivation = sized["derivation"]
assert derivation["base_target_weight"] == 0.20
assert derivation["confidence_adjustment"]["status"] == "APPLIED"
assert derivation["confidence_adjustment"]["confidence"] == 80
assert derivation["confidence_adjustment"]["multiplier"] == 0.80
assert derivation["volatility_adjustment"]["status"] == "APPLIED"
assert derivation["volatility_adjustment"]["multiplier"] == 0.50
assert derivation["risk_budget_adjustment"]["status"] == "APPLIED"
assert derivation["risk_budget_adjustment"]["multiplier"] == 0.50
assert derivation["final_target_weight"] == 0.04
assert derivation["final_target_value"] == 400.0
assert derivation["proposed_quantity"] == 4.0
assert derivation["price_used"] == 100.0
assert derivation["skipped_adjustments"] == []

# Confidence-adjusted sizing without optional market risk data.
confidence_only = engine.size_positions(
    [
        {
            "symbol": "MSFT",
            "confidence": 50,
            "base_target_weight": 0.20,
            "sector": "Technology",
        }
    ],
    portfolio=sizing_portfolio,
    market_data={"prices": {"MSFT": 100}},
)
confidence_derivation = confidence_only["orders"][0]["derivation"]
assert confidence_derivation["final_target_weight"] == 0.10
assert confidence_derivation["final_target_value"] == 1000.0
assert confidence_only["orders"][0]["order"]["quantity"] == 10.0

# Unavailable volatility and risk budget data are recorded as SKIPPED.
skipped = confidence_derivation["skipped_adjustments"]
assert skipped == [
    {
        "adjustment": "volatility",
        "status": "SKIPPED",
        "reason": "Volatility data is unavailable; no volatility adjustment applied.",
    },
    {
        "adjustment": "risk_budget",
        "status": "SKIPPED",
        "reason": "Risk budget data is unavailable; no risk budget adjustment applied.",
    },
]
assert confidence_derivation["volatility_adjustment"]["status"] == "SKIPPED"
assert confidence_derivation["risk_budget_adjustment"]["status"] == "SKIPPED"

# Quantity calculation uses final target value, current value, and price.
existing_position_size = engine.size_positions(
    [
        {
            "symbol": "MSFT",
            "confidence": 100,
            "base_target_weight": 0.20,
            "sector": "Technology",
        }
    ],
    portfolio={
        "cash": 9000,
        "positions": {
            "MSFT": {"quantity": 5, "price": 100, "sector": "Technology"},
        },
    },
    market_data={"prices": {"MSFT": 100}},
)
existing_order = existing_position_size["orders"][0]
assert existing_order["derivation"]["final_target_value"] == 1900.0
assert existing_order["derivation"]["current_value"] == 500.0
assert existing_order["derivation"]["proposed_value"] == 1400.0
assert existing_order["order"]["quantity"] == 14.0

# Zero or invalid price is marked invalid loudly.
invalid_price = engine.size_positions(
    [{"symbol": "MSFT", "confidence": 80, "base_target_weight": 0.20}],
    portfolio=sizing_portfolio,
    market_data={"prices": {"MSFT": 0}},
)
assert invalid_price["orders"][0]["status"] == "INVALID"
assert invalid_price["orders"][0]["order"] is None
assert "positive price" in invalid_price["orders"][0]["reason"]

# Sizing output can be passed into evaluate without mutation or integration.
evaluation_from_sizing = engine.evaluate(
    sized["order"],
    portfolio=sizing_portfolio,
    limits={**base_limits(), "max_position_size": 1, "max_sector_exposure": 1},
)
assert evaluation_from_sizing["status"] == "APPROVED"
assert evaluation_from_sizing["order"]["quantity"] == sized["order"]["quantity"]
assert evaluation_from_sizing["order"]["price"] == sized["order"]["price"]

print("Risk management checks passed")
