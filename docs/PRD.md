# Product Requirements

KnK Capital Terminal is a private investment operating system for KnK Capital with a separate public website. Version 0.1 establishes the executable demo-mode platform and the safety boundaries for later connected-provider work.

## Goals

- Run locally without external credentials.
- Show all demo financial information as `DEMO DATA`.
- Keep public content separate from portfolio, broker, signal, and private research data.
- Support provider connections without code changes.
- Keep broker integration read-only and paper-account oriented.

## Initial Scope

- Public website with firm, product, methodology, research, disclosure, privacy, legal, about, and contact routes.
- Private terminal shell with the requested market, portfolio, risk, research, quant, reporting, data, system, and settings routes.
- FastAPI backend with health, metrics, public-content, market, portfolio, risk, provider, job-event, and broker-status endpoints.
- Data worker, quant worker, report engine, and broker agent service boundaries.
- Safety tests that fail when forbidden broker action method names enter application source.
