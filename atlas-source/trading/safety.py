def check_buy_plan_safety(buy_plan, budget):
    for trade in buy_plan:
        if trade["amount"] <= 0:
            return False, "Trade amount must be greater than $0."

        if trade["amount"] > budget:
            return False, "A single trade cannot be larger than the full budget."

        if trade["type"] == "Stock" and trade["amount"] > budget * 0.20:
            return False, "Single stock position is too large."

    total_amount = sum(trade["amount"] for trade in buy_plan)

    if total_amount > budget:
        return False, "Buy plan is over budget."

    return True, "Buy plan passed safety checks."