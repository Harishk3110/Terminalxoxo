export type CostMethod = "AVERAGE" | "FIFO";

export interface AccountingPolicy {
  method: CostMethod;
  capitalize_commissions: boolean;
  capitalize_fees: boolean;
}

export interface PortfolioMetadata {
  id: string;
  code: string;
  name: string;
  base_currency: string;
  accounting_policy: AccountingPolicy;
  accounts: Array<{
    id: string;
    name: string;
    type: string;
    provider: string | null;
  }>;
}

export interface SettlementCash {
  currency: string;
  amount: string;
  settled: string;
  receivable: string;
  payable: string;
  available: string;
  base_value: string | null;
  fx_rate: string | null;
  quality: string;
  source: string;
  as_of: string | null;
}

export interface PositionLot {
  id: string;
  instrument_id: string;
  entry_id: string;
  opened: string;
  direction: "LONG" | "SHORT";
  quantity: string;
  native_basis: string;
  base_basis: string;
  multiplier: string;
}

export interface LedgerSummary {
  portfolio: {
    id: string;
    code: string;
    base_currency: string;
    nav: string | null;
    cash: string | null;
    settled_cash: string | null;
    available_cash: string | null;
    settlement_receivables: string | null;
    settlement_payables: string | null;
    accounting_policy: AccountingPolicy;
  };
  cash: SettlementCash[];
  lots: PositionLot[];
  positions: Array<{ instrument_id: string; symbol: string }>;
  valuation_run_id: string;
  calculation_version: string;
  quality: string;
  calculated_at: string;
}

export interface RevisionSnapshot {
  entry?: {
    quantity: string;
    price: string;
    amount: string;
    commission: string;
    fee: string;
    tax: string;
    fx: string;
    day: string;
    settle_date: string | null;
  };
  notes?: string | null;
  void?: boolean;
}

export interface TransactionRevision {
  id: string;
  version: number;
  action: "AMEND" | "VOID";
  reason: string;
  actor_user_id: string | null;
  created_at: string;
  before: RevisionSnapshot;
  after: RevisionSnapshot;
}

export interface LedgerTransaction {
  id: string;
  type: string;
  symbol: string | null;
  trade_date: string;
  settle_date: string | null;
  quantity: string;
  price: string;
  gross_amount: string;
  currency: string;
  commission: string;
  fee: string;
  tax: string;
  fx_rate_to_base: string;
  notes: string | null;
  audit_version: number;
  ledger_state: "ACTIVE" | "VOID";
  revisions: TransactionRevision[];
}

export interface RevisionResult {
  transaction_id: string;
  revision_id: string;
  audit_version: number;
  ledger_state: "ACTIVE" | "VOID";
}

export const portfolioPath = (key: string) =>
  `/api/v1/portfolios/${encodeURIComponent(key)}`;
