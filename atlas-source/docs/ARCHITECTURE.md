# Atlas Architecture

Atlas is a modular AI investment research platform. The system is organized
around small engines that handle market analysis, recommendation scoring,
forecasting, portfolio analysis, persistence, history, and report generation.

The current application is command-line driven, with SQLite persistence and
Markdown report output. The architecture is intentionally modular so future API,
dashboard, broker, automation, and AI integrations can be added without
rewriting the core analysis flow.

## Source Of Truth

`ATLAS_STATE.md` is the project source of truth for current Private Beta
status, completed systems, active providers, safe defaults, limitations,
policies, and recommended next milestones. Use it as the first handoff document
before diving into implementation-specific architecture details.

## Main Application Flow

The active Atlas run starts at:

```text
backend.main -> atlas.application -> InvestmentPlatform -> IntelligencePipeline -> engines
```

Flow summary:

1. `backend.main` creates and starts the Atlas application.
2. `atlas.application` loads approved tickers from settings and delegates to the platform service.
3. `InvestmentPlatform` delegates to `IntelligencePipeline`.
4. `IntelligencePipeline` coordinates the complete analysis lifecycle.
5. Engines analyze markets, build recommendations, create a dashboard, save database records, save a portfolio snapshot, and export a Markdown report.

## Intelligence Pipeline

`IntelligencePipeline` is the top-level orchestration layer. It does not replace
or duplicate existing engine logic. It coordinates the execution order and lets
existing engines keep ownership of their domain behavior.

Execution order:

1. Fetch market data through `MarketEngine` and the configured data provider.
2. Run technical analysis through the market analysis flow.
3. Run fundamental analysis through `RecommendationEngine` and `FundamentalEngine`.
4. Run news analysis through `RecommendationEngine` and `NewsEngine`.
5. Run forecast provider analysis through `RecommendationEngine` and `ForecastEngine`.
6. Prepare portfolio context through `PortfolioEngine`.
7. Prepare risk context through `RiskEngine`.
8. Build evidence through `EvidenceEngine`.
9. Calibrate confidence through `ConfidenceEngine`.
10. Evaluate signal quality through `SignalQualityEngine`.
11. Build recommendations through `RecommendationEngine`.
12. Initialize validation status for saved recommendations.
13. Keep benchmark logging available for completed validations.
14. Persist dashboard, recommendations, and portfolio snapshot.
15. Return the final recommendation while preserving the existing dashboard return value.

Current recommendation behavior remains inside `RecommendationEngine`. Future AI
providers should be added behind existing provider interfaces or dedicated
engines, then connected to the pipeline at the appropriate stage. Extension
points include data providers, forecast providers, news providers, fundamental
filing providers, portfolio optimizers, risk models, validation jobs, and
benchmark runners.

Pipeline visibility is exposed through `backend.status` and the FastAPI
`/dashboard` response. The status payload reports whether the pipeline is
active, execution mode, selected data provider, selected forecast provider,
validation availability, and benchmark availability. This is read-only
operational visibility and does not affect recommendation behavior.

## Engines

- `MarketEngine` - wraps market analysis and returns analyzed stocks for approved tickers.
- `RecommendationEngine` - builds investment recommendations from analyzed stocks and attaches intelligence scores, recommendation stability, and knowledge depth.
- `DecisionEngine` - converts technical stock analysis into a BUY, HOLD, or AVOID recommendation with confidence, reasons, and risks.
- `FundamentalEngine` - provider-based company fundamentals analysis with mock default and optional Yahoo/yfinance fallback-safe provider.
- `InvestmentIntelligenceEngine` - combines technical, fundamental, portfolio, risk, and forecast scores into an overall investment score and rating.
- `SignalQualityEngine` - scores setup quality from 1-10 using technical, fundamental, forecast, news, risk, and volatility signals. Weak quality can downgrade BUY recommendations to HOLD or AVOID before output.
- `EvidenceEngine` - converts technical, fundamental, forecast, news, portfolio, risk, and signal quality signals into a weighted evidence breakdown for each recommendation.
- `ConfidenceEngine` - estimates reliability for each evidence item and adds confidence, reliability label, and a short explanation.
- `HypothesisEngine` - explains deterministic assumptions behind each recommendation, identifies fragile assumptions, lists evidence dependencies, and creates counterfactual scenarios without changing BUY, HOLD, or AVOID logic.
- `ExecutiveReviewEngine` - performs a deterministic final quality review for readiness, evidence completeness, committee agreement, historical consistency, validation context, discovery conflicts, confidence calibration, missing providers, missing data, event placeholders, and stability. It never changes recommendation actions.
- `IntelligenceFusionEngine` - aggregates existing technical, fundamental, forecast, news, portfolio, risk, evidence, and confidence outputs into an explainable conviction assessment without replacing recommendation logic.
- `InvestmentCommitteeEngine` - turns existing evidence and fusion output into deterministic specialist views from a Technical Analyst, Fundamental Analyst, Forecast Analyst, News Analyst, Portfolio Manager, Risk Manager, Validation Analyst, and Benchmark Analyst.
- `ForecastEngine` - delegates forecasting to a configured forecast provider.
- `NewsEngine` - lightweight news intelligence interface. It fetches recent ticker headlines from a no-key Yahoo Finance RSS feed and returns sentiment, confidence, headline count, top headlines, and a summary.
- `PortfolioEngine` - tracks simple cash and position state for portfolio snapshots.
- `PortfolioStrategyEngine` - deterministic read-only portfolio strategy layer that measures exposure, concentration, cash, diversification, overlap, risk, expected return, expected volatility, Sharpe estimate, simulations, replay, and portfolio-level lessons without executing trades.
- `PortfolioConstructionEngine` - deterministic institutional allocation layer that turns existing recommendations and paper portfolio state into suggested allocations, risk budgets, diversification analysis, scenario analysis, and rebalancing suggestions without changing recommendation behavior or executing trades.
- `PaperTradingEngine` - paper-only portfolio layer. `historical_price_replay` is the only active paper-testing mode: it applies Atlas recommendation snapshots day by day to real historical OHLCV close prices, tracks virtual positions and trades, stores replay portfolio values, records price-source labels, and never connects brokers or executes real orders. `broker_paper_pending` is disabled future architecture (Alpaca Paper config validation only). Demo paper trading no longer exists as a product mode; fake/demo data is allowed only in tests.
- `DailyCycleEngine` - deterministic market-day paper-testing cycle with pre-market, market-open, market-close, and post-market phases. It records operating snapshots, updates paper portfolio state, and never changes recommendation behavior or executes real trades.
- `DailyJournalEngine` - deterministic end-of-cycle research journal that stores market regime, runtime state, paper portfolio, benchmarks, provider health, macro/catalyst context, recommendations, performance, lessons, and follow-up research tasks without changing recommendation behavior.
- `RuntimeEngine` - Atlas Beta Runtime state machine for continuous paper-only operation. It records current runtime state, timeline, provider health, watchlist size, paper portfolio state, alerts, health, and operations summary without deploying, connecting brokers, or executing real trades.
- `RiskEngine` - calculates portfolio risk level and cash percentage.
- `HistoryEngine` - reads recent runs, recommendations, and portfolio snapshots from persistence.
- `MarkdownReportEngine` - exports saved Atlas runs as Markdown reports in `reports/`.
- `PortfolioHealthEngine` - evaluates portfolio snapshot quality and produces a health score.
- `ChangeEngine` - compares recent runs, recommendation changes, and portfolio health changes.
- `AdvisorEngine` - provides simple advisory output based on portfolio health, available cash, and recommendations.
- `BacktestEngine` - standalone foundation for evaluating historical recommendation outcomes, hit rate, returns, and placeholder risk-adjusted metrics.
- `ValidationEngine` - evaluates completed recommendations over a holding period, assigns validation status, and summarizes hit rate and return metrics.
- `BenchmarkEngine` - Atlas Benchmark Suite measurement layer for forecast models, evidence sources, recommendation quality, signal quality, and confidence calibration. It stores benchmark metrics without changing recommendation behavior.
- `ModelEvaluationLab` - standardized read-only laboratory for comparing external model/provider candidates before Atlas trusts them. It stores accuracy, return, risk, runtime, memory, cost, integration difficulty, recommendations, and rankings without installing or activating models.
- `CaseStudyEngine` - deterministic research case generator for validated recommendations. It turns outcomes, evidence, committee review, executive review, hypotheses, counterfactuals, benchmark context, knowledge score, and stability score into structured lessons learned without changing recommendation behavior.
- `ResearchMemoryEngine` - deterministic institutional research memory layer that retrieves similar historical cases by ticker, sector, market regime, evidence profile, committee agreement, executive review, knowledge score, stability score, catalyst profile, probability profile, and portfolio strategy. It returns explainable analog scores and lessons without changing recommendation behavior.
- `SecEngine` - offline-first SEC filing intelligence layer with mock default and future EDGAR provider support. It normalizes 10-K, 10-Q, 8-K, DEF 14A, and S-1 filings into filing date, form type, company, ticker, sections available, filing URL placeholder, and deterministic section summaries.
- `MacroEngine` - offline-first macroeconomic intelligence layer with mock default and future FRED-style provider support. It tracks CPI, Fed Funds Rate, Unemployment, GDP Growth, 10Y Treasury Yield, and Yield Curve Spread, then produces a deterministic macro regime, pressure readings, recession risk, risk score, and summary.
- `InstitutionalReportEngine` - deterministic institutional report generator that assembles existing Atlas intelligence into structured Markdown reports with future PDF/HTML placeholders. It does not use an LLM and does not change recommendation behavior.
- `ResearchEngine` - Atlas Research Laboratory layer for experiments, strategy comparisons, provider rankings, recommendation attribution, and Markdown research reports. It evaluates Atlas itself and does not change recommendation behavior.
- `DiscoveryEngine` - analyzes historical recommendations, validations, benchmarks, committee output, and research experiments to produce evidence-backed observations and research suggestions. It never modifies Atlas automatically.
- `PerformanceObservatory` - read-only platform measurement layer that aggregates recommendation validation, benchmarks, committee history, discoveries, providers, and experiments into report cards and platform metrics.
- `MarketRegimeEngine` - deterministic market environment classifier for Strong Bull, Bull, Sideways, Volatile, Bear, and Strong Bear regimes using trend, volatility, drawdown, moving-average position, and period return. It is measurement-only and never changes recommendations or evidence weights.
- `HistoricalRunner` - deterministic historical validation framework for replaying historical market rows, generating Atlas-style recommendations, validating outcomes, computing performance/risk/statistical metrics, comparing variants, and producing Markdown reports.
- `SimulationArena` - deterministic research-only layer that compares full Atlas strategy configurations across historical rows, regimes, and validation windows. It ranks strategy configurations without changing default recommendation behavior, deploying, connecting brokers, or executing trades.
- `HistoricalDataAdapter` - interface for loading replayable historical OHLCV rows by ticker and date range.
- `MockHistoricalDataAdapter` - default offline historical adapter that returns deterministic OHLCV rows for approved tickers without paid APIs, API keys, broker connections, or network dependencies.
- `YahooHistoricalDataAdapter` - optional historical market data adapter that can load Yahoo OHLCV rows through `yfinance` when explicitly selected and falls back to mock rows if unavailable.
- `KnowledgeGraphEngine` - deterministic institutional memory layer that projects persisted Atlas records into nodes, relationships, related-knowledge queries, and natural-language knowledge summaries.
- `ProviderRegistry` - centralized read-only provider catalog for market data, historical data, forecast, news, fundamentals, catalysts, macro, portfolio, and research providers. It records name, category, version, status, capabilities, API-key requirements, deterministic/offline support, priority, health, and metadata without selecting providers or changing recommendations.

