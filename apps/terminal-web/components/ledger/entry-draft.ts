import type { PortfolioMetadata } from "./contracts";

export const transactionTypes = [
  "BUY",
  "SELL",
  "SHORT",
  "COVER",
  "DEPOSIT",
  "WITHDRAWAL",
  "DIVIDEND",
  "INTEREST",
  "COMMISSION",
  "FEE",
  "TAX",
  "TRANSFER_IN",
  "TRANSFER_OUT",
  "FX_CONVERSION",
  "SPLIT",
  "REVERSE_SPLIT",
  "SPINOFF",
  "MERGER",
  "OTHER_ADJUSTMENT",
] as const;
export type TransactionType = (typeof transactionTypes)[number];

export type EntryOptions = {
  portfolio: PortfolioMetadata;
  transaction_types: TransactionType[];
  currencies: string[];
  strategies: { id: string; name: string; state: string }[];
  theses: {
    id: string;
    title: string;
    instrument_id: string | null;
    state: string;
  }[];
};

export type EntryDraft = {
  transaction_type: TransactionType;
  transfer_mode: "CASH" | "SECURITY";
  trade_date: string;
  settle_date: string;
  trade_time: string;
  account_id: string;
  symbol: string;
  quantity: string;
  price: string;
  currency: string;
  amount: string;
  commission: string;
  fee: string;
  tax: string;
  contract_multiplier: string;
  fx_rate_to_base: string;
  external_reference: string;
  broker_execution_id: string;
  strategy_id: string;
  thesis_id: string;
  notes: string;
  child_symbol: string;
  ratio: string;
  cost_allocation: string;
  exchange_ratio: string;
  cash_per_share: string;
  cash_cost_allocation: string;
  to_currency: string;
  to_amount: string;
  adjustment_direction: "CREDIT" | "DEBIT";
  adjustment_reason: string;
};

export function newEntryDraft(
  day = new Date().toISOString().slice(0, 10),
): EntryDraft {
  return {
    transaction_type: "BUY",
    transfer_mode: "CASH",
    trade_date: day,
    settle_date: "",
    trade_time: "",
    account_id: "",
    symbol: "AAPL",
    quantity: "1",
    price: "",
    currency: "USD",
    amount: "",
    commission: "0",
    fee: "0",
    tax: "0",
    contract_multiplier: "1",
    fx_rate_to_base: "",
    external_reference: "",
    broker_execution_id: "",
    strategy_id: "",
    thesis_id: "",
    notes: "",
    child_symbol: "",
    ratio: "",
    cost_allocation: "",
    exchange_ratio: "",
    cash_per_share: "0",
    cash_cost_allocation: "0",
    to_currency: "SGD",
    to_amount: "",
    adjustment_direction: "CREDIT",
    adjustment_reason: "",
  };
}

export function entryMode(draft: EntryDraft) {
  const type = draft.transaction_type;
  const transfer = type === "TRANSFER_IN" || type === "TRANSFER_OUT";
  const trade = ["BUY", "SELL", "SHORT", "COVER"].includes(type);
  const action = ["SPLIT", "REVERSE_SPLIT", "SPINOFF", "MERGER"].includes(type);
  const income = type === "DIVIDEND" || type === "INTEREST";
  const expense = ["COMMISSION", "FEE", "TAX"].includes(type);
  const securityTransfer = transfer && draft.transfer_mode === "SECURITY";
  return {
    transfer,
    trade,
    action,
    income,
    expense,
    securityTransfer,
    security: trade || action || income || securityTransfer,
    priced: trade || securityTransfer,
    cashAmount: !trade && !action && !securityTransfer,
  };
}

export function entryPayload(draft: EntryDraft): Record<string, unknown> {
  const mode = entryMode(draft);
  const payload: Record<string, unknown> = {
    transaction_type: draft.transaction_type,
    trade_date: draft.trade_date,
    currency: draft.currency,
  };
  for (const key of [
    "settle_date",
    "account_id",
    "external_reference",
    "broker_execution_id",
    "strategy_id",
    "thesis_id",
    "notes",
    "fx_rate_to_base",
  ] as const) {
    if (draft[key].trim()) payload[key] = draft[key].trim();
  }
  if (draft.trade_time) {
    const time = new Date(draft.trade_time);
    if (!Number.isFinite(time.getTime()))
      throw new Error("Trade time is invalid");
    payload.trade_timestamp = time.toISOString();
  }
  if (mode.security && draft.symbol.trim())
    payload.symbol = draft.symbol.trim().toUpperCase();
  if (mode.priced) {
    payload.quantity = draft.quantity;
    payload.price = draft.price;
    payload.contract_multiplier = draft.contract_multiplier;
    if (draft.amount.trim()) payload.amount = draft.amount;
  } else if (mode.cashAmount) payload.amount = draft.amount;
  if (!mode.expense) {
    payload.commission = draft.commission || "0";
    payload.fee = draft.fee || "0";
    payload.tax = draft.tax || "0";
  }
  const metadata: Record<string, string> = {};
  if (draft.transaction_type === "FX_CONVERSION") {
    metadata.to_currency = draft.to_currency;
    metadata.to_amount = draft.to_amount;
  }
  if (["SPLIT", "REVERSE_SPLIT"].includes(draft.transaction_type))
    metadata.ratio = draft.ratio;
  if (["SPINOFF", "MERGER"].includes(draft.transaction_type))
    payload.child_symbol = draft.child_symbol.trim().toUpperCase();
  if (draft.transaction_type === "SPINOFF") {
    payload.quantity = draft.quantity;
    metadata.cost_allocation = draft.cost_allocation;
  }
  if (draft.transaction_type === "MERGER") {
    metadata.exchange_ratio = draft.exchange_ratio;
    metadata.cash_per_share = draft.cash_per_share;
    metadata.cash_cost_allocation = draft.cash_cost_allocation;
  }
  if (draft.transaction_type === "OTHER_ADJUSTMENT") {
    metadata.direction = draft.adjustment_direction;
    metadata.reason = draft.adjustment_reason;
  }
  payload.metadata = metadata;
  return payload;
}
