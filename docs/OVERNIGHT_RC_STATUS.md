# Overnight Release Status

Controlling directive: final overnight continuation, 2026-09-12 SGT.
Starting commit: 3466694fd7513bf1c494419ab0fb09767748cd0e.
Branch: main. Remote: https://github.com/Harishk3110/Terminalxoxo.git.
Recovery tag: pre-overnight-rc-closure, pushed before code changes.

M1 pipeline: owned SQL report jobs, pinned input, write-once outputs, authenticated
XLSX/PPTX/PDF downloads and observed worker health/metrics are implemented. All 16
kind/format combinations produce real files in tests. Financial-model report depth
and rendered artifact review remain PARTIAL; these are source-pinned review exports.

Next milestone: M2 static cleanup, then full browser closure. First unchecked report
subtask: complete financial model/deck content and actual rendered-artifact review.
Next command: `.venv-sprint/Scripts/python.exe -m ruff check services/api/app --fix`.

Current evidence:
- Full backend rerun: 959 passed / 13 warnings / 294.49s; 86.5700% statement coverage.
- Subsequent native-chart report selection: 34 passed. Eight new report/watchdog
  modules passed scoped strict mypy; changed modules passed Ruff.
- Full frontend: 240 initially; three new report-control tests also passed.
- Workspace TypeScript/lint and Node 22 local/Docker production builds passed.
- Report browser workflow passed twice, including the mobile resize fix and
  persisted date/format; screenshots at 1440px/390px were inspected.
- Isolated PostgreSQL/MinIO report smoke passed: three formats, hashes, owned
  download, anonymous rejection and persistence after worker termination.
- Seven migrations: SQLite lifecycle and PostgreSQL fresh/latest roundtrip passed.
- Watchdog: three tests and live observe-only pass; background startup pending.

Global Ruff remains 218 errors; mypy baseline remains 1,260 errors in 56 files.
The first full backend attempt used incompatible test/HTTPS-cookie configuration:
949 passed / 3 failed. Correct local-demo auth selection passed all 47; no runtime
security checks were weakened. Full browser zero-failure gate is still open.

Ten long-running Docker services, including reports, are healthy; MinIO init exited
0. Images have been rebuilt with the report/UI changes and await final refresh.
Local URL: http://127.0.0.1:3001/overview (private login, not hosted).
Existing SQLite, local objects, `.env`, Compose credentials and volumes are preserved.
PostgreSQL backup/restore, all dashboards, release runner and later domain gates
remain open. No live provider or cloud deployment is certified. No execution added.
