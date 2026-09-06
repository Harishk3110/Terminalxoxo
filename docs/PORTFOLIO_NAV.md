# Portfolio NAV

The managed KNK_MAIN demo starts with SGD 100,000 on 2026-06-03. It is not a broker account or live-price representation. The coherent demo closes on 2026-09-04 at SGD 100,597.57. Current requests retain the last accepted prices with stale-data warnings; they never invent live prices.

NAV is assets minus liabilities. Positive settled cash, long positions, accrued income and receivables comprise assets. Overdrafts, shorts, payables, accrued fees and other liabilities comprise liabilities. Economic cash includes settlement receivables/payables once. Transaction-time FX determines book cost; marked price and valuation-time FX determine current value. Balance-sheet and P&L reconciliations are independent checks.

`knk-nav-4.7` persists exact Decimal strings alongside display values for each opening/closing NAV, external flow, P&L, net return, benchmark return and fee expense. Gross fee addbacks use recorded fees/commissions and changes in accrued-fee liabilities, excluding taxes. Missing benchmark observations invalidate the linked benchmark; they are not zero returns.

Performance uses beginning-of-day external flows, geometric linked returns and sample statistics. Risk-free rates are annual effective rates converted to the observation frequency. Calendar returns beginning after their boundary are PARTIAL_PERIOD. Annual ratios require 60 complete observations; CAGR and annual XIRR require one year. Non-conventional flows do not produce a claimed unique IRR. Partial weeks/months remain visible but are excluded from annual risk samples. Irregular intervals and missing observations invalidate annualisation.

The authenticated Performance workspace supports portfolios, dates, daily/weekly/monthly frequency, net/gross fees, risk-free rates, rolling windows and persisted audited calculations. Saved runs pin their valuation ID. Historical snapshots without exact values remain readable and explicitly report LEGACY_ROUNDED precision; gross results require recorded fee data.

The current model uses a weekday valuation calendar, not instrument-specific exchange holidays. Cash FX risk and liability sensitivities are not included in the current-weight security covariance model. These limitations remain visible; this is not a production risk certification.

## Capital correction evidence

`services/api/scripts/correct_demo_capital.py` creates and checks a SQLite backup, appends a guarded amendment to the original managed 70K contribution, and verifies the original transaction/detail and saved valuation/analysis tables remain byte-equivalent as row hashes. Real/custom/previously-amended books are not automatically changed. Existing saved runs retain their original results.

Local application: `logs/pre-capital-100k.sqlite`; 16 transaction rows, 9 detail rows, 23 valuation runs and 1 analysis run preserved. New capital revision is audited. Reconciliation: BALANCED. The backup is ignored by Git.
