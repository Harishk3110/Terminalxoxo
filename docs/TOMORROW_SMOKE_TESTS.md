# Tomorrow Smoke Tests

Status: PARTIAL. The requested executable tomorrow-smoke wrappers remain tracked
in FINAL_CLOSURE_TASKS.md. Record each observation with time, source commit,
environment and exact output; unavailable credentials are not a successful test.

- [ ] Authentication, password/TOTP setup, revocation and anonymous 401/403 denial.
- [ ] API readiness, database, Redis, private object store and all worker heartbeats.
- [ ] Real FRED request with original dates, provider state and retained provenance.
- [ ] Authorised Koyfin file mapping, approval, duplicates and immutable lineage.
- [ ] KNK_MAIN cash/positions/NAV reconciliation, no ledger reset or silent fallback.
- [ ] Source precedence, independent FX, stale and missing-value behavior.
- [ ] Source-pinned financial statements, DCF/WACC/comparables and thesis versions.
- [ ] Backtest lifecycle, results, cancellation, versions and cost assumptions.
- [ ] Risk, stress and manual hedge/rebalance review with truthful history coverage.
- [ ] Options units, expiry, partial-chain coverage and no missing-to-zero substitution.
- [ ] Owned XLSX/PPTX/PDF generation/download; anonymous and wrong-owner rejection.
- [ ] IBKR Paper read-only connection, outbound agent pairing/revocation and reconciliation.
- [ ] No broker order execution capability or automatically transmitted recommendation.
- [ ] Backup verification, isolated restore and active-record persistence after restart.
- [ ] Authorised hosted URL, root/private overview, same-origin API and secure cookies.

Do not use fictional templates as real account data. Do not log secrets, cookies,
unredacted account identifiers or real file contents into Git or shared evidence.
