# Production Hosting Status

Wrap-up verified on 2026-09-07 SGT (2026-09-06 UTC); new product work is paused. The 25K sprint
is not complete. Current source is retained, including the performance service
explicitly marked IN DEVELOPMENT. No broker execution capability was added.

## Vercel Projects

Use the existing repository https://github.com/Harishk3110/Terminalxoxo and branch main.
Create/import each project only if a matching project does not already exist.

| Setting | Terminal | Public Website |
| --- | --- | --- |
| Project name | knk-capital-terminal | knk-capital-public |
| Root Directory | apps/terminal-web | apps/public-web |
| Framework Preset | Next.js | Next.js |
| Node.js | 22.x | 22.x |
| Install Command | corepack pnpm install --frozen-lockfile | corepack pnpm install --frozen-lockfile |
| Build Command | corepack pnpm build | corepack pnpm build |
| Output Directory | Next.js default | Next.js default |
| Include source files outside Root Directory | Enabled | Enabled |

The repository pins pnpm 9.15.4; shared packages remain workspaces and are
transpiled by Next.js. Output tracing includes the repository root. There are no
Windows filesystem paths in either app's build configuration.

Terminal environment variable names:
`KNK_API_URL`, `NEXT_PUBLIC_APP_ENV`, `NEXT_PUBLIC_DEMO_MODE`,
`NEXT_PUBLIC_TERMINAL_NAME`. `NEXT_PUBLIC_API_BASE_URL` is accepted as a legacy
server configuration input, but browser requests intentionally use `/backend`.
Prefer `KNK_API_URL`; no provider credential belongs in `NEXT_PUBLIC_*`.

The hosted terminal requires a public HTTPS FastAPI origin. Missing configuration,
loopback/private-network targets, embedded credentials and non-origin URLs are
rejected. VERCEL=1 enforces hosted checks even if a local-mode flag was supplied.
There is no fake frontend or hosted demo API fallback. The public site has no API
requirement and must not receive private service credentials.

Vercel CLI 59.11.7 `whoami` returned "Logged out" (exit 1). No local project links
or Vercel credential environment variables were found. No deployment was made,
no production URL is verified, and no production API has been identified.

## Backend Services

FastAPI runs locally with the existing SQLite ledger and local object storage.
The local health endpoint returned HTTP 200 at `http://127.0.0.1:8000/health/live`.
The real database was backed up to `logs/pre-wrapup-backup.sqlite`, then upgraded
from migration 0003 through 0005. All captured original record hashes survived.
Neither the backup nor the live database is tracked by Git.

Separate hosting is still required for the authenticated FastAPI API, PostgreSQL,
Redis, durable object storage, data worker, quant worker and report engine.
The local IBKR read-only agent and Windows folder watcher remain local processes.
Deploying either Next.js frontend does not deploy any of these services.
Docker Desktop's Linux engine was unavailable during wrap-up; no healthy database,
Redis or worker stack is claimed.
Compose now reads ignored `.env` credentials instead of hardcoded demo passwords.
Set `POSTGRES_PASSWORD`, `DATABASE_URL`, `MINIO_ACCESS_KEY` and `MINIO_SECRET_KEY`
before starting it. Preserve existing volume credentials. Configuration parsing
passed with temporary process-only validation values; no containers were started.

## Local Startup

Run the API from the repository root, using the same database as Alembic:

```powershell
cd C:\Dev
$env:KNK_ENV='local-demo'
$env:DATABASE_URL='sqlite:///C:/Dev/knk_terminal.db'
.\.venv-sprint\Scripts\python.exe -m uvicorn app.main:app --app-dir services/api --host 127.0.0.1 --port 8000
```

Build the terminal from its app directory with explicit local configuration:

```powershell
cd C:\Dev\apps\terminal-web
$env:NEXT_PUBLIC_APP_ENV='local'
$env:KNK_API_URL='http://127.0.0.1:8000'
corepack pnpm build
corepack pnpm start --hostname 127.0.0.1 --port 3001
```

`OPEN-KNK-TERMINAL.cmd` uses this `.next` build. The terminal launcher was blocked
by this agent session's execution policy; no alternative launch was used to bypass
it. Port 3001 was not reachable at the last check. The user must start that local
process before its URL can be verified and opened in Firefox.

Public site is running on port 3000; its page and seven static assets returned
HTTP 200. Desktop (1440px) and mobile (390px) browser checks verified Tailwind
styles, no horizontal page overflow and no fatal runtime errors. The final
default `.next` build includes the corrected CSS; the earlier unstyled output
was not accepted as successful verification. To restart it, run `corepack pnpm build`, then
`corepack pnpm start --hostname 127.0.0.1 --port 3000` in `apps/public-web`.
After HTTP verification, Firefox can be opened with
`firefox.exe --kiosk http://127.0.0.1:3001/overview`; F11 is the normal-window fallback.

Generated screenshots remain local and ignored. Optional golden-image comparisons
use `KNK_COMPARE_SCREENSHOTS=1` with separately supplied local baselines; normal
Playwright runs still assert layout, theme, populated regions and workflow behavior.

References: [Vercel monorepo settings](https://vercel.com/docs/monorepos/monorepo-faq),
[supported Node versions](https://vercel.com/docs/functions/runtimes/node-js/node-js-versions),
[Next.js security update](https://nextjs.org/blog/august-2026-security-release).
