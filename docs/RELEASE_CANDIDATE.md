# Local Release Checkpoint

This command verifies the existing private local-demo stack. It is not a cloud
deployment command, a data reset, or proof that unfinished domain requirements
are complete. Current acceptance status is in OVERNIGHT_RC_STATUS.md.

## Run

From the repository on the Windows release workstation:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/release-candidate.ps1 --list
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/release-candidate.ps1 --acknowledge-unencrypted
```

The Make equivalent is:

```sh
make release-candidate PYTHON=.venv-sprint/Scripts/python.exe RELEASE_ARGS="--acknowledge-unencrypted"
```

`scripts/overnight_release.ps1` and `scripts/overnight_release.sh` delegate to the
same one-pass runner. Python 3.12, Corepack, installed dependencies, Git, Docker,
and the existing `.env.compose.local` are prerequisites. The default PostgreSQL
tools container is `knk-final-local-postgres-1`; override it with `--pg-container`.
Use `--env-file` only for another explicitly local-demo configuration.

Native Excel integration currently requires installed Microsoft Excel on Windows.
The runner enables that integration explicitly. A platform-dependent skip is a
failed release gate, not an independent-recalculation pass.

The unencrypted-backup acknowledgement is mandatory: archives contain private
data and database credentials. Keep them local/private. Do not upload generated
archives, logs, databases, reports, screenshots, or environment files to GitHub.

## Gate Order

1. Environment validation.
2. Secret scan.
3. Python dependency check and frozen-lockfile pnpm installation.
4. SQLite migration tests and isolated PostgreSQL latest downgrade/upgrade.
5. First-party Python formatting.
6. Ruff.
7. Distribution-aware strict mypy.
8. Backend unit tests.
9. Backend integration tests, managed backup, and independent Excel recalculation.
10. Backend coverage, minimum 86.58%.
11. Frontend lint.
12. TypeScript.
13. Frontend unit tests.
14. Node 22 production frontend build.
15. Docker build.
16. Detached Docker startup with health waiting; no volume reset.
17. Observe-only stack health checks.
18. PostgreSQL/private-object report-generation smoke.
19. Full Playwright suite with one worker and zero retries.
20. Explicit visual comparison against reviewed local baselines.
21. Authentication/enrollment and terminal-only security tests.
22. No-execution scan.
23. Managed PostgreSQL/object backup.
24. Archive integrity verification.
25. Restore into a new database and a new private bucket only.
26. Real API/report-worker process restart with persisted ledger/NAV/report checks.
27. Validated build-evidence receipt.

## Evidence And Failure

Every invocation gets a new `logs/release-candidate/<UTC>-<id>/` directory.
`manifest.json` records the source-tree SHA-256, commit, branch, timestamps,
ordered states, exact command arguments, working directories, exit codes,
command-log hashes and test-result hashes. JSON is replaced atomically.

The first nonzero exit stops execution. Later gates remain `NOT_RUN`; they are
not labelled passed or skipped. Source edits during the run fail the checkpoint.
Each command has a bounded timeout; timeout cleanup targets only that command's
process tree. There are no automatic test retries or automatic snapshot updates.

Pytest XML receipts must contain executed cases and no failures, errors or skips.
Browser JSON must contain passed cases with no unexpected, skipped or flaky
results and no global errors. Full and visual browser receipts have separate
paths. Missing receipts cannot turn a zero process exit into a pass.

The final evidence check revalidates the exact gate/command contract and all
preceding log/result hashes. Until it succeeds, no BUILD_EVIDENCE.md is generated
for that checkpoint. This supplements, rather than replaces, domain acceptance
and direct financial/report/screenshot review.

Migration and restart tests allocate fresh PostgreSQL database names. Restart
tests use separate loopback API/worker processes and isolated local report objects;
the live terminal and its database are not restarted or used as test fixtures.
The separate report/backup gates verify real private MinIO storage.

Latest executed checkpoint on 2026-09-12 SGT:
`20260911T193027Z-5985dadc`. Gates 1-6 passed, including 16 migration tests.
Gate 7 returned 1: whole-repository strict types remain open. Gates 8-27 were
not run in that invocation. Do not treat this checkpoint as a release pass.
