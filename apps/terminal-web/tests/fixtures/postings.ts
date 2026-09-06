import type {
  AccountingActivityResult,
  AccountingRecord,
} from "../../components/ledger/accounting-activity";

export const income: AccountingRecord = {
  id: "income-record",
  key: "transaction-1:DIVIDEND",
  category: "INCOME",
  kind: "DIVIDEND",
  effective_date: "2026-01-06",
  settlement_date: "2026-01-08",
  currency: "USD",
  native_amount: "12",
  base_amount: "15.6",
  fx_rate: "1.3",
  capitalized_base: "0",
  transaction_id: "transaction-1",
  adjustment_id: null,
  account_id: "account-1",
  instrument_id: "AAA",
  provenance: { basis: "RECORDED TRANSACTION FX", source: "USER PROVIDED" },
};
export const fee: AccountingRecord = {
  ...income,
  id: "fee-record",
  key: "transaction-1:TAX",
  category: "FEE",
  kind: "TAX",
  native_amount: "2",
  base_amount: "2.6",
};
export const activity: AccountingActivityResult = {
  state: "AVAILABLE",
  valuation_run_id: "run-1",
  base_currency: "SGD",
  items: [income, fee],
  totals: {
    external_flows: "10000",
    income: "15.6",
    expensed_fees: "0",
    capitalized_charges: "0",
    taxes: "2.6",
  },
  reconciliation: { state: "BALANCED", differences: {} },
};