## Data Models

- `StockAnalysis` - technical and market analysis data for a ticker, including returns, moving averages, RSI, MACD, trend, volatility, and score.
- `InvestmentRecommendation` - recommendation output with action, confidence, reasons, risks, intelligence scores, forecast fields, signal quality fields, evidence breakdown, confidence metadata, validation status, overall score, and rating.
- Fusion fields on `InvestmentRecommendation` - aggregate conviction, bull case, bear case, neutral case, strongest factors, conflicts, missing inputs, and summary generated by `IntelligenceFusionEngine`.
- Committee fields on `InvestmentRecommendation` - evidence-based specialist stances, committee bull/bear/neutral cases, agreement, strongest bull and bear arguments, disagreement, and final committee summary.
- Hypothesis fields on `InvestmentRecommendation` - key assumptions, strongest and weakest assumptions, counterfactuals, flip conditions, and confidence drivers generated deterministically from existing evidence.
- Executive review fields on `InvestmentRecommendation` - final readiness status, executive confidence, summary, warnings, strengths, weaknesses, required research, and underlying quality checks.
- Stability and knowledge fields on `InvestmentRecommendation` - deterministic analysis-only quality signals that score action robustness and evidence/history depth without changing BUY, HOLD, or AVOID logic.
- `Dashboard` - run-level dashboard summary with market status, average RSI, average volatility, and recommendations.
- `WatchlistItem` - lightweight watchlist item with ticker, target price, and notes.

## Database Tables

Atlas uses SQLite through `database/atlas.db`.

- `atlas_runs` - stores run time, market status, average RSI, and average volatility.
- `recommendations` - stores recommendations linked to a run, including action, confidence, reasons, risks, technical score, fundamental score, portfolio score, risk score, forecast fields, overall score, and rating.
- Hypothesis columns on `recommendations` store assumptions, counterfactuals, flip conditions, and confidence drivers as JSON text for history and dashboard review.
- Executive review columns on `recommendations` store final quality-gate output as JSON/text for history, dashboard review, research analysis, and observatory metrics.
- Stability and knowledge columns on `recommendations` store robustness score, most sensitive factor, knowledge depth score, and explanations for history, dashboard review, and observatory metrics.
- `portfolio_snapshots` - stores portfolio state linked to a run, including cash, portfolio value, position count, risk level, and cash percentage.
- `recommendation_validations` - stores validation results linked to recommendations, including prices, holding period, predicted direction, actual direction, return, success flag, status, timestamps, and notes.
- `benchmark_results` - stores Atlas Benchmark Suite metric rows with engine name, version, benchmark date, metric, value, and notes.
- `evidence_benchmarks` - stores evidence source effectiveness, sample count, last benchmark date, engine name, version, and notes.
- `research_experiments` - stores Atlas Research Laboratory experiment metadata, dataset, ticker list, provider configuration, validation window, benchmark snapshot, status, and notes.
- `research_strategy_results` - stores per-experiment strategy comparison metrics including hit rate, average return, confidence, runtime, and missing data.
- `research_provider_results` - stores per-experiment provider comparison rows for forecast, news, fundamental, and future provider categories.
- `research_attributions` - stores per-recommendation attribution results showing strongest engine contribution, confidence drag, and evidence that changed the recommendation.
- `discoveries` - stores ranked Discovery Engine observations with supporting data, sample size, confidence, importance, related engines, related providers, support level, warnings, suggestions, and status.
- `historical_validation_runs` - stores historical validation summaries with configuration, metrics, comparison tables, statistical analysis, and Markdown reports as JSON/text.
- `model_evaluations` - stores Model Evaluation Lab scorecards for candidate models, including model identity, dataset, date range, validation window, sample size, accuracy, win rate, return, Sharpe ratio, max drawdown, runtime, memory, cost, integration difficulty, recommendation, and status.
- `case_studies` - stores structured validated recommendation case studies with ticker, recommendation, market regime, evidence, committee, executive review, knowledge/stability scores, outcome, return, holding period, validation, benchmark, hypotheses, counterfactuals, and lessons learned.
- `scientific_validation_reports` - stores deterministic scientific validation reports for proposed engines, providers, models, features, or evidence sources, including experiment ID, date, tested feature, baseline, candidate, sample size, required metric comparison, cross-regime validation, generalization tests, scientific result, adoption decision, explanation, and policy.
- `simulation_arena_runs` - stores Simulation Arena run summaries with arena ID, date, dataset, tickers, date range, validation window, strategy configurations, market regimes tested, results, comparison rankings, scientific validation output, and policy.
- `paper_portfolio_snapshots` - stores simulated paper portfolio state including cash, positions, current value, realized/unrealized P/L, portfolio value, daily return, total return, and policy.
- `paper_trades` - stores virtual trades with trade ID, ticker, action, entry/exit dates and prices, holding period, quantity, P/L, reason, and recommendation snapshot.
- `paper_performance_reports` - stores paper trading performance statistics, benchmark comparison, research summaries, and policy.
- `portfolio_construction_reports` - stores candidate allocation reports with recommended allocations, rebalancing actions, risk budget, diversification, constraints, scenario analysis, scientific validation metadata, operations summary, and policy.
- `daily_cycle_runs` - stores deterministic daily cycle records with cycle ID, date, phase, status, recommendation count, paper portfolio value, daily return, alpha versus S&P 500, warnings, summary, details, and policy.
- `daily_journals` - stores permanent daily research journal entries with market regime, runtime state, paper portfolio summary, benchmark comparison, provider health, macro/catalyst summaries, recommendation counts, performance summary, lessons learned, research tasks, and policy.
- `runtime_states` - stores Atlas Beta Runtime snapshots with runtime ID, current state, market date, phase, last cycle time, next cycle, provider health, paper portfolio value, watchlist size, open positions, recommendations today, alerts, tasks, operations summary, health, and policy.
- Research memory reports are stored as JSON on `recommendations` when generated. They are advisory evidence only and do not change BUY, HOLD, AVOID, providers, thresholds, or execution.

