# Stress Test Workspace

Layout: scenario library, editable configuration, four KPI cells, P&L contribution chart and grouped contribution table, with run inspector. The library contains 16 named assumptions including equity, FX, rate and historical-proxy scenarios. Search, select, duplicate, save, reset, compare and export are wired.

## Contract
POST /api/v1/terminal/runs with kind=stress stores a frozen portfolio snapshot and parameters. A separate Python process changes QUEUED -> RUNNING -> SUCCEEDED or FAILED. Cancellation records CANCELLED and discards late results. GET detail/list return persisted history. Export creates an XLSX with sources, assumptions, warnings, contributions and a cached, trusted Post-NAV formula.

Per-position scenario return:
- Scoped market return times estimated historical beta.
- TLT-only rate sensitivity using explicitly assumed duration 16.
- USD/SGD FX shock compounded with asset return.
- Asset loss capped at 100%.

P&L is rounded per position; total loss sums those rounded contributions. Post-NAV equals pre-NAV plus P&L. Position, sector, country and currency views aggregate the same saved results. Editing an assumption does not mutate an earlier run; another run must be submitted.

## Limits
This is a linear scenario estimate, not a full repricing engine. VIX direct sensitivity is unavailable and explicitly zero. Historical scenarios are proxies, not historical portfolio replays. Correlation convergence uses an equity-market shock proxy, not a rebuilt covariance matrix. No liquidity, tax, optionality or second-order model is claimed. Worker cancellation is cooperative result discard, not process termination. Interrupted workers require cancellation/retry; no distributed heartbeat supervisor is implemented.
