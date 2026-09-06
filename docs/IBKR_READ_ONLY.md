# IBKR Paper Read-Only Boundary

The active outbound reader is services/local-agent/broker_reader.py. It uses
ib_async with readonly=True and only account updates, positions and execution
history. It rejects non-loopback hosts, non-paper ports (allowed: TWS 7497,
Gateway 4002) and accounts without the DU paper prefix. The selected account and
reported base currency must match. The user's broker password is never stored.

Pair from Data Drop's broker-enabled agent controls. The scoped token is stored
in the operating-system credential vault. Broker snapshots are bound to a
portfolio scope; revocation, account mismatch and replay protections are tested.
The reader uploads snapshots, cash, FX, positions and observed fills only.
It has no order placement, transmission, amendment or cancellation API.

Broker Monitor keeps reported PAPER NAV separate from internally calculated NAV
and reference performance. Snapshot/agent freshness must both satisfy the live
read-only window. Offline last-known balances remain labelled, not live. Reported
prices use account-snapshot time rather than asserting an exchange tick time.

Importing an observed fill into the internal ledger requires explicit approval,
transaction type, FX and rationale. That records history; it never repeats the
broker trade. Corrected/voided internal entries reconcile through audited revisions.
Hedges, signals, proposed trades and manual tickets remain research/review output.

Run corepack pnpm security-check to scan application source for forbidden broker
action methods. Mocked reader, scope, replay, fill import and reconciliation tests
exist; actual TWS/Gateway connectivity is unverified until the user's Paper
account, permissions and running local agent are configured.
