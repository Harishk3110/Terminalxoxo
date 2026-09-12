# Final Closure Tasks

Controlling directive: 2026-09-12 final release-closure attachment.
Starting checkpoint: 41baacb on main. Preserve OVERNIGHT_RC_* evidence.
Unchecked below means not certified against this directive, not necessarily missing code.

## Immediate Queue

- [x] Correct the documented single-period FIN chart invisibility with negative and positive browser evidence.
- [x] Bring the existing release runner from 27 to the required 29 ordered gates, preserving fail-fast and isolation checks.
- [x] Correct incomplete-NAV reconciliation serialization and validate recorded comparison inputs without changing the unconnected path.
- [x] Close trade-monitor evidence boundary and review browser verification; 186 affected/security/report tests pass and final desktop/mobile review browser passes.
- [x] Reject malformed new trade notes/rationale before persistence and preserve complete saved risk exposures.
- [x] Type valuation position/P&L/cash/curve records, reject missing transaction posting totals, and verify exact prior-output parity plus five browser workflows.
- [ ] Eliminate remaining 539 canonical first-party strict diagnostics without weakening contracts (whole run 58).
- [ ] Complete the full current baseline and all final gates; frozen fcaa774 backend 37 passed 2,053 tests with native 0 and 89.9076517% coverage. Later valuation-record work has focused evidence; full final certification remains open.


## 6. REPORT ENGINE - FIRST RELEASE BLOCKER

- [ ] Report ID.
- [ ] Requesting user.
- [ ] Portfolio ID.
- [ ] Security ID where applicable.
- [ ] Strategy ID where applicable.
- [ ] Backtest ID where applicable.
- [ ] Dataset ID.
- [ ] Exact immutable dataset-version ID.
- [ ] Calculation-version ID.
- [ ] Data-source snapshot.
- [ ] Report type.
- [ ] Output format.
- [ ] Status.
- [ ] Progress.
- [ ] Created time.
- [ ] Started time.
- [ ] Completed time.
- [ ] Worker ID.
- [ ] Error type.
- [ ] Error message.
- [ ] File checksum.
- [ ] File size.
- [ ] Object-storage reference.
- [ ] Retention/expiry state.
- [ ] Audit history.
- [ ] `PENDING`
- [ ] `QUEUED`
- [ ] `RUNNING`
- [ ] `SUCCEEDED`
- [ ] `FAILED`
- [ ] `CANCELLED`
- [ ] `EXPIRED`
- [ ] Portfolio XLSX.
- [ ] Portfolio risk XLSX.
- [ ] Portfolio performance XLSX.
- [ ] Portfolio PDF.
- [ ] Portfolio review PPTX.
- [ ] Backtest XLSX.
- [ ] Factor-analysis XLSX.
- [ ] Quant strategy PPTX.
- [ ] Backtest PDF.
- [ ] Equity model XLSX.
- [ ] DCF XLSX.
- [ ] Comparables XLSX.
- [ ] Internal equity-research PPTX.
- [ ] Equity-research PDF.
- [ ] Macro XLSX.
- [ ] Risk-review PPTX.
- [ ] Risk PDF.
- [ ] KnK Capital identity.
- [ ] Internal-use disclosure.
- [ ] Report date.
- [ ] Data as-of date.
- [ ] Base currency.
- [ ] Data state.
- [ ] Sources.
- [ ] Dataset versions.
- [ ] Calculation version.
- [ ] Methodology.
- [ ] Validation/check section.
- [ ] `POST /api/v1/reports`
- [ ] `GET /api/v1/reports`
- [ ] `GET /api/v1/reports/{report_id}`
- [ ] `GET /api/v1/reports/{report_id}/status`
- [ ] `GET /api/v1/reports/{report_id}/download`
- [ ] `POST /api/v1/reports/{report_id}/cancel`
- [ ] `POST /api/v1/reports/{report_id}/regenerate`
- [ ] report-engine Docker service.
- [ ] health check.
- [ ] readiness check.
- [ ] worker heartbeat.
- [ ] Prometheus metrics.
- [ ] Grafana panels.
- [ ] System Health row.
- [ ] frontend progress state.
- [ ] authenticated download.
- [ ] browser report workflow.
- [ ] Container healthy.
- [ ] Request persists.
- [ ] Queue dispatches.
- [ ] File generates.
- [ ] Checksum exists.
- [ ] Object exists after restart.
- [ ] Authenticated download succeeds.
- [ ] Anonymous download fails.
- [ ] Dataset version is pinned.
- [ ] Tests pass.

