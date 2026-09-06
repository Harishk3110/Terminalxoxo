# Quant Research

Private commands: QUANT/QMON, BACKTEST, FACTOR, ALPHA, MODEL, WALK, MC and EDGE.
All output is research. There is no order-routing, automatic portfolio mutation,
broker action, automatic promotion or fabricated paper performance.

## Input Evidence

`research_inputs.py` snapshots actual OHLC rows into content-addressed object
storage, RawObject, DatasetVersion and DatasetLineage. Workers verify hashes.
Complete positive OHLC, unique chronological daily dates and consistent high/low
bounds are required. A missing open is not replaced by a close. Carried price
observations cannot be treated as executable bars. Multi-security grids must match.

SOURCE_AWARE uses selected price-source history. DEMO_RESEARCH explicitly selects
the independent synthetic multi-year fixture and cannot be mistaken for the
internal portfolio's coherent valuation history. Curated file versions can be
selected directly. They require complete executable bars, not merely chart data.
Current security classification and universe selection are not survivorship-free
or point-in-time historical classifications.

## Backtests

The isolated worker uses offline Backtrader with pandas data feeds only. Approved
templates include SMA, RSI, MACD, breakout, time-series/cross-sectional momentum,
mean reversion, low volatility, inverse volatility, risk parity and a technical
momentum/volatility rank composite. Signals use completed bars and market fills
occur at the next bar open. No cheat-on-close or live broker store is enabled.

Up to twelve equities/ETFs and 5,000 complete daily observations are supported.
Controls include long-only/long-short, daily/weekly rebalance, equal/signal/inverse-
volatility/risk-parity weighting, gross/position/sector caps, minimum cash, capital,
commissions, half-spread, slippage and a constant short borrowing assumption.
Risk parity is long-only and solves equal sample-covariance variance contributions
with scipy SLSQP. Failed optimisation does not silently use equal weights.

Capital defaults to 100,000 in the explicitly selected base currency (SGD default).
Each bar's OHLC is converted using a pinned fixing published before that UTC date.
That single fixing applies to the entire bar; it is an explicit approximation,
not contemporaneous open/close FX. Missing/stale FX rejects the run. Non-demo
prices cannot silently use demo FX. Cash is in the base currency and earns zero.

Actual simulated fills, closed trades, daily positions/cash/NAV, target exposures,
fees, rejected orders, benchmark, drawdown, daily/monthly/annual returns and
statistical metrics are retained. Open positions remain marked at the final close.
No closing fill is invented. Cash/weight limits constrain intended targets, not
guaranteed post-gap fills. Whole-share rounding leaves residual cash.

New results retain NET and a separately rerun zero-cost GROSS curve. Metrics use
zero risk-free rate; annual statistics need 60 daily returns and CAGR needs one
year. Calendar bins can be partial. CAPM inference uses the shared alpha engine.
Benchmark is equal-weight buy-and-hold over the selected universe, before costs.

Not yet supported: raw weekly/intraday feeds, explicit dividend/split event
accounting, point-in-time membership, sector-rotation calendars, market impact,
instrument-specific financing/locates and tax. Unadjusted OHLC is explicitly
flagged for corporate-action review. These omissions are not represented as
implemented by the template list. Cancellation prevents publication; an in-flight
library fit may finish before its result is discarded.

## Models and Walk-Forward

scikit-learn pipelines implement linear/logistic, ridge/lasso/elastic-net, tree,
forest, gradient boosting, voting ensemble and k-means examples. Features include
past close returns/momentum/volatility/trend/range. Targets start at the next open.
At least 240 complete labelled observations are required; at most 5,000 bars.

Chronological train/validation/test partitions purge the forward label horizon.
Scaling and model fitting use training rows only. Validation/test do not refit the
selected model. Separate expanding TimeSeriesSplit folds also include the purge.
Metrics, predictions, fitted importance/coefficients, seed and settings are saved.
Joblib artifacts are server-generated and hash-verified on authenticated download.
User-provided pickle/joblib objects are never loaded.

Validation and test predictions separately feed native-currency, daily, long-only
positive-signal next-open cost simulations. These are held-out diagnostics, not
SGD ledger performance. Clusters have no invented trading direction. XGBoost,
LightGBM, regime classifiers, feature selection and general strategy parameter
walk-forward optimisation are not yet implemented. WALK currently opens the
model expanding-window workflow, not a strategy optimisation certification.

## Factors and Monte Carlo

Technical factors include 1/3/6/12-month momentum, reversal, volatility, beta,
trend and distance from moving averages. Latest cross-sections include raw values,
2.5/97.5-percentile winsorisation, z-scores, ranks, quantiles and classifications.
Historical Pearson/rank IC, coverage, IC volatility/IR, hit fraction, target
membership turnover, forward quantile returns and entry-cost sensitivity are
measured with a 70/30 split and forward-horizon purge. Overlapping forward labels
are not compounded NAV. Fundamental historical factors, decay/regime analysis and
factor correlations need further point-in-time data and implementation.

MC resamples saved NET portfolio/backtest returns with a configured seed using
bootstrap, contiguous blocks, normal draws or shuffling. It reports wealth
quantiles, terminal distribution, loss/drawdown/ruin thresholds and simulation
standard error. At least sixty eligible returns are required. Ruin is an explicit
wealth fraction. Normal draws below -100% receive a disclosed limited-liability
floor. This is conditional research, not a forecast or a portfolio optimisation.

## Review and Operations

Edge candidates retain hypothesis, rationale, version, universe, feature/target/
signal, construction, costs and chronological periods. Reviews append actor,
reason, state and matching-version completed run references. Positive output does
not pass point-in-time, multiple-testing or paper-validation gates automatically.
Unverified promotion remains blocked. The Quant monitor separates research job
kinds and displays actual status, stage, runtime and available held-out Sharpe.

Primary references:
- https://www.backtrader.com/docu/order-creation-execution/order-creation-execution/
- https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html
- https://www.statsmodels.org/stable/generated/statsmodels.regression.linear_model.OLSResults.get_robustcov_results.html
