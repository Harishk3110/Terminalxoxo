# Architecture

The repository is a monorepo with deployable applications under `apps/`, Python services under `services/`, shared TypeScript packages under `packages/`, and operational configuration under `infrastructure/` and `monitoring/`.

## Runtime

- `apps/public-web`: Next.js public website. It reads sanitized public content only.
- `apps/terminal-web`: Next.js private terminal. It renders demo data, route shells, function search, portfolio, risk, options, quant, reports, and system panels.
- `services/api`: FastAPI application for authentication, data access, portfolio, risk, providers, broker status, jobs, health, and metrics.
- `services/worker-data`: background ingestion and data-quality workflow boundary.
- `services/worker-quant`: analytical worker boundary for backtests, factors, simulations, and models.
- `services/report-engine`: report request service for XLSX, PPTX, PDF, and chart exports.
- `services/broker-agent`: local read-only paper-account bridge.

## Safety Boundaries

Public APIs expose only public models. Broker action methods are not implemented. Demo data carries source, dataset, timestamp, currency, methodology, and quality labels.
