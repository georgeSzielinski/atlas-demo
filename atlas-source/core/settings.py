import os


BOT_NAME = "AI Investing Bot"

BUDGET = 50
SCHEDULE = "weekly"
STYLE = "balanced"
DATA_PROVIDER = os.environ.get("DATA_PROVIDER", "mock")
SUPPORTED_DATA_PROVIDERS = ["mock", "yahoo"]
HISTORICAL_DATA_PROVIDER = os.environ.get("HISTORICAL_DATA_PROVIDER", "mock")
SUPPORTED_HISTORICAL_DATA_PROVIDERS = [
    "mock",
    "yahoo",
    "polygon",
    "alpha_vantage",
    "csv",
    "parquet",
]
NEWS_PROVIDER = os.environ.get("NEWS_PROVIDER", "fake")
SUPPORTED_NEWS_PROVIDERS = ["fake", "rss"]
FUNDAMENTAL_PROVIDER = os.environ.get("FUNDAMENTAL_PROVIDER", "mock")
SUPPORTED_FUNDAMENTAL_PROVIDERS = ["mock", "yahoo"]
CATALYST_PROVIDER = os.environ.get("CATALYST_PROVIDER", "mock")
SUPPORTED_CATALYST_PROVIDERS = [
    "mock",
    "earnings_calendar",
    "economic_calendar",
    "sec_events",
    "corporate_actions",
]
FORECAST_PROVIDER = "mock"
SUPPORTED_FORECAST_PROVIDERS = ["mock", "kronos"]
MACRO_PROVIDER = os.environ.get("MACRO_PROVIDER", "mock")
SUPPORTED_MACRO_PROVIDERS = ["mock", "fred"]
PORTFOLIO_PROVIDER = os.environ.get("PORTFOLIO_PROVIDER", "local")
SUPPORTED_PORTFOLIO_PROVIDERS = ["local"]
RESEARCH_PROVIDER = os.environ.get("RESEARCH_PROVIDER", "local")
SUPPORTED_RESEARCH_PROVIDERS = ["local"]
KRONOS_REPO_PATH = os.environ.get("KRONOS_REPO_PATH", "")
KRONOS_MODEL_NAME = os.environ.get("KRONOS_MODEL_NAME", "NeoQuasar/Kronos-small")
KRONOS_TOKENIZER_NAME = os.environ.get(
    "KRONOS_TOKENIZER_NAME",
    "NeoQuasar/Kronos-Tokenizer-base"
)


def _env_flag(name, default):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


# Live Paper Fund automatic operation. Off by default: the scheduler never
# fires unless explicitly enabled with a real market data provider. Offline and
# CI keep the mock default and stay deterministic.
AUTO_FUND_ENABLED = _env_flag("AUTO_FUND_ENABLED", False)
AUTO_FUND_MARKET_HOURS_ONLY = _env_flag("AUTO_FUND_MARKET_HOURS_ONLY", True)

# Backend scheduler lifecycle. Off by default so tests, CI, and development
# reload never start a background scheduler. This only gates whether the
# lifecycle owner runs its background loop; it does not enable any trading
# (that stays gated by AUTO_FUND_ENABLED).
ATLAS_SCHEDULER_ENABLED = _env_flag("ATLAS_SCHEDULER_ENABLED", False)

# Seconds between scheduler loop iterations (each iteration calls the guarded
# /paper-fund/tick path once).
ATLAS_SCHEDULER_INTERVAL_SECONDS = int(
    os.environ.get("ATLAS_SCHEDULER_INTERVAL_SECONDS", "300")
)

# Autonomous research cycle. Off by default: when disabled the scheduler tick
# reduces exactly to the guarded paper-fund tick. Enabling it lets scheduled
# ticks generate deterministic watchlist recommendation records and run the
# research-only committee on them. It never enables any trading (that stays
# gated by AUTO_FUND_ENABLED), never uses an LLM, and still requires a real
# market data provider before anything is generated.
AUTO_RESEARCH_ENABLED = _env_flag("AUTO_RESEARCH_ENABLED", False)

# Minutes between automatic recommendation-generation attempts (default: once
# per day). Successful runs stay fresh for this interval.
AUTO_RESEARCH_INTERVAL_MINUTES = int(
    os.environ.get("AUTO_RESEARCH_INTERVAL_MINUTES", "1440")
)

# Retry cooldown after a FAILED/REFUSED generation attempt. Much shorter than
# the freshness interval so one provider hiccup does not silence research for
# a whole day; a successful run still refreshes only per the interval above.
AUTO_RESEARCH_RETRY_MINUTES = int(
    os.environ.get("AUTO_RESEARCH_RETRY_MINUTES", "30")
)

# Deterministic recommendation outcome evidence. Disabled by default until
# migration 005 has been applied and read/status surfaces have been verified.
# It reuses the main scheduler interval and never enables trading.
AUTO_OUTCOME_ENABLED = _env_flag("AUTO_OUTCOME_ENABLED", False)

ETF_ALLOCATION = 0.70
STOCK_ALLOCATION = 0.30

APPROVED_ETFS = ["VOO", "VTI", "QQQ", "SCHD"]
APPROVED_STOCKS = ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "COST"]

APPROVED_TICKERS = APPROVED_ETFS + APPROVED_STOCKS
