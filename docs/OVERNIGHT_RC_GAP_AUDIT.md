# Overnight Gap Audit

M2 inspection identified a historical FX risk in `MarketRepository.fx_rate`:
the direct-rate query honors `on_date`, but its inverse fallback does not. Add a
dated inverse-rate regression and fix the shared repository during the next batch.
This is a code-controlled issue, not an external-data blocker.

Baseline 3466694, 2026-09-12. Detailed domain limits in FINAL_GAP_AUDIT.md,
ACCOUNT_SECURITY.md, PROVIDER_CONNECTIONS.md, EQUITY_RESEARCH.md, OPTIONS_DATA.md.

| Domain | Classification | Outstanding acceptance |
| --- | --- | --- |
| Private terminal and local Docker | DEMO_FUNCTIONAL | Full release checks and report service |
| Ledger/NAV/performance | DEMO_FUNCTIONAL | Fresh full certification and attribution extensions |
| Risk/stress/hedge | PARTIAL | Dated browser success, nonlinear/covariance/rebalance scope |
| Data Drop/agent | PARTIAL | Complete profile/consumer/Windows acceptance |
| Providers/IBKR | PROVIDER_READY_UNVERIFIED | Adapter gaps remain separately PARTIAL; real connectivity unverified |
| Quant | PARTIAL | Corporate actions, PIT fundamentals, general walk-forward |
| Equity | PARTIAL | Segments, ROIC, historical/forward multiples and feeds |
| Options | PARTIAL | Historical OI/cones, multi-expiry and full portfolio scope |
| Reports | PARTIAL | Owned queued exports verified; full financial-model content and rendered artifacts pending |
| MFA/auth | PARTIAL | Trusted devices, provisioning and concurrency closure |
| Monitoring/backup | PARTIAL | Ten dashboards and PostgreSQL/remote object restore |
| Python quality | PARTIAL | Ruff/format pass; full API mypy still 1,140 errors in 46 files |
| Browser release | BROKEN | Prior full run 28/35; six unresolved after targeted backtest fix |
| Release command / hosted deployment | MISSING | Script implementation / external account access |

No report formatting, service health or test count certifies financial accuracy.
