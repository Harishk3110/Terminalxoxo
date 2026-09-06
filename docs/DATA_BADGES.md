# Data Badges and Provenance

DEMO DATA: deterministic synthetic provider or reference-ledger fixture.
USER PROVIDED: imported file with recorded hash, mapping and user-supplied licence; not independently verified.
CALCULATED: derived result; does not make its inputs live or verified.
PAPER: broker mode boundary, not a connected balance or executable ticket.
ASSUMPTIONS: editable scenario/model inputs.
OBSERVED: current service probe.
NOT_CONFIGURED / OFFLINE / NOT_VERIFIED / provider_required: missing credentials, failed connection or absence of a current probe.

Panel footers show source, quality and observation date. Info/context details show full timestamps and warnings. Run inspectors show data timestamp separately from creation/start/completion. Timestamp formatting normalizes timezone-less database timestamps as UTC and displays SGT.

Changing a provider configuration does not relabel existing demo observations. Provider states and per-series provenance are kept separate. API latency is measured at the client; it is not a hardcoded 24ms.

Limit: some source footers represent several series and therefore say per-series or mixed; inspect individual records for exact provenance.
