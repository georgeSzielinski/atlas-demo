# Atlas Research

This folder contains research notes, benchmark plans, and architecture documentation for Atlas as an AI investment research platform.

## Architecture

- `architecture/atlas_intelligence_stack.md` describes the long-term Atlas intelligence architecture.
- `architecture/atlas_pipeline.md` describes the staged research and recommendation pipeline.
- `laboratory/README.md` describes the Atlas Research Laboratory workflow.

## Research Domains

- Data Providers: provider contracts for market, filing, macro, and news data sources.
- Forecasting: time-series models, benchmark plans, and forecasting candidates.
- News: news AI, sentiment models, event detection, and explainability.
- Fundamentals: SEC filings, earnings reports, and financial statement extraction.
- SEC Intelligence: offline-first filing retrieval, normalization, and section summaries.
- Portfolio: correlation, diversification, efficient frontier, and optimization research.
- Portfolio Strategy: whole-portfolio exposure, risk, simulation, replay, and strategy research.
- Portfolio Construction: position sizing, capital allocation, risk budgeting, diversification, and rebalancing research.
- Risk: VaR, expected shortfall, volatility regimes, and tail risk research.
- Macro: FRED, CPI, GDP, Fed meetings, Treasury yields, and unemployment research.
- Macro Intelligence: offline-first FRED-style indicators, macro regimes, pressure readings, and recession risk context.
- Benchmarks: model scorecards, validation methods, and candidate evaluation.
- Model Evaluation Lab: standardized scorecards for external model/provider candidates before adoption.
- Case Studies: structured lessons learned from validated recommendations.
- Laboratory: experiments, strategy comparisons, provider rankings, recommendation attribution, and controlled learning.
- Research Laboratory: deterministic experiment registry, lifecycle, queue, timeline, roadmap, baseline-versus-candidate comparison, and searchable history where every experimental feature must earn adoption through Simulation Arena metrics and Scientific Validation before human approval.
- Performance Analytics: deterministic measurement of Atlas itself — equity curve, benchmark comparison, risk statistics, recommendation analytics, learning curve, research progress, and monthly reports — so the platform can show with statistics, not opinion, whether it should be trusted more today than yesterday.
- Discovery: statistically interesting observations from history, validations, benchmarks, committee output, and research experiments.
- Hypotheses: deterministic recommendation assumptions, fragile assumptions, confidence drivers, and counterfactual scenarios.
- Observatory: platform-wide performance measurement for recommendations, engines, providers, committees, discoveries, and experiments.
- Executive Review: final deterministic readiness checks before recommendation presentation.
- Historical Validation: replay historical market rows to prove whether Atlas works over time.
- Historical Providers: offline-first historical OHLCV provider selection for mock, Yahoo, and future real-data sources.
- Provider Registry: swappable provider catalog, health, metadata, and offline capability across Atlas data categories.
- Market Regimes: deterministic Strong Bull, Bull, Sideways, Volatile, Bear, and Strong Bear tagging for historical performance analysis.
- Knowledge Graph: relationship memory across recommendations, validations, experiments, discoveries, providers, reviews, and historical replays.
- Research Memory: explainable retrieval of historically similar investment cases and lessons.
- Institutional Reports: deterministic research reports assembled from existing Atlas engines.
- Daily Journal: permanent end-of-cycle records of market context, paper portfolio performance, lessons learned, and follow-up research tasks.

Future data provider candidates include Polygon, AlphaVantage, SEC, FRED, and
News providers. Each candidate should be evaluated for coverage, reliability,
latency, licensing, cost, failure behavior, and fit with Atlas provider
interfaces before integration.

The Provider Registry records candidates before Atlas relies on them. Registry
health and metadata are read-only; they do not activate providers, change
recommendations, tune weights, deploy changes, or connect brokers.

