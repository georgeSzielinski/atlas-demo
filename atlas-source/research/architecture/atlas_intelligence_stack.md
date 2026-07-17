# Atlas Intelligence Stack

Atlas should be designed as an orchestration platform for investment research, not as a single AI model. The platform coordinates specialized intelligence layers, evidence collection, confidence scoring, validation, and recommendation history so that each signal can be traced, benchmarked, and improved over time.

## Architecture Principles

- Use specialized models for specialized jobs.
- Keep every recommendation evidence-backed and auditable.
- Separate signal generation from validation and presentation.
- Benchmark candidate AI systems before production integration.
- Preserve model outputs, confidence inputs, and recommendation outcomes for historical review.
- Treat AI providers as replaceable components behind stable Atlas interfaces.

## 1. Forecast Intelligence

Forecast Intelligence estimates future price, return, volatility, or trend behavior from market data.

### Current

- Mock forecast provider for deterministic development and testing.
- Kronos integration for time-series forecasting experiments.

### Future Candidates

- Chronos for probabilistic time-series forecasting.
- TimesFM for large-scale time-series foundation model evaluation.
- Moirai for universal forecasting across different asset and feature types.
- Lag-Llama for autoregressive probabilistic forecasts.

### Responsibilities

- Generate horizon-specific forecasts.
- Produce uncertainty ranges where available.
- Track model version, input window, forecast horizon, and data source.
- Compare forecast output against historical realized outcomes.

## 2. News Intelligence

News Intelligence converts market news into structured sentiment, event, and explanation signals.

### Current

- Fake provider for repeatable local development.
- News Engine for ingesting, normalizing, and scoring news items.

### Future

- FinBERT for finance-specific sentiment classification.
- Financial RoBERTa for broader financial language understanding.
- LLM explainability for summarizing why news matters to a ticker, sector, or macro theme.

### Responsibilities

- Classify article sentiment and relevance.
- Detect events such as earnings surprises, guidance changes, analyst actions, litigation, mergers, and macro shocks.
- Separate source credibility from model confidence.
- Attach article-level evidence to downstream recommendations.

## 3. Fundamental Intelligence

Fundamental Intelligence evaluates business quality, valuation, financial health, and earnings trajectory.

### Current

- Foundational research documentation exists for SEC, earnings, and financial research domains.
- Current implementation should be treated as early-stage and orchestration-ready rather than complete.

### Future

- SEC filing analysis for 10-K, 10-Q, 8-K, proxy, and registration statement review.
- Earnings report analysis across transcripts, press releases, guidance, and analyst Q&A.
- Financial statement extraction for income statement, balance sheet, cash flow, segment, and footnote data.

### Responsibilities

- Extract structured financial metrics.
- Identify trends in revenue, margins, cash flow, leverage, dilution, and guidance.
- Detect accounting, liquidity, concentration, and governance risks.
- Provide evidence-backed business quality and valuation signals.

## 4. Portfolio Intelligence

Portfolio Intelligence evaluates how a recommendation affects a portfolio rather than only a single asset.

### Current

- Research documentation exists for portfolio analysis.
- Current production scope should be considered incomplete until portfolio-aware scoring is implemented.

### Future

- Correlation analysis across holdings, sectors, factors, and market regimes.
- Diversification scoring for concentration and exposure balance.
- Efficient frontier analysis for risk and return tradeoffs.
- Portfolio optimization with constraints for position size, risk budget, liquidity, and user preferences.

### Responsibilities

- Estimate marginal contribution to portfolio risk.
- Detect overexposure to sectors, themes, factors, and single-name concentration.
- Support position sizing and rebalance recommendations.
- Explain portfolio impact in plain language.

## 5. Risk Intelligence

Risk Intelligence identifies downside exposure, instability, and conditions where signals should be discounted.

### Current

- Risk should be treated as a required orchestration layer even where implementation remains limited.
- Existing market and forecast outputs can provide basic volatility and downside inputs.

### Future

- Value at Risk for portfolio and asset-level loss estimates.
- Expected shortfall for tail-loss severity.
- Volatility regime detection.
- Tail risk detection using historical shocks, drawdowns, liquidity stress, and correlation breakdowns.

### Responsibilities

- Estimate downside risk by horizon.
- Flag fragile recommendations when uncertainty or tail exposure is high.
- Detect changing regimes that reduce model reliability.
- Feed risk penalties into confidence, signal quality, and recommendation scoring.

## 6. Macro Intelligence

Macro Intelligence connects asset-level recommendations to the broader economic environment.

### Future

- FRED economic data integration.
- CPI and inflation trend analysis.
- GDP growth and revision tracking.
- Fed meeting calendars, statements, rate decisions, and dot plot interpretation.
- Treasury yield curve and real yield analysis.
- Unemployment and labor market trend analysis.

### Responsibilities

- Track macro regimes that affect valuation, rates, credit, and risk appetite.
- Connect macro releases to sector and asset sensitivity.
- Provide context for market moves and recommendation changes.
- Add macro evidence to recommendation history.

## 7. Explainability

Explainability turns raw model output into an auditable investment thesis.

