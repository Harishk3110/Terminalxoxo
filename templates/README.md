# Fictional Import Templates

Every value in these files is fictional. `SAMPLE_EQ` is not a real security.
The January 2026 dates are historical examples, not current observations. The
options are expired historical contracts, not a current tradable chain. `ACTUAL`
demonstrates a data classification only; it does not authenticate these examples.

Do not import these transactions, prices or FX marks into KNK_MAIN. For a dry run,
use an isolated demonstration portfolio/database and a fictional SGD security
named SAMPLE_EQ in its security master. For real onboarding, replace every sample
row with your authorized source export and match each security/currency first.
Keep the source date and units; never redate a stale observation to make it current.

| File | Mapping profile | Consumer |
| --- | --- | --- |
| positions.csv | GENERIC_POSITIONS | Reconciliation reference only; no position creation |
| transactions.csv | GENERIC_PORTFOLIO_TRANSACTIONS | Reviewed ledger import; changes cash and holdings |
| prices.csv | GENERIC_OHLCV | Valuation and research price history |
| fx.csv | GENERIC_FX_HISTORY | Dated currency conversion marks |
| options_chain.csv | GENERIC_OPTIONS_CHAIN | Saved options analysis; no ledger or broker orders |
| fundamentals_long.csv | GENERIC_FUNDAMENTALS_LONG | Explicit metric/unit statement inputs |
| fundamentals_wide.csv | GENERIC_FUNDAMENTALS_WIDE | Numeric metric columns sharing a stated scale |

## Fields

- `symbol` (or `underlying` in the options profile): exact security-master symbol.
  `currency` must match that security.
- `date`: observation day, YYYY-MM-DD. `timestamp`: timezone-aware observation
  instant. Neither means the time the file was uploaded.
- `quantity`: units held or transacted. `average_cost`: native-currency unit cost
  in a reconciliation reference. Position files never override the ledger.
- `transaction_type`: supported ledger type. This example includes a contribution,
  purchase and partial sale. Settlement cannot precede `trade_date`.
- `price`, `amount`: native unit price and gross amount before charges. Trade
  amount must reconcile to quantity times price times contract multiplier.
- `fx_rate_to_base`: base-currency units per native-currency unit. Use 1 for a
  base-currency transaction. `fee`, `commission`, `tax`: separate native amounts.
- `external_reference`: unique source identifier for duplicate detection. Do not
  recycle the fictional references for actual transactions.
- `open`, `high`, `low`, `close`: consistent, positive OHLC marks. `volume`: units
  traded; blank means missing, not zero. Supply the source's adjustment convention.
- `base_currency`, `quote_currency`, `rate`: one base unit equals `rate` quote
  units. The example 1.30 means USD 1 = SGD 1.30; it is not a verified market rate.
- `option_symbol`: unique contract identifier. `expiry` plus `expiry_time_utc`
  specifies the UTC expiration clock. `strike` is native currency; `right` is
  CALL/PUT, `multiplier` is units per contract, `exercise_style` is explicit.
- `iv_unit`: DECIMAL or PERCENT; 0.25 DECIMAL means 25%. Blank IV is unknown.
  `bid`, `ask`, `last` are native quoted premiums; ask cannot be below bid.
  `volume`, `open_interest` count contracts. Optional `oi_change` is signed.
  Optional delta/gamma/theta/vega/rho require documented `greek_units=STANDARD`;
  this template leaves them absent and uses UNSPECIFIED, not fabricated Greeks.
- `period`, `frequency`: fiscal period and ANNUAL/QUARTERLY classification.
  Quarterly cash flows must be standalone quarters, not cumulative year-to-date.
- `metric`, `value`: long-format metric name and numeric value. Wide-format
  metric columns are numeric; do not add free-text columns as financial metrics.
- `unit`, `scale`: native currency or SHARES, and numeric multiplier. A value of
  100 with scale 1000000 means 100 million units. Long format separates share
  counts from currency amounts. Wide-format columns share the specified scale.
- `actual_estimate`: ACTUAL or ESTIMATE, kept distinct. `report_date`: source
  publication/availability date. An import alone does not establish point-in-time
  verification, licensing or independent filing validation.

## Import Review

Select the matching profile in Data Drop, inspect column mappings and defaults,
resolve filename/content conflicts explicitly, and run validation before approval.
Record the source, licence and observation date. Save the returned file/version ID
and inspect downstream results against that same version. Automatic first-import
approval is disabled. Never mix fictional rows with actual broker statements.

These seven files pass the repository's parser and profile normalization tests.
That verifies their format, not financial authenticity or live-provider readiness.
