# Local Data Agent

Implementation: services/local-agent/agent.py. Outbound-only polling watcher;
no inbound HTTP listener, tunnel, broker password or administrator token.
Pairing tokens are one-time-issued, scoped, hashed server-side and revocable.
Windows uses keyring WinVaultKeyring; no plaintext credential fallback.

Install in an isolated environment:
python -m venv .venv-local-agent
.venv-local-agent\Scripts\python -m pip install -r services/local-agent/broker-requirements.txt
Use that environment's python for the commands below. The optional broker
dependency pins tzdata separately from the API environment.
Set KNK_DATA_DROP_ROOT to a chosen directory and KNK_TERMINAL_API to the API
origin. In Data Drop create a pairing code, then run:
python services/local-agent/agent.py pair
The code is entered without echo and the resulting token goes to the OS vault.
Run the watcher with: python services/local-agent/agent.py run
For explicit local development add --url http://127.0.0.1:8000
--allow-loopback-http. Non-loopback HTTP and URL credentials are rejected.

Folders: inbox/koyfin, inbox/prices, inbox/fundamentals, inbox/macro,
inbox/portfolio, inbox/positions, inbox/transactions, inbox/options, inbox/custom,
processing, review, processed/YYYY/MM, rejected, quarantine and logs.
The root is configured, never a hardcoded user's path. Files must be
unchanged across scans before hashing and upload. A SQLite queue retains state;
server hash deduplication handles retry uncertainty. Imported files are archived;
rejected and quarantined files retain separate destination folders. Logs omit
token/header contents.

Archive intent is committed to the queue before moving the file. ARCHIVE_PENDING
retains the original path, content hash and planned destination until the local
hash and server acknowledgement are verified. A network failure or interrupted
rename can resume after restart without selecting a different month's folder.
Missing or modified content is never marked LOCAL_ARCHIVED. Do not manually edit
the queue or replace archive contents to clear a retry. Existing queue databases
gain the nullable archive journal column without deleting their records.

Status synchronization requests the pending queue's file IDs in batches of at
most 100. It is not limited to the API's latest 500-file listing. Server ownership
and scope checks apply to every lookup. Unknown or revoked credentials cannot
read statuses. Missing remote records retain their local state and enter retry
backoff without blocking other returned files. Unexpected response IDs, duplicate
IDs and content-hash changes cannot advance a queued file's state.

Commands pause/resume use a PAUSE marker. rescan performs a bounded scan.
The watcher checks every five seconds and retries uploads with capped backoff.
First mapping/import approval remains in the browser. Failed raw-storage writes
retry the original hash/file identity. Automatic profile import, remote upgrades
and a Windows installer/service are not implemented. The existing
services/broker-agent is retired and disabled, not the new reader.

## Optional Paper Account Reader
In Data Drop enable the read-only broker scope before generating the pairing
code. The token is bound to the current portfolio ID; resetting that portfolio
requires new pairing. Configure TWS/Gateway API access in read-only mode on
loopback, paper port 7497 or 4002, with an explicit DU paper account:

```powershell
.\.venv-local-agent\Scripts\python.exe services/local-agent/broker_reader.py --account DU123456 --currency SGD --url http://127.0.0.1:8000 --allow-loopback-http
```

Replace the sample account and confirm its actual base currency. The client
sets readonly=True, retrieves balances, positions and executions, and posts
snapshots every 30 seconds. No live account, non-loopback broker host or live
port is accepted. Client IDs must be between 1 and 2147483647; ID 0 is rejected
before creating a broker client because it has special binding behavior in the
upstream library. A missing derivative multiplier is unavailable, not an assumed
one. It has no order-action calls. Unsupported contracts can be
shown as reported positions, but only mapped stock/ETF fills enter the ledger.
No TWS credentials or user password are stored in the agent. Actual connectivity
is unverified; mocked read-only transport and server rules are tested.

The development requirements include the pinned optional reader dependencies so
release typing and SDK-record contract tests do not omit this module. Production
reader installation should still use its separate local virtual environment.

Reference: [ib_async API](https://ib-api-reloaded.github.io/ib_async/api.html).

Reference: [keyring documentation](https://keyring.readthedocs.io/).
