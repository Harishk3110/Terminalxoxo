# Demo to Connected Data

Start with the separately seeded KNK_MAIN book. Opening capital is exactly
SGD 70,000 and its deterministic prices/trades/FX reconcile. The old reference
book is retained. The seed ends on 2026-09-04; later use naturally becomes stale.

For permitted external data, upload files, inspect mapping/units/date/symbol,
validate, add licence note and approve. Review Source Preferences and
provenance. The accepted file can replace the selected demo source without
deleting it. Imported prices remain FILE IMPORT, not live. Stale imported
prices remain selected until a new observation or explicit override is approved.

Record real manual transactions only with their actual amounts, currency,
charges and recorded FX. Reconcile funding and opening positions before
treating the book as an operating account. Do not mix a demonstration opening
book with a real brokerage account without explicit reconciliation.

The local agent requires a scoped pairing and OS credential vault. IBKR Paper
uses the optional services/local-agent/broker_reader.py, with a broker-scoped
pairing, explicit paper account/base currency and loopback TWS/Gateway. This
connector still needs verification against the user's account; the old
broker agent is a demo stub. FRED and other configured providers require their
own credentials/licences. No user or administrator password belongs in the
file watcher. Nothing in this application transmits broker orders.
