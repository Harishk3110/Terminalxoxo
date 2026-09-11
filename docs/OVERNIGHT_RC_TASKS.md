# Overnight Release Tasks

The 2026-09-12 overnight directive controls acceptance; prior checkmarks are not
substitutes for its release gates. All requirements within each referenced
milestone remain open unless explicitly verified below.

- [x] Read directive and baseline architecture/security/methodology documents.
- [x] Recalculate Git, Ruff, mypy, test inventory and Docker baseline.
- [x] Push pre-overnight-rc-closure recovery tag.
- [x] M1: authenticated report submission, owner scope, immutable input/hash/version.
- [x] M1: SQL worker claim, bounded failure, private storage, download retention, audit.
- [ ] M1: all 16 XLSX/PPTX/PDF report families with verified financial models.
- [x] M1: source metadata, hashes, owned downloads, worker-exit persistence and anonymous tests.
- [x] M1: Excel Studio / Deck Builder, health, metrics, browser generation.
- [ ] M2: whole first-party formatting/Ruff/mypy, TypeScript, ESLint, OpenAPI.
- [x] M2: first-party Ruff and formatting, OpenAPI generation (170 paths).
- [x] M2: typed provider transport, JSON validation, SEC filing shapes, option-pricing and storage boundaries.
- [ ] M2: persisted model/repository contracts and remaining engine/API types.
- [ ] M3: full single-run browser suite, zero retries masking failures.
- [ ] M3: 16 requested pages at four desktop sizes and 390px, inspected screenshots.
- [ ] M4: all 19 ledger types, lot/cash/FX/NAV/performance/alpha/attribution certification.
- [ ] M4: BUY/partial SELL/dividend -> downstream risk/review and restart persistence.
- [ ] M5: all formats/profiles/types, immutable raw/curated versions and consumers.
- [ ] M6: Windows outbound watcher/pairing/revocation/credentials/logs/startup.
- [ ] M7: full FRED/SEC/OpenFIGI/vendor/FX/options adapters and source conflicts.
- [ ] M8: complete paper read-only broker contract/reconnect/dedup tests.
- [ ] M9: corporate actions, PIT factors, diagnostics, walk-forward, OOS, artifacts.
- [ ] M10: segments/ROIC/multiples/normalization/estimates/research linkage and DCF.
- [ ] M11: full options unit/expiry/coverage/history/portfolio acceptance.
- [ ] M12: Pine compatibility/equivalence/download/webhook, compilation honest.
- [ ] M13: trusted devices, production bootstrap, forced MFA, concurrency/security.
- [ ] M14: all ten monitoring dashboards and real metrics/probes.
- [ ] M15: PostgreSQL and complete objects backup/verification/isolated restore.
- [ ] M16: production images/environment/admin/CORS/cookies/rollback smoke.
- [ ] CI: every critical test/build/security/report/backup gate blocks deployment.
- [x] Operations: bounded watchdog code, three tests and live observe-only check.
- [x] Operations: hidden background watchdog started and healthy observations verified.
- [ ] Operations: background watchdog startup and one-pass release scripts.
- [ ] Release: make release-candidate and PowerShell command pass all 27 stages.
- [ ] Handoff: seven fictional import templates and onboarding/deploy/smoke scripts.
- [ ] Handoff: all required runbooks, matrix, exact external blockers and commands.
- [ ] Final: every applicable gate green, verified commit pushed, services left running.