## Beta Runtime

Atlas Beta Runtime turns Atlas into a continuously operating paper-only
research system. Supported runtime states are `INITIALIZING`, `PRE_MARKET`,
`MARKET_OPEN`, `MARKET_CLOSE`, `POST_MARKET`, `IDLE`, and `ERROR`.

The runtime orchestrates provider health, macro update, catalyst update,
research memory refresh placeholder, recommendation watchlist generation,
paper portfolio update, observatory update, scientific validation summary, and
operations summary. Runtime timeline output includes last completed task,
current task, next scheduled task, last successful cycle, and runtime uptime.

Runtime health is deterministic: `Healthy`, `Warning`, `Degraded`, or
`Offline`, with an explanation. The runtime is paper trading only. It cannot
connect brokers, execute real trades, deploy changes, or alter recommendation
logic. Read-only API routes are `/runtime`, `/runtime/status`, and
`/runtime/tasks`.

## Daily Market Cycle

Atlas Daily Cycle is a paper-testing operating loop for market days. It
supports `pre_market`, `market_open`, `market_close`, and `post_market` phases.
Pre-market checks provider health, loads macro and catalyst context, creates a
watchlist recommendation snapshot, and records the cycle state. Market-close
updates paper portfolio prices, calculates daily paper P/L, updates benchmark
comparison, and stores the cycle result. Post-market refreshes observatory
context, records lessons learned, and creates follow-up research items.

Daily cycle records are read-only operating evidence. They do not connect
brokers, execute trades, deploy changes, or alter Atlas recommendation logic.
The API exposes `/daily-cycle` and `/daily-cycle/latest` for review.

`/paper-sim/run` can still trigger deterministic pre-market, market-close, or
full daily-cycle runs for research context, and `/paper-sim/reset` clears local
paper replay records. Removed demo paper modes (`demo_simulation`,
`demo_preview`, `fake_paper`) are rejected with HTTP 400. Daily-cycle
simulations no longer create paper portfolio, trade, or performance records:
the paper tables only ever hold price-backed historical replay data. These
controls never connect brokers, send orders, or alter recommendation behavior.

Completed market-close cycles also create an Atlas Daily Journal entry. The
journal is a permanent paper-only research record that summarizes the market
regime, runtime state, paper portfolio, benchmark comparison, provider health,
macro and catalyst context, recommendation mix, paper performance, lessons
learned, and deterministic follow-up research tasks. The API exposes
`/daily-journal` and `/daily-journal/latest` for review.

## Paper Trading

Atlas Paper Trading Mode manages a completely simulated portfolio from Atlas
recommendation snapshots and market prices. It tracks cash, positions, cost
basis, current value, realized P/L, unrealized P/L, and total portfolio value.
BUY and SELL recommendations create virtual trades. HOLD and AVOID create no
position change. No broker is connected and no real order is sent.

Paper Trading no longer supports a demo product mode. `historical_price_replay`
is the only active paper-testing mode: it uses historical OHLCV close prices
from Yahoo through the historical adapter (or test-mocked rows in tests), runs
through each historical date, stores daily replay portfolio values, and fails
loudly when required prices are missing or only fallback rows are available.
`broker_paper_pending` is disabled future architecture: `GET
/paper-broker/status` validates Alpaca Paper configuration
(`ALPACA_API_KEY`/`ALPACA_API_SECRET`) but exposes no order endpoint, requires
no account connection, and always reports `execution_enabled: false` and
`real_money: false`. Historical replay runs record price-backed status, data
source, fallback status, last price date, transaction cost and slippage
placeholders (both zero by default), and remain paper-only. Fake/demo data is
allowed only in tests, in clearly named test fixtures.

Paper trading records every virtual trade with entry and exit data, holding
period, reason, and the recommendation snapshot that produced the action.
Performance reports include daily return, total return, win rate, Sharpe,
Sortino, max drawdown, alpha versus S&P 500, beta placeholder, volatility, and
benchmark comparisons against S&P 500, NASDAQ-100, and an equal-weight
placeholder.

Paper trading is another validation source for research and observability. The
Performance Observatory exposes a paper trading dashboard, portfolio history,
and rolling performance. Research summaries include best trades, worst trades,
biggest winners, biggest mistakes, longest holds, and most profitable sectors.
The API exposes read-only `/paper-portfolio`, `/paper-trades`, and
`/paper-performance` routes, which return only stored price-backed replay data
or an empty setup state — never demo values. `/paper-trading/status` reports
replay activity (status, last replay time, replays completed, trades and
portfolio points generated, price-backed flag, current mode) plus an Atlas
Learning summary that activates only after a price-backed replay completes.
`/paper-replay/health` reports whether yfinance is installed and the historical
provider is available, with actionable fix instructions. The React Paper
Trading page has three sections: Historical Price Replay (inputs, run button,
audit trail, price rows sample, and a P/L chart and replay trades table that
appear only after a successful price-backed replay), Paper Trading Activity &
Learning, and Broker Paper Trading (clearly labeled DISABLED / coming later).

## Live Paper Fund

The Live Paper Fund (`LivePaperFundEngine`, mode `live_paper_fund`) runs Atlas
as a continuously operating paper fund, separate from Historical Price Replay.
It keeps a persistent fund state (OFF, READY, RUNNING, PAUSED, ERROR) with a
watchlist, virtual cash, open paper positions, and an update interval. Each
analysis cycle: checks market status, refreshes validated latest prices through
the Market Data Manager, generates deterministic equal-weight recommendation
snapshots, computes target allocations, creates simulated virtual orders,
fills them immediately at the validated prices, snapshots the portfolio
(value, realized/unrealized P/L, daily and total return), and appends activity
log and learning log entries.

Cycles require validated, non-fallback prices from a real provider. If prices
fail validation, a fallback was used, or the mock/demo provider is active, the
cycle fails loudly: the fund enters ERROR with an actionable `last_error`
(for example, set `MARKET_DATA_PROVIDER=yahoo`), and no orders, fills, or
snapshots are created from fake prices.

Storage uses dedicated tables (`paper_fund_states`, `paper_fund_orders`,
`paper_fund_snapshots`, `paper_fund_activity`, `paper_fund_learning`) so the
fund never mixes with price-backed replay records. The API exposes
`GET /paper-fund/status` and `POST /paper-fund/start|pause|resume|stop|reset|cycle`.
There is no live order endpoint. All orders are simulated
(`status: FILLED_SIMULATED`, `simulated: true`), the broker stays disabled,
real money is always false, and explicit human approval is required before any
future broker integration.

## Portfolio Construction

Portfolio Construction answers how much Atlas should own after
recommendations already exist. It sizes positions, ranks capital allocation
priorities, checks concentration limits, balances sector/factor exposure,
builds risk budgets, analyzes diversification, estimates scenario effects, and
generates deterministic rebalancing suggestions.

Construction output is paper-only and advisory. It does not replace
BUY/HOLD/AVOID logic, execute trades, connect brokers, or deploy changes.
Candidate allocation strategies must pass Simulation Arena and Scientific
Validation before any human-approved implementation can affect behavior. The
API exposes read-only `/portfolio-construction`, `/allocation`, `/rebalance`,
and `/risk-budget` routes.

## Simulation Arena

The Atlas Simulation Arena compares complete research strategy configurations
against each other over deterministic historical experiments. Supported
configurations include Current Atlas, No News, No Forecast, No SEC, No Macro,
No Catalysts, No Committee, No Executive Review, No Probability, and Candidate
Model Placeholder.

Each arena run records arena ID, date, dataset, tickers, date range,
validation window, strategy configs, market regimes tested, and results. Each
strategy result includes win rate, average return, Sharpe ratio, max drawdown,
probability calibration, recommendation accuracy, trade frequency, average
holding period, stability score, and knowledge score.

The arena ranks best overall, best risk-adjusted, best low-drawdown, most
stable, most knowledgeable, and not recommended strategies. The ranking is
research-only and integrates with Historical Runner, Research Laboratory,
Scientific Validation, Performance Observatory, and Discovery Engine without
changing default recommendation behavior.

## Scientific Validation

The Scientific Validation Framework is Atlas's adoption evidence gate. It does
not create, alter, or override BUY/HOLD/AVOID recommendations. It evaluates
whether a proposed engine, provider, model, feature, or evidence source has
scientifically demonstrated improvement before Atlas considers adoption.

