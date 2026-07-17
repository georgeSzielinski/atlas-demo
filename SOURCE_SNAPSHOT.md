# Atlas Source Snapshot

This repository contains a security-sanitized, history-free snapshot of the real Atlas codebase under `atlas-source/`.

## Why the snapshot is history-free

The original private development repository contains historical `.env` versions. To avoid exposing historical credentials, this public repository intentionally begins with a new clean Git history after credential rotation and a source audit. It does not reproduce or claim historic commit timestamps, coding hours, or contributor activity.

## What is included

- Atlas application, API, engine, data-model, market, portfolio, research, service, and trading-safety source
- Backend and frontend test source
- Frontend source and package manifests
- Public-facing project README and dependency manifest

## What is deliberately excluded

- `.env` files and credentials
- databases, SQLite/WAL files, backups, generated reports, and local caches
- original Git history
- local agent configuration and internal work instructions

## Demo relationship

The deployed demo remains fixture-only and browser-only. It does not run the backend from `atlas-source/`, connect to any provider, access an account, or execute trades. This separation lets reviewers inspect real product code without turning the public demo into a live financial system.
