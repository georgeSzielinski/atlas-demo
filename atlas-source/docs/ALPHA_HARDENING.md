# Atlas Alpha Hardening

Atlas alpha defaults are intentionally safe and local-first.

## Safe Defaults

- Market data defaults to `mock`.
- Historical market data defaults to `mock`.
- News defaults to `fake`.
- Fundamentals default to `mock`.
- Forecasting defaults to `mock`.
- Kronos remains optional and lazy-loaded.

## Deployment Boundary

Atlas has no public deployment configuration in the application path. FastAPI
and Vite are local development surfaces unless explicitly deployed by a human.

## Trading Boundary

Atlas does not connect brokers or live trading APIs. Trading helpers remain
simulation and approval utilities; recommendation, research, historical replay,
and observability layers do not execute trades.

## Generated Files

Generated caches, local databases, reports, frontend builds, coverage output,
and local environment files should remain ignored. If any generated artifact was
tracked before this hardening pass, leave it untouched unless a human explicitly
approves an untracking cleanup.

## Controlled Learning

Benchmark, discovery, historical validation, observatory, executive review, and
knowledge graph outputs are measurement layers. They can suggest research but
must not automatically modify recommendation behavior, providers, thresholds,
or deployment state.