## 7. WHOLE-BACKEND RUFF AND MYPY CLOSURE

- [ ] Shared types and protocols.
- [ ] Database models.
- [ ] Repositories.
- [ ] Provider adapters.
- [ ] Portfolio.
- [ ] Performance and Alpha.
- [ ] Risk, stress, hedge, and reconciliation.
- [ ] Quant and backtesting.
- [ ] Equity.
- [ ] Options.
- [ ] Reports.
- [ ] API routes.
- [ ] Workers.
- [ ] Local agent.
- [ ] Operational scripts.
- [ ] No global ignores.
- [ ] No blanket module exclusions.
- [ ] No disabling strict mode.
- [ ] No broad Any used solely to silence errors.
- [ ] No deleting functioning tests.
- [ ] No changing response contracts silently.
- [ ] No unsafe cast without runtime validation.
- [ ] No hiding errors behind dynamic dictionaries when typed models are appropriate.
- [ ] Whole-backend Ruff: exit 0.
- [ ] Whole-backend mypy: exit 0.
- [ ] OpenAPI generation: exit 0.
- [ ] Backend tests remain green.
- [ ] Migration tests remain green.

## 8. STRESS, HEDGE, AND BETA-HISTORY CLOSURE

- [ ] Benchmark.
- [ ] Frequency.
- [ ] Start date.
- [ ] End date.
- [ ] Estimation window.
- [ ] Minimum aligned observations.
- [ ] Return convention.
- [ ] Missing-value policy.
- [ ] Calculate Beta.
- [ ] Persist sample size.
- [ ] Persist R-squared.
- [ ] Persist Alpha.
- [ ] Persist confidence interval.
- [ ] Persist data and benchmark versions.
- [ ] Available observations.
- [ ] Required observations.
- [ ] Missing date range.
- [ ] Benchmark.
- [ ] Calculation method.
- [ ] Run ID.
- [ ] Portfolio.
- [ ] Scenario.
- [ ] Assumptions.
- [ ] Source data.
- [ ] Position contribution.
- [ ] Sector contribution.
- [ ] Country contribution.
- [ ] Currency contribution.
- [ ] Factor contribution.
- [ ] Hedge contribution.
- [ ] Pre-stress NAV.
- [ ] Post-stress NAV.
- [ ] Data timestamp.
- [ ] Calculation timestamp.
- [ ] Status.
- [ ] Current Beta.
- [ ] Target Beta.
- [ ] Required notional.
- [ ] Instrument.
- [ ] Direction.
- [ ] Rounded quantity.
- [ ] Residual.
- [ ] Before/after gross.
- [ ] Before/after net.
- [ ] Before/after Beta.
- [ ] Estimated cost.
- [ ] Estimated VaR effect.
- [ ] Stress effect.
- [ ] Manual-review status.

## 9. EQUITY RESEARCH FINAL GAPS

- [ ] FIN.
- [ ] FCFF.
- [ ] WACC.
- [ ] Comparables.
- [ ] Thesis.
- [ ] Interactive chart workflows.
- [ ] Thesis version history.
- [ ] Manual-ledger references.
- [ ] Restatement provenance.
- [ ] Unit-rejection behaviour.

### 9.1 Segment reporting

