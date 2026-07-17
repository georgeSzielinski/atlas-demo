def create_buy_plan(results, budget):
    etf_budget = budget * 0.70
    stock_budget = budget * 0.30

    top_etfs = [item for item in results if item["type"] == "ETF"][:2]
    top_stocks = [item for item in results if item["type"] == "Stock"][:2]

    buy_plan = []

    for etf in top_etfs:
        buy_plan.append({
            "ticker": etf["ticker"],
            "amount": etf_budget / len(top_etfs),
            "type": "ETF"
        })

    for stock in top_stocks:
        buy_plan.append({
            "ticker": stock["ticker"],
            "amount": stock_budget / len(top_stocks),
            "type": "Stock"
        })

    return buy_plan