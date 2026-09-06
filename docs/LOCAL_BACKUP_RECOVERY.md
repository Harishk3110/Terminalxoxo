# Local Backup and Recovery

The local SQLite backup uses SQLite's online backup API, not a copy of an active
database file. It includes the local object store and a manifest of SHA-256 hashes,
file sizes and all SQLite table row counts. Verification checks inventory, hashes,
SQLite integrity, foreign keys and row counts. Restores only accept a new target
directory and recheck every restored file. No retention deletion is automatic.

Archives contain private research, ledger data, authentication hashes and any
stored integration material. They are **not encrypted**. Store them in a private,
access-controlled directory on encrypted storage. POSIX mode 0600 does not set
Windows ACLs; verify inherited Windows permissions. Never commit or upload them.
The explicit acknowledgment flag prevents silently creating an unencrypted archive.
Environment files and external provider credentials are not separately collected.

From `C:\Dev`:
```powershell
.\.venv-sprint\Scripts\python.exe infrastructure/scripts/backup.py --database knk_terminal.db --objects .knk-object-store --destination infrastructure/backups --acknowledge-unencrypted
.\.venv-sprint\Scripts\python.exe infrastructure/scripts/verify_backup.py <archive.zip>
.\.venv-sprint\Scripts\python.exe infrastructure/scripts/restore.py <archive.zip> --target C:\Dev\logs\isolated-restore
```

Pause imports/calculations for cross-store consistency. The database snapshot is
transactionally consistent, but the filesystem and database are not one atomic
transaction. Files changing during copy abort verification. The archive size limit
is 20 GB expanded. PostgreSQL/remote object stores require their native backup
systems; this command does not pretend to back them up.

After an isolated restore, inspect the recovered ledger and object hashes before
changing any runtime database configuration. Live data is never overwritten by
the restore command. Keep older archives until a new recovery has been tested.

System Health reads `latest-backup.json` in `KNK_BACKUP_DIR` (default
`infrastructure/backups`). It reports the last verification, not a new checksum
scan on each HTTP request. Missing/changed archives fail, and receipts older than
24 hours are stale. Scheduled runs, off-machine encrypted copies and managed
PostgreSQL recovery are not configured by this local procedure.