Every validation report records the experiment ID, date, tested feature,
baseline, candidate, sample size, win rate, average return, Sharpe ratio,
maximum drawdown, probability calibration, recommendation accuracy, average
holding period, and trade frequency. Reports also include cross-regime checks
for bull, bear, sideways, high-volatility, low-volatility, rising-rate, and
falling-rate environments, plus generalization checks for training,
validation, out-of-sample, and walk-forward placeholder periods.

The framework produces deterministic scientific results: `Improved`,
`Neutral`, `Regression`, or `Not Enough Evidence`. Adoption decisions are
limited to `ADOPT`, `RETEST`, or `REJECT`, with deterministic explanations.
`ADOPT` is a research approval signal only; it does not install providers,
activate models, change thresholds, change weights, deploy code, connect
brokers, or execute trades.

## Historical Validation

The Historical Validation Framework is not a recommendation engine. It replays
historical market rows through deterministic Atlas decision logic, validates
future outcomes with configured holding windows, and measures whether Atlas
worked. Replay rows now come from a historical data adapter. The default mock
adapter returns deterministic OHLCV rows and validates date ranges, ticker
coverage, row sufficiency, and sorted timestamps. It supports experiment IDs,
date ranges, ticker filters, provider configuration metadata,
committee/executive toggles, portfolio configuration, comparison variants,
attribution reports, statistical analysis, and Markdown reports.

Historical experiments can enable or disable technical, fundamentals, forecast,
news, portfolio, risk, committee, executive review, hypothesis, and discovery
subsystems. Disabled subsystems are recorded as disabled evidence rows with
zero score and zero confidence instead of being silently omitted. These toggles
apply only to historical and research experiments and do not change default
Atlas recommendation behavior.

Historical validation also reports statistical significance metadata so Atlas
can separate possible signal from noise. Each replay includes sample size, mean
return, standard deviation, standard error, 95% return confidence interval, win
rate confidence interval, comparison deltas, and a practical significance label:
`Insufficient Sample`, `Not Meaningful`, `Possibly Meaningful`, or `Meaningful`.
Comparison mode evaluates Full Atlas against disabled-subsystem variants without
changing live recommendation behavior.

Historical replay rows are also tagged with deterministic market regimes:
Strong Bull, Bull, Sideways, Volatile, Bear, or Strong Bear. Regime tags let
Atlas measure whether historical performance varies by environment without
changing BUY, HOLD, AVOID, evidence weights, provider selection, or execution
behavior.

## Knowledge Graph

The Atlas Knowledge Graph is a read-only relationship projection over persisted
Atlas records. It connects tickers, recommendations, validations, benchmarks,
discoveries, research experiments, committee reviews, executive reviews,
historical replays, performance snapshots, hypotheses, counterfactuals,
evidence, research memory analogs, and providers.

Relationships are deterministic and auditable. Examples include
`validated_by`, `discussed_by`, `reviewed_by`, `benchmarked_by`,
`generated_discovery`, `tested`, `historical_analog`, `supported_by`,
`assumed`, `challenged_by`, and `similar_to`. The graph supports institutional
memory queries such as similar recommendations, similar discoveries, historical
analogs, common failures, successful assumptions, provider history, committee
history, executive history, and research memory summaries. Research memory
relationships include scored `strongest_analog` and `weakest_analog` edges plus
recurring patterns and recurring failures.

The graph does not create recommendations, change recommendations, tune
providers, or deploy changes. It helps Atlas remember how evidence, decisions,
reviews, experiments, and outcomes relate over time.

Historical validation can persist summaries for later review and expose them
through read-only APIs. It does not deploy changes, connect brokers, modify
recommendations, or tune Atlas automatically.

## Historical Provider Architecture

Atlas separates historical market data from historical replay logic. The
`HistoricalDataAdapter` contract exposes `get_ohlcv()` and
`get_supported_tickers()`, while `HistoricalDataProviderFactory` selects the
adapter from `HISTORICAL_DATA_PROVIDER`. `HistoricalRunner` and
`RecommendationEngine` do not need provider-specific code.

Mock remains the default historical provider. It is offline, deterministic,
requires no API keys, and is safe for tests and local development. Yahoo is
available only when explicitly selected with `HISTORICAL_DATA_PROVIDER=yahoo`
or a direct factory request. The Yahoo adapter uses `yfinance` when available,
normalizes rows into Atlas OHLCV format with `date`, `timestamp`, `open`,
`high`, `low`, `close`, and `volume`, and validates sorted dates, missing
values, invalid tickers, invalid date ranges, and insufficient Yahoo row
coverage. If Yahoo, `yfinance`, the network, or Yahoo row validation fails,
Atlas gracefully falls back to mock historical rows and records the failure
message in provider health.

Historical provider health reports requested provider, active provider,
healthy status, rows available, date range, fallback usage, and failure
message. Future historical providers are reserved for Polygon, AlphaVantage,
CSV, and Parquet sources, but unsupported providers currently resolve to the
mock adapter. This keeps historical research offline-first and prevents
provider selection from changing recommendation behavior.

## Provider Integration Platform

Atlas is offline-first. Mock providers remain the default for market data,
historical data, forecast, news, fundamentals, catalysts, macro placeholders,
portfolio state, and research records. Real providers are optional, swappable,
and registered before they are trusted by recommendation logic.

The Provider Registry exposes each provider with:

- name, category, version, status, capabilities, priority, and health
- whether it requires an API key
- whether it is deterministic
- whether it supports offline operation
- supported tickers, coverage, earliest date, latest date, update frequency,
  and known limitations

Provider health uses the controlled statuses `Healthy`, `Unavailable`,
`Offline`, `Mock`, `Experimental`, and `Deprecated`. Health is observational:
it does not activate providers, tune weights, change BUY/HOLD/AVOID, deploy
changes, or connect brokers.

Read-only provider visibility is available through `/providers`,
`/provider-health`, `backend.status`, and the Performance Observatory provider
health summary.

Future integrations are registered as candidates before use:

- Yahoo for market, historical, and fundamentals data
- SEC EDGAR for filings and company facts
- FRED for macroeconomic series
- Polygon for market and historical data
- Alpha Vantage for market and historical data
- Finnhub for market and company data
- Stooq for market and historical data
- CSV for offline historical files
- Parquet for offline historical datasets

## SEC Intelligence

Atlas SEC Intelligence is read-only research context for public company
filings. The default `mock` provider is deterministic and offline-capable. The
future `edgar` provider is registered for no-key SEC EDGAR integration, but it
falls back to mock output in offline mode and is not required for tests.

Supported filing types are `10-K`, `10-Q`, `8-K`, `DEF 14A`, and `S-1`.
Normalized filings expose filing date, form type, company, ticker, sections
available, and a filing URL placeholder. Every filing includes placeholder
summaries for Business, Risk Factors, MD&A, Financial Statements, Management
Guidance, and Legal Proceedings.

SEC filings are integrated into provider health, status output, read-only API
routes `/sec` and `/sec-summary`, the Performance Observatory, and the
Knowledge Graph as `SEC Filing` nodes connected to ticker nodes. SEC
Intelligence does not change recommendations, evidence weights, thresholds,
providers, broker behavior, or execution.

## Macro Intelligence

Atlas Macro Intelligence is an offline-first FRED-style provider architecture
for macroeconomic context. The default `mock` provider is deterministic and
requires no API keys or internet. The future `fred` provider is registered as an
optional no-key test path and falls back to mock output in offline mode.

Supported indicators are CPI, Fed Funds Rate, Unemployment, GDP Growth, 10Y
Treasury Yield, and Yield Curve Spread. `MacroEngine` converts those readings
into current macro regime, inflation pressure, rate pressure, growth pressure,
recession risk, macro risk score, and a deterministic summary.

Macro output is integrated into provider health, `backend.status`, read-only
API routes `/macro` and `/macro-summary`, the Performance Observatory, Discovery
Engine observations, and the Knowledge Graph as macro regime and indicator
nodes. Macro intelligence is research context only and does not change
recommendations, evidence weights, thresholds, providers, broker behavior, or
execution.

## Institutional Research Reports

Atlas Institutional Research Reports are deterministic and reproducible. The
report engine assembles existing Atlas outputs only: recommendation records,
probability reports, confidence and evidence fields, knowledge and stability
scores, executive review, investment committee output, catalysts, SEC
highlights, fundamental/technical/forecast/news scores, portfolio context,
historical analogs, case studies, risk fields, expected return, scenarios, and
research memory.

Reports include structured chart placeholders for probability distribution,
evidence breakdown, catalyst timeline, historical return distribution, and
committee agreement. Markdown output is available now, while PDF and HTML are
explicit future placeholders. Report metadata records generation time, report
version, data sources used, active providers, and provider health snapshots.

