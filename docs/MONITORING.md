# Monitoring

## Implemented Endpoints

API:

- `GET /health/live`: process liveness.
- `GET /health/ready`: database, Redis, and object-storage readiness summary.
- `GET /metrics`: Prometheus metrics.
- `GET /api/v1/system/health`: terminal-facing health state, provider state, and table counts.

Report engine:

- `GET /health/live`
- `GET /metrics`

Broker agent:

- `GET /health/live`
- `GET /metrics`

## Metrics Present

The API exports:

- `knk_api_requests_total`
- `knk_api_request_seconds`
- `knk_jobs_by_state`
- `knk_data_records_ingested_total`
- `knk_auth_failures_total`

Report and broker services export basic service counters. More detailed provider latency, job duration, and security-event dashboards remain tracked in `TASKS.md`.

## Compose Monitoring

`docker-compose.yml` includes Prometheus and Grafana services. Prometheus is configured to scrape API, report-engine, and broker-agent metrics.

On 2026-09-06 in C:\Dev, the Linux API image built and its in-process readiness
check passed against isolated PostgreSQL and Redis containers, with local object
storage ready and NAV reconciliation difference 0.00. That test stack was then
stopped. Full Compose, MinIO, distributed workers and web-container health have
not been verified; see `docs/PORTFOLIO_ACCEPTANCE.md` for current evidence. The
working workstation's Redis remains OFFLINE until separately configured.
