# SEC Intelligence Research

Atlas SEC Intelligence is an offline-first provider architecture for company
filing research.

## Providers

- `mock` is the default deterministic provider.
- `edgar` is registered as a future no-key SEC EDGAR provider.

Mock remains the default so tests and research run without internet, API keys,
deployment, or broker connections.

## Filing Types

Atlas supports normalized placeholders for:

- `10-K`
- `10-Q`
- `8-K`
- `DEF 14A`
- `S-1`

## Normalized Filing Shape

Each filing exposes:

- filing date
- form type
- company
- ticker
- sections available
- filing URL placeholder

## Summary Sections

Each filing includes deterministic summary placeholders for:

- Business
- Risk Factors
- MD&A
- Financial Statements
- Management Guidance
- Legal Proceedings

## Policy

SEC Intelligence is read-only research context. It does not change
BUY/HOLD/AVOID, evidence weights, provider selection, thresholds, broker
behavior, or execution.