### Evidence Engine

The Evidence Engine collects supporting and opposing evidence from forecasts, news, fundamentals, portfolio context, risk, and macro data. It should preserve source, timestamp, model, score, and reasoning metadata for every evidence item.

### Confidence Engine

The Confidence Engine combines model confidence, evidence agreement, source quality, historical model accuracy, data freshness, and regime stability into a recommendation confidence score.

### Signal Quality

Signal Quality measures whether the signal is actionable. It should account for evidence breadth, conflict between layers, data age, model reliability, volatility, liquidity, and whether the signal has been validated historically.

### Validation

Validation checks whether the signal type has performed well under comparable historical conditions. It should gate or downgrade recommendations that lack sufficient historical support.

### Recommendation Engine

The Recommendation Engine converts validated signals into user-facing outputs such as buy, hold, sell, watch, avoid, resize, or rebalance. It should include rationale, confidence, risks, evidence links, and expected review date.

## 8. Validation Layer

The Validation Layer is responsible for proving whether Atlas intelligence works before and after integration.

### Backtesting

Backtesting evaluates strategies, signals, and recommendation rules against historical market data with realistic assumptions around timing, slippage, transaction costs, and survivorship bias.

### Historical Evaluation

Historical evaluation compares model forecasts, sentiment calls, fundamental signals, and risk warnings against realized outcomes.

### Recommendation Grading

Recommendation grading tracks whether each recommendation was directionally correct, risk-adjusted, timely, and useful relative to alternatives.

### Model Benchmarking

Model benchmarking compares candidate models against Atlas baselines using common datasets, horizons, asset groups, error metrics, calibration metrics, and economic utility metrics.

## 9. Research Layer

The Research Layer evaluates candidate AI systems before integration into Atlas.

Candidate systems should move through this path:

1. Research survey and fit assessment.
2. Offline benchmark against Atlas baseline data.
3. Error, calibration, latency, cost, and reliability review.
4. Shadow-mode evaluation without user-facing recommendations.
5. Limited integration behind feature flags or provider interfaces.
6. Recommendation impact review.
7. Promotion, rollback, or rejection decision.

Research outputs should include model cards, benchmark reports, failure cases, integration risks, and maintenance requirements.

## 10. Final Architecture

```text
                                   +-------------------+
                                   |    Market Data    |
                                   | prices, volume,   |
                                   | news, filings,    |
                                   | macro, portfolio  |
                                   +---------+---------+
                                             |
                                             v
+--------------------------------------------------------------------------------+
|                       Specialized Intelligence Layers                           |
|                                                                                |
|  +----------------+  +---------------+  +------------------+  +--------------+ |
|  | Forecast       |  | News          |  | Fundamental      |  | Portfolio    | |
|  | Mock, Kronos,  |  | Fake Provider,|  | SEC, earnings,   |  | correlation, | |
|  | Chronos,       |  | News Engine,  |  | statements,      |  | frontier,    | |
|  | TimesFM,       |  | FinBERT,      |  | valuation        |  | optimization | |
|  | Moirai,        |  | FinRoBERTa    |  |                  |  |              | |
|  | Lag-Llama      |  |               |  |                  |  |              | |
|  +----------------+  +---------------+  +------------------+  +--------------+ |
|                                                                                |
|  +----------------+  +---------------+                                         |
|  | Risk           |  | Macro         |                                         |
|  | VaR, expected  |  | FRED, CPI,    |                                         |
|  | shortfall,     |  | GDP, Fed,     |                                         |
|  | volatility,    |  | yields, jobs  |                                         |
|  | tail risk      |  |               |                                         |
|  +----------------+  +---------------+                                         |
+--------------------------------------+-----------------------------------------+
                                       |
                                       v
                              +-----------------+
                              | Evidence Engine |
                              | supporting and  |
                              | opposing facts  |
                              +--------+--------+
                                       |
                                       v
                             +-------------------+
                             | Confidence Engine |
                             | model, source,    |
                             | history, regime   |
                             +---------+---------+
                                       |
                                       v
                              +----------------+
                              | Signal Quality |
                              | freshness,     |
                              | agreement,     |
                              | actionability  |
                              +--------+-------+
                                       |
                                       v
                              +----------------+
                              |   Validation   |
                              | backtests,     |
                              | grading,       |
                              | benchmarks     |
                              +--------+-------+
                                       |
                                       v
                              +----------------+
                              | Recommendation |
                              | buy, hold,     |
                              | sell, watch,   |
                              | resize         |
                              +--------+-------+
                                       |
                                       v
                              +----------------+
                              |   Dashboard    |
                              | web and mobile |
                              | research UI    |
                              +--------+-------+
                                       |
                                       v
                              +----------------+
                              |    History     |
                              | outcomes,      |
                              | evidence,      |
                              | decisions      |
                              +--------+-------+
                                       |
                                       v
                         +-------------------------+
                         | Research Feedback Loop  |
                         | benchmark, improve,     |
                         | replace, or retire AI   |
                         +------------+------------+
                                      |
                                      +-----------> Specialized Intelligence Layers
```
