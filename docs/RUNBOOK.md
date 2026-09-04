# Runbook

## Local Non-Docker Validation

```bash
python -m pip install -r services/api/requirements.txt
corepack pnpm install
python -m alembic upgrade head
python services/api/scripts/seed_demo.py --reset
python -m pytest services/api/tests
corepack pnpm typecheck
corepack pnpm lint
corepack pnpm test
corepack pnpm --filter @knk/public-web build
corepack pnpm --filter @knk/terminal-web build
corepack pnpm test-e2e
```

## Local Servers

API:

```bash
cd services/api
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Terminal:

```bash
corepack pnpm --filter @knk/terminal-web dev --hostname 127.0.0.1 --port 3001
```

## Docker

```bash
docker compose config --quiet
docker compose up --build
```

If Docker fails with `npipe:////./pipe/dockerDesktopLinuxEngine`, start Docker Desktop and enable the Linux engine before rerunning Compose.

## Provider Operations

- Review FRED state at `/api/v1/providers/fred/status`.
- Test FRED with `POST /api/v1/providers/fred/test` after setting `FRED_ENABLED=true` and `FRED_API_KEY`.
- Trigger manual macro refresh from the terminal Macro page or `POST /api/v1/macro/backfills`.

## Safety Checks

```bash
corepack pnpm security-check
rg -n "placeOrder|cancelOrder|reqGlobalCancel|transmitOrder|modifyOrder|submitOrder|executeTrade|autoRebalance|autoHedge" .
```

Application source must not contain broker execution methods.