Historical provider research follows the same provider-family pattern as
forecast, news, fundamentals, and market data. Mock historical data remains the
default for deterministic offline experiments. Yahoo historical data can be
selected explicitly for real OHLCV research without API keys. Yahoo rows are
normalized into Atlas `date`/`timestamp`, open, high, low, close, and volume
fields, then validated for sorted dates, missing values, ticker coverage, date
ranges, and sufficient rows. If Yahoo, `yfinance`, the network, or validation
fails, Atlas falls back to mock historical rows and reports the failure in
provider health. Future historical candidates include Polygon, AlphaVantage,
CSV, and Parquet sources. Any real provider must preserve graceful fallback,
health reporting, and a clear separation between data loading and
recommendation behavior.

## Long-Term Direction

Atlas should be an orchestration platform. Specialized AI systems should produce structured signals, while Atlas coordinates evidence, confidence, validation, recommendations, dashboard presentation, history, and research feedback.

The core architecture path is:

```text
Market Data
  -> Specialized Intelligence Layers
  -> Evidence Engine
  -> Confidence Engine
  -> Intelligence Fusion
  -> Signal Quality
  -> Validation
  -> Benchmark
  -> Recommendation
  -> Dashboard
  -> History
  -> Research Feedback Loop
```

Current expansion focus:

- Fusion logic: aggregate conviction, agreement, disagreement, uncertainty, and rationale.
- Validation flow: 7, 30, 90, 180, and 365 day windows.
- Benchmark flow: per-engine accuracy, rolling accuracy, validation success, and controlled-learning suggestions that require human approval.
- Model evaluation flow: compare candidate AI/model providers before any integration or activation.
- Case study flow: convert validated recommendations into reusable research cases and lessons learned.
- Research memory flow: compare new recommendations with validated historical analogs by ticker, sector, regime, evidence, committee agreement, executive review, knowledge, stability, catalysts, probabilities, and portfolio strategy.
- Portfolio strategy flow: compare Atlas portfolio simulations and historical replay against baseline portfolios.
- Portfolio construction flow: rank capital allocation, size paper positions,
  budget risk, analyze diversification, and suggest rebalancing after
  recommendations already exist.
- Research Laboratory flow: compare engine combinations, provider configurations, and attribution patterns before promoting any change.
- Simulation Arena flow: compare full Atlas strategy configurations across
  historical experiments, regimes, and validation windows before promoting any
  configuration change.
- Paper trading flow: run a simulated portfolio for months using market prices
  and Atlas recommendation snapshots before any human-approved live trading
  discussion.
- Daily market cycle flow: run pre-market, market-open, market-close, and
  post-market paper-testing records on market days.
- Daily journal flow: store deterministic end-of-cycle research records with
  paper performance, benchmark context, lessons, and follow-up questions.
- Beta runtime flow: maintain continuous paper-only operating state, runtime
  health, task timeline, alerts, and Operations Center status.
- Scientific validation flow: require every proposed engine, provider, model,
  feature, or evidence source to prove improvement against a baseline before
  Atlas considers adoption.
- Discovery flow: observe historical patterns, assign confidence and support level, flag tiny samples, and turn findings into controlled research hypotheses.
- Market regime flow: compare win rate, average return, evidence rankings,
  committee agreement, knowledge score, and stability score across regimes.
- Portfolio adjustment research: test public-information-only AI portfolio
  adjustments against the original portfolio over quarterly windows.
- Provider hierarchy: mock/fake defaults with optional failure-safe external providers.
- Provider integration platform: register real data candidates with health and metadata before any use in recommendation workflows.

## Scientific Method

Atlas research follows a controlled scientific loop:

```text
Observe -> Discover -> Form Hypothesis -> Test in ARL -> Validate Scientifically -> Human Review
```

Discovery Engine output is not an instruction to modify Atlas. It is an
evidence-backed observation with warnings, sample size, confidence, and
suggested follow-up research. Atlas does not self-modify.

