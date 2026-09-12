KnK Capital Terminal is a private internal portfolio, equity research, quantitative research, options analytics and risk-monitoring platform.

# KnK Capital Terminal

One frontend: `apps/terminal-web`. The existing black-and-amber shell opens the
Portfolio Command Centre after sign-in. All investment APIs require a session,
including deterministic demo mode. Broker connections are read-only; transactions
record manual activity and never transmit orders.

## Start

Use Node.js 22, pnpm 9.15.4 and Python 3.12. Install frontend and Python dependencies:

For file-backed SQLite, use a Python runtime with SQLite 3.51.3+ or a fixed
maintenance backport. See [Local SQLite Runtime](docs/SQLITE_RUNTIME.md) for the
verified `.venv-rc` setup. The Docker stack uses PostgreSQL and is unaffected.

```powershell
corepack pnpm install --frozen-lockfile
python -m pip install -r services/api/requirements.txt
python -m pip install -r requirements-dev.txt
```

The default `corepack pnpm dev` starts the terminal, API, required workers,
PostgreSQL, Redis and object storage with Docker Compose. Configure the ignored
`.env` from `.env.example` first. Supply `POSTGRES_PASSWORD`, `DATABASE_URL`,
`MINIO_ACCESS_KEY` and `MINIO_SECRET_KEY`; retain existing persistent-volume
credentials. Never commit the populated environment file.

For local SQLite operation, run the following in separate terminals from this
repository's root. Existing records are retained by migrations and normal seeding.

```powershell
$env:KNK_ENV='local-demo'
$env:DATABASE_URL='sqlite:///./knk_terminal.db'
python -m alembic upgrade head
python -m uvicorn app.main:app --app-dir services/api --host 127.0.0.1 --port 8000
```

```powershell
corepack pnpm dev:terminal
```

Private terminal: http://127.0.0.1:3001/overview
Root http://127.0.0.1:3001/ redirects to /overview, then /login if unauthenticated.
First-use local administrator creation is on the sign-in screen. Hosted account
registration is disabled; provision the first administrator from the backend
console with `python services/api/scripts/create_admin.py`.

## Production Build

Private data connections and required server configuration are documented in
[Provider Connections](docs/PROVIDER_CONNECTIONS.md). Lawful Koyfin exports,
folder-agent controls and private attachments are covered in
[Koyfin File Import](docs/KOYFIN_FILE_IMPORT.md). No connected provider changes
unrelated demo figures to LIVE.

```powershell
$env:NEXT_PUBLIC_APP_ENV='local'
$env:KNK_API_URL='http://127.0.0.1:8000'
corepack pnpm --filter @knk/terminal-web build
```

`OPEN-KNK-TERMINAL.cmd` runs the resulting build on port 3001. Keep its window
open. The agent's previous local launch was policy-blocked; see STATUS.md for
current observed availability rather than assuming a localhost URL is running.

Vercel uses one project, `knk-capital-terminal`, root `apps/terminal-web`.
Hosted builds require a reachable HTTPS API origin in server-only `KNK_API_URL`.
No credentials belong in `NEXT_PUBLIC_*`. See
[Hosting](docs/PRODUCTION_HOSTING_STATUS.md) and [Architecture](docs/TERMINAL_ARCHITECTURE.md).

## Verification

Private Pine templates and external-export comparison are documented in
[TradingView Studio](docs/TRADINGVIEW_STUDIO.md). Existing XLSX exports remain
available; complete model/deck/PDF outputs remain blocked as recorded in
[Report Readiness](docs/REPORT_READINESS.md).

See [Operations](docs/OPERATIONS_VERIFICATION.md) for real worker queues, expiring
heartbeats and authentication controls, and [Backup Recovery](docs/LOCAL_BACKUP_RECOVERY.md)
for checksummed local backups and non-overwriting restores. No automatic reset or
backup retention deletion is performed. Local archives are private and unencrypted.

```powershell
corepack pnpm lint
corepack pnpm typecheck
corepack pnpm test
python -m pytest services/api/tests tests/sprint
corepack pnpm test-e2e
python scripts/scan_release_secrets.py
```

Playwright uses isolated ports 8001/3002, an isolated database and an authenticated
test session. Logs, screenshots and session state remain ignored. The test runner
does not disable application authentication. `PLAYWRIGHT_PYTHON` may select the
Python interpreter; `PLAYWRIGHT_DIST_DIR` selects an alternate test build.

See [Acceptance](docs/TERMINAL_ACCEPTANCE.md), [Scope](docs/PRD_TERMINAL_ONLY.md)
and [Removal Record](docs/PUBLIC_SITE_REMOVAL.md). Features and provider gaps are
reported individually, never presented as live data merely because one provider connects.
