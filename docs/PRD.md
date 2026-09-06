# Product Requirements

KnK Capital Terminal is a private internal investment operating system. The controlling requirements are in PRD_TERMINAL_ONLY.md; earlier visitor-facing scope is cancelled.

## Goals

- Run locally without external credentials.
- Show all demo financial information as `DEMO DATA`.
- Require authentication for all investment information.
- Support provider connections without code changes.
- Keep broker integration read-only and paper-account oriented.

## Initial Scope

- Private terminal shell with the requested market, portfolio, risk, research, quant, reporting, data, system, and settings routes.
- FastAPI backend with health, metrics and authenticated investment, provider, job and read-only broker endpoints.
- Data worker, quant worker, report engine, and broker agent service boundaries.
- Safety tests that fail when forbidden broker action method names enter application source.