The read-only API route `/institutional-report/{ticker}` returns the structured
report. Reports do not use an LLM, do not guess missing information, do not
change BUY/HOLD/AVOID, and do not connect brokers or execute trades.

## Hypothesis and Counterfactual Reasoning

Atlas treats each recommendation as a hypothesis about current evidence, not as
an automatically self-improving rule. The Hypothesis Engine reads only existing
recommendation evidence and produces deterministic assumptions, confidence
drivers, fragile assumptions, and counterfactuals. Counterfactual scenarios show
what would strengthen, weaken, or potentially reverse a conclusion, but they do
not alter recommendation actions or deploy changes.

## Atlas Performance Observatory

The Performance Observatory measures Atlas itself. It aggregates historical
recommendations, validations, benchmark rows, committee agreement, discovery
history, provider rankings, and research experiments into platform metrics,
engine report cards, provider report cards, and controlled-learning summaries.

The Observatory is read-only. It reports lifetime recommendations, validated
recommendations, win rate, rolling win rate, returns, placeholders for Sharpe
and drawdown, confidence calibration, recommendation distribution, and committee
agreement distribution. It also aggregates recommendation stability and
knowledge score distributions so Atlas can measure robustness and evidence
depth over time. These measurements can guide research, but they never modify
recommendation logic, provider selection, thresholds, engine weights, or stored
recommendations.

The Observatory also reports performance by market regime, including win rate,
average return, recommendation distribution, average committee agreement,
average knowledge score, average stability score, and evidence rankings inside
each regime. Discovery and Research Laboratory workflows can use this to compare
evidence performance across regimes before proposing any human-reviewed
experiment.

The Observatory also tracks research memory retrieval accuracy, analog success
rate, similarity score calibration, and pattern frequency. These metrics measure
whether historical analog retrieval is useful evidence; they do not tune Atlas
automatically.

## Executive Review

The Executive Review Engine is Atlas's final deterministic quality gate before
presentation. It evaluates readiness, not action direction. The engine can mark
a recommendation as `READY`, `CAUTION`, `NEEDS_REVIEW`, or
`INSUFFICIENT_DATA`, and it records confidence, warnings, strengths,
weaknesses, and required follow-up research.

Executive review is a controlled decision process. It may highlight missing
providers, incomplete evidence, weak committee agreement, limited historical
similarity, validation gaps, discovery conflicts, confidence-calibration issues,
major-event placeholders, or unstable counterfactuals. It does not alter BUY,
HOLD, or AVOID, and it does not automatically modify Atlas behavior.

## Atlas Research Laboratory

The Atlas Research Laboratory is a measurement and experimentation subsystem,
not a recommendation engine. It answers which engines, providers, evidence
combinations, and configurations improve Atlas over time.

Research workflow:

1. Create a research experiment with dataset, ticker list, provider
   configuration, selected providers, validation window, benchmark snapshot,
   status, and notes.
2. Compare strategies such as Technical only, Technical + Forecast, Technical +
   Forecast + Fundamentals, and Everything.
3. Compare providers side by side across forecast, news, fundamentals, and
   future provider families.
4. Attribute recommendations to the evidence category that contributed most,
   the engine that hurt confidence, and the evidence that materially changed
   the recommendation.
5. Persist normalized experiment, strategy, provider, and attribution rows.
6. Generate Markdown research reports with executive summary, configuration,
   results, recommendations, next experiments, and future work.

ARL outputs are exposed through the read-only `/research` API endpoint. They
feed the research feedback loop and benchmark planning, but they do not
self-modify Atlas, alter provider selection, or change live recommendation
behavior. Any tuning idea remains advisory until a human explicitly approves and
implements it.

## Model Evaluation Laboratory

The Model Evaluation Lab is Atlas's standard gate for external AI/model
providers. It can compare candidates such as Mock Forecast, Kronos, Chronos,
TimesFM, FinBERT, and Financial RoBERTa using deterministic benchmark records.
The lab records model name, model type, provider, dataset, date range,
validation window, sample size, accuracy, win rate, average return, Sharpe
ratio, maximum drawdown, runtime placeholder, memory placeholder, cost
placeholder, integration difficulty, and recommendation.

Model rankings include best overall, best accuracy, best risk-adjusted, best
low-cost, best speed, and not recommended. These rankings are research signals,
not deployment instructions. Atlas can suggest model adoption candidates, but it
cannot install, activate, switch to, or auto-adopt any model. Human approval,
benchmark review, implementation, and testing are required before any model can
affect production behavior.

The `/model-evaluations` endpoint exposes saved evaluations read-only. The
Performance Observatory summarizes rankings, the Discovery Engine can surface
model evaluation observations, and the Research Laboratory can use model
scorecards to plan future experiments. No paid APIs are called by the
evaluation lab.

## Case Study Engine

The Case Study Engine converts validated recommendations into institutional
research cases. Each case captures ticker, recommendation, market regime,
evidence, committee context, executive review, knowledge score, stability
score, outcome, return, holding period, validation result, benchmark context,
hypotheses, and counterfactuals.

Lessons learned include most useful evidence, least useful evidence,
unexpected outcome, confidence calibration, committee effectiveness, executive
effectiveness, hypothesis success, and future improvements. These lessons are
for historical analysis only. They do not change BUY, HOLD, AVOID, evidence
weights, providers, broker behavior, or execution.

Case studies are stored in `case_studies` and exposed read-only through
`/case-studies`. The Knowledge Graph creates a Case Study node for each case and
links it to related recommendations, validations, discoveries, experiments,
historical replays, and providers. The Performance Observatory summarizes best
case, worst case, most educational case, and similar cases. The Research
Laboratory can filter winning cases, losing cases, bull-market cases,
bear-market cases, committee disagreements, forecast failures, and news
failures.

## Portfolio Strategy Engine

The Portfolio Strategy Engine evaluates the whole portfolio rather than only
individual securities. It measures sector exposure, factor exposure,
concentration, cash, diversification, position overlap, risk, expected return,
expected volatility, and a Sharpe estimate.

Strategy recommendations can be Increase, Reduce, Maintain, Replace,
Diversify, or Raise cash. These are advisory portfolio research actions only.
Atlas does not connect brokers, deploy changes, or execute trades. Every
strategy action requires human approval.

The engine compares Current Portfolio, Atlas Portfolio, and Difference views,
and can replay portfolio returns over historical periods to evaluate whether
Atlas strategy variants outperformed a baseline. Portfolio-level case studies
capture lessons learned from simulations and replay. The Knowledge Graph stores
Portfolio, Portfolio Strategy, and Portfolio Optimization nodes, while Research
and Observatory summaries track whether Atlas portfolio strategies outperform
baseline portfolios.

AI-assisted portfolio adjustment is a research-only ARL topic. Inspired by
AI analyst research, Atlas can evaluate whether public-information-only
portfolio adjustments would have improved historical results. The experiment
design compares an AI-adjusted portfolio with the original portfolio over
quarterly evaluation windows, while tracking return improvement, risk change,
turnover, drawdown, and concentration limits.

Future experiment idea: `Atlas vs Original Portfolio`.

Future benchmark: AI-adjusted return improvement over baseline portfolio.

This workflow is not live trading, does not guarantee returns, and does not
authorize automatic execution. Portfolio changes require validation, risk
controls, human approval, and separate implementation before any production
behavior can change.

## Investment Committee

The Investment Committee is an evidence-based specialist debate layer. It is not
random AI debate, does not use OpenAI, and does not create uncontrolled agents.
Each committee member is a deterministic view over one existing evidence
category:

- Technical Analyst -> Technical evidence.
- Fundamental Analyst -> Fundamental evidence.
- Forecast Analyst -> Forecast evidence.
- News Analyst -> News evidence.
- Portfolio Manager -> Portfolio evidence.
- Risk Manager -> Risk evidence.
- Validation Analyst -> Validation evidence.
- Benchmark Analyst -> Benchmark evidence.

Each member outputs stance, confidence, evidence, concern, and summary. Stance
is derived from evidence score thresholds: Bullish at 70 or higher, Bearish
below 50, Neutral from 50 through 69, and Missing when no supported evidence was
provided.

A deterministic moderator summarizes committee bull, bear, and neutral cases,
committee agreement, bullish/bearish/neutral members, strongest bull argument,
strongest bear argument, main disagreement, and final committee summary. The
moderator only uses supplied evidence and fusion context; it does not invent
unsupported claims.

Committee output is persisted with recommendations and displayed in history and
the recommendation card. It is explanatory only. Atlas does not self-modify and
committee output does not change recommendation actions.

## Discovery Engine

The Discovery Engine is Atlas's scientific observation layer. It studies saved
Atlas history and produces evidence-backed discoveries such as:

