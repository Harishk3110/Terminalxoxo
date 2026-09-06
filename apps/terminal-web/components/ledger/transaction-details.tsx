import { Badge, number, timestamp } from "../ui";
import type { LedgerTransaction } from "./contracts";

export function TransactionDetails({
  transaction,
}: {
  transaction: LedgerTransaction;
}) {
  const fields: [string, string | null | undefined][] = [
    ["Portfolio", transaction.portfolio_id],
    ["Account", transaction.account_id],
    ["Instrument", transaction.instrument_id],
    ["External reference", transaction.external_reference],
    ["Broker execution reference", transaction.broker_execution_id],
    ["Source file", transaction.source_file_id],
    ["Strategy", transaction.strategy_id],
    ["Thesis", transaction.thesis_id],
    ["Created by", transaction.created_by],
    ["Creator provenance", transaction.creator_state],
    ["Source", transaction.source],
    ["Reconciliation", transaction.reconciliation_state],
  ];
  return (
    <section aria-label="Transaction audit details">
      <dl className="ledger-totals ledger-audit-fields">
        <div>
          <dt>Net amount / {transaction.currency}</dt>
          <dd>{number(transaction.net_amount, 8)}</dd>
        </div>
        <div>
          <dt>Source-currency cash in base</dt>
          <dd>{number(transaction.net_base_value, 8)}</dd>
        </div>
        <div>
          <dt>Total cash effect in base</dt>
          <dd>{number(transaction.net_cash_base, 8)}</dd>
        </div>
        <div>
          <dt>Trade timestamp / SGT</dt>
          <dd>{timestamp(transaction.trade_timestamp)}</dd>
        </div>
        <div>
          <dt>Timestamp provenance</dt>
          <dd>
            <Badge>{transaction.trade_timestamp_state}</Badge>
          </dd>
        </div>
        <div>
          <dt>Cash effect</dt>
          <dd>
            <Badge>{transaction.cash_effect_state}</Badge>
          </dd>
        </div>
        {fields.map(([label, value]) => (
          <div key={label}>
            <dt>{label}</dt>
            <dd>{value ?? "Not recorded"}</dd>
          </div>
        ))}
        <div>
          <dt>Created / SGT</dt>
          <dd>{timestamp(transaction.created_at)}</dd>
        </div>
        <div>
          <dt>Updated / SGT</dt>
          <dd>{timestamp(transaction.updated_at)}</dd>
        </div>
      </dl>
      <div className="ledger-table-scroll">
        <table className="ledger-table" aria-label="Transaction cash legs">
          <thead>
            <tr>
              <th scope="col">Currency</th>
              <th scope="col">Economic cash effect</th>
              <th scope="col">Base cash effect</th>
            </tr>
          </thead>
          <tbody>
            {transaction.net_cash_by_currency.map((leg) => (
              <tr key={leg.currency}>
                <th scope="row">{leg.currency}</th>
                <td>{number(leg.amount, 8)}</td>
                <td>{number(leg.base_amount, 8)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {transaction.net_cash_by_currency.length === 0 && (
        <div className="ledger-loading">No replayed cash legs</div>
      )}
      <dl className="ledger-methodology">
        <dt>Net amount basis</dt>
        <dd>{transaction.net_amount_basis}</dd>
        <dt>Timestamp treatment</dt>
        <dd>{transaction.trade_timestamp_usage}</dd>
      </dl>
      {transaction.context_warnings.map((warning) => (
        <div key={warning} className="ledger-error" role="status">
          {warning}
        </div>
      ))}
    </section>
  );
}
