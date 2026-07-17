# Atlas Demo

A browser-only, static demonstration of the Atlas investment-research experience.

## Safety boundary

- No backend or API routes
- No network requests, credentials, databases, cookies, analytics, or user-data collection
- No market-data provider, broker, portfolio, account, order, or trading integration
- All displayed values, events, scenarios, and research labels are deterministic synthetic fixtures
- Educational demonstration only; not financial advice

## Run locally

Open `index.html` in a browser, or serve the directory with any static file server:

```bash
python3 -m http.server 8000
```

Then visit `http://localhost:8000`.

## Publish safely

This repository is intentionally history-free and contains no `.env` file, dependency lockfile, backend code, or deployment secret. It is suitable for static hosting such as GitHub Pages.

Before public release, run a secret scan, inspect the Git history, and verify the deployed page in an incognito browser.