- Highest-performing evidence combinations.
- Weakest evidence combinations.
- Best committee agreement ranges.
- Worst committee disagreements.
- Provider performance.
- Forecast model performance.
- Sector trend coverage gaps.
- Confidence calibration.
- Validation success.
- Benchmark trends.

Every discovery includes sample size, confidence score, support level, warnings,
supporting data, related engines, related providers, status, and advisory
suggestions. Tiny samples are explicitly flagged so early observations are not
mistaken for conclusions.

Discovery suggestions can say things like "Investigate increasing technical
weight" or "Forecast contributes little under current configuration," but those
suggestions are research leads only. The engine does not change weights,
providers, recommendation actions, validation rules, or any Atlas behavior.

Research experiments can reference discovery IDs. This connects observations to
future tests while preserving controlled learning: observe, form a hypothesis,
test in ARL, review results, then require human approval before any behavior
change.

## Intelligence Dashboard

The React dashboard includes a system-wide Atlas intelligence view backed by
the FastAPI `/dashboard` endpoint. It summarizes Atlas itself, not only the
latest recommendation list.

Dashboard sections include:

- System health: backend status, database status, forecast provider, validation status, backtesting availability, and news engine status.
- Recommendation metrics: total recommendations, pending validations, successful validations, failed validations, hit rate, and average return.
- Evidence metrics: average technical, fundamental, forecast, news, portfolio, and risk scores across saved recommendations.
- Forecast information: configured forecast provider and the effective display provider, including `Mock (Kronos unavailable)` when Kronos is not available.
- Latest recommendation: ticker, action, confidence, signal quality, and validation status.

Aggregate recommendation and evidence metrics are calculated in
`database.repository` from saved recommendation and validation rows. The API
keeps the older latest-run dashboard fields and adds intelligence fields so
existing consumers continue to work.

## Future AI Stack

Atlas will evaluate specialized AI systems by research domain before any
production integration. The `research/` directory is the planning layer for this
work.

```text
Atlas Intelligence Research Program
├── Forecasting AI
│   └── Time-series and provider models for expected direction and change
├── News AI
│   └── Sentiment, catalyst extraction, and source-grounded summaries
├── SEC AI
│   └── Filing parsing, XBRL intelligence, and risk-factor comparison
├── Earnings AI
│   └── Calendar, transcript, guidance, and surprise analysis
├── Portfolio AI
│   └── Allocation, exposure, diversification, and risk-fit models
├── Macro AI
│   └── Regime, rates, inflation, employment, and sector context
├── Backtesting AI
│   └── Recommendation validation, benchmark comparison, and simulation
├── Knowledge Graph
│   └── Company, sector, event, filing, news, and portfolio relationships
└── Benchmarks
    └── Accuracy, speed, memory, license, maintenance, community, integration difficulty, and Atlas Score
```

Future integrations should pass through benchmark review before reaching Atlas
engines. This keeps the production system modular and prevents one model from
becoming responsible for unrelated tasks.

## Forecast Provider Architecture

Forecasting is provider-based so Atlas can support multiple forecasting
backends. `FORECAST_PROVIDER` defaults to `"mock"` so Atlas remains deterministic
and dependency-free by default.

- `ForecastProvider` - base provider interface. Forecast providers implement `forecast(stock)`.
- `MockForecastProvider` - default provider with deterministic simulated forecasts for approved tickers.
- `KronosForecastProvider` - optional Kronos-backed provider. It imports Kronos only inside the provider, supports `KRONOS_REPO_PATH`, `KRONOS_MODEL_NAME`, and `KRONOS_TOKENIZER_NAME`, and loads tokenizer/model lazily.

This design keeps Atlas from depending directly on any specific forecasting
library. Providers accept stock or OHLCV data and return direction, confidence,
expected change, forecast horizon, and forecast score.

If `FORECAST_PROVIDER = "kronos"` but Kronos cannot be imported, the configured
repo path is invalid, or model loading fails, `ForecastEngine` logs the issue and
falls back to `MockForecastProvider`. This keeps Atlas usable without Kronos and
prevents optional forecasting dependencies from breaking normal runs.

## Data Provider Architecture

Market data is provider-based so Atlas can support multiple external data
sources without changing the analysis engines. `DATA_PROVIDER` defaults to
`"mock"` for deterministic offline runs and tests. Supported values are
`"mock"` and `"yahoo"`.

- `DataProvider` - base provider interface. Providers implement `get_price_history(ticker)`, `get_latest_price(ticker)`, and `get_supported_tickers()`.
- `MockDataProvider` - deterministic offline provider used by default and by tests.
- `YahooDataProvider` - optional Yahoo/yfinance-backed provider. It catches import, network, and empty-history failures and falls back to mock data so Atlas does not crash when Yahoo data is unavailable.

`market.data` selects the configured provider, falls back to mock for invalid
provider names, and preserves the existing market analysis contract by returning
price history with a `Close` series for indicator calculation.

`data_provider_health()` reports the active provider, supported ticker count,
latest price availability, health status, and failure message. `backend.status`
prints this health check so provider availability can be inspected without
running a full Atlas analysis.

Future data providers can be added behind the same interface for Polygon,
AlphaVantage, SEC filings, FRED macro data, and News sources. Paid APIs and API
keys should remain outside the default path until provider contracts, failure
handling, caching, and benchmark evaluation are complete.

## News Intelligence Architecture

News intelligence is provider-based and routed through
`NewsEngine.analyze(ticker)`. `NEWS_PROVIDER` defaults to `"fake"` so Atlas
remains deterministic, offline, and safe for tests. Supported values are
`"fake"` and `"rss"`.

- `NewsProvider` - base provider interface. Providers implement `get_headlines(ticker)`, `get_provider_name()`, and `health_check()`.
- `FakeNewsProvider` - deterministic offline provider used by default.
- `RSSNewsProvider` - optional free RSS provider. It catches network, parsing, and source failures and returns an empty headline list instead of crashing Atlas.

The engine interface returns:

- `sentiment`
- `confidence`
- `headline_count`
- `headlines`
- `top_headlines`
- `summary`
- `provider`

Sentiment and summary remain placeholder intelligence fields until Atlas adds a
real NLP provider. RSS can provide real headlines, but the default fake provider
preserves the existing offline behavior.

Future providers can be added behind `NewsEngine` for Google News, Yahoo
Finance, SEC filings, FinBERT, Financial RoBERTa, and source-grounded
explainability models. Those providers should fetch or receive source material,
normalize it into the same news intelligence output, and keep the rest of Atlas
insulated from provider-specific API details.

Recommendation scoring should not depend on news intelligence until the provider
contract, caching behavior, and failure handling are implemented.

## Intelligence Fusion Architecture

`IntelligenceFusionEngine` is an aggregation layer. It consumes existing outputs
from technical analysis, fundamentals, forecast, news, portfolio, risk,
evidence, and confidence metadata, then returns an explainable conviction
assessment.

Fusion output includes:

- overall conviction from 0-100
- bull case
- bear case
- neutral case
- strongest positive factor
- strongest negative factor
- conflicting signals
- missing inputs
- fusion summary

`RecommendationEngine` attaches fusion output to each recommendation after the
existing evidence and confidence steps. Fusion does not replace
`RecommendationEngine`, change the recommendation action, alter confidence, or
change sorting behavior.

Expanded fusion output also includes confidence breakdown by engine, evidence
weighting table, engine contribution percentages, strongest agreement,
strongest disagreement, uncertainty score, and recommendation rationale. These
fields are explainability metadata only.

## Fundamental Provider Architecture

Company fundamentals are provider-based so Atlas can support multiple sources
without changing recommendation behavior. `FUNDAMENTAL_PROVIDER` defaults to
`"mock"` for deterministic offline runs and tests. Supported values are
`"mock"` and `"yahoo"`.

- `FundamentalProvider` - base provider interface. Providers implement `get_company_profile(ticker)`, `get_fundamentals(ticker)`, `health_check()`, and `provider_name()`.
- `MockFundamentalProvider` - deterministic offline provider used by default.
- `YahooFundamentalProvider` - optional Yahoo/yfinance-backed provider. It catches import, network, and missing-data failures and falls back to mock fundamentals so Atlas does not crash when Yahoo fundamentals are unavailable.

`FundamentalEngine` preserves the existing `analyze(dict)` behavior used by
recommendation scoring while also supporting provider-backed ticker analysis.
Its output includes revenue, EPS, P/E, debt, cash, market cap, profit margin,
ROE, confidence, and provider metadata.

Future providers can be added behind the same interface for SEC CompanyFacts,
SEC filings, earnings reports, normalized financial statements, and paid market
data vendors after benchmark review.

## Backtesting Architecture

