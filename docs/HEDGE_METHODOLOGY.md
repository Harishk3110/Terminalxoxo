# Hedge Methodology

Implemented hedge logic:

- Reads latest portfolio NAV and beta snapshot.
- Targets beta reduction to `0.80`.
- Calculates target notional from NAV and beta difference.
- Uses SPY as the seeded ETF hedge instrument.
- Rounds hedge units with `Decimal` arithmetic.
- Calculates residual notional.
- Persists `hedge_recommendations` and `hedge_recommendation_items`.

The terminal Hedge page and `/api/v1/hedge/default` return manual recommendations only.

Not implemented:

- Futures hedge selection.
- Multi-instrument optimization.
- Liquidity/basis-risk scoring.
- Broker ticket creation or execution. This is intentionally prohibited.
