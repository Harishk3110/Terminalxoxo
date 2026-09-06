# Private Equity Research

## Statements and Ratios

FIN separates income, balance sheet, cash flow and ratios. Annual, standalone
quarterly and TTM views keep actuals and estimates separate. TTM requires four
consecutive `YYYYQn` periods: flows sum; balances and end-period share counts use
the final quarter. Missing components stay null. Quarterly imports must not
contain cumulative YTD flows. Weighted-average diluted EPS is not inferred.

Koyfin/generic imports use preview, mapping, validation, approval and immutable
hash verification. Amounts normalize to company currency millions and shares
millions. Metric-level version/report-date provenance survives partial
restatements. Currency amounts in SHARES units are excluded. Wide share columns
use the declared scale as counts. Imported rows are not independently verified
filings or certified point-in-time data. Missing imported fields are never
demo-filled. Production requests do not create new synthetic statements;
historical synthetic snapshots retain explicit DEMO DATA labels.

Margins, growth, leverage, liquidity and average-balance ROE/ROA use available
inputs. Market multiples use current source-aware prices and annual/TTM flows;
quarterly earnings are not annualized into a P/E. Non-positive denominators stay
null. Negative earnings/FCF yields are retained. Forward P/E, historical multiple
percentiles, segments and measured after-tax ROIC remain unavailable.

## Valuation

DCF saves baseline statements, metric lineage, quote provenance, assumptions,
calculation version, actor, timestamp and SHA256 digest. Decimal FCFF uses
34-digit local precision and decimal-string API values; display rounding is
separate. `FCFF = EBIT - cash tax + D&A - CapEx - change in non-cash WC`.

Up to ten years of revenue growth and EBIT margins are editable in BULL/BASE/BEAR.
Tax, D&A/revenue, CapEx/revenue and NWC/revenue are explicit assumptions. Initial
NWC is supplied or estimated using the scenario ratio. Losses get no immediate
cash tax credit. End-year discounted terminal value uses perpetuity FCFF or an
EBITDA exit multiple. Perpetuity WACC must exceed growth. Equity = EV - debt +
cash; fair value = equity / positive shares. Negative values are not floored.

WACC weights CAPM equity cost and after-tax debt cost using market capital.
Inputs are user assumptions, not live rates. It can be saved independently or
explicitly applied to all scenarios. WACC/growth and WACC/exit sensitivities are
calculated. Financial firms and ETFs are rejected by company FCFF valuation.
NOL carryforwards, dilution, pensions, minority interests and non-operating asset
adjustments are not modelled. Terminal FCFF grows the final forecast FCFF, an
explicit simplifying assumption, not validated company guidance.
Method reference: [Damodaran valuation lectures](https://pages.stern.nyu.edu/~adamodar/New_Home_Page/lectures/val.html).

COMP pins statements/quotes and peers. Positive multiples produce mean, median,
quartiles, 1.5-IQR outliers and target-currency implied prices. Target excluded;
outliers identified but retained. Absolute amounts are never pooled across
currencies. Fiscal calendars/accounting definitions and small samples may differ.

## Theses and Security Views

Theses include narrative, variant perception, cases/probabilities, fair-value
range, catalysts, risks, invalidation, monitoring, horizon, weights, confidence,
review date, exit/post-mortem, citations, attachments and same-security DCF links.
Probabilities sum to one; target weight cannot exceed maximum. Each save is an
immutable version with a parent reference. Branches are allowed: IDs, not version
numbers alone, identify records. Matching immutable InvestmentThesis records
preserve compatibility with manual ledger and decision-journal foreign keys.
Existing free-form notes remain through the sidebar and `/ideas`. Historical
notes, theses and trades are not deleted. The desk excludes compatibility
references from duplicate structured-thesis counts.

DES/Q/GP show observed quote fields, timestamps, available 52-week range and
provider identifiers. Candlestick/line/area, daily/weekly/monthly aggregation,
daily rebased comparison and SMA20/50 are available. Missing bid/ask/VWAP stay
null. Intraday, event overlays, ownership, short-interest and verified earnings/
filings feeds are not fabricated. The desk shows current coverage, saved fair
values, upside and review dates, not unsupported live recommendations.

## Verification

Tests cover FCFF/NWC, WACC, losses, sensitivities, invalid assumptions, negative
equity, TTM completeness, missing ratios, peers, immutable versions, source hashes,
audit/authentication and quote-field honesty. Browser tests cover FIN -> DCF ->
COMP -> thesis save/revision/refresh, desktop/mobile geometry and price charts.
