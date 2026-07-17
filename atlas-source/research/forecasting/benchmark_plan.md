# Forecasting Benchmark Plan

This plan defines an offline benchmark for comparing forecasting providers
before any production integration. It does not install models or change Atlas
engines.

## Models To Compare

- Mock: current deterministic Atlas baseline.
- Kronos: finance-specific OHLCV/K-line forecasting candidate.
- Amazon Chronos: general-purpose probabilistic time-series baseline.
- Google TimesFM: general-purpose long-context time-series baseline.

## Fixed Tickers

Use the current Atlas approved universe so benchmark results align with normal
recommendation workflows:

- ETFs: VOO, VTI, QQQ, SCHD
- Stocks: AAPL, MSFT, NVDA, AMZN, GOOGL, COST

## Forecast Horizon

Primary horizon:

- 5 trading days

Secondary research horizons:

- 10 trading days
- 20 trading days

The first pass should score all models on the 5-trading-day horizon before
expanding to longer horizons.

## Input Data Format

Each benchmark sample should contain:

- ticker
- prediction timestamp
- ordered OHLCV rows ending before the prediction timestamp
- open
- high
- low
- close
- volume
- optional amount, derived as `close * volume` when unavailable
- realized close price at the forecast horizon

Minimum history:

- 60 OHLCV rows for Kronos compatibility
- Prefer 252 trading days when available for general model context

Atlas normalized input contract:

```text
{
  "ticker": "AAPL",
  "history": [
    {
      "date": "YYYY-MM-DD",
      "open": 0.0,
      "high": 0.0,
      "low": 0.0,
      "close": 0.0,
      "volume": 0,
      "amount": 0.0
    }
  ],
  "horizon_days": 5
}
```

Model adapters may transform this format internally, but benchmark scoring must
use the same source rows and realized horizon close for every model.

## Evaluation Metrics

Forecast quality:

- Directional hit rate
- Average percentage return after predicted direction
- Mean absolute percentage error for expected change
- Expected-change calibration by confidence bucket
- Bullish precision
- Bearish precision
- Neutral accuracy

Atlas compatibility:

- Forecast score stability
- Confidence calibration
- Missing-data behavior
- Error clarity
- Deterministic repeatability for the same input

## Speed And Memory Notes

Record for every model:

- cold start time
- warm forecast time per ticker
- batch forecast time for all fixed tickers
- peak memory during model load
- peak memory during forecast
- CPU-only viability
- GPU requirement or benefit
- model weight size on disk

The benchmark should separate model load time from forecast time because Atlas
can eventually load providers lazily and reuse them.

## Pass/Fail Criteria

A model passes the first Atlas benchmark gate only if:

- It runs offline without breaking Atlas when unavailable.
- It returns direction, confidence, expected_change, days, and forecast_score.
- It completes all fixed tickers for the 5-trading-day horizon.
- It meets or beats Mock directional hit rate on the benchmark sample.
- It has clear failure behavior for missing or insufficient data.
- Its license is compatible with Atlas research usage.
- Its integration path does not require live trading, broker access, or
  deployment changes.

A model fails the first gate if:

- It cannot be run reproducibly on local benchmark data.
- It crashes instead of returning a clear unavailable/error state.
- It requires unavailable proprietary data for basic forecasts.
- It underperforms Mock with materially higher runtime or memory cost.
- Its license or terms are unclear enough to block integration.

## Feeding Results Into Atlas EvidenceEngine

Benchmark output should be converted into candidate forecast evidence fields:

- `forecast_direction`
- `forecast_confidence`
- `expected_change`
- `forecast_score`
- provider name
- horizon
- benchmark hit rate
- benchmark calibration notes

`EvidenceEngine` should eventually treat forecasting as one evidence category
among technical, fundamental, portfolio, risk, signal quality, and news
evidence. Benchmark results should inform forecast evidence weight and
confidence metadata, not replace other evidence sources.

## Safety Note

Forecasts are evidence, not trade decisions. Atlas should use forecasting
outputs as one input into research recommendations. Forecast models must not
trigger live trading, broker actions, deployment changes, or automated execution.