- [ ] Instrument ID.
- [ ] Fiscal period.
- [ ] Period end.
- [ ] Filing/publication date.
- [ ] Segment name.
- [ ] Parent segment where applicable.
- [ ] Metric.
- [ ] Value.
- [ ] Currency.
- [ ] Unit.
- [ ] Scale.
- [ ] Annual/quarterly frequency.
- [ ] Actual/estimate state.
- [ ] Source.
- [ ] Filing ID.
- [ ] Dataset version.
- [ ] Restatement state.
- [ ] Segment revenue.
- [ ] Segment operating income.
- [ ] Segment assets where provided.
- [ ] Segment margins.
- [ ] Segment growth.
- [ ] Segment mix.
- [ ] Annual and quarterly views.
- [ ] Source and filing links.
- [ ] Missing-segment state.
- [ ] Segment table.
- [ ] Segment revenue chart.
- [ ] Segment margin chart.
- [ ] Segment mix chart.
- [ ] Segment contribution to company growth.

### 9.2 ROIC and invested-capital bridge

- [ ] Net working capital.
- [ ] Net property, plant, and equipment.
- [ ] Capitalised leases where data permit.
- [ ] Other operating assets.
- [ ] Other operating liabilities.
- [ ] Goodwill and intangibles inclusion/exclusion.
- [ ] Cash exclusion.
- [ ] Debt/equity reconciliation.
- [ ] NOPAT.
- [ ] Invested capital.
- [ ] Average invested capital.
- [ ] ROIC.
- [ ] Incremental ROIC where sufficient history exists.
- [ ] ROIC history.
- [ ] Methodology.
- [ ] Assumptions.
- [ ] Source.
- [ ] Insufficient-data state.

### 9.3 Historical valuation multiples

- [ ] P/E.
- [ ] P/B.
- [ ] P/S.
- [ ] EV/Sales.
- [ ] EV/EBITDA.
- [ ] EV/EBIT.
- [ ] FCF yield.
- [ ] Earnings yield.
- [ ] Historical market price/market cap.
- [ ] Historical enterprise value.
- [ ] Latest information available as of each date.
- [ ] TTM fundamentals available as of each date.
- [ ] Shares and debt available as of each date.
- [ ] Currency and scale.
- [ ] Current.
- [ ] Historical median.
- [ ] Historical average.
- [ ] Percentile.
- [ ] Z-score.
- [ ] Min/max.
- [ ] Chart.
- [ ] Source.
- [ ] Data coverage.

### 9.4 Forward valuation multiples

- [ ] Forward P/E.
- [ ] Forward EV/Sales.
- [ ] Forward EV/EBITDA.
- [ ] Forward EV/EBIT.
- [ ] Forward FCF yield.
- [ ] Forecast period.
- [ ] Consensus publication date.
- [ ] Analyst count.
- [ ] High/low/median where supplied.
- [ ] Source.
- [ ] Dataset version.

### 9.5 Unconnected-provider workflow

- [ ] DEMO_AVAILABLE.
- [ ] FILE_IMPORT.
- [ ] CONNECTED.
- [ ] PROVIDER_REQUIRED.
- [ ] DATA_UNAVAILABLE.
- [ ] STALE.

## 10. QUANT FINAL GAPS


### 10.1 Corporate-action backtesting

- [ ] Cash dividends.
- [ ] Stock splits.
- [ ] Reverse splits.
- [ ] Spin-offs where sufficient data exist.
- [ ] Symbol changes.
- [ ] Delistings.
- [ ] Merger consideration where represented.
- [ ] Rights issues as explicit unsupported or implemented state.
- [ ] Quantity adjusts.
- [ ] Price adjusts appropriately.
- [ ] Cash dividends credit cash.
- [ ] Cost basis remains coherent.
- [ ] Corporate-action timing uses effective date.
- [ ] Backtest logs action processing.
- [ ] Data provenance is preserved.

### 10.2 Point-in-time fundamental factors

- [ ] Period end.
- [ ] Filing date.
- [ ] Publication date.
- [ ] Revision/restatement date.
- [ ] Provider timestamp.
- [ ] Dataset version.
- [ ] Using future filings.
- [ ] Using latest restated numbers in earlier decisions without explicit restatement mode.
- [ ] Using current constituents for historical universes without warning.
- [ ] Using forward estimates before publication.

### 10.3 Full attribution

- [ ] Security.
- [ ] Sector.
- [ ] Industry.
- [ ] Country.
- [ ] Currency.
- [ ] Factor.
- [ ] Signal.
- [ ] Long/short book.
- [ ] Fees.
- [ ] Commission.
- [ ] Spread.
- [ ] Slippage.
- [ ] FX.
- [ ] Cash.
- [ ] Hedge.

