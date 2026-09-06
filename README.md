# KnK Capital Terminal

Repository: `Terminalxoxo`

KnK Capital Terminal is a local investment-research workstation for KnK Capital. The V2 terminal rebuild introduces a full-height black/amber shell, security-aware commands, persistent workspaces/tabs, dense analytical views, an inspector, and source-labelled data. Stress and moving-average backtests execute as persisted jobs in separate processes. The existing public website and read-only broker boundary are preserved.

The registry contains 102 functions: 17 operational, 31 demo analytical, 42 provider-required and 12 in development. This is not a live trading terminal or complete implementation of every specialist function. See [Function Registry](docs/FUNCTION_REGISTRY.md), [Demo Data Mode](docs/DEMO_DATA_MODE.md), and [Status](STATUS.md).

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
python services/api/scripts/seed_demo.py
```

API:

```bash
python -m uvicorn app.main:app --app-dir services/api --host 127.0.0.1 --port 8000
```

Terminal web:

```bash
corepack pnpm --filter @knk/terminal-web dev --hostname 127.0.0.1 --port 3001
```

Open http://127.0.0.1:3001/overview, or http://127.0.0.1:3001/stress-tests for the scenario workspace. Run the API from the repository root so it uses the same database as migrations. KNK_API_URL controls the terminal's server-side API proxy (default http://127.0.0.1:8000). In PowerShell, setting `$env:KNK_NEXT_DIST_DIR='logs/terminal-dev'` gives development its own output directory and avoids sharing production build files.

Account setup/sign-in is under SECURITY. Local demo access is intentionally allowed without an account; outside local-demo, private API routes require a session. Keep the local server bound to loopback. Credentials, databases, uploads, logs and generated workbooks are ignored by Git.

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
docker compose config --quiet
```

See `STATUS.md`, `TASKS.md`, `docs/CORE_ACCEPTANCE.md`, and `docs/BUILD_EVIDENCE.md` for exact results.

Terminal V2 browser validation uses isolated ports 8001/3002 and its own database/object store. Build the test artifact and run (PowerShell):

```powershell
$env:KNK_NEXT_DIST_DIR='logs/terminal-v2-build'
corepack pnpm --filter @knk/terminal-web build
corepack pnpm test-e2e
```

Set `PLAYWRIGHT_DIST_DIR` when the built terminal uses another output directory, for example `logs/terminal-v2-verified`. The test harness uses explicit child-process teardown and writes `logs/terminal-e2e-results.json`. Transient traces and failure screenshots use the OS temp directory's `knk-terminal-e2e` folder to avoid OneDrive cleanup locks; `PLAYWRIGHT_OUTPUT_DIR` overrides it.

Screenshots and geometry checks cover Overview, Macro, Portfolio, Performance, Risk, Stress, Hedge and Backtests at four desktop sizes plus mobile monitoring. See [Visual Acceptance](docs/VISUAL_ACCEPTANCE.md). Baselines are Windows/Chromium specific. Generating new baselines requires `--update-snapshots`; normal test runs compare against committed images.
