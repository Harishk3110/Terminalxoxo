# Broker Agent

The old `services/broker-agent` demo service is retired. Its dummy account,
pairing and snapshot interfaces are disabled and must not be presented as a
working broker connection.

The current paper-account reader is `services/local-agent/broker_reader.py`.
It connects only to loopback paper ports with an explicit paper account and a
nonzero client ID, requests read-only account data and uploads scoped snapshots.
Fills still require explicit internal-ledger approval. It has no execution API.

See [Local Data Agent](LOCAL_DATA_AGENT.md) for installation and pairing. Tokens
are revocable and stored in the OS credential vault. No TWS password is stored.
Real TWS/Gateway connectivity remains unverified until the operator supplies a
paper session; SDK-shaped contract tests do not certify live connectivity.
