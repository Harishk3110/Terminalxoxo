# KnK Capital Terminal

Repository: `Terminalxoxo`

KnK Capital Terminal is a private investment-terminal monorepo for KnK Capital. The current V1 remediation replaces the rejected static demo with database-backed FastAPI services, Alembic migrations, deterministic demo ingestion, an API-backed terminal UI, provider abstractions, FRED integration, portfolio/risk/backtest calculations, upload/report/Pine export paths, and security guardrails.

The build remains deliberately safe:

- Demo mode works without external credentials and labels seeded records as `DEMO DATA`.
- FRED is `NOT_CONFIGURED` until `FRED_ENABLED=true` and `FRED_API_KEY` are supplied.
- Broker integration is read-only by design.
- No broker order execution methods are present in application source.
- Public content is separated from private portfolio, provider, research, strategy, and risk APIs.

## Run Locally

```bash
corepack prepare pnpm@9.15.4 --activate
corepack pnpm install
python -m pip install -r services/api/requirements.txt
python -m alembic upgrade head
python services/api/scripts/seed_demo.py --reset
corepack pnpm --filter @knk/terminal-web build
```

API:

```bash
cd services/api
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Terminal web:

```bash
corepack pnpm --filter @knk/terminal-web dev --hostname 127.0.0.1 --port 3001
```

Public web:

```bash
corepack pnpm --filter @knk/public-web dev --hostname 127.0.0.1 --port 3000
```

## Docker

```bash
cp .env.example .env
docker compose up --build
```

Docker Compose config validates, but the latest local `docker compose build` could not run because Docker Desktop's Linux engine was not reachable on this machine. See `docs/BUILD_EVIDENCE.md`.

## Verification

```bash
python -m compileall -q services/api/app services/api/scripts services/worker-data/app services/worker-quant/app services/report-engine/app services/broker-agent
python -m pytest services/api/tests --cov=services/api/app --cov-report=term-missing
corepack pnpm typecheck
corepack pnpm lint
corepack pnpm test
corepack pnpm --filter @knk/public-web build
corepack pnpm --filter @knk/terminal-web build
corepack pnpm test-e2e
docker compose config --quiet
```

See `STATUS.md`, `TASKS.md`, `docs/CORE_ACCEPTANCE.md`, and `docs/BUILD_EVIDENCE.md` for exact results.
