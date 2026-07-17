# Scientific Validation Framework

The Scientific Validation Framework is Atlas's research-quality gate for
proposed engines, providers, models, features, and evidence sources.

It validates adoption evidence only. It does not change BUY/HOLD/AVOID logic,
does not deploy code, does not connect brokers, and does not execute trades.

## Required Experiment Record

Each experiment records:

- Experiment ID
- Date
- Feature tested
- Baseline metrics
- Candidate metrics
- Sample size

## Required Metrics

- Win rate
- Average return
- Sharpe ratio
- Maximum drawdown
- Probability calibration
- Recommendation accuracy
- Average holding period
- Trade frequency

## Required Validation Coverage

Cross-regime validation covers bull, bear, sideways, high-volatility,
low-volatility, rising-rate, and falling-rate environments.

Generalization tests cover training period, validation period, out-of-sample
period, and a walk-forward placeholder.

## Outcomes

Scientific results are deterministic:

- `Improved`
- `Neutral`
- `Regression`
- `Not Enough Evidence`

Adoption decisions are deterministic:

- `ADOPT`
- `RETEST`
- `REJECT`

`ADOPT` means the proposal has passed the research evidence gate. Human
approval, implementation, and tests are still required before any system
behavior can change.
