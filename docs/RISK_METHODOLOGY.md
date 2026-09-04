# Risk Methodology

Implemented metrics:

- Beta snapshot.
- Annualized volatility from deterministic return observations.
- Historical 95% VaR.
- Historical 95% CVaR.
- Maximum drawdown.
- Gross exposure.
- Net exposure.
- Position concentration.
- One persisted stress scenario and result.

Risk snapshots are persisted in `risk_snapshots` and served by `GET /api/v1/risk/default`. Stress results are served by `GET /api/v1/stress/default`.

Not yet implemented:

- Parametric VaR endpoint.
- Liquidity and borrow stress.
- Risk-limit breach engine beyond seeded models.
- Position-level factor contribution decomposition.
