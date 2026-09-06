# Architecture

KnK Capital Terminal is a monorepo with deployable apps under `apps/`, Python services under `services/`, shared TypeScript packages under `packages/`, Alembic migrations under `migrations/`, and infrastructure under `docker-compose.yml`, `infrastructure/`, and `monitoring/`.

## Runtime Layers

The backend follows this path for operational data:

`API routes -> application services -> domain logic -> repositories -> SQLAlchemy models -> database`

Financial calculations live in `services/api/app/domain.py` and service classes, not in route handlers. HTTP handlers under `services/api/app/main.py` bind request/response concerns to services and repositories.

## Services

- `services/api`: authenticated investment APIs, sessions, providers, ledger, performance, risk, hedge, data, research jobs and internal reports.
- `services/worker-data`: Redis-backed job consumer that updates persisted `ingestion_jobs`.
- `services/worker-quant`: analytical worker boundary with DB health check.
- `services/report-engine`: independent report service that generates real `.xlsx` files.
- `services/broker-agent`: read-only local heartbeat/status agent. No execution capability exists.
- `apps/terminal-web`: private Next.js terminal, backed by `@knk/api-client`.

## Persistence

Alembic revision `0001_core_schema` creates auth, reference, provider, raw object, macro, market data, data operations, portfolio, performance/risk/hedge, quant, research, and operations tables. Authoritative money values use SQLAlchemy `Numeric` and Python `Decimal`.

Local non-Docker development defaults to SQLite. Docker Compose config points `DATABASE_URL` to PostgreSQL 16.

## Data Flow

Demo ingestion follows the real pipeline:

`DemoProvider -> raw object -> validation/normalization -> database -> service -> API -> terminal UI`

FRED follows the same raw-to-curated path when credentials are configured:

`FRED JSON -> object storage -> content hash -> Pydantic parse -> macro series/observations/vintages -> provider health/job state -> macro dashboard`

## Safety Boundaries

- All investment API routes, including legacy aliases, require authentication.
- Private terminal API owns portfolios, transactions, strategies, risk, provider state, jobs, and uploads.
- Broker agent is read-only.
- Repository-wide no-execution tests fail if forbidden broker action method names appear in application source.
- FRED and other provider secrets are loaded from environment variables and are not returned to the browser.
