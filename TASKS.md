# TASKS

## Completed in Initial Build

- Created KnK Capital Terminal monorepo structure.
- Added public website and private terminal apps.
- Added shared domain, search, design-system, and terminal function packages.
- Added FastAPI demo backend with health, metrics, public content, market, portfolio, risk, provider, and job endpoints.
- Added worker, report-engine, and read-only broker-agent service skeletons.
- Added Docker Compose with PostgreSQL, Redis, MinIO, Prometheus, and Grafana.
- Added safety checks for forbidden broker execution capabilities.
- Added core documentation, environment template, Makefile, and CI.

## Next Implementation Milestones

- Add persistent PostgreSQL models and Alembic migrations.
- Replace in-memory demo fixtures with seeded database fixtures.
- Add full authentication persistence, TOTP enrollment, and recovery-code storage.
- Expand provider adapters for configured vendors.
- Add richer report generation templates.
- Add full Playwright acceptance coverage.
- Harden production deployment policies and secret rotation.
