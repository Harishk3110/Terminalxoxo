import type { NavStatementSnapshot } from "../../components/ledger/nav-inspector";

export const navSnapshot: NavStatementSnapshot = {
  portfolio: { id: "book", base_currency: "SGD", nav: "9947.65" },
  balance_sheet: {
    state: "AVAILABLE",
    items: {
      nav: "9947.65432109",
      cash: "10200",
      cash_assets: "10200",
      cash_overdrafts: "0",
      market_value: "-240",
      long_market_value: "0",
      short_liabilities: "240",
      gross_asset_value: "10200",
      accrued_income: "0",
      receivables: "0",
      payables: "0",
      accrued_fees: "12.34567891",
      other_liabilities: "0",
      liabilities: "252.34567891",
    },
    difference: "0E-8",
    reconciliation_state: "BALANCED",
    warnings: [],
    methodology:
      "Gross assets minus all liabilities equals NAV; currency overdrafts are not netted away",
  },
  state: "AVAILABLE",
  valuation_run_id: "run-1",
  valuation_date: "2026-01-09",
  calculation_version: "knk-nav-4.6",
  quality: "FILE IMPORT",
  calculated_at: "2026-01-09T20:00:00Z",
};
