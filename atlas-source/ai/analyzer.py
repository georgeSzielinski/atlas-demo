def analyze_stock(name, week_return, month_return, volatility):

    score = 0

    if month_return > 5:
        score += 2

    if week_return > 0:
        score += 1

    if volatility < 2:
        score += 2

    return score