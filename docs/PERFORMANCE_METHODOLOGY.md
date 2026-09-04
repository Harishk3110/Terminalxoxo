# Performance Methodology

Implemented metrics:

- Time-weighted return from deterministic return series.
- CAGR from reference capital to latest NAV.
- Annualized volatility.
- Sharpe ratio.
- Sortino ratio.
- Maximum drawdown.

Current performance snapshots are persisted in `performance_snapshots` and served by `GET /api/v1/performance/default`.

Not yet implemented:

- Full money-weighted return.
- Contribution and attribution.
- Benchmark-relative performance.
- Cash-flow adjusted daily return history beyond seeded/demo calculations.
