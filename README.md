# KnK Capital Terminal

Repository: `Terminalxoxo`

KnK Capital Terminal is a local portfolio, equity, quant and risk workstation for KnK Capital. HOME is the Portfolio Command Centre for KNK_MAIN, with an explicit SGD 70,000 demonstration opening ledger, source-aware NAV and auditable trade reviews. The approved dense black/amber shell, persistent workspaces, inspector and public website are preserved. Stress and version-pinned moving-average backtests run as persisted jobs in separate processes.

The registry contains 110 functions, including NAV, PNL, TRADES, RISKMON, QMON, EQUITY, KOYFIN and DATADROP. CSV/XLSX/JSON files pass through mapping, validation and explicit approval into immutable raw/curated versions. Koyfin means permitted exported files, not a direct API or live feed. The local agent supports OS-vault pairing and an optional read-only paper-account reader. See [Portfolio Acceptance](docs/PORTFOLIO_ACCEPTANCE.md), [Local Agent](docs/LOCAL_DATA_AGENT.md), and [Status](STATUS.md) for measured results and remaining limitations.

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

For the verified production build on Windows, keep the API running, then use
`OPEN-KNK-TERMINAL.cmd`. It starts the main terminal on port 3001; keep its
window open. To rebuild that launcher's output:

```powershell
$env:KNK_NEXT_DIST_DIR='logs/dev-portfolio-release'
corepack pnpm --filter @knk/terminal-web build
```

The latest agent session could not start the user's web process under its
execution policy. A localhost link works only while the launcher/dev server
is running; this repository push is not a public hosting deployment.

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

The Linux API image, container migration/seed and API readiness/NAV checks passed
against an isolated PostgreSQL/Redis stack in C:\Dev. Full Compose startup,
MinIO, distributed workers and web-container health have not been verified.
See [Portfolio Acceptance](docs/PORTFOLIO_ACCEPTANCE.md) for current evidence;
`docs/BUILD_EVIDENCE.md` is the archived V1 record.

## Verification

The backend tests also exercise the local agent. Install its optional test
dependencies with `python -m pip install -r services/local-agent/requirements.txt`.

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