`BacktestEngine` evaluates a recommendation against a known entry price, exit
price, holding period, and recommendation timestamp. It is the calculation layer
used by validation workflows.

Per-recommendation metrics include:

- recommendation id
- recommendation action
- predicted direction
- actual direction
- percentage return
- hit or miss
- holding period
- recommendation timestamp

Batch summaries include overall hit rate, BUY/HOLD/AVOID hit rates, average
return, average gain, average loss, largest gain, largest loss, win/loss ratio,
and placeholders for max drawdown and Sharpe ratio.

`generate_report(results)` formats those summary metrics into a readable text
report for local validation and future reporting workflows.

## Validation Architecture

`ValidationEngine` is the first complete recommendation validation layer. It
evaluates completed recommendations using deterministic inputs:

- recommendation id
- ticker
- recommendation action
- recommendation timestamp
- evaluation timestamp
- entry timestamp
- exit timestamp
- holding period
- expected holding period
- starting price
- ending price
- percentage return
- predicted direction
- actual direction
- success or failure
- notes
- validation notes
- validation window

Atlas tracks standard validation windows of 7, 30, 90, 180, and 365 days.

Validation status is one of:

- `Pending`
- `Succeeded`
- `Failed`
- `Expired`

The lifecycle of a recommendation is:

1. Atlas creates and saves a recommendation with `Pending` validation status.
2. A future validation process supplies starting price, ending price, holding period, and evaluation timestamp.
3. `ValidationEngine` compares predicted direction with actual direction and marks the result `Succeeded` or `Failed`.
4. Expired recommendations can be marked `Expired` when no valid evaluation can be completed.
5. Validation results are persisted in `recommendation_validations`, while the latest status is also reflected on the recommendation.
6. History views present the recommendation, its validation result, and aggregate performance metrics.

Future expansion can add scheduled validation jobs, price-source adapters,
configurable holding periods, benchmark-relative returns, drawdown and Sharpe
calculations, richer validation notes, and API endpoints dedicated to validation
runs. This framework does not add live trading, broker integrations, or
deployment behavior.

## Atlas Benchmark Suite

The Atlas Benchmark Suite is a measurement subsystem. It evaluates whether each
intelligence component improves recommendation quality, but it does not alter
live recommendation behavior.

ABS benchmark categories:

- Per-engine accuracy, rolling accuracy, rolling performance, recommendation accuracy, validation success, average recommendation lifetime, and historical benchmark snapshots.
- Forecast models: direction accuracy, MAE placeholder, RMSE placeholder, and runtime placeholder.
- Evidence sources: effectiveness score, sample count, and last benchmark date.
- Recommendation quality: BUY accuracy, HOLD accuracy, AVOID accuracy, overall hit rate, average return, average gain, and average loss.
- Signal quality: high-signal-quality accuracy, low-signal-quality accuracy, and sample count.
- Confidence calibration: high-confidence accuracy and low-confidence accuracy.

Benchmark rows are additive and append-only. The benchmark tables let Atlas
compare engine versions over time, identify intelligence components that help or
hurt recommendation outcomes, and promote candidate systems only after
repeatable measurement.

Atlas does not self-modify. Benchmark results may include
`suggested_adjustment`, `adjustment_reason`, and `requires_human_approval`, but
these are advisory only. `requires_human_approval` defaults to `True`, and the
benchmark layer must never apply tuning changes, alter thresholds, change model
selection, or modify recommendation behavior automatically.

## Future Architecture

## Provider Hierarchy

Atlas providers are selected through settings and isolated behind stable
interfaces:

- Data providers: mock default, optional Yahoo/yfinance.
- Forecast providers: mock default, optional Kronos.
- News providers: fake default, optional RSS.
- Fundamental providers: mock default, optional Yahoo/yfinance.
- Historical providers: mock default, optional Yahoo and future file/API adapters.
- Catalyst providers: mock default, future earnings calendar, economic calendar,
  SEC events, and corporate action adapters.

Future provider additions should preserve mock/offline defaults, avoid API keys
in source, handle failures gracefully, and pass benchmark review before they
affect production recommendation behavior.

## Catalyst Intelligence

Catalyst Intelligence adds deterministic awareness of upcoming company, macro,
and market events. The mock provider remains the default and includes company
events such as earnings, dividends, investor days, product launches, SEC
filings, and guidance updates; macro events such as CPI, PPI, jobs reports,
FOMC, GDP, and retail sales; and market events such as options expiration and
index rebalances.

For each recommendation context, Atlas can report upcoming events, days until
event, importance, confidence, risk level, historical relevance placeholder,
and potential volatility level. Historical replays and case studies can carry
catalyst metadata, and the Knowledge Graph links catalysts to recommendations,
validated cases, tickers, and research history.

The Performance Observatory summarizes catalyst frequency, win rate, average
return, best-performing catalyst, and worst-performing catalyst. Discovery can
surface deterministic observations such as CPI weeks increasing volatility or
FOMC weeks reducing recommendation stability. These outputs are research and
reporting only: they do not change BUY, HOLD, AVOID, evidence weights,
providers, broker behavior, deployment behavior, or execution.

## Probabilistic Intelligence

Probabilistic Intelligence estimates outcome likelihoods from validated Atlas
history. For each recommendation context, Atlas can report probability of
outperformance, market performance, and underperformance, with probabilities
forced to sum to 100%. It also estimates expected return, expected holding
period, best case, base case, worst case, sample size, similar historical
cases, probability confidence, and uncertainty level.

Similarity uses deterministic Atlas context: market regime, evidence rankings,
committee agreement, executive review, knowledge score, stability score,
catalyst profile, historical validation, and case studies. Small samples
produce higher uncertainty, and every probability report includes an
explainable summary of the historical basis.

The Performance Observatory tracks probability calibration, expected versus
actual return, expected versus actual holding period, probability accuracy, and
uncertainty distribution. Discovery may surface observations such as
high-probability recommendations outperforming more often, high-uncertainty
recommendations underperforming, or high knowledge scores improving
calibration.

Probability estimates are advisory measurement only. They must not change BUY,
HOLD, AVOID, evidence weights, provider selection, deployment behavior, broker
behavior, or execution.

Planned architecture extensions:

- FastAPI backend for API access to runs, recommendations, reports, and portfolio data.
- React/mobile dashboard for interactive research and portfolio monitoring.
- OpenAI explanation engine for richer natural-language reasoning and report commentary.
- Automation engine for scheduled Atlas runs, alerts, and report generation.
- Broker integration for account data, live positions, and eventually guarded execution workflows.

## Research Laboratory

The Atlas Research Laboratory (`engines/research_lab_engine.py`) is the place
where every experimental feature lives before it can ever reach production.
Atlas is no longer only an investing bot; it is an institutional investment
research laboratory in which recommendations are one output and the primary
purpose is learning which investment ideas actually work.

The laboratory is a deterministic, read-only orchestration layer. It does not
reimplement metrics or validation logic; instead it reuses the existing
`SimulationArena` for deterministic performance metrics and the
`ScientificValidationEngine` for adoption decisions.

### Experiment Registry

Every experiment carries an experiment id, title, description, status, created
date, author, feature being tested, baseline strategy, candidate strategy,
validation state, notes, and priority. Experiment ids are deterministic hashes
of the title, tested feature, and created date. Experiments move through a
fixed lifecycle: PROPOSED, IMPLEMENTING, READY_FOR_TEST, RUNNING, VALIDATING,
ADOPTED, REJECTED, and ARCHIVED.

### Simulation and Validation

Running an experiment executes it inside the Simulation Arena and stores Sharpe,
Sortino, win rate, average return, drawdown, trade frequency, holding period,
alpha, probability calibration, knowledge score, and stability score for both
the baseline and candidate. Each experiment then receives a scientific result of
Improved, Neutral, Regression, or Not Enough Evidence, and an adoption decision
of ADOPT, RETEST, or REJECT. No experiment may automatically modify Atlas.

### Queue, Timeline, Roadmap, Comparison, History

The laboratory produces an experiment queue (highest priority, waiting,
currently running, recently completed), a research timeline (planned, active,
completed, rejected), a deterministic research roadmap grouped by High, Medium,
and Low priority, a baseline-versus-candidate comparison that highlights
improvements, and a searchable experiment history by feature, market regime,
date, result, and status.

### Operations and API

The Operations Center displays active experiments, the latest validation, the
latest adoption decision, and research progress. The API exposes `/research-lab`,
`/experiments`, `/experiments/history`, `/experiments/active`, and
`/validation/latest`. The React Research Laboratory page renders the queue,
comparison, validation results, arena comparison, roadmap, timeline, and history
with graceful loading, empty, and API-failure states.

Every improvement must be measurable, every experiment must be repeatable, and
every adoption must be scientifically justified. Evidence always wins. Nothing
becomes part of Atlas because an AI thinks it sounds better.

