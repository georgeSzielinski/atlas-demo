# Kronos Integration

Kronos is an optional forecast provider for Atlas. It implements the same
provider interface as the current mock forecast provider, but it is not the
default and Atlas must continue to run when Kronos is not installed.

Atlas should not depend directly on Kronos. Instead, `ForecastEngine` will call a
configured `ForecastProvider`, which allows Kronos, mock forecasts, or any future
forecasting model to be swapped in without changing recommendation logic.

When Kronos is activated, Atlas provides OHLCV market data to the
Kronos-backed provider. The provider returns:

- direction
- confidence
- expected_change
- days
- forecast_score

## OHLCV Payload Contract

Kronos input should be a stock payload that includes an OHLCV history collection.
Each history row must include:

- date
- open
- high
- low
- close
- volume

Optional field:

- amount

The Kronos-backed provider requires at least 60 OHLCV rows before running a
forecast. Shorter histories are rejected by the provider.

## Atlas to Kronos Mapping

`KronosForecastProvider._to_kronos_payload(stock)` prepares Atlas market data for
Kronos calls without importing Kronos. It accepts a stock object or dict
with one of these history attributes/keys:

- `ohlcv`
- `history`
- `prices`

Each Atlas row maps into Kronos input as follows:

- `date` -> `timestamps`
- `open` -> `open`
- `high` -> `high`
- `low` -> `low`
- `close` -> `close`
- `volume` -> `volume`
- `amount` -> `amount`

If `amount` is missing, Atlas will derive it as `close * volume` for the adapter
payload.

The adapter returns a dict-of-lists that matches the required DataFrame columns:

- `timestamps`
- `open`
- `high`
- `low`
- `close`
- `volume`
- `amount`

The provider converts this structure to `pandas.DataFrame(...)` before calling
`KronosPredictor.predict(...)`.

Adapter validation checks:

- at least 60 history rows
- ascending timestamps
- numeric `open`, `high`, `low`, `close`, `volume`, and `amount`

Kronos imports happen inside `KronosForecastProvider`, so Atlas remains fully
functional without Kronos installed.

## Kronos Prediction Path

`KronosForecastProvider.forecast(...)` is guarded by availability checks and
lazy model loading.

The provider:

1. accepts a properly formatted pandas DataFrame with `timestamps`, `open`,
   `high`, `low`, `close`, `volume`, and `amount`
2. loads `KronosTokenizer` from `KRONOS_TOKENIZER_NAME`
3. loads `Kronos` from `KRONOS_MODEL_NAME`
4. creates `KronosPredictor(model, tokenizer, max_context=512)`
5. calls `KronosPredictor.predict(...)` with a short future timestamp horizon
6. converts predicted close values into Atlas forecast fields

Kronos imports are local to the provider so Atlas remains importable when
Kronos, Torch, or model weights are not installed. If Kronos is selected but
unavailable, `ForecastEngine` logs a warning and falls back to
`MockForecastProvider`.

The forecast result should use this format:

```python
{
    "direction": "Bullish",
    "confidence": 72.5,
    "expected_change": 3.2,
    "days": 5,
    "forecast_score": 76,
}
```

## Kronos Forecast Scoring

`KronosForecastProvider._score_prediction(historical_close, predicted_close)`
converts raw Kronos close predictions into Atlas forecast fields without
leaking Kronos-specific output into Atlas scoring.

Scoring rules:

- `expected_change` is the percentage move from the last historical close to the
  final predicted close.
- `direction` is `Bullish` when expected change is greater than 1%.
- `direction` is `Bearish` when expected change is less than -1%.
- `direction` is `Neutral` otherwise.
- `forecast_score` starts at 50.
- Bullish predictions add up to 30 points based on expected change.
- Bearish predictions subtract up to 30 points based on expected change.
- Neutral predictions stay at 50.
- `forecast_score` is clamped from 0 to 100.
- `confidence` is a placeholder based on absolute expected change and clamped
  from 1 to 99.

Atlas will combine the forecast result with technical analysis, fundamental
analysis, portfolio health, and risk analysis to produce the overall investment
intelligence score.

## Optional Activation

Kronos remains optional. The mock provider remains the default because it is
deterministic, dependency-free, and keeps Atlas usable on any development
machine.

Configure Kronos with environment variables before starting Atlas:

```bash
export KRONOS_REPO_PATH="/path/to/Kronos"
export KRONOS_MODEL_NAME="NeoQuasar/Kronos-small"
export KRONOS_TOKENIZER_NAME="NeoQuasar/Kronos-Tokenizer-base"
```

Activate Kronos by setting:

```python
FORECAST_PROVIDER = "kronos"
```

or by constructing `ForecastEngine(forecast_provider="kronos")` in a controlled
test or experiment.

If the repo path is missing, dependencies are not importable, or Kronos loading
fails, Atlas falls back to the mock provider instead of crashing.

## Forecast Provider Selection

Atlas configures forecast provider selection through `core.settings`:

```python
FORECAST_PROVIDER = "mock"
KRONOS_REPO_PATH = ""
KRONOS_MODEL_NAME = "NeoQuasar/Kronos-small"
KRONOS_TOKENIZER_NAME = "NeoQuasar/Kronos-Tokenizer-base"
```

Supported values:

- `"mock"`
- `"kronos"`

`ForecastEngine` also accepts an explicit `forecast_provider` option for tests
and one-off construction:

- `forecast_provider="mock"` uses `MockForecastProvider`.
- `forecast_provider="kronos"` attempts to use `KronosForecastProvider`.

The setting default remains `mock`, so existing Atlas runs continue to use the
mock forecast provider. If `kronos` is selected but Kronos is not importable, or
if an invalid value is configured, Atlas logs a clear warning and safely falls
back to `MockForecastProvider`.