### 10.4 General walk-forward optimisation

- [ ] Rolling windows.
- [ ] Expanding windows.
- [ ] Train window.
- [ ] Validation window.
- [ ] OOS window.
- [ ] Refit interval.
- [ ] Parameter grid.
- [ ] Parameter selection metric.
- [ ] Constraints.
- [ ] Transaction costs.
- [ ] Aggregated OOS series.
- [ ] Parameter-stability report.
- [ ] Performance-degradation report.
- [ ] Regime breakdown.
- [ ] Run cancellation.
- [ ] Persistence.

### 10.5 Edge validation gates

- [ ] OOS return.
- [ ] OOS Sharpe.
- [ ] Maximum drawdown.
- [ ] Turnover.
- [ ] Cost sensitivity.
- [ ] Parameter stability.
- [ ] Regime consistency.
- [ ] Data coverage.
- [ ] Correlation to existing strategies.
- [ ] Capacity proxy.

## 11. OPTIONS FINAL GAPS


### 11.1 Unit normalisation

- [ ] Price per share.
- [ ] Premium per contract.
- [ ] Delta per option.
- [ ] Position Delta.
- [ ] Dollar Delta.
- [ ] Gamma per unit underlying.
- [ ] Dollar Gamma.
- [ ] Vega per one-volatility-point move.
- [ ] Theta per calendar day.
- [ ] Contract multiplier.
- [ ] Currency.

### 11.2 Expiry conventions

- [ ] Expiration date.
- [ ] Expiration timestamp.
- [ ] Exchange timezone.
- [ ] Last trading time.
- [ ] Settlement type.
- [ ] AM/PM settlement where provided.
- [ ] Calendar-day time to expiry.
- [ ] Trading-day time to expiry where used.
- [ ] Expired contracts.
- [ ] Same-day expiry.
- [ ] Zero time to expiry.
- [ ] Weekend/holiday expiry.
- [ ] Missing expiry time.

### 11.3 Missing and partial chains

- [ ] Complete.
- [ ] Partial.
- [ ] Stale.
- [ ] Missing.
- [ ] Provider required.
- [ ] Entitlement required.
- [ ] Expected contracts.
- [ ] Received contracts.
- [ ] Missing strikes.
- [ ] Missing expiries.
- [ ] Missing OI.
- [ ] Missing Greeks.
- [ ] Coverage percentage.

### 11.4 Limits

- [ ] Maximum selected underlyings.
- [ ] Maximum expiries.
- [ ] Maximum strikes.
- [ ] Maximum contracts.
- [ ] Maximum date range.
- [ ] Maximum imported rows.
- [ ] Maximum API pagination.
- [ ] Maximum GEX scenario points.

### 11.5 Options provider boundary

- [ ] Contract definitions.
- [ ] Chain.
- [ ] Bid/ask/last.
- [ ] OI.
- [ ] Volume.
- [ ] IV.
- [ ] Greeks.
- [ ] Multiplier.
- [ ] Exercise style.
- [ ] Settlement type.
- [ ] Timestamp.
- [ ] Entitlements.

## 12. PROVIDERS, SEC CURATION, AND FX PRECEDENCE


### 12.1 SEC financial curation

- [ ] CIK mapping.
- [ ] Filing discovery.
- [ ] 10-K.
- [ ] 10-Q.
- [ ] 8-K.
- [ ] 20-F.
- [ ] 6-K.
- [ ] XBRL company facts.
- [ ] Filing and accession provenance.
- [ ] Amendment status.
- [ ] Statement period alignment.
- [ ] Annual/quarterly classification.
- [ ] Units and scales.
- [ ] Currency.
- [ ] Restatement handling.
- [ ] Historical fact versions.
- [ ] Statement-line mapping.
- [ ] Raw filing links.

### 12.2 Market/fundamental provider adapters

