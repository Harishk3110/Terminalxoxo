# STATUS

## 2026-09-05

Application: KnK Capital Terminal

Brand: KnK Capital

Environment: `local-demo`

Base currency: `SGD`

Reference capital: `70,000`

Current state:

- Working demo-mode scaffold created from an empty workspace.
- Public and terminal web apps are implemented as Next.js applications.
- Backend API is implemented with FastAPI and deterministic demo payloads.
- Worker, report, and broker-agent services are present and runnable.
- Safety checks are included to prevent broker execution capabilities from entering application source.
- Documentation has been added for architecture, operation, security, data providers, broker agent, publishing, reports, and limitations.
- Verified `corepack pnpm typecheck`.
- Verified `corepack pnpm lint`.
- Verified `corepack pnpm test`.
- Verified `python -m pytest services/api/tests`.
- Verified `corepack pnpm build`.

Known limitations:

- Demo fixtures are in code rather than fully migrated database tables.
- External provider credentials are not configured.
- The broker agent is a read-only pairing/status interface and fixture adapter until IBKR is configured locally.
- E2E tests are scaffolded but not exhaustive.
- `docker compose build` was attempted, but Docker Desktop's Linux engine was not running locally.
