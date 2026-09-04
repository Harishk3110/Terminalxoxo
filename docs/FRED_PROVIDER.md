# FRED Provider

Implementation date: 2026-09-05

Official documentation checked:

- https://fred.stlouisfed.org/docs/api/fred/
- https://fred.stlouisfed.org/docs/api/fred/series.html
- https://fred.stlouisfed.org/docs/api/fred/series_observations.html
- https://fred.stlouisfed.org/docs/api/fred/series_vintagedates.html

## Configuration

```text
FRED_ENABLED=false
FRED_API_KEY=
FRED_BASE_URL=https://api.stlouisfed.org/fred
FRED_REQUEST_TIMEOUT_SECONDS=15
FRED_MAX_RETRIES=3
```

The FRED API requires an `api_key`; the documented key format is a 32-character lowercase alpha-numeric string. The adapter never hardcodes credentials and redacts browser-facing configuration.

## Implemented Endpoints

The adapter uses `httpx.AsyncClient` with explicit timeout and tenacity retry handling. Requests include `file_type=json`.

- `fred/series`: metadata lookup by `series_id`.
- `fred/series/observations`: observations by `series_id`, sorted ascending, with optional `observation_start`.
- `fred/series/search`: series search.
- `fred/series/vintagedates`: vintage/revision dates.

## Pipeline

`FRED response -> object storage -> SHA-256 content hash -> Pydantic validation -> macro series upsert -> observation version insert -> vintage insert -> provider state update -> API/dashboard`

Missing FRED observation values represented as `.` are stored as missing values, not zero.

Observation uniqueness is enforced by:

`series_id + observation_date + realtime_start + realtime_end + vintage_date`

## Demo And Mixed Source Behavior

When `FRED_ENABLED=false` or `FRED_API_KEY` is empty:

- `/api/v1/providers/fred/status` returns `NOT_CONFIGURED`.
- Demo macro series remain available as `DEMO DATA`.
- FRED refresh/backfill records a provider-not-configured quality issue.
- No fake live FRED call is shown.

When credentials are configured:

- `POST /api/v1/providers/fred/test` performs a live metadata request.
- Refresh/backfill stores raw JSON and curated observations.
- Only series actually ingested from FRED switch to provider `FRED` and quality `EOD DATA`.

## Default Watchlist

The default macro fixture/watchlist uses FRED-compatible identifiers:

`FEDFUNDS`, `SOFR`, `DGS2`, `DGS10`, `T10Y2Y`, `CPIAUCSL`, `CPILFESL`, `PCEPI`, `PCEPILFE`, `UNRATE`, `PAYEMS`, `GDPC1`, `INDPRO`, `RSAFS`, `VIXCLS`, `BAMLH0A0HYM2`, `DTWEXBGS`.

Live validation of every identifier requires a configured FRED key; mocked provider tests validate parsing and missing-value behavior without external HTTP.