Scientific validation records experiment ID, date, tested feature, baseline,
candidate, sample size, required performance metrics, cross-regime checks, and
generalization checks. Outcomes are deterministic: `Improved`, `Neutral`,
`Regression`, or `Not Enough Evidence`, producing `ADOPT`, `RETEST`, or
`REJECT` as research-only adoption decisions. These decisions do not change
BUY/HOLD/AVOID logic, providers, thresholds, weights, broker connections, or
execution.

Simulation Arena runs compare Current Atlas against controlled strategy
variants such as No News, No Forecast, No SEC, No Macro, No Catalysts, No
Committee, No Executive Review, No Probability, and Candidate Model
Placeholder. Arena rankings identify best overall, risk-adjusted,
low-drawdown, stable, knowledgeable, and not recommended strategies. These
rankings are research-only and require scientific validation plus human review
before any code or configuration change.

Paper trading sits after Simulation Arena. It uses virtual execution only:
cash, positions, cost basis, current value, realized P/L, unrealized P/L,
portfolio value, trade history, benchmark comparison, and rolling performance
are tracked without real money, broker connections, or order execution. Paper
cycle records add pre-market provider/macro/catalyst checks, market-close paper
P/L updates, and post-market lessons learned. Human approval is still required
before anything real. Paper trading research identifies best trades, worst
trades, biggest winners, biggest mistakes, longest holds, and profitable
sectors as validation evidence.

Portfolio construction sits after recommendations and before any hypothetical
paper allocation decision. It answers how much Atlas should own, not what Atlas
should recommend. Allocation candidates must be evaluated through Simulation
Arena and Scientific Validation before any human-approved change can affect
portfolio behavior. No construction output can auto-execute, connect brokers,
or alter BUY/HOLD/AVOID logic.

Beta Runtime sits above the daily cycle as the continuous paper-only operating
state. It tracks runtime state, market phase, provider health, watchlist size,
paper portfolio value, open positions, recommendations today, alerts, timeline,
and health. It does not deploy, connect brokers, execute trades, or change
recommendation behavior.

Atlas Daily Journal sits after completed market-close cycles. It converts the
cycle, paper portfolio, provider health, macro context, catalyst context,
recommendation mix, and performance into a permanent research entry. Lessons
learned and research tasks are deterministic follow-up prompts only; they do
not alter BUY/HOLD/AVOID logic, execute trades, connect brokers, or deploy
changes.

## Model Evaluation Philosophy

Atlas should benchmark external AI/model providers before trusting them. The
Model Evaluation Lab compares candidates such as Mock Forecast, Kronos,
Chronos, TimesFM, FinBERT, and Financial RoBERTa with deterministic scorecards
covering accuracy, win rate, return, Sharpe ratio, drawdown, runtime, memory,
cost, and integration difficulty.

Model rankings can identify best overall, best accuracy, best risk-adjusted,
best low-cost, best speed, and not recommended candidates. These rankings are
advisory only. Atlas can suggest adoption, but it cannot install, activate, or
auto-adopt models. Benchmark review, human approval, implementation, and tests
are required before any candidate can affect recommendation behavior.

## Case Study Philosophy

Atlas should learn from validated recommendations as structured research cases,
not as automatic self-modifying rules. Case studies preserve the full context of
a completed recommendation: ticker, action, market regime, evidence, committee,
executive review, knowledge score, stability score, outcome, return, holding
period, validation, benchmark, hypotheses, and counterfactuals.

Lessons learned identify useful evidence, weak evidence, unexpected outcomes,
confidence calibration, committee effectiveness, executive effectiveness,
hypothesis success, and future improvements. The Research Laboratory can filter
winning cases, losing cases, bull-market cases, bear-market cases, committee
disagreements, forecast failures, and news failures. Case studies are read-only
research memory and must not change BUY, HOLD, AVOID, evidence weights,
providers, broker behavior, or execution.

