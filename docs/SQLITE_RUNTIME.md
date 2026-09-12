# Local SQLite Runtime

The detached terminal at `http://127.0.0.1:3001/overview` uses PostgreSQL. These
requirements apply to local file-backed SQLite and isolated browser tests only.

File-backed SQLite uses write-ahead logging (WAL) so a research read does not
block a workspace save from committing. The connection pool configures WAL on
its synchronized first connection, checks the returned journal mode, and preserves FULL
synchronization, the default 5-second busy timeout, and automatic checkpoints.
In-memory SQLite and the PostgreSQL pool configuration are unchanged. This does
not eliminate writer/writer contention or make SQLite a multi-host database.

Creating an engine, importing application modules and requesting CLI help do not
open or create a database. Initialization completes before the first connection
is handed to a caller and runs again if the pool is disposed and recreated. A
failed WAL initialization closes its DBAPI connection and propagates the error.

## Required Version

SQLite 3.51.3 or newer is required. Fixed 3.50.7 and 3.44.6 maintenance branches
are also accepted. Earlier affected runtimes fail before a database is opened;
they do not silently enable vulnerable WAL behavior. See the upstream
[WAL-reset advisory](https://sqlite.org/wal.html#walresetbug).

Python's version alone does not identify its bundled SQLite. The verified local
runtime is the uv 0.12.13 managed CPython 3.12.13 build dated 2026-08-07, with
SQLite 3.53.1. CI installs the same uv/Python versions. An older uv download of
Python 3.12.13 bundled SQLite 3.50.4 and is not suitable.

```powershell
uv --version
uv python install 3.12.13
uv venv .venv-rc --python 3.12.13 --managed-python
uv pip install --python .venv-rc/Scripts/python.exe -r services/api/requirements.txt -r services/local-agent/requirements.txt -r requirements-dev.txt
.venv-rc/Scripts/python.exe -c "import sqlite3; print(sqlite3.sqlite_version)"
$env:PLAYWRIGHT_PYTHON = 'C:\Dev\.venv-rc\Scripts\python.exe'
```

Use uv 0.12.13 or newer. If a managed 3.12.13 installation predates the fixed
SQLite build, stop processes using that interpreter before reinstalling it with
`uv python install 3.12.13 --reinstall`. Do not replace an interpreter used by
the running watchdog. The existing `.venv-sprint` and `.venv-release` were
preserved; release verification now uses `.venv-rc` with the same 121 pinned
packages as the previous release environment.

The PowerShell release wrapper and `make` prefer `.venv-rc` when present. A
`PYTHON` override still takes precedence in `make`; activate a suitable runtime
or set the override explicitly when using another environment.

## Storage And Recovery

Keep SQLite on a local disk, not a network share. WAL creates `-wal` and `-shm`
sidecars; do not delete or copy them independently while the database is open.
Use `infrastructure/scripts/backup.py`, which uses SQLite's online backup API,
and restore into a separate directory. The regression suite verifies that
committed changes still in WAL survive this backup/restore path while another
connection holds an older read snapshot.

No active database, object store, credential file, or Docker volume was reset.
