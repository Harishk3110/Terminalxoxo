# Risk Methodology

## Inputs and Scope

`knk-nav-4.8` pins a valuation snapshot and source-aware base-currency security
history. Current signed marked security weights use complete positive internal
NAV. Broker-reported snapshots are not substituted into this model. Source, oldest
contributing timestamp, data state and version remain attached. Stale inputs remain
visibly stale; calculated does not mean live.

The security model excludes cash-FX, liabilities, nonlinear options, borrow,
liquidity and financing risk. Currency exposures and FX stress include economic
cash and signed balance adjustments. Settlement is not counted twice.

## Estimators

`risk_statistics.calculate_risk` requires finite positive aligned marks, unique
increasing dates and 60 daily return observations by default. Weekends are excluded.
Irregular weekday intervals are not silently treated as daily observations. Input
marks follow the valuation policy, including its stale/carried-mark provenance.
This is not an exchange-calendar-adjusted return feed.

- Gross, net, long/short exposure, concentration and HHI (sum of squared NAV weights).
- Sample covariance (`ddof=1`); annual volatility with 252 periods.
- Bias-corrected pandas EWMA variance, default decay 0.94.
- Historical linear-quantile 95%/99% one-day VaR and tail-mean CVaR.
- Normal parametric and seeded normal-return Monte Carlo 95%/99% VaR;
  Monte Carlo CVaR at 95%. Default seed 3110, 10,000 draws.
- Benchmark/rolling beta, beta contribution, marginal/component volatility and
  percentage variance contribution. Undefined contributions remain null.

VaR is negative P&L, clamped at zero for an all-positive tail. Limit metrics
`var_loss_95`, `cvar_loss_95` and `drawdown_loss` are positive loss magnitudes.
Zero benchmark variance does not produce zero beta. Insufficient data returns null
statistics and a reason. History, settings and covariance are in `risk_model`.

References: [pandas window estimators](https://pandas.pydata.org/pandas-docs/stable/user_guide/window.html)
and [NumPy random sampling](https://numpy.org/doc/stable/reference/random/index.html).

## Limits and Audit

Authenticated `GET /api/v1/risk/portfolios/{portfolio}/monitor` evaluates enabled
policies. Administrator-only limit/settings writes require a reason. Units are
NAV fractions, ratios or positive loss amounts. The screen targets SGD KNK_MAIN;
the API is book-scoped.

States: OK, BREACH, NOT_EVALUATED and DISABLED. Missing/nonpositive NAV cannot clear
a limit. Breaches, changed observations and resolutions are audited. Repeated
unchanged checks do not duplicate alerts. Missing inputs leave existing alerts
open with undetermined breach state. Reopening creates a new alert but retains the
original breach identifier and first-ever timestamp. Last checked is current.

## Stress

`knk-stress-3.0` stores immutable portfolio inputs with each analysis. Linear equity
stress uses estimated beta, sector scope and constant holdings. TLT rate sensitivity
assumes duration 16, not a measured feed. USD/SGD shocks require SGD base NAV.
Equity/rate/FX interaction and price flooring are attributed separately so factor
and position P&L reconcile.

Results include post-NAV, constant-beta post-shock exposure, position/sector/country/
currency/factor contributions and ranked losses. Hedge contribution remains null
unless holdings are explicitly tagged; shorts are not assumed to be hedges.
The linear engine rejects options.

Correlation convergence blends covariance toward a same-volatility, perfectly
positively correlated matrix. The shock is a one-day normal 95% conditional
portfolio tail, zero drift, with covariance-based asset contributions. It is not
the former fixed equity shock. VIX mapping is UNAVAILABLE with null loss: a VIX
move is not automatically an option-IV move. Crisis templates are hypothetical
factor proxies, not historical path replays. Scenarios are not forecasts.

## Hedge Estimates

`POST /api/v1/risk/portfolios/{portfolio}/hedges` saves internal analysis. ETF beta
uses the same valuation-date marks against SPY; price and FX follow source
precedence. Signed target-beta notional is `(target - current beta) * NAV / hedge
beta`. Decimal sizing rounds units toward zero and retains residual notional.
Target-net/classified-sector modes use exposure differences. Currency mode is a
cash-conversion estimate, not a forward-price or margin model.

Futures estimates require explicit user price, beta, currency and multiplier, not
assumed live specifications. Gross exposure accounts for reducing/crossing held
ETFs. Assumed costs reduce NAV; post-beta/net/gross use that denominator. ETF VaR
is recalculated with the hedge included in covariance. Futures/FX VaR remain
unavailable. Incremental linear equity/FX stress effects are separate.

Saved analyses retain valuation ID, full inputs and provenance. Draft, reviewed,
accepted manually and rejected states have dated actor/reason history. No analysis
or review changes the ledger or transmits a broker instruction.

**MANUAL REVIEW REQUIRED - NO ORDER WILL BE SUBMITTED**

## Trade Review and Reconciliation

Trade Monitor retains detection time, source, reference, ledger ID, thesis/strategy,
review notes and saved before/after beta and weights. These are counterfactual
trade-date-close snapshots, not pre-execution live risk. Missing historical
snapshots remain unavailable. Reconciliation uses effective amended transactions;
voids no longer count as matched fills. Broker/internal snapshots have independent
timestamps, and timing differences can explain breaks. Original rows remain intact.
