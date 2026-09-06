# Private Terminal Product Requirements

The controlling scope is the user's terminal-only correction of 2026-09-07.
KnK Capital Terminal is private, internal and proprietary, with no external clients.
Existing terminal, accounting, research, risk, workers and data must be preserved.

Primary portfolio: KNK_MAIN, KnK Capital Main Portfolio. Required deterministic
opening contribution and reference capital: SGD 100,000. Base currency SGD,
timezone Asia/Singapore. Manual execution only, IBKR Paper monitoring only.

Priority order: portfolio/NAV; risk/trades; quant/alpha/backtests; equity/valuation;
options/gamma/GEX; provider/file ingestion; Excel/decks/Pine; operations.
A function is AVAILABLE only when its executable workflow is verified. Other
states are DEMO_AVAILABLE, PROVIDER_REQUIRED or IN_DEVELOPMENT.

Required milestones:
1. One frontend; recovery tag; removed visitor routes; authentication; noindex.
2. Transaction-derived cash, positions, cost basis, NAV, returns and Overview.
3. Exposure, risk limits, trade monitoring, reconciliation, stress and manual hedges.
4. Persisted quant runs, alpha, factor evaluation, walk-forward and model review.
5. Private equity research, financials, DCF, WACC, comparables and theses.
6. Options-chain ingestion, Greeks, gamma, GEX/DEX and explicit sign assumptions.
7. Browser/file-agent Data Drop, Koyfin file attribution and provider readiness.
8. Formula-driven Excel, internal decks/PDF and compatible Pine Script export.
9. Actual component health, backups, browser workflows, complete tests and push.

Every analytical value needs source, dataset/version, currency, data state and
market/ingestion/calculation timestamps where applicable. Missing observations
must never become fabricated live values. Annualised statistics require adequate
history. Excess return is not proof of statistically significant alpha.

Imported raw objects and saved valuation runs remain immutable. Demo resets are
explicit, deterministic and archive previous records rather than erase them.
The old ledger must be retained when correcting the reference-capital specification.

No broker order may be placed, modified, cancelled or transmitted. Recommendations,
signals, Pine alerts and proposed trades require manual review and never execute.
