# Portfolio-First Gap Audit

Date: 2026-09-06. Baseline: 6e707d3.

The approved terminal shell is retained. The operating priority is KNK_MAIN,
not a replacement visual design or repository.

## Findings

Measured baseline: portfolio endpoint 1916 ms, NAV SGD 134,311.65, four
positions and seven transactions. DB probe 0.6 ms, Redis OFFLINE, workers IDLE.
These are baseline observations, not current release metrics.

- The existing reference portfolio has SGD 70,000 metadata, but its opening
  contribution is a zero-quantity transaction with an implicit capital fallback.
- Historical trade prices and generated market history are unrelated. In
  particular, the D05 valuation creates an artificial large gain.
- The existing ledger deducts foreign trades from base-currency cash and does
  not support explicit currency conversion, short positions or full cash flows.
- Missing quotes are skipped and missing historical FX can become 1.0. This
  makes a complete NAV indistinguishable from a partial valuation.
- Portfolio analytics repeatedly load historical data and do not persist a
  complete immutable valuation input/output record.
- Overview is market-first. It lacks a reconciled P&L decomposition, trade
  events, valuation provenance, a source selector and linked operating desks.
- Upload preview/mapping/backtests exist, but there is no persistent file inbox,
  approved mapping profile, hash-level idempotency or market-price integration.
- The old broker agent exposes local HTTP demonstration endpoints; it is not an
  outbound folder watcher and does not securely pair or store credentials.
- Trade review, source comparison and integrated operating monitors are absent.
- Last measured browser health includes Redis OFFLINE; this must not be painted
  healthy. Broker/provider/backup states lack verified current heartbeats.

## Implementation Boundaries

Preserve existing accounts, transactions, uploads, raw objects and analytical
runs. Create a separate deterministic KNK_MAIN demonstration ledger and make it
the default. Any demo reset must be explicit, administrator-confirmed and scoped
to that portfolio, with an audit record. It must not reset authentication or
external datasets.

Use Decimal for financial amounts, retain native-currency cash, record all
source selections and fail a complete valuation when a required price or FX
rate is unavailable. Keep stale selected prices with warnings instead of
silently replacing them with demo data. Koyfin means permitted exported files,
not a direct or live Koyfin API integration.

The file agent will be outbound-only, scoped and revocable. Local HTTP may be
used only for explicit loopback development; non-loopback endpoints require
HTTPS. No broker execution capability may be added.

## Verification Plan

Focused ledger/NAV/source tests; API persistence and idempotency tests; file
classification, validation and agent tests; full backend regression; unit tests;
typecheck/lint/build; portfolio-first browser workflows and four desktop plus
mobile image checks. Docker and provider checks must report actual availability.
