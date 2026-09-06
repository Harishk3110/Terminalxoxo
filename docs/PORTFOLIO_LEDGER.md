# Portfolio Ledger

Default code KNK_MAIN; SGD 100,000 explicit opening DEPOSIT on 2026-06-03.
The previous reference portfolio and its transactions are retained unchanged
and are no longer the default. The managed demo's original 70K contribution is
preserved with an audited amendment to 100K, not overwritten. Custom, real or
previously amended contributions are not automatically corrected.

Supported events: DEPOSIT, WITHDRAWAL, BUY, SELL, SHORT, COVER, DIVIDEND,
INTEREST, COMMISSION, FEE, TAX, FX_CONVERSION, SPLIT, REVERSE_SPLIT, SPINOFF,
MERGER, TRANSFER_IN, TRANSFER_OUT, OTHER_ADJUSTMENT.

API: POST /api/v1/operations/transactions. Fields include trade/settlement date,
symbol, quantity, native price/currency, gross amount, transaction FX, fees,
commission, tax, multiplier, account, external reference, rationale and metadata.
FX_CONVERSION metadata requires to_currency and to_amount; SPLIT needs ratio;
SPINOFF needs child_symbol and cost_allocation; corrections require reason and
CREDIT/DEBIT direction. Thesis and strategy IDs are validated when supplied.

Posting replays the entire chronological ledger, including later transactions.
Oversales and overcovers fail. Imported batches use a savepoint and roll back
together if any ledger event fails. External references are deduplicated within
portfolio and source; file rows without references use file hash plus row index.
Positions cannot be directly edited.

Trade events and counterfactual trade-date-close pre/post snapshots accompany
writes. These snapshots are not pre-execution real-time risk checks.
Reset requires RESET KNK_MAIN DEMO and administrator access, including local-demo;
it archives the prior demo profile and retains transactions, files and history.
