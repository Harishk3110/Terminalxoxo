# Backtesting Methodology

Implemented backtest:

- Moving-average crossover over persisted SPY daily bars.
- Fast/slow parameters read from persisted `strategy_versions`.
- Initial capital `SGD 70000`.
- Long-only entries and exits.
- Commission and slippage assumptions.
- Persisted run, metrics, equity curve, positions, and trades.
- Metrics include total return, max drawdown, annualized volatility, and trade count.

Implemented APIs:

- `GET /api/v1/strategies`
- `GET /api/v1/backtests`
- `POST /api/v1/backtests/demo-run`
- `GET /api/v1/backtests/{run_id}`

Not yet implemented:

- Asynchronous quant job queue for new parameterized user runs.
- Walk-forward analysis.
- Monte Carlo.
- Multi-asset portfolio backtesting.
- Corporate-action adjusted accounting beyond seeded demo prices.
