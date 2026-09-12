# Tomorrow Data Onboarding

Status: PARTIAL. Do not onboard real data until FINAL_CLOSURE_STATUS.md certifies
the critical code gates. The requested tomorrow-onboarding wrappers are not yet
implemented; their absence is tracked in FINAL_CLOSURE_TASKS.md.

Preserve KNK_MAIN, SGD 100,000 reference capital, SGD base currency and
Asia/Singapore timestamps. Existing transactions and valuations must not be reset.
Position files are reconciliation references, not authority to overwrite holdings.

## Preparation

1. Provision a production administrator and enable TOTP using ACCOUNT_SECURITY.md.
2. Configure the authorised PostgreSQL, Redis and private object-store endpoints.
3. Enter provider credentials on the backend only. Never put secrets in browser
   variables, source control, templates or screenshots.
4. Configure FRED, SEC user agent, OpenFIGI and the selected market/fundamental,
   options and AI providers. Test each capability without claiming untested LIVE.
5. Run supported security-master and historical backfills before comparing prices.

## Files And Review

The seven existing templates and their actual parser field definitions are in
templates/README.md. They contain fictional, dated observations; do not import
their sample trades into KNK_MAIN. Use an isolated dry-run database first.

Upload authorised Koyfin prices, fundamentals, transactions or positions, FX and
options as needed. Review mapping, currency, scale, symbol identity, source dates,
licence and duplicates before approval. Retain file IDs and immutable version IDs.
Do not change observation dates to remove stale labels or substitute missing zero.

Select benchmark, tracking start, cost-basis method and risk limits. Revalue and
reconcile cash, positions, NAV and P&L before running performance/risk/stress/hedge.
Run a source-pinned backtest and generate a private portfolio workbook/equity deck.
Verify reported values, versions, downloads and access control.

Start IBKR Paper and the outbound read-only agent only after configuration review.
Pair, ingest broker state and reconcile recorded fills. Never transmit orders.
Record real-response schema differences separately from previously verified tests.
