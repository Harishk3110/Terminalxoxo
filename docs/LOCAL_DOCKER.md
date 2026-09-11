# Local Docker Runtime

Workspace: `C:\Dev`. This local stack is not a public hosted deployment.
The private terminal is `http://127.0.0.1:3001/overview`; anonymous users are sent
to the administrator setup/sign-in page. No default administrator password is
created by the Docker bootstrap.

## Preserve Existing Data

The final-build verification uses project `knk-final-local`, a separate generated
environment and new PostgreSQL/Redis/MinIO/Grafana volumes. It does not migrate or
replace the existing `knk_terminal.db` or `.knk-object-store` directory. Existing
`.env` and unrelated Docker volumes are preserved. The Docker demo and the old
SQLite installation are distinct datasets; do not mistake one for a migrated copy.

From the workspace, with Docker Desktop running:

```powershell
.\.venv-sprint\Scripts\python.exe scripts/prepare_local_stack.py
docker compose --env-file .env.compose.local config --quiet
docker compose --env-file .env.compose.local up -d --build postgres redis minio minio-init api worker-data worker-quant terminal-web prometheus grafana
docker compose --env-file .env.compose.local ps
```

The bootstrap needs `python-dotenv` and `cryptography` from the API requirements.
It refuses to overwrite `.env.compose.local`. Keep this file with secure recovery
material: changing PostgreSQL or MinIO credentials without coordinating their
persistent volumes will break access. Its `AUTH_SECRET` is needed to recover MFA.
Do not delete volumes, run seed reset, or regenerate credentials to fix startup.

The API runs Alembic before non-reset demo seeding. Worker processes use the
existing SQL queue and expiring database heartbeats. There is no Celery/Prefect
queue or inbound broker agent in this stack. No order execution is enabled.
The frontend Docker image builds Next.js and runs `next start` as the non-root
Node user; it does not depend on keeping a foreground PowerShell window open.
Containers restart unless stopped, provided Docker Desktop itself is running.

## Local Endpoints

| Component | Address |
| --- | --- |
| Terminal main page | http://127.0.0.1:3001/overview |
| API readiness | http://127.0.0.1:8000/health/ready |
| Prometheus | http://127.0.0.1:9090 |
| Grafana | http://127.0.0.1:3003 |
| MinIO console | http://127.0.0.1:9001 |

All published ports bind only to IPv4 loopback. Grafana and MinIO credentials are
in the private environment file. Grafana uses username `admin`; anonymous access
and sign-up are disabled. Port 3002 remains reserved for isolated Playwright tests.

## Remaining Infrastructure Work

`report-engine` is deliberately omitted from the command above: its former
unauthenticated renderer is disabled and readiness returns 503. An authenticated,
source-pinned report queue/worker must replace it before the full Compose gate can
pass. Existing private API XLSX exports are narrower capabilities, not that worker.

One real Grafana dashboard is provisioned. The complete requested nine-dashboard
suite, backup/restore of PostgreSQL plus remote objects, stronger secret handling,
production hosting and full clean-clone acceptance remain outstanding. No external
market-data provider has been connected. September demo observations remain dated
and may correctly be labelled STALE; tests must not relabel them as fresh.