- [ ] EODHD-compatible provider.
- [ ] FMP-compatible provider.
- [ ] Test Connection.
- [ ] Capabilities.
- [ ] Security master.
- [ ] Price history.
- [ ] Latest/EOD quote where supported.
- [ ] Corporate actions.
- [ ] Fundamentals.
- [ ] Calendars.
- [ ] Usage/rate-limit state.
- [ ] Backfill.
- [ ] Incremental refresh.
- [ ] Raw storage.
- [ ] Curated storage.
- [ ] Provider health.

### 12.3 Separate FX precedence

- [ ] Dedicated connected FX provider.
- [ ] IBKR quote.
- [ ] Imported validated FX data.
- [ ] Demo FX provider.
- [ ] Direct rates.
- [ ] Inverse rates.
- [ ] Cross rates.
- [ ] Timestamp matching.
- [ ] Missing-rate state.
- [ ] Stale-rate state.
- [ ] Audited override.
- [ ] Source conflict.

## 13. LOCAL AGENT AND IBKR READ-ONLY READINESS


### 13.1 Local file agent

- [ ] Configurable watched folder.
- [ ] Stable-file detection.
- [ ] Partial-write avoidance.
- [ ] SHA-256.
- [ ] Duplicate prevention.
- [ ] Outbound authenticated upload.
- [ ] Retry with backoff.
- [ ] Resume where practical.
- [ ] Pause.
- [ ] Resume.
- [ ] Manual rescan.
- [ ] Archive.
- [ ] Reject.
- [ ] Quarantine.
- [ ] Heartbeat.
- [ ] Pairing.
- [ ] Revocation.
- [ ] Windows Credential Manager.
- [ ] Structured local logs.
- [ ] Secret redaction.
- [ ] Foreground mode.
- [ ] Startup mode.
- [ ] Service-install scripts where practical.

### 13.2 IBKR read-only agent

- [ ] TWS Paper.
- [ ] IB Gateway Paper.
- [ ] Host.
- [ ] Port.
- [ ] Client ID.
- [ ] Account ID.
- [ ] Read-only state.
- [ ] Account summary.
- [ ] Net liquidation value.
- [ ] Cash.
- [ ] Positions.
- [ ] Open-order monitoring.
- [ ] Executions.
- [ ] Fills.
- [ ] Commissions.
- [ ] Realised P&L.
- [ ] Unrealised P&L.
- [ ] Contract details.
- [ ] Quotes where entitled.
- [ ] Heartbeat.
- [ ] Reconnect.
- [ ] Duplicate-event prevention.
- [ ] Sequence handling.
- [ ] Pairing.
- [ ] Revocation.
- [ ] Outbound encrypted cloud connection.
- [ ] Security tests.
- [ ] Documentation describing prohibition.

## 14. SECURITY FINAL GAPS

- [ ] TOTP.
- [ ] Recovery codes.
- [ ] Password changes.
- [ ] Session revocation.

### 14.1 Trusted devices

- [ ] Device ID.
- [ ] Device name.
- [ ] Browser/OS metadata.
- [ ] Enrolled time.
- [ ] Last-used time.
- [ ] Expiry.
- [ ] Revoked time.
- [ ] User-visible device list.
- [ ] Revoke one device.
- [ ] Revoke all other devices.
- [ ] Audit events.
- [ ] Session association where appropriate.

### 14.2 First-administrator provisioning

- [ ] Secure CLI bootstrap.
- [ ] One-time setup token.
- [ ] Expiring token.
- [ ] Forced password creation.
- [ ] Forced TOTP setup.
- [ ] Token invalidation after use.
- [ ] No default production password.
- [ ] Audit event.

### 14.3 Concurrency hardening

- [ ] Simultaneous login attempts.
- [ ] Session creation.
- [ ] Session revocation race.
- [ ] Recovery-code one-use race.
- [ ] TOTP replay.
- [ ] Duplicate setup-token use.
- [ ] Concurrent password change.
- [ ] Device revocation.

### 14.4 Production settings

