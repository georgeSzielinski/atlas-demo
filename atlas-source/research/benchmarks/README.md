# Benchmarks Research

## Purpose

Maintain repeatable evaluation criteria for comparing future Atlas AI
components before integration.

The Atlas Benchmark Suite turns those criteria into stored measurements for
each intelligence component. ABS is a research and validation subsystem only; it
does not change recommendation behavior.

## Candidate Technologies

- Local benchmark scripts
- Historical recommendation validation sets
- Model comparison scorecards
- Model Evaluation Lab scorecards for Mock Forecast, Kronos, Chronos, TimesFM, FinBERT, and Financial RoBERTa candidates
- Latency and memory profilers
- License and maintenance review checklists

## Evaluation Criteria

- Accuracy against deterministic tasks
- Recommendation quality: BUY accuracy, HOLD accuracy, AVOID accuracy, overall hit rate, average return, average gain, and average loss
- Confidence calibration: high-confidence accuracy and low-confidence accuracy
- Signal quality: high-signal-quality accuracy and low-signal-quality accuracy
- Forecast quality: direction accuracy, MAE placeholder, RMSE placeholder, and runtime placeholder
- Evidence quality: effectiveness score, sample count, and last benchmark date
- Speed and memory use
- License compatibility
- Maintenance risk
- Community health
- Integration difficulty
- Clear Atlas Score across candidates

## Stored Results

ABS stores additive benchmark records with:

- Engine name
- Version
- Benchmark date
- Metric
- Value
- Notes

Evidence sources also store source name, effectiveness score, sample count, and
last benchmark date.

The Model Evaluation Lab stores candidate model scorecards with model name,
model type, provider, dataset, date range, validation window, sample size,
accuracy, win rate, average return, Sharpe ratio, max drawdown, runtime
placeholder, memory placeholder, cost placeholder, integration difficulty, and
recommendation.

Model rankings include best overall, best accuracy, best risk-adjusted, best
low-cost, best speed, and not recommended. Rankings can suggest future model
adoption research, but Atlas must not auto-adopt any model.

## Integration Status

Research and measurement only. Benchmark templates and stored ABS results guide
future AI integrations before promotion into production workflows.
External model providers require benchmark review, human approval,
implementation, and tests before integration. No paid APIs or new models are
required for the evaluation lab.
