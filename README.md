# Atlas Showcase

A security-sanitized Atlas source snapshot plus a browser-only fixture-mode demo built from the real React frontend components and view-model selectors.

## Safety boundary

- No deployed backend or API routes
- No runtime `fetch`/XHR, credentials, databases, cookies, analytics, or user-data collection
- No market-data provider, broker, account, order, or trading integration
- Only four read-only product views are available: Mission Control, Recommendation Explorer, Research Memory, and Learning Center
- All displayed values, events, scenarios, and research labels are deterministic synthetic fixtures served from an in-memory adapter
- Educational demonstration only; not financial advice

## Review the real code

`atlas-source/` contains the audited, history-free Atlas source snapshot. See [SOURCE_SNAPSHOT.md](SOURCE_SNAPSHOT.md) for the public-release boundary and exclusions.

## Run the fixture demo locally

```bash
cd demo
npm ci
npm run dev
```

For a production-equivalent build:

```bash
cd demo
npm run build
npm run preview
```

## Publish safely

This repository is intentionally history-free. The source snapshot has no `.env`, credential, database, cache, backup, or deployment secret. The GitHub Pages workflow deploys only `demo/dist`, never `atlas-source/`.

Before public release, run a secret scan, inspect the Git history, and verify the deployed page in an incognito browser.