- [ ] Secure cookies.
- [ ] SameSite.
- [ ] Cookie domain.
- [ ] CSRF.
- [ ] CORS allowlist.
- [ ] CSP.
- [ ] HSTS.
- [ ] Proxy headers.
- [ ] Rate limits.
- [ ] Brute-force protections.
- [ ] Secret redaction.
- [ ] Account-ID redaction.
- [ ] Security events.

## 15. GRAFANA AND MONITORING

- [ ] Platform Overview.
- [ ] API Performance.
- [ ] Data Ingestion.
- [ ] Provider Health.
- [ ] Portfolio and NAV Operations.
- [ ] Risk and Breaches.
- [ ] Quant and Backtest Jobs.
- [ ] PostgreSQL and Redis.
- [ ] Authentication and Security.
- [ ] Report Engine and Object Storage.
- [ ] Request rate.
- [ ] Request latency.
- [ ] HTTP errors.
- [ ] Database pool.
- [ ] Query latency.
- [ ] Redis health.
- [ ] Queue depth.
- [ ] Worker heartbeat.
- [ ] Job state count.
- [ ] Job duration.
- [ ] Retries.
- [ ] Provider latency.
- [ ] Provider errors.
- [ ] Provider rate limits.
- [ ] Records received.
- [ ] Records accepted.
- [ ] Records rejected.
- [ ] Dataset freshness.
- [ ] NAV duration.
- [ ] Risk duration.
- [ ] Backtest duration.
- [ ] Report duration.
- [ ] Local-agent heartbeat.
- [ ] Broker-agent heartbeat.
- [ ] Authentication failures.
- [ ] Session events.
- [ ] Backup status.

## 16. BACKUP AND RESTORE

- [ ] PostgreSQL.
- [ ] Raw objects.
- [ ] Curated Parquet datasets.
- [ ] Reports.
- [ ] Model artifacts.
- [ ] Configuration metadata excluding secrets.
- [ ] Timestamped manifest.
- [ ] Checksums.
- [ ] Optional encryption.
- [ ] Retention policy.
- [ ] Backup verification.
- [ ] Isolated PostgreSQL restore.
- [ ] Isolated object restore.
- [ ] Business-table row-count comparison.
- [ ] Critical-record hash comparison.
- [ ] Object inventory comparison.
- [ ] Backup metrics.
- [ ] Failure alerts.
- [ ] System Health state.
- [ ] `make backup`
- [ ] `make verify-backup`
- [ ] `make restore-test`

## 17. DEPLOYMENT CONFIGURATION

- [ ] Vercel-compatible production build.
- [ ] Private authentication.
- [ ] noindex.
- [ ] nofollow.
- [ ] No anonymous financial content.
- [ ] No localhost production API URL.
- [ ] No provider secret in NEXT_PUBLIC variables.
- [ ] Root routes to /overview after authentication.
- [ ] FastAPI image.
- [ ] Data-worker image.
- [ ] Quant-worker image.
- [ ] Report-engine image.
- [ ] PostgreSQL configuration.
- [ ] Redis configuration.
- [ ] S3/R2 configuration.
- [ ] Migration command.
- [ ] Admin-bootstrap command.
- [ ] Backup command.
- [ ] Health checks.
- [ ] Readiness checks.
- [ ] Production environment-variable inventory.
- [ ] CORS configuration.
- [ ] Cookie configuration.
- [ ] Database SSL.
- [ ] Redis TLS where applicable.
- [ ] Trusted proxy configuration.
- [ ] Deployment order.
- [ ] Migration order.
- [ ] Rollback procedure.
- [ ] Local production-mode smoke test.
- [ ] Deploy to existing staging projects.
- [ ] Do not create duplicate projects.
- [ ] Verify the URLs.
- [ ] Verify HTTP.
- [ ] Verify authentication.
- [ ] Verify API connection.
- [ ] Do not claim deployment.
- [ ] Complete configurations.
- [ ] Complete production builds.
- [ ] Produce tomorrow’s exact commands.
- [ ] Record the external blocker.

## 18. SINGLE RELEASE-CANDIDATE COMMAND

