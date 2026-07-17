def execute_trades(buy_plan):
    print("\nExecuting Trades:")

    for trade in buy_plan:
        print("--------------------------------")
        print("BUY:", trade["ticker"])
        print("Type:", trade["type"])
        print("Amount: $", round(trade["amount"], 2))

    print("\nAll approved trades have been prepared.")