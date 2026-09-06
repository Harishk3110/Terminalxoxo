# NAV Methodology

Version: knk-nav-4.7. See PORTFOLIO_NAV.md for current implementation evidence.
Authoritative calculation:
cash + sum(quantity * price * FX-to-SGD * contract multiplier) + accrued income
+ receivables - payables - accrued fees - other liabilities.

Financial quantities use Decimal; display amounts use half-even cent rounding.
Native cash is retained separately for each currency. Transaction FX records
historical cost and flows; current source-selected FX converts current assets.
Missing required price/FX invalidates complete NAV. Identity FX is one only when
the currencies are identical. Stale selected prices remain selected.

## Ledger and Returns
Policy-selected FIFO, average cost and specific-lot accounting retain native/base
cost. Charges are capitalized or expensed according to the recorded policy.
Partial sales release cost under that policy; shorts have signed cost
and covers release short proceeds proportionally. Splits preserve total cost;
spinoffs require explicit child quantity and cost allocation.

Daily P&L = closing NAV - opening NAV - external flows.
Daily return = daily P&L / (opening NAV + external flows).
All external flows are assumed at the beginning of the valuation day. TWR
geometrically links daily returns. Initial capital is an explicit contribution,
never inferred from an empty deposit. Transfers use declared fair value as
external flows. Nonpositive return denominators produce unavailable returns.

MWR uses PyXIRR and is deannualized to the observed period. Annual XIRR, CAGR
and Calmar require at least one year. Annual volatility, Sharpe and Sortino
require 60 trading observations. Ratios with zero denominators are unavailable.
MTD/QTD/YTD geometrically link complete daily returns and flag partial history.
Risk-free rate defaults explicitly
to zero in the demonstration profile. Nonconventional flows can have multiple
IRR roots; the application reports no claimed unique result for these flows.

Drawdown uses the flow-adjusted return index. Benchmark NAV is a shadow SPY
investment with the same external flows and SGD conversion.

## Audit and Limitations
Each calculation stores an immutable input fingerprint, result, selected-price
and FX provenance, calculation version, source dates and metric metadata.
Holdings/cash/DailyReturn tables are rebuildable current projections.
Historical calculations use currently accepted data versions and are restated,
not point-in-time backtests. Current-weight risk excludes cash-FX and liability
sensitivities; stale observations can understate variation. Historical covariance
and simulation are estimates, not forecasts or guaranteed loss limits.

Method references: [GIPS handbook](https://www.gipsstandards.org/standards/gips-standards-for-firms/gips-standards-handbook-for-firms/)
for linking subperiod returns; [PyXIRR](https://github.com/Anexen/pyxirr)
for dated cash-flow IRR. This implementation does not claim GIPS compliance.