- [ ] `make release-candidate`
- [ ] `scripts/release-candidate.ps1`
- [ ] Validate environment.
- [ ] Secret scan.
- [ ] Broker-action scan.
- [ ] Dependency validation.
- [ ] Database migration upgrade.
- [ ] Database downgrade/upgrade test.
- [ ] Backend format check.
- [ ] Ruff.
- [ ] mypy.
- [ ] Backend unit tests.
- [ ] Backend integration tests.
- [ ] Coverage.
- [ ] Frontend lint.
- [ ] TypeScript.
- [ ] Frontend unit tests.
- [ ] Shared package tests.
- [ ] Production frontend build.
- [ ] Docker image builds.
- [ ] Docker startup.
- [ ] Service health.
- [ ] Report-engine smoke.
- [ ] Full browser suite.
- [ ] Visual suite.
- [ ] Security suite.
- [ ] Backup.
- [ ] Backup verification.
- [ ] Isolated restore test.
- [ ] Restart-persistence smoke.
- [ ] Build-evidence update.

## 19. FINAL RELEASE GATES

- [ ] PostgreSQL healthy.
- [ ] Redis healthy.
- [ ] MinIO/object storage healthy.
- [ ] API healthy.
- [ ] Data worker healthy.
- [ ] Quant worker healthy.
- [ ] Report engine healthy.
- [ ] Terminal healthy.
- [ ] Prometheus targets healthy.
- [ ] Grafana dashboards provisioned.
- [ ] Clean upgrade passes.
- [ ] Downgrade/upgrade passes.
- [ ] Seed passes.
- [ ] Restart persistence passes.
- [ ] Full backend tests: zero failure.
- [ ] Ruff: zero error.
- [ ] mypy: zero error.
- [ ] OpenAPI generation passes.
- [ ] Coverage meets existing threshold.
- [ ] Frontend tests: zero failure.
- [ ] Shared tests: zero failure.
- [ ] TypeScript: zero error.
- [ ] Lint: zero error.
- [ ] Production build passes.
- [ ] Full browser run: zero failure.
- [ ] Visual run: zero failure.
- [ ] SGD 100,000 opening capital reconciles.
- [ ] Transactions drive cash.
- [ ] Transactions drive positions.
- [ ] NAV calculates.
- [ ] P&L calculates.
- [ ] Performance calculates.
- [ ] Alpha calculates or truthfully reports insufficient history.
- [ ] Risk changes when positions change.
- [ ] Restart preserves state.
- [ ] Browser upload passes.
- [ ] Local-agent integration test passes.
- [ ] Duplicate detection passes.
- [ ] Mapping profile passes.
- [ ] Dataset versioning passes.
- [ ] Lineage passes.
- [ ] Koyfin state passes.
- [ ] Source precedence passes.
- [ ] Source conflict passes.
- [ ] Stale-data state passes.
- [ ] Asynchronous backtest passes.
- [ ] Result persistence passes.
- [ ] Dataset version pin passes.
- [ ] Corporate actions pass.
- [ ] Point-in-time factor test passes.
- [ ] Full attribution passes.
- [ ] Walk-forward passes.
- [ ] Monte Carlo passes.
- [ ] FIN passes.
- [ ] Segments pass.
- [ ] ROIC passes.
- [ ] Historical multiples pass.
- [ ] Forward multiples pass or display honest provider-required state.
- [ ] DCF passes.
- [ ] WACC passes.
- [ ] COMP passes.
- [ ] Thesis passes.
- [ ] Demo/imported chain passes.
- [ ] Unit normalisation passes.
- [ ] Expiry convention passes.
- [ ] Missing/partial-chain state passes.
- [ ] Greeks pass.
- [ ] Gamma passes.
- [ ] GEX passes.
- [ ] DEX passes.
- [ ] IV passes.
- [ ] Payoff passes.
- [ ] XLSX passes.
- [ ] PPTX passes.
- [ ] PDF passes.
- [ ] Authenticated download passes.
- [ ] Anonymous download fails.
- [ ] Dataset version pin passes.
- [ ] Anonymous investment routes fail with 401/403.
- [ ] Trusted-device tests pass.
- [ ] Provisioning tests pass.
- [ ] Concurrency tests pass.
- [ ] Secret scan passes.
- [ ] Broker-action scan passes.
- [ ] No execution path exists.
- [ ] Backup passes.
- [ ] Verification passes.
- [ ] Isolated restore passes.
- [ ] Critical data comparison passes.
- [ ] Production frontend build passes.
- [ ] Production backend images build.
- [ ] No localhost production URL.
- [ ] Environment inventory complete.
- [ ] Local production-mode smoke passes.
- [ ] Hosted URL reported only if actually deployed and verified.

