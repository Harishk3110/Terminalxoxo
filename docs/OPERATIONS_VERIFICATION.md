# Operations Verification

The API probes database and object storage for readiness; a failed required probe
returns HTTP 503. Redis availability is reported separately. Terminal health uses
actual provider observations, worker heartbeats, file-agent/broker snapshots,
valuation input timestamps and the last verified backup receipt. A configured
provider is not a successful connection; old observations expire.

Analytical jobs have an atomic QUEUED-to-RUNNING claim shared by the API-launched
process and optional SQL queue dispatcher. Duplicate claims do not execute twice.
Per-run process heartbeats expire after 60 seconds. Stopped/crashed processes are
not inferred alive from persisted RUNNING jobs. The data dispatcher only handles
the explicit provider-health-check template and records each observed response;
unknown jobs fail. Disabled/unconfigured providers are skipped and zero probes is
reported as such. File/market backfill imports still run through private API routes.

Compose builds both dispatchers from the API image so they use the same engines,
provider libraries and shared object store. The older standalone entrypoints are
compatibility launchers, not synthetic completion loops. For local operation:

```powershell
.\.venv-sprint\Scripts\python.exe services/worker-data/app/main.py --daemon
.\.venv-sprint\Scripts\python.exe services/worker-quant/app/main.py --daemon
```

These are optional for ordinary API-launched analyses; queued provider checks need
the data dispatcher. Set the same database/object-store configuration as the API.
No automatic stale-job retry is performed. Cancel a failed analytical run and
create a new run with explicit inputs. Dispatcher heartbeats are process liveness,
not evidence that a provider connection or calculation succeeded.

Sign-in attempts are persisted and throttled after 10 failed account attempts or
100 failed peer-IP attempts in 15 minutes. TOTP failures are recorded. This is a
database-backed soft limit, not a replacement for edge rate limiting. Proxy IPs
are not blindly trusted. Mutation origins use `KNK_ALLOWED_ORIGINS`; cross-site
browser mutations are rejected. Nonbrowser clients may omit Origin. HTTP-only,
SameSite=Strict session cookies and per-user all-session revocation remain enforced.
Hosted origins must be explicitly added to the JSON allowlist; credentials stay
server-side. Production TLS, secret rotation and edge controls are deployment tasks.

The dangerous global demo reset now rejects without deleting records. Supported
portfolio archive/correction workflows remain separate and retain history.

Backups: see LOCAL_BACKUP_RECOVERY.md. Local unencrypted backup of the active
database and 316 object files was verified and restored to an isolated directory.
The archive SHA-256 is
`c1dfd125fece565e18f1865317df286bd728950fe80ade48732b935f02c1a0b4`.
No live data was overwritten. Archives and restored private content remain ignored.

The local API was restarted and returned HTTP 200 readiness; an anonymous
investment endpoint returned 401. Data/quant dispatcher healthchecks returned
fresh RUNNING observations. `scripts/verify_local_recovery.py` compared ten
business-table snapshots against the isolated restore, including 16 ledger
transactions, nine transaction details, two dataset versions, one saved analysis,
two notes and three investment theses; all matched. These counts describe retained
local records, not externally verified investment performance.

The standalone report renderer rejects its former unauthenticated hardcoded
exports; Compose probes its readiness endpoint, which deliberately returns 503.
Private API XLSX exports remain separate. Full reporting packages are incomplete.

Docker daemon availability, hosted deployment, automatic scheduling/retention,
encrypted remote copies and full PPTX/PDF rendering are not certified by unit tests.
Local Compose validation also stops because `POSTGRES_PASSWORD` is unset. Supply
deployment credentials through the ignored environment configuration; do not
replace existing database or object-store credentials with generated placeholders.
