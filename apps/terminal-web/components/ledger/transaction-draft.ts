import type { LedgerTransaction } from "./contracts";

export const amendmentFields = [
  ["trade_date", "Trade date", "date"],
  ["settle_date", "Settlement date", "date"],
  ["quantity", "Quantity", "decimal"],
  ["price", "Price", "decimal"],
  ["commission", "Commission", "decimal"],
  ["fee", "Fee", "decimal"],
  ["tax", "Tax", "decimal"],
  ["fx_rate_to_base", "Recorded FX", "decimal"],
] as const;

export type AmendmentField =
  | (typeof amendmentFields)[number][0]
  | "amount"
  | "notes";
export type TransactionDraft = Record<AmendmentField, string>;

export function transactionDraft(
  transaction: LedgerTransaction,
): TransactionDraft {
  return {
    trade_date: transaction.trade_date,
    settle_date: transaction.settle_date ?? transaction.trade_date,
    quantity: transaction.quantity,
    price: transaction.price,
    commission: transaction.commission,
    fee: transaction.fee,
    tax: transaction.tax,
    fx_rate_to_base: transaction.fx_rate_to_base,
    amount: transaction.gross_amount,
    notes: transaction.notes ?? "",
  };
}

export function changedFields(
  transaction: LedgerTransaction,
  draft: TransactionDraft,
): Partial<TransactionDraft> {
  const original = transactionDraft(transaction);
  const result: Partial<TransactionDraft> = {};
  for (const key of Object.keys(original) as AmendmentField[]) {
    if (draft[key] !== original[key]) result[key] = draft[key];
  }
  return result;
}

export function securityMovement(transaction: LedgerTransaction): boolean {
  return (
    Boolean(transaction.symbol) &&
    ["BUY", "SELL", "SHORT", "COVER", "TRANSFER_IN", "TRANSFER_OUT"].includes(
      transaction.type,
    )
  );
}

export function revisionFieldChanges(
  before: Record<string, unknown>,
  after: Record<string, unknown>,
): Array<{ field: string; before: string; after: string }> {
  return Object.keys({ ...before, ...after })
    .filter((key) => JSON.stringify(before[key]) !== JSON.stringify(after[key]))
    .map((field) => ({
      field,
      before: String(before[field] ?? "--"),
      after: String(after[field] ?? "--"),
    }));
}
