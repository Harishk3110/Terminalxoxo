import type {
  LedgerSummary,
  LedgerTransaction,
  PortfolioMetadata,
} from "../../components/ledger/contracts";

export const metadata: PortfolioMetadata = {
  id: "book",
  code: "TEST_BOOK",
  name: "Test portfolio",
  base_currency: "SGD",
  accounting_policy: {
    method: "AVERAGE",
    capitalize_commissions: false,
    capitalize_fees: false,
  },
  accounts: [
    {
      id: "account",
      name: "Internal ledger",
      type: "INTERNAL",
      provider: null,
    },
  ],
};

export const summary: LedgerSummary = {
  portfolio: {
    id: "book",
    code: "TEST_BOOK",
    base_currency: "SGD",
    nav: "10200",
    cash: "9000",
    settled_cash: "10000",
    available_cash: "9000",
    settlement_receivables: "0",
    settlement_payables: "1000",
    accounting_policy: metadata.accounting_policy,
  },
  cash: [
    {
      currency: "SGD",
      amount: "9000",
      settled: "10000",
      available: "9000",
      receivable: "0",
      payable: "1000",
      base_value: "9000",
      fx_rate: "1",
      quality: "INTERNAL",
      source: "IDENTITY",
      as_of: "2026-01-07T20:00:00Z",
    },
  ],
  lots: [
    {
      id: "lot-1",
      instrument_id: "AAA",
      entry_id: "buy-1",
      opened: "2026-01-06",
      direction: "LONG",
      quantity: "10",
      native_basis: "1000",
      base_basis: "1000",
      multiplier: "1",
    },
  ],
  positions: [{ instrument_id: "AAA", symbol: "AAA" }],
  valuation_run_id: "run-1",
  calculation_version: "knk-nav-4.0",
  quality: "FILE IMPORT",
  calculated_at: "2026-01-07T20:01:00Z",
};

export const transaction: LedgerTransaction = {
  id: "buy-1",
  type: "BUY",
  symbol: "AAA",
  trade_date: "2026-01-06",
  settle_date: "2026-01-08",
  quantity: "10.00000000",
  price: "100.00000000",
  gross_amount: "1000.00000000",
  currency: "SGD",
  commission: "2.00000000",
  fee: "0.00000000",
  tax: "0.00000000",
  fx_rate_to_base: "1.00000000",
  notes: null,
  audit_version: 1,
  ledger_state: "ACTIVE",
  revisions: [],
};
