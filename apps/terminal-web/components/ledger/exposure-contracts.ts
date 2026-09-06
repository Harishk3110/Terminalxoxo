import type { MarkProvenance, NumericValue } from "./position-contracts";

export const exposureDimensions = {
  currency: "Currency",
  sector: "Sector",
  country: "Country",
  asset_class: "Asset class",
} as const;

export type ExposureDimension = keyof typeof exposureDimensions;

export interface ExposureGroup {
  name: string;
  value: NumericValue;
  weight: NumericValue;
  net_value?: NumericValue;
  gross_value?: NumericValue;
  known_value?: NumericValue;
  long_value?: NumericValue;
  short_value?: NumericValue;
  cash_value?: NumericValue;
  balance_value?: NumericValue;
  gross_weight?: NumericValue;
  state?: "AVAILABLE" | "INCOMPLETE";
  item_count?: number;
  position_count?: number;
  missing_count?: number;
  stale_count?: number;
}

export interface ExposureFreshness {
  stale_market_value: NumericValue;
  stale_nav_pct: NumericValue;
  price_coverage_pct: number;
  stale_cash_value?: NumericValue;
  stale_balance_value?: NumericValue;
  stale_total_value?: NumericValue;
  known_marked_value?: NumericValue;
  cash_fx_coverage_pct?: number;
  state?: "AVAILABLE" | "INCOMPLETE";
  unavailable_items?: number;
  stale_items?: number;
  item_count?: number;
  methodology?: string;
}

export interface ExposureBalance {
  bucket: string;
  currency: string;
  amount: string;
  base_value: string | null;
  fx_rate: string | null;
  fx_provenance: MarkProvenance;
}

export interface ExposureSnapshot {
  groups: Partial<Record<ExposureDimension, ExposureGroup[]>>;
  balances: ExposureBalance[];
  freshness: ExposureFreshness | null;
  methodology: string | null;
  state: "AVAILABLE" | "INCOMPLETE" | "LEGACY_SNAPSHOT";
  warnings: string[];
  portfolio_id: string;
  base_currency: string;
  nav: string | null;
  valuation_run_id: string;
  valuation_date: string;
  calculation_version: string;
  quality: string;
  calculated_at: string;
}
