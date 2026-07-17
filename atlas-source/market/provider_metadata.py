def provider_metadata(
    supported_tickers=None,
    coverage="",
    earliest_date=None,
    latest_date=None,
    update_frequency="",
    known_limitations=None,
):
    return {
        "supported_tickers": supported_tickers or [],
        "coverage": coverage,
        "earliest_date": earliest_date,
        "latest_date": latest_date,
        "update_frequency": update_frequency,
        "known_limitations": known_limitations or [],
    }
