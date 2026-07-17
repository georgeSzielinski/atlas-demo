# Atlas Intelligence Pipeline

Atlas should operate as a staged research pipeline. Each stage has a narrow responsibility, produces structured outputs, and passes auditable context to the next stage.

The production orchestration layer is `IntelligencePipeline` in
`services.investment_platform`. It coordinates the lifecycle without rewriting
existing engines or changing recommendation behavior.

## Pipeline Flow

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

## Runtime Execution Order

The current Atlas runtime uses this execution order:

1. Fetch market data through `MarketEngine` and the configured `DataProvider`.
2. Run technical analysis through the existing market analysis flow.
3. Run fundamental analysis through `RecommendationEngine` and `FundamentalEngine`.
4. Run news analysis through `RecommendationEngine` and `NewsEngine`.
5. Run forecast provider analysis through `RecommendationEngine` and `ForecastEngine`.
6. Prepare portfolio context through `PortfolioEngine`.
7. Prepare risk context through `RiskEngine`.
8. Build evidence through `EvidenceEngine`.
9. Calibrate confidence through `ConfidenceEngine`.
10. Aggregate evidence through `IntelligenceFusionEngine`.
11. Evaluate signal quality through `SignalQualityEngine`.
12. Build recommendations through `RecommendationEngine`.
13. Initialize validation status for saved recommendations.
14. Keep benchmark logging available for completed validations.
15. Persist dashboard, recommendations, portfolio snapshot, and report output.
16. Return the final recommendation while preserving the current dashboard return value.

`RecommendationEngine` currently owns the combined fundamental, news, forecast,
evidence, confidence, signal quality, and recommendation construction flow.
`IntelligencePipeline` coordinates that flow from above instead of duplicating
the business logic.

## Extension Points

Future AI systems should attach at stable orchestration boundaries:

- Data providers for market, SEC, FRED, news, and other external data.
- Forecast providers for Chronos, TimesFM, Moirai, Lag-Llama, and other models.
- News providers for financial sentiment, event extraction, and explainability.
- Fundamental providers for filings, earnings, transcripts, and statements.
- Portfolio engines for optimization, correlation, diversification, and efficient frontier analysis.
- Risk engines for VaR, expected shortfall, regimes, and tail risk.
- Validation jobs for historical evaluation and recommendation grading.
- Benchmark runners for measuring candidate model quality before promotion.

## Fusion, Validation, And Benchmark Flow

Fusion combines technical, fundamental, forecast, news, portfolio, risk,
evidence, and confidence outputs into conviction, cases, engine contributions,
agreement, disagreement, uncertainty, and rationale.

The Investment Committee sits beside fusion as an evidence-based debate layer.
It is not a collection of uncontrolled agents and does not use random AI
argument generation. Technical, Fundamental, Forecast, News, Portfolio, Risk,
Validation, and Benchmark specialists each read the evidence category assigned
to them and produce a deterministic stance, confidence, evidence, concern, and
summary.

The committee moderator compares those specialist views into bull, bear, and
neutral cases, committee agreement, strongest bull and bear arguments, and main
disagreement. It only uses existing evidence and fusion context. Committee
output explains the recommendation but does not change recommendation actions,
engine weights, provider selection, or Atlas behavior without human approval.

Validation records expected holding period, entry timestamp, exit timestamp,
notes, and standard validation windows of 7, 30, 90, 180, and 365 days.

Benchmarking tracks per-engine accuracy, rolling accuracy, confidence
calibration, recommendation accuracy, validation success, average recommendation
lifetime, rolling performance, and historical snapshots. Benchmark suggestions
are advisory and require human approval before any behavior changes.

## Research Laboratory Flow

The Atlas Research Laboratory sits after history, validation, and benchmarks.
It evaluates Atlas itself rather than producing recommendations.

ARL responsibilities:

- Create experiment records with dataset, ticker list, providers, validation
  window, benchmark snapshot, status, and notes.
- Compare evidence combinations such as Technical only, Technical + Forecast,
  Technical + Forecast + Fundamentals, and Everything.
- Rank forecast, news, fundamental, and future providers side by side.
- Attribute each recommendation to the strongest contributing engine, the
  confidence drag, and the evidence that materially changed the decision.