## Research Memory Philosophy

Atlas Research Memory retrieves historically similar investment situations as
evidence, not as hard rules. Similarity scoring is deterministic and explainable
across ticker, sector, market regime, evidence profile, committee agreement,
executive review, knowledge score, stability score, catalyst profile,
probability profile, and portfolio strategy.

Every memory report includes similar historical cases, average historical
return, average holding period, win rate, common successful patterns, common
failure patterns, useful evidence, and frequent catalyst behavior. Discovery can
turn repeated analog behavior into observations such as high committee
agreement plus strong fundamentals resembling successful cases, or Technology
earnings setups recurring in Bull markets.

Research Memory is read-only. It must not change BUY, HOLD, AVOID, connect
brokers, execute trades, deploy changes, tune providers, or modify engine
weights.

## Provider Integration Philosophy

Atlas should be able to consume real data without requiring real data to run.
The default provider stack remains mock, fake, local, deterministic, and
offline-capable so tests and research remain reproducible.

Every provider must be swappable through a provider category, registry entry,
health status, and metadata record. Provider registry output tracks whether a
provider requires an API key, whether it is deterministic, whether it supports
offline operation, what it can do, what tickers or datasets it covers, and what
limitations are known.

Provider health statuses are `Healthy`, `Unavailable`, `Offline`, `Mock`,
`Experimental`, and `Deprecated`. These statuses explain readiness only. They
do not activate providers, change BUY/HOLD/AVOID, tune weights, connect
brokers, or deploy changes.

Future provider research should evaluate Yahoo, SEC EDGAR, FRED, Polygon,
Alpha Vantage, Finnhub, Stooq, CSV, and Parquet sources for coverage,
reliability, latency, licensing, cost, offline fallback, deterministic test
behavior, and fit with Atlas provider interfaces before integration.

## Macro Intelligence Philosophy

Atlas macro intelligence should provide economic context without becoming a
trading engine. The mock macro provider remains default and deterministic. The
future FRED-style provider is optional, requires no API key for tests, and must
fall back safely to mock output.

Macro research tracks CPI, Fed Funds Rate, Unemployment, GDP Growth, 10Y
Treasury Yield, and Yield Curve Spread. These inputs produce macro regime,
inflation pressure, rate pressure, growth pressure, recession risk, and macro
risk score. Macro output is read-only context for research, observatory,
discovery, and knowledge graph workflows. It must not change BUY/HOLD/AVOID,
provider selection, thresholds, broker behavior, or execution.

## Portfolio Strategy Philosophy

Atlas portfolio strategy research evaluates allocation decisions at the
portfolio level. It measures sector exposure, factor exposure, concentration,
cash, diversification, overlap, risk, expected return, expected volatility, and
Sharpe estimate before suggesting advisory actions.

Strategy recommendations include Increase, Reduce, Maintain, Replace,
Diversify, and Raise cash. Atlas can simulate a Current Portfolio against an
Atlas Portfolio and replay both over historical periods, but it must not connect
brokers, deploy allocation changes, or execute trades. Human approval is
required before any portfolio change.

Research should evaluate whether Atlas portfolio strategies outperform baseline
portfolios, and portfolio-level case studies should preserve lessons learned
from simulations and historical replay.

## Catalyst Intelligence Research

Atlas Catalyst Intelligence studies upcoming company, macroeconomic, and market
events as research context. Default catalyst data is deterministic and offline.
Future providers may include earnings calendars, economic calendars, SEC events,
and corporate actions, but they must be benchmarked before use.

Future catalyst studies should compare:

- Before earnings.
- After earnings.
- Macro weeks.
- High-volatility periods.

Research reports may rank catalysts by frequency, win rate, and average return,
and may compare examples such as Earnings versus Product Launches, CPI weeks,
or FOMC weeks. Catalyst research is not live trading, does not guarantee
returns, requires validation, requires human approval before any process change,
and must never execute automatically.

