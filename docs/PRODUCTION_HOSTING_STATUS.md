# Production Hosting Status

Only one frontend project is in scope.

| Setting | Value |
| --- | --- |
| Repository | https://github.com/Harishk3110/Terminalxoxo |
| Branch | main |
| Vercel project | knk-capital-terminal |
| Root directory | apps/terminal-web |
| Framework | Next.js |
| Node version | 22.x |
| Install | corepack pnpm install --frozen-lockfile |
| Build | corepack pnpm build |
| Output | Next.js default |
| Include files outside root directory | Enabled |

Environment names: `KNK_API_URL`, `NEXT_PUBLIC_APP_ENV`,
`NEXT_PUBLIC_DEMO_MODE`, `NEXT_PUBLIC_TERMINAL_NAME`.
The server API origin must be HTTPS and not localhost or a private address.
The browser uses the same-origin /backend proxy. Secrets remain backend-only.

The frontend verifies the opaque session with the API before rendering private
routes. Investment pages are dynamic, no-store and noindex; robots disallows
indexing. Account setup in hosted environments is console-only, not registration.
Configure the backend environment as production-paper and provision an administrator
with services/api/scripts/create_admin.py before deployment.

Vercel CLI was logged out at the last check. No authenticated deployment or
production API URL has been verified. The former second-project plan is cancelled.
No cloud resource was created or removed without account access.

FastAPI, PostgreSQL, Redis, object storage, data/quant workers and the report
engine need separate persistent hosting. The read-only IBKR and local file agents
remain outbound local processes. Frontend deployment does not deploy them.

Local terminal: http://127.0.0.1:3001/overview
Local API health: http://127.0.0.1:8000/health/live
Local process status and current verification are recorded in STATUS.md.
