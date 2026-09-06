# Alpha Methodology

ALPHA is a private, saved analytical workflow at `/alpha`. An AnalysisRun records
the resolved valuation/backtest input, factor version, settings, output and actor.
It never labels raw benchmark excess return as evidence of skill.

## Calculation

The dependent variable is the selected portfolio/strategy period return minus the
period risk-free return. CAPM regresses it on benchmark excess return with a
constant. FF3 uses MKT_RF/SMB/HML; FF5 adds RMW/CMA; Carhart adds MOM. CUSTOM accepts
one to twelve explicitly named excess-return columns from a persisted dataset.

Factor inputs are decimal returns (0.01 = 1%), not prices or percentage points.
Their dates and frequency must match the selected return observations. An optional
RF column supplies period risk-free returns; otherwise an annual effective rate is
converted using `(1 + annual_rate)^(1 / periods_per_year) - 1`. Missing factor dates
are not forward-filled or dropped to make a regression pass.

statsmodels OLS uses HAC/Bartlett covariance, configured lags, small-sample
correction and Student-t inference. The minimum sample is at least 60 by default,
and also exceeds the parameter/lag requirements. Duplicate, unordered, non-finite
and rank-deficient designs return an explicit unavailable/insufficient state.

Annualised alpha is the arithmetic period intercept multiplied by 252/52/12,
not a compound return or CAGR. Confidence intervals receive the same scaling.
The page reports intercept, interval, p-value, R-squared, sample size and factor
coefficients. Rolling regressions use only observations through each window end.
Raw cumulative excess return is linked portfolio return minus linked benchmark
return and is labelled separately.

## Cost Bases

NET portfolio returns use the exact saved ledger curve. GROSS adds back recorded
fees/commissions and accrued-fee changes, not taxes. Missing gross fee evidence
does not become zero. Estimated extra costs are explicit per-period basis points
subtracted from NET, not an estimate of unobserved actual fills.

New backtests retain a separate zero-cost gross counterfactual. Older runs without
one show gross alpha as unavailable. Counterfactual integer sizes and cash-driven
rejections can differ, so cost drag is not identical to commission totals.

## Limits

Short/partial/ineligible portfolio histories cannot generate inference. Daily
strategy curves are supported; non-daily strategy aggregation is not yet enabled.
HAC intervals are not proof of an edge: selection bias, overlapping observations,
survivorship, model search and multiple testing remain review risks.

Security selection, sector allocation, currency and hedge attribution require
matched benchmark holdings and exposures. They are not fabricated by decomposing
an aggregate regression intercept. Dedicated regime/decay/signal attribution
remains pending those inputs and validated attribution workflows.

Implementation: `alpha_statistics.py`, `alpha_api.py`, `quant_data.py`.
Primary reference: https://www.statsmodels.org/stable/generated/statsmodels.regression.linear_model.OLSResults.get_robustcov_results.html
