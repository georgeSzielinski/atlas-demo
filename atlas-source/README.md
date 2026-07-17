# Atlas - AI Investment Research Platform

Atlas is a modular investment research platform that combines market data,
technical analysis, fundamentals, forecasting, portfolio intelligence, risk
analysis, historical tracking, and explainable recommendations.

## Project State

See [ATLAS_STATE.md](ATLAS_STATE.md) for the current Private Beta status,
completed systems, active providers, safe defaults, limitations, policies, and
recommended next milestones.

## Features

- Market data analysis
- Technical indicators
- Fundamental analysis
- Forecast engine provider architecture
- Investment intelligence scoring
- Portfolio health scoring
- Recommendation history
- Markdown report export
- SQLite persistence
- Atlas health/status checks

## Architecture

- `ai/` - lightweight AI/scoring helpers and OpenAI connection test utilities.
- `atlas/` - application wrapper that starts the Atlas platform.
- `backend/` - command-line entry points, status checks, exports, and test scripts.
- `core/` - project settings, approved tickers, budgets, and allocation defaults.
- `database/` - SQLite connection, setup, persistence, and history repositories.
- `engines/` - core analysis, recommendation, forecasting, reporting, portfolio, risk, and intelligence engines.
- `market/` - market data retrieval, indicators, reports, and sample fundamentals.
- `models/` - dataclass models for analyses, dashboards, recommendations, and watchlists.
- `portfolio/` - allocation and buy-plan helper logic.
- `reports/` - generated Markdown Atlas reports.
- `research/` - research program notes, candidate AI systems, evaluation criteria, and scorecards.
- `services/` - high-level investment platform workflow orchestration.
- `trading/` - safety, approval, and simulated trade execution helpers.

## Atlas Intelligence Research Program

Atlas is designed to integrate best-in-class specialized AI systems instead of
depending on a single general-purpose model for every research task. Forecasting,
news intelligence, SEC analysis, earnings research, portfolio construction,
macro context, backtesting, knowledge graphs, and benchmarks each have different
data requirements, evaluation methods, and failure modes.

The `research/` directory organizes those future AI workstreams. Each area
documents its purpose, candidate technologies, evaluation criteria, and current
integration status before any production engine changes are made.

## Commands

Run Atlas:

```bash
venv/bin/python -m backend.main
```

View run history:

```bash
venv/bin/python -m backend.history
```

Export the latest report:

```bash
venv/bin/python -m backend.export_report
```

Check Atlas status:

```bash
venv/bin/python -m backend.status
```

Run health and compile checks:

```bash
venv/bin/python -m backend.check
```

## Kronos Integration

Atlas is prepared for future Kronos integration through `ForecastProvider` and
`KronosForecastProvider`, but Kronos is not installed yet. The active forecast
path currently uses `MockForecastProvider`.

## Disclaimer

Atlas is educational and research software only. It is not financial advice.