## 20. TOMORROW DATA TEMPLATES

- [ ] `templates/positions.csv`
- [ ] `templates/transactions.csv`
- [ ] `templates/prices.csv`
- [ ] `templates/fx.csv`
- [ ] `templates/fundamentals_long.csv`
- [ ] `templates/fundamentals_wide.csv`
- [ ] `templates/options_chain.csv`
- [ ] symbol
- [ ] quantity
- [ ] average_cost
- [ ] currency
- [ ] account
- [ ] as_of_date
- [ ] trade_date
- [ ] settlement_date
- [ ] symbol
- [ ] transaction_type
- [ ] quantity
- [ ] price
- [ ] currency
- [ ] commission
- [ ] fee
- [ ] account
- [ ] external_reference
- [ ] symbol
- [ ] date
- [ ] open
- [ ] high
- [ ] low
- [ ] close
- [ ] adjusted_close
- [ ] volume
- [ ] currency
- [ ] pair
- [ ] date
- [ ] rate
- [ ] source
- [ ] underlying
- [ ] expiration
- [ ] strike
- [ ] option_type
- [ ] bid
- [ ] ask
- [ ] last
- [ ] volume
- [ ] open_interest
- [ ] implied_volatility
- [ ] delta
- [ ] gamma
- [ ] theta
- [ ] vega
- [ ] rho
- [ ] contract_multiplier
- [ ] timestamp

## 21. TOMORROW RUNBOOK

- [ ] `scripts/tomorrow-onboarding.ps1`
- [ ] `scripts/tomorrow-onboarding.sh`
- [ ] `scripts/tomorrow-deploy.ps1`
- [ ] `scripts/tomorrow-deploy.sh`
- [ ] `scripts/tomorrow-smoke.ps1`
- [ ] `scripts/tomorrow-smoke.sh`
- [ ] Bootstrap production administrator.
- [ ] Set password.
- [ ] Configure TOTP.
- [ ] Enter PostgreSQL configuration.
- [ ] Enter Redis configuration.
- [ ] Enter S3/R2 configuration.
- [ ] Enter FRED key.
- [ ] Configure SEC user agent.
- [ ] Enter OpenFIGI key.
- [ ] Enter selected market/fundamental provider key.
- [ ] Enter options-provider key.
- [ ] Enter AI-provider key.
- [ ] Test each connection.
- [ ] Run security-master backfill.
- [ ] Run FRED backfill.
- [ ] Upload Koyfin price file.
- [ ] Confirm mapping.
- [ ] Upload fundamentals.
- [ ] Upload positions or transactions.
- [ ] Upload FX if required.
- [ ] Upload options chain if required.
- [ ] Select benchmark.
- [ ] Set tracking start date.
- [ ] Select cost-basis method.
- [ ] Configure risk limits.
- [ ] Revalue KNK_MAIN.
- [ ] Verify NAV.
- [ ] Verify source states.
- [ ] Run performance.
- [ ] Run risk.
- [ ] Run stress.
- [ ] Generate hedge.
- [ ] Run backtest.
- [ ] Generate portfolio XLSX.
- [ ] Generate equity deck.
- [ ] Start IBKR Paper.
- [ ] Start local agent.
- [ ] Pair agent.
- [ ] Import broker account state.
- [ ] Run reconciliation.
- [ ] Deploy backend.
- [ ] Deploy terminal.
- [ ] Run production smoke tests.

Detailed constraints, formulas and acceptance semantics remain in the user directive.
Existing verified component evidence: OVERNIGHT_RC_BUILD_EVIDENCE.md and FINAL_CLOSURE_BUILD_EVIDENCE.md.
No checked domain completion is inferred from historical test totals alone.
