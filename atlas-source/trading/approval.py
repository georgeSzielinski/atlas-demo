def ask_for_approval(buy_plan):
    print("\nPlanned Trades:")

    for trade in buy_plan:
        print("--------------------------------")
        print(trade["ticker"], "-", trade["type"])
        print("Amount: $", round(trade["amount"], 2))

    answer = input("\nApprove these trades? (yes/no): ")

    return answer.lower() == "yes"