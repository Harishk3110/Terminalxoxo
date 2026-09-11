# Overnight Gap Audit

M2 corrected the historical inverse-FX fallback in `MarketRepository.fx_rate`:
both rate directions now honor `on_date`, with future-only rejection tests.
Price-bar history now preserves absent volume as null rather than fabricating zero.
These targeted fixes do not certify every FX resolver or valuation caller.

Baseline 3466694, 2026-09-12. Detailed domain limits in FINAL_GAP_AUDIT.md,
ACCOUNT_SECURITY.md, PROVIDER_CONNECTIONS.md, EQUITY_RESEARCH.md, OPTIONS_DATA.md.

| Domain | Classification | Outstanding acceptance |
| --- | --- | --- |
| Private terminal and local Docker | DEMO_FUNCTIONAL | Full release checks and report service |
| Ledger/NAV/performance | DEMO_FUNCTIONAL | Fresh full certification and attribution extensions |
| Risk/stress/hedge | PARTIAL | Dated workflows pass; complete browser gate and nonlinear/covariance/rebalance scope remain |
| Data Drop/agent | PARTIAL | Complete profile/consumer/Windows acceptance |
| Providers/IBKR | PROVIDER_READY_UNVERIFIED | Adapter gaps remain separately PARTIAL; real connectivity unverified |
| Quant | PARTIAL | Corporate actions, PIT fundamentals, general walk-forward |
| Equity | PARTIAL | Segments, ROIC, historical/forward multiples and feeds |
| Options | PARTIAL | Historical OI/cones, multi-expiry and full portfolio scope |
| Reports | PARTIAL | Owned queued exports verified; full financial-model content and rendered artifacts pending |
| MFA/auth | PARTIAL | Trusted devices, provisioning and concurrency closure |
| Monitoring/backup | PARTIAL | Ten dashboards and PostgreSQL/remote object restore |
| Python quality | PARTIAL | Ruff/format pass; whole first-party strict runner now executes, but engine/API/test errors remain |
| Browser release | PARTIAL | Populated full run: 36/37; upload handoff corrected and focused pass; full rerun underway |
| Release command / hosted deployment | MISSING | Script implementation / external account access |

No report formatting, service health or test count certifies financial accuracy.

The unused inbound broker demo bridge is now disabled: it cannot issue a dummy
pairing token, claim a broker heartbeat or return hard-coded account balances.
The supported outbound paper reader and authenticated snapshot ingestion remain
unchanged. This closes a misleading legacy surface, not the entire IBKR milestone.
