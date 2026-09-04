# API

Base path: `/api/v1`

Health and metrics:

- `GET /health/live`
- `GET /health/ready`
- `GET /metrics`

Auth:

- `POST /api/v1/auth/setup`
- `POST /api/v1/auth/login`

Public:

- `GET /api/v1/public/content`

Discovery and reference:

- `GET /api/v1/environment`
- `GET /api/v1/functions`
- `GET /api/v1/search`
- `GET /api/v1/instruments`
- `GET /api/v1/instruments/{instrument_id}`

Providers and macro:

- `GET /api/v1/providers`
- `POST /api/v1/providers/fred/test`
- `GET /api/v1/providers/fred/status`
- `GET /api/v1/macro/series`
- `GET /api/v1/macro/series/search`
- `GET /api/v1/macro/series/{series_id}`
- `GET /api/v1/macro/series/{series_id}/observations`
- `POST /api/v1/macro/series/{series_id}/refresh`
- `POST /api/v1/macro/backfills`
- `GET /api/v1/macro/backfills/{job_id}`
- `GET /api/v1/macro/dashboard`

Portfolio, performance, and risk:

- `GET /api/v1/portfolios/default`
- `POST /api/v1/portfolios/default/transactions`
- `POST /api/v1/portfolios/default/recalculate`
- `GET /api/v1/performance/default`
- `GET /api/v1/risk/default`
- `GET /api/v1/stress/default`
- `GET /api/v1/hedge/default`

Quant:

- `GET /api/v1/strategies`
- `GET /api/v1/backtests`
- `POST /api/v1/backtests/demo-run`
- `GET /api/v1/backtests/{run_id}`

Data operations:

- `POST /api/v1/uploads`
- `GET /api/v1/datasets`
- `GET /api/v1/jobs`
- `POST /api/v1/jobs/provider-health-check`

Reports and exports:

- `POST /api/v1/reports/portfolio-xlsx`
- `POST /api/v1/reports/risk-xlsx`
- `POST /api/v1/reports/backtest-xlsx`
- `POST /api/v1/reports/macro-xlsx`
- `GET /api/v1/reports/{report_id}`
- `GET /api/v1/reports/{report_id}/download`
- `GET /api/v1/pine/export`

Operations:

- `GET /api/v1/alerts`
- `POST /api/v1/alerts/{alert_id}/acknowledge`
- `GET /api/v1/system/health`

Backward-compatible first-build routes remain for old clients:

- `GET /api/environment`
- `GET /api/portfolio`
- `GET /api/risk`