## Probabilistic Intelligence Research

Atlas probability research estimates likely outcomes from validated historical
evidence. Each report should show outperformance, market-performance, and
underperformance probabilities that sum to 100%, along with expected return,
expected holding period, best case, base case, worst case, similar cases, and
uncertainty.

Future studies should evaluate probability calibration, expected versus actual
return, expected versus actual holding period, probability accuracy, and the
distribution of uncertainty. Research should specifically test whether
high-probability recommendations outperform, whether high-uncertainty
recommendations underperform, and whether high knowledge scores improve
calibration.

Probability reports are explainable research outputs only. They do not change
BUY, HOLD, or AVOID, do not trigger trades, do not deploy anything, and require
validation before any human-approved process change.

## Hypothesis Philosophy

Atlas recommendations should expose their assumptions. The Hypothesis Engine
does not invent new evidence; it converts existing technical, fundamental,
forecast, news, portfolio, risk, validation, and benchmark evidence into
auditable assumptions and counterfactual scenarios. Counterfactual reasoning is
deterministic: the same evidence produces the same assumptions, confidence
drivers, fragile points, and possible flip conditions.

## Observatory Philosophy

Atlas should continuously measure itself without automatically changing itself.
The Performance Observatory aggregates validation, benchmark, committee,
provider, discovery, and experiment history into read-only report cards and
platform metrics. Its output supports controlled learning: research can propose
follow-up experiments or human-reviewed changes, but Atlas must not
auto-adjust recommendation logic, thresholds, providers, or engine weights from
observatory findings.

## Executive Review Philosophy

Executive review is a quality gate, not a recommendation engine. It checks
evidence completeness, committee agreement, historical consistency, validation
context, discovery conflicts, confidence calibration, missing providers,
missing data, event placeholders, and recommendation stability. It may require
follow-up research or mark a recommendation as not ready, but it never changes
BUY, HOLD, or AVOID. Any process change remains controlled learning and
requires human review.

## Historical Validation Philosophy

Atlas must be measured over historical data before any behavior change is
trusted. Historical validation replays deterministic market rows, validates
future outcomes, computes performance and risk metrics, compares controlled
variants, and produces Markdown reports. It integrates with validation,
benchmarking, discovery, observatory, and research workflows, but it remains a
measurement framework only.

## Market Regime Philosophy

Market Regime Intelligence classifies historical environments as Strong Bull,
Bull, Sideways, Volatile, Bear, or Strong Bear using deterministic metrics such
as trend, volatility, drawdown, moving-average position, and period return.
Regime tags exist so Atlas can compare historical evidence performance across
different environments.

Research Laboratory planning should use regime summaries to compare evidence
performance across regimes, such as whether Forecast works best in Bull
markets, News contributes most in Volatile regimes, or committee agreement is
strongest in Sideways markets. These are observations for controlled research,
not automatic behavior changes. Regime analysis must not change BUY, HOLD,
AVOID, evidence weights, provider selection, or execution behavior.

## AI-Assisted Portfolio Adjustment Note

Atlas may research AI-assisted portfolio adjustment as a historical experiment:
use only public information available at the decision date, propose
risk-controlled portfolio changes, and compare the AI-adjusted portfolio with
the original portfolio over quarterly evaluation windows.

Future experiment idea: `Atlas vs Original Portfolio`.

Future benchmark: AI-adjusted return improvement over baseline portfolio.

This is not live trading and does not guarantee returns. Atlas must validate
results before any behavior change, require human approval for any portfolio
change, and never execute changes automatically from research output.

## Knowledge Graph Philosophy

Atlas should remember relationships, not only rows. The Knowledge Graph turns
persisted records into an institutional memory of which recommendations were
validated, which evidence supported them, which committee and executive reviews
examined them, which experiments tested providers, and which discoveries or
historical replays relate. Graph queries are read-only and deterministic.
