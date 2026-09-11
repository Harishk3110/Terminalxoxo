# PostgreSQL And Object Backup

The managed backup command creates a sensitive, unencrypted local ZIP. Keep the
destination on private storage. The acknowledgement flag is mandatory. Database
rows include password hashes, sessions and encrypted provider records; the separate
configuration export deliberately excludes secrets. Preserve deployment secrets
in the existing secret manager, not in Git. Cluster roles are not exported.

The database dump and ordered row hashes use the same exported PostgreSQL
repeatable-read snapshot. PostgreSQL documents this mechanism in
[pg_dump](https://www.postgresql.org/docs/16/app-pgdump.html). All application tables
are compared after restoration, including exact JSON-serialized numeric values.
The configured object bucket is inventoried, including raw, curated,
reports, model artifacts and unreferenced retained objects. Database references
must match the archived hashes and sizes. Objects are conditionally downloaded,
hashed and checked against an unchanged final inventory. Concurrent bucket
changes fail the attempt; pause ingestion before retrying. This is not a claim
of a distributed transaction across PostgreSQL and S3.

Only `health/readiness.txt`, `health/report-worker.txt` and `health/probe.txt`
are excluded and listed explicitly in the manifest. These transient write/read
probes are recreated by running services. Other files, including other keys under
`health/`, remain included. A database reference to an excluded key fails validation.

## Windows Local Stack

From the repository root, with the existing Compose environment and PostgreSQL
container running:

```powershell
$python = '.venv-sprint/Scripts/python.exe'
$connection = @('--env-file', '.env.compose.local', '--database-host', '127.0.0.1', '--s3-endpoint', 'http://127.0.0.1:9000', '--pg-tools-container', 'knk-final-local-postgres-1')
& $python -m infrastructure.scripts.managed_backup backup @connection --destination infrastructure/backups --retention-days 30 --acknowledge-unencrypted
if ($LASTEXITCODE -ne 0) { throw 'Backup failed' }
$receipt = Get-Content infrastructure/backups/latest-backup.json -Raw | ConvertFrom-Json
$archive = Join-Path infrastructure/backups $receipt.archive
& $python -m infrastructure.scripts.managed_backup verify --archive $archive
if ($LASTEXITCODE -ne 0) { throw 'Verification failed' }
& $python -m infrastructure.scripts.managed_backup restore-test @connection --archive $archive --sha256 $receipt.sha256 --acknowledge-unencrypted --acknowledge-trusted-source
if ($LASTEXITCODE -ne 0) { throw 'Restore test failed' }
```

`scripts/backup.ps1 -Action backup` forwards subsequent arguments to the same
command. No credentials appear in process arguments or success receipts.
For a managed server, omit the local host/endpoint overrides and container flag;
install matching `pg_dump`/`pg_restore` tools and supply the private environment
file or process environment. TLS connection options are preserved.

## Make Commands

`make backup`, `make verify-backup` and `make restore-test` use the managed command.
Set `PYTHON`, `BACKUP_ARGS`, `BACKUP_ARCHIVE` and `BACKUP_SHA256` as appropriate.
`BACKUP_ARGS` contains the connection settings and explicit acknowledgement flags.
The old local SQLite commands remain available as `make backup-sqlite`,
`make verify-backup-sqlite`, and `make restore`.

## Restore Safety

Restore tests require the expected checksum from a trusted receipt and an explicit
trusted-source acknowledgement. PostgreSQL dumps execute SQL during restoration;
checksums establish integrity, not trust in an arbitrary third-party dump.
See [pg_restore](https://www.postgresql.org/docs/16/app-pgrestore.html).

Every restore creates a random `knk_restore_<id>` database and `knk-restore-<id>`
bucket. Existing resources are never emptied or reused. The restore is one
transaction with failure-on-error, followed by table hashes, object hashes,
metadata, inventory counts, ACL/policy checks and anonymous access rejection.
Success writes `latest-restore.json`. Failed/verified isolated resources remain
for inspection and deliberate cleanup. Do not point the active application at
these test resources.

Offline `verify` checks archive structure, inventory and hashes; it does not claim
that PostgreSQL restored successfully. That is a separate gate. Temporary archives
are published only after verification. `latest-backup-attempt.json` records failed
attempts without removing previous archives. `retain_until` is recorded according
to `--retention-days`; this command never automatically deletes backups. Limits:
20 GB expanded data, 100,000 members, 25 MB manifest, 30-minute PostgreSQL tool run.

## Observability And Tests

Compose mounts the backup directory read-only into the API. System Health shows
the last receipt and labels it as a recorded verification, not a fresh checksum
probe. A newer failed/incomplete attempt cannot display the older backup as healthy.
`knk_backup_state` exposes bounded state labels; Prometheus evaluates missing,
stale and failed-backup alerts. Alert delivery still requires an Alertmanager
destination; local rule evaluation is not external notification delivery.

```powershell
& $python -m pytest tests/sprint/test_managed_backup.py tests/sprint/test_backup_health.py tests/sprint/test_backup_archives.py
$env:KNK_MANAGED_BACKUP_TEST_ENV = '.env.compose.local'
$env:KNK_TEST_PG_TOOLS_CONTAINER = 'knk-final-local-postgres-1'
& $python -m pytest tests/integration/test_managed_backup.py
```

The real integration test creates isolated fixtures and proves snapshot consistency
under a concurrent write, all object classes, private restoration and exact decimals.
Without its explicit environment it is skipped, not certified as an integration pass.
