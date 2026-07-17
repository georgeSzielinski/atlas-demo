# Forecasting Research

## Purpose

Track candidate time-series and market forecasting systems that could improve
Atlas forecasts without replacing the existing provider interface.

## Candidate Technologies

- Kronos time-series forecasting
- Amazon Chronos
- Google TimesFM
- Moirai
- PatchTST
- Lag-Llama

## Evaluation Criteria

- Directional accuracy over fixed holding periods
- Calibration of confidence and expected change
- Runtime on local hardware
- Memory and dependency footprint
- License compatibility
- Ease of integration with `ForecastProvider`
- Robustness when price history is incomplete
- Fit for financial OHLCV data
- Support for probabilistic forecasts or confidence intervals
- Ability to run locally without managed cloud services

## Current Survey

See `forecasting_survey.md` for the first Atlas comparison of Kronos, Amazon
Chronos, Google TimesFM, Moirai, PatchTST, and Lag-Llama.

## Benchmark Plan

See `benchmark_plan.md` for the offline benchmark design comparing Mock, Kronos,
Amazon Chronos, and Google TimesFM on fixed Atlas tickers and forecast horizons.

## Integration Status

Research only. Kronos is optional behind safe guards, while the mock provider
remains the default forecast path.
