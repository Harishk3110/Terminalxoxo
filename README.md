# KnK Capital Terminal

Repository: `Terminalxoxo`

KnK Capital Terminal is a production-shaped demo-mode investment platform for KnK Capital. It includes a public website, a private terminal, a FastAPI backend, background workers, a report service, a read-only local broker agent, security tests, Docker Compose, and setup documentation.

The current build is intentionally safe:

- Demo data works without external credentials.
- The operating mode is labelled as `DEMO DATA`.
- Broker integration is read-only by design.
- No broker execution API is implemented.
- Public content is separated from private portfolio data.

## Run Locally

```bash
corepack prepare pnpm@9.15.4 --activate
corepack pnpm install
corepack pnpm dev
```

Public web: http://localhost:3000

Terminal web: http://localhost:3001

API: http://localhost:8000

## Docker

```bash
cp .env.example .env
docker compose up --build
```

Docker Desktop must be running before Compose commands are executed.

## Demo Login

Demo mode uses a local single-administrator setup flow. Open the terminal web app and use Settings > Security to inspect the configured state. The API exposes deterministic demo data until real providers are configured.

## Provider Connections

Credentials are supplied through Settings > Connections or environment variables. Data providers start in `DEMO` mode and transition dataset-by-dataset to connected mode after a successful connection test and backfill.

## IBKR Paper Agent

Run the broker agent next to TWS or IB Gateway with API read-only mode enabled. The agent only exposes account, position, fill, commission, and heartbeat data. It does not include broker order submission, revision, or cancellation paths.

## Verification

```bash
corepack pnpm typecheck
corepack pnpm lint
corepack pnpm test
python -m pytest services/api/tests
corepack pnpm build
docker compose build
```

See [STATUS.md](./STATUS.md), [TASKS.md](./TASKS.md), and [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md).