- Produce Markdown research reports with recommendations for future tests.

Research output feeds benchmark planning and provider review. It does not
change runtime provider selection, engine weights, or recommendation behavior
without human approval.

## 1. Market Data

Market Data is the raw input layer. It should include prices, volume, corporate actions, fundamentals, news, SEC filings, earnings data, macro data, and portfolio holdings.

Each dataset should preserve source, timestamp, coverage, freshness, and known quality issues.

## 2. Specialized Intelligence Layers

Atlas routes data into independent intelligence layers:

- Forecast Intelligence for time-series forecasts.
- News Intelligence for sentiment, event detection, and news explanations.
- Fundamental Intelligence for business quality, filings, earnings, and statements.
- Portfolio Intelligence for holdings-aware risk and return impact.
- Risk Intelligence for downside, volatility, regime, and tail risk.
- Macro Intelligence for economic context and rate-sensitive interpretation.

Each layer should return structured signals rather than final recommendations.

## 3. Evidence Engine

The Evidence Engine merges layer outputs into an evidence set. Evidence should be classified as supporting, opposing, neutral, or missing.

Required evidence metadata:

- Source system.
- Model or provider name.
- Asset, sector, portfolio, or macro scope.
- Timestamp and freshness.
- Signal direction.
- Strength.
- Explanation.
- Raw reference or source link when available.

## 4. Confidence Engine

The Confidence Engine estimates whether Atlas should trust a signal.

Inputs should include:

- Agreement across intelligence layers.
- Historical accuracy of the model and signal type.
- Data freshness and completeness.
- Source credibility.
- Forecast uncertainty.
- Risk regime.
- Conflict between evidence items.

Confidence should be separate from recommendation direction. A bullish signal can have low confidence, and a bearish signal can have high confidence.

## 5. Signal Quality

Signal Quality determines whether the signal is actionable.

It should consider:

- Evidence breadth.
- Evidence conflict.
- Model benchmark performance.
- Market liquidity.
- Volatility.
- Portfolio relevance.
- Time horizon fit.
- Whether the signal is stale, crowded, or unsupported.

Low-quality signals should be downgraded, held for review, or excluded from recommendation output.

## 6. Validation

Validation checks the signal against historical evidence before it becomes a recommendation.

Validation methods:

- Backtesting of rule sets and model-driven signals.
- Historical evaluation of forecasts and event calls.
- Recommendation grading by realized outcome.
- Model benchmarking against current Atlas baselines.

Validation should produce approval, downgrade, reject, or research-required outcomes.

## 7. Recommendation

The Recommendation Engine converts validated signals into investment research actions.

Recommendation outputs should include:

- Action such as buy, hold, sell, watch, avoid, resize, or rebalance.
- Time horizon.
- Confidence score.
- Signal quality score.
- Primary thesis.
- Key evidence.
- Key risks.
- Review trigger or expiration date.

## 8. Dashboard

The Dashboard presents recommendations, evidence, confidence, risk, and history in a web and mobile-friendly interface.

The dashboard should let users inspect:

- Why Atlas made a recommendation.
- Which intelligence layers contributed.
- Which evidence disagreed.
- How confident Atlas is.
- What would change the recommendation.
- How past recommendations performed.

## 9. History

History is the audit and learning layer. Atlas should store recommendation snapshots, evidence sets, confidence inputs, signal quality scores, validation decisions, and realized outcomes.

History enables:

- Recommendation grading.
- Model performance review.
- User trust and auditability.
- Regression detection after model or provider changes.

## 10. Research Feedback Loop

The Research Feedback Loop turns history into platform improvement.

It should identify:

- Models that outperform or underperform.
- Signal types that decay over time.
- Regimes where Atlas is weak.
- Data sources that create noisy or stale evidence.
- Candidate AI systems worth benchmarking.

Research findings should feed back into provider selection, benchmark design, model promotion, and model retirement.

The Research Laboratory is the concrete implementation of this feedback loop.
It turns saved history, validation outcomes, benchmark snapshots, and provider
metadata into controlled experiments that can be reviewed before any Atlas
configuration or engine behavior changes.
