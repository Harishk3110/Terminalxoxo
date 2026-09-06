# Trade Monitor

Route /trade-monitor. Manual and approved file ledger events appear with trade
date, event type, symbol, quantity, price, currency, source, charges and review
state. The browser records all supported ledger types including FX conversion,
splits, spinoffs and explicit corrections.

Each write retains transaction linkage, external reference, source file,
rationale and optional validated thesis/strategy IDs. Pre/post beta and risk
snapshots use the same valuation service at trade-date close. Missing-thesis
and negative-cash warnings accompany risk-policy breaches. This is an
after-recording control, not order preclearance.

Review states: REQUIRES_REVIEW, REVIEWED, FLAGGED. A nonempty note is required;
reviews append audit records rather than deleting a trade. No order
transmission, cancellation, amendment or broker credential entry exists.
The optional ib_async reader records paper executions without placing orders.
Broker Monitor approves mapped stock/ETF fills into the ledger using an explicit
trade-date FX rate and rationale. Execution IDs deduplicate approvals. Missing
or foreign-currency commissions and unsupported contracts require reconciliation.
Actual paper-account connectivity has not been verified on this machine.
