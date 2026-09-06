# Risk & Trade Monitor

Route /risk-trade-monitor combines the ledger blotter, review, risk summary,
position covariance contribution and native-currency exposure including cash.
Stress Test and Hedge Review link to the existing analytical workspaces.

Available measures: current-weight beta, annual covariance volatility,
historical VaR95/VaR99/CVaR95, flow-adjusted drawdown, gross/net exposure,
position/sector/currency concentration, cash weight and policy breaches.
Position marginal volatility and normalized variance contribution are computed
from the same covariance matrix. At least 60 paired trading observations are
required. Risk excludes cash-FX and liability sensitivity; stale-source and
insufficient-history warnings remain visible.

Stress uses immutable recorded inputs, linear position beta, FX shocks and an
explicit TLT duration assumption. It is not full option repricing or a forecast.
Hedges are indicative manual beta reductions and require manual review.

Reconciliation compares independently timestamped broker snapshot NAV, cash,
quantity and average cost when a snapshot exists. Without a real broker
snapshot it returns BROKER_NOT_CONNECTED, not a fake matched account. Recorded
executions are matched by ID, quantity, price and commission across retained
snapshots. Open breaks clear when no longer observed; review is audited.
Production connector certification and real TWS validation remain outstanding.
Broker-current holdings never inherit the internal demo book's risk history.
