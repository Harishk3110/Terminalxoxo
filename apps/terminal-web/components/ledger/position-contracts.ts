import type { AccountingPolicy, PositionLot } from "./contracts";

export type NumericValue = string | number | null;

export interface MarkProvenance {
  source: string;
  data_state: string;
  as_of: string | null;
  stale: boolean;
  value?: string;
  source_category?: string;
  source_file_id?: string | null;
  dataset_version_id?: string | null;
  observation_id?: string;
  age_hours?: number;
  ingested_at?: string;
  adjustment_state?: string;
  inverse?: boolean;
  conflict?: boolean;
}

export interface PositionDailyPnl {
  instrument_id: string;
  opening_value: string | null;
  closing_value: string | null;
  economic_cash: string;
  external_security_flow: string;
  internal_transfer: string | null;
  pnl: string | null;
  state: "AVAILABLE" | "UNAVAILABLE";
  methodology: string;
  warnings: string[];
}

export interface PositionSnapshot {
  instrument_id: string;
  portfolio_id: string;
  symbol: string;
  name: string;
  currency: string;
  base_currency: string;
  sector: string;
  country: string | null;
  asset_class: string;
  quantity: string;
  contract_multiplier: string;
  average_cost: string | null;
  cost_basis_base: string;
  market_price: string | null;
  market_value: string | null;
  unrealised_pnl: string | null;
  realised_pnl: string;
  total_pnl: string | null;
  income: string;
  fees: string;
  fx_rate: string | null;
  beta: NumericValue;
  risk_contribution: NumericValue;
  weight: NumericValue;
  quality: string;
  measurement_state: "AVAILABLE" | "LEGACY_SNAPSHOT";
  direction?: "LONG" | "SHORT" | "CLOSED";
  cost_basis_native?: string;
  market_value_native?: string | null;
  market_value_base_exact?: string | null;
  unrealised_pnl_native?: string | null;
  unrealised_price_pnl_base?: string | null;
  unrealised_fx_pnl_base?: string | null;
  nav_weight?: NumericValue;
  sector_weight?: NumericValue;
  beta_contribution?: NumericValue;
  capitalized_charges?: string;
  expensed_charges?: string;
  valuation_state?: "AVAILABLE" | "UNAVAILABLE";
  valuation_warnings?: string[];
  unrealised_decomposition_method?: string;
  daily_pnl_details?: PositionDailyPnl;
  price_provenance: MarkProvenance;
  fx_provenance: MarkProvenance;
  lots: PositionLot[];
  accounting_policy: AccountingPolicy | null;
  valuation_run_id: string;
  valuation_date: string;
  calculation_version: string;
  calculated_at: string;
}