## Performance Analytics

The Performance Analytics system (`engines/performance_analytics_engine.py`)
measures Atlas itself. Its objective is not to improve recommendations but to
accumulate objective, deterministic evidence about Atlas so the platform can
answer, using statistics instead of opinion, whether it should be trusted more
today than yesterday. Atlas never claims it is improving; it demonstrates
improvement through measurable evidence, and evidence is more important than
optimism.

The engine is deterministic and read-only. It does not change recommendation
logic, portfolio construction, thresholds, weights, brokers, or execution.
Rather than duplicating logic, it reuses the Paper Trading statistics (Sharpe,
Sortino, drawdown, volatility), the Performance Observatory (platform metrics
and probability calibration), and the Research Laboratory (experiment adoption,
completion, and validation success). The Performance Observatory exposes it via
`performance_analytics(...)`.

### What it measures

- Equity curve: portfolio value with daily, weekly, monthly, rolling, and
  cumulative return.
- Benchmark comparison against the S&P 500, NASDAQ-100, and Equal Weight, with
  alpha, relative return, outperformance rate, and tracking difference.
- Risk statistics: Sharpe, Sortino, Calmar, volatility, maximum drawdown,
  average drawdown, best day, and worst day.
- Recommendation analytics: BUY success rate, HOLD accuracy, AVOID accuracy,
  average holding period, recommendation frequency, confidence calibration, and
  probability calibration.
- Learning curve: knowledge score, stability score, scientific validation
  success, experiment adoption rate, and research completion rate over time.
- Research progress: active, completed, rejected, and adopted experiments plus
  the current roadmap.
- Monthly reports: deterministic monthly summaries of performance, major
  lessons, best decisions, largest mistakes, research progress, and validation.
- A trust assessment that reports an evidence-based verdict of Improving, Mixed,
  Not Improving, or Not Enough Evidence, with the underlying signals listed.

### Surfaces

The API exposes `/analytics`, `/analytics/equity`, `/analytics/benchmarks`,
`/analytics/calibration`, `/analytics/research`, and `/monthly-report/latest`.
Monthly reports can be persisted to the `monthly_reports` table. The React
Analytics page renders the performance dashboard, equity curve, benchmark
comparison, calibration, learning curve, research progress, and monthly report
with graceful loading, empty, and API-failure states, and never crashes.

## Market Integration Layer

The Market Integration Layer connects Atlas to real market information while
preserving deterministic behavior and safety. Its objective is not to trade but
to let Atlas observe the market exactly as a human analyst would. It connects no
live broker, executes no trades, enables no automatic execution, and changes no
recommendation logic. Paper trading only; human approval required.

### Market Data Manager

`market/market_data_manager.py` is the single entry point for all market data.
It owns provider selection, validation, fallback, caching, and health. Mock is
the default so tests and offline operation stay deterministic, and Atlas never
fails because one provider is unavailable — every external dependency falls back
to the deterministic mock provider. Reliability is more important than speed.

### Providers

The manager supports Mock (default, deterministic), Yahoo (optional, reuses the
existing `YahooDataProvider` with mock fallback), and Polygon and Alpaca Market
Data placeholders that are registered but not integrated and always fall back
offline. The Alpaca provider is market data only and never connects a broker or
executes trades. Provider selection is configurable via the
`MARKET_DATA_PROVIDER` or `DATA_PROVIDER` environment variables or the
`MarketDataManager(provider_name=...)` argument, and all providers are also
described in the Provider Registry.

### Validation

`market/data_validator.py` validates data before Atlas trusts it: ticker exists,
timestamps ordered, OHLC consistency, no missing values, and no duplicate rows,
plus explicit placeholders for corporate action awareness and the market
calendar. Latest-price responses are validated for presence, numeric type, and
positivity. When validation fails, the manager falls back to the mock provider.

### Caching

`market/data_cache.py` caches recent responses with an injectable clock so
behavior is deterministic in tests. Each entry tracks provider, timestamp, cache
age, and whether a fallback was used, and the cache reports fresh, expired, and
fallback counts.

### Operations and Paper Trading

The Runtime `market_overview()` and Market Engine `market_status()` /
`data_snapshot()` expose validated status for Operations, which displays the
current provider, data freshness, market status, provider health, and fallback
status, plus market open/closed. Paper trading consumes validated prices through
`PaperTradingEngine.market_prices(...)`, which sources prices from the Market
Data Manager without changing any execution behavior. Snapshots can be persisted
to the `market_data_snapshots` table.

### API

The API exposes `/market/status`, `/market/provider`, `/market/health`, and
`/market/cache`. All are read-only, deterministic offline, and degrade
gracefully to the mock provider.

## Atlas Brain (Explainability Workspace)

Atlas Brain is a transparent window into Atlas's reasoning. It is not a new AI
engine and it recomputes nothing — it is an explainability and trust layer that
composes existing Atlas outputs into one coherent explanation of how Atlas
reached a recommendation. It is read-only and deterministic and changes no
recommendation, probability, or portfolio behavior. Atlas should never ask users
to trust a black box: every score is traceable and every conclusion has
evidence.

### Composition, not duplication

The Brain reuses existing engines: `RecommendationEngine.explain(...)` turns a
saved recommendation into a reasoning summary, engine contributions, confidence
breakdown, decision tree, and decision flow; `ProbabilityEngine.explain(...)`
reformats an existing probability report; `PerformanceAnalyticsEngine.trust_indicators(...)`
composes validation, experiment, calibration, provider health, and market
freshness signals; and `ResearchEngine.brain_report(...)` orchestrates these
together with `ResearchMemoryEngine`, `PortfolioConstructionEngine`, and the
Market Data Manager. When no saved recommendation exists for a ticker, a
deterministic illustrative example is returned so the flagship page never
crashes and always explains something.

### What the Brain answers

Why? What evidence mattered? Which engines contributed? What raised confidence
and what reduced it? How did Atlas arrive here? The report includes a Brain
overview (recommendation, confidence, probability, knowledge, stability,
executive review, committee decision), an animated decision flow across the full
pipeline (Market Data through Final Recommendation), evidence contribution
percentages, a confidence breakdown, a chronological reasoning timeline, a
decision tree that explains why rather than just what, historical influence
(analogs, case studies, similarity, past outcomes), portfolio impact (allocation,
risk budget, sector, cash, diversification), catalyst impact, and trust
indicators.

### API

The API exposes `/brain/{ticker}`, `/brain/summary/{ticker}`,
`/brain/evidence/{ticker}`, and `/brain/timeline/{ticker}`. All are read-only,
reuse existing Atlas outputs, and duplicate no backend logic. The React Atlas
Brain page is the flagship view, with dark institutional styling, animation,
graceful loading and empty states, and graceful API-failure handling.

## Historical Price Replay (Price-Backed or Failed)

Paper trading has two clearly separated modes. **Demo Preview** is fake UI data
for first-use only and is always labelled as such. **Historical Price Replay**
must prove it used real OHLCV rows, or fail loudly as NOT PRICE BACKED. Replay
never silently falls back to demo/mock rows.

`PaperTradingEngine.run_historical_price_replay(...)` sources price rows from
either explicitly injected `historical_rows` (real or test-mocked) or a real
historical adapter. If the adapter falls back (`fallback_used`), if no rows are
returned, or if requested tickers are missing prices on some dates, the replay
returns `replay_status = "FAILED"`, `price_backed = false`,
`error = "Historical prices unavailable"`, and produces no P/L, no trades, and no
chart. Failed replays are never persisted.

P/L is computed only from price rows. For a BUY, `quantity = floor(allocation_cash
/ entry_close)`, `unrealized_pnl = (current_close - entry_close) * quantity`, and
`portfolio_value = cash + shares * current_close`. For example, AAPL closes of
100 → 105 → 110 with $100,000 starting cash and a 10% allocation buy 100 shares
at 100 and end at 110, for an unrealized P/L of `(110 - 100) * 100 = 1000` and a
portfolio value of `90,000 + 100 * 110 = 101,000`, with the portfolio curve
changing across all three dates.

### Replay audit trail

Every `/paper-replay/run` response includes an `audit` object: `replay_id`,
`mode`, `requested_tickers`, `start_date`, `end_date`, `price_source`,
`fallback_used`, `price_backed`, `rows_used_count`, `first_price_date`,
`last_price_date`, `price_rows_used` (the first five rows with
date/open/high/low/close/volume), `trades_generated`,
`portfolio_points_generated`, and `failure_reason`. The Paper Trading page renders
this audit trail so the price source, price-backed flag, rows used, first/last
price dates, the first five price rows, and any failure reason are all visible.
No broker is connected, no real money is used, and no live execution occurs.
