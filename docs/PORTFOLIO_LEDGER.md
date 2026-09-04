# Portfolio Ledger

## Reference Portfolio

The deterministic seed creates `KnK Capital Reference Portfolio` with base currency `SGD` and reference capital `70000`.

Seeded transactions include:

- Owner capital deposit.
- USD buys for AAPL, MSFT, and SPY.
- AAPL dividend.
- SGD fee.
- SGD buy for DBS Group Holdings (`D05`).

## Calculation Rules

The ledger service recalculates positions from transactions every time a manual transaction is added or `/api/v1/portfolios/default/recalculate` is called.

- Deposits increase cash.
- Buys increase quantity and cost basis and reduce base-currency cash by gross value times FX plus fee.
- Sells reduce quantity/cost basis, increase cash, and record realized P&L.
- Dividends increase base-currency cash using transaction FX.
- Fees reduce base-currency cash.
- Latest quotes and FX rates are read from the database.
- NAV equals base-currency cash plus position market value.
- Weights equal position market value divided by NAV.

Authoritative money values use Python `Decimal` and SQLAlchemy `Numeric`.

## Implemented APIs

- `GET /api/v1/portfolios/default`
- `POST /api/v1/portfolios/default/transactions`
- `POST /api/v1/portfolios/default/recalculate`
- `GET /api/v1/performance/default`
- `GET /api/v1/risk/default`
- `GET /api/v1/stress/default`
- `GET /api/v1/hedge/default`

The terminal Portfolio, Positions, Performance, Risk, Stress Tests, and Hedge pages load through these APIs.
