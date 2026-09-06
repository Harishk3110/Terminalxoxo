import type {
  PortfolioPayload,
  MacroDashboardPayload,
  ProviderPayload,
} from "@knk/api-client";
import type { TerminalFunction } from "@knk/terminal-functions";

export type Row = Record<string, unknown>;
export type Metrics = Record<string, number | string | null>;
export interface Quote extends Row {
  id: string;
  symbol: string;
  name: string;
  price: number;
  change: number;
  change_pct: number;
  exchange: string;
  currency: string;
  asset_class: string;
  sector: string;
  country: string;
  source: string;
  quality: string;
  as_of: string;
  market_state: string;
}
export interface CurvePoint extends Row {
  date: string;
  equity: number;
  benchmark?: number;
  drawdown: number;
  return?: number;
}
export interface PortfolioData extends PortfolioPayload {
  positions: Array<
    PortfolioPayload["positions"][number] & {
      sector: string;
      country: string;
      currency: string;
      beta: number;
      daily_pnl: number;
      source: string;
      as_of: string;
      fx_rate: number;
      risk_contribution: number;
    }
  >;
  performance: Metrics;
  risk: Metrics;
  curve: CurvePoint[];
  monthly: { month: string; return: number }[];
  correlation: { symbols: string[]; values: (number | null)[][] };
  source: string;
  as_of: string;
  quality: string;
  warnings: string[];
}
export interface Scenario extends Row {
  id: string;
  name: string;
  category: string;
  equity_shock: number;
  fx_shock: number;
  rates_bp: number;
  scope: string;
}
export interface Tab {
  id: string;
  title: string;
  route: string;
  security?: string;
  dirty?: boolean;
}
export interface Configuration {
  tabs: Tab[];
  activeTab?: string;
  securities: string[];
  rail: boolean;
  inspector: boolean;
  sizes?: number[];
  favourites?: string[];
  recents?: string[];
  tabStates?: Record<string, Row>;
  inspectRunId?: string;
  watchlist?: string[];
  hiddenGroups?: string[];
}
export interface Workspace {
  id: string;
  name: string;
  configuration: Configuration;
}
export interface Bootstrap {
  functions: TerminalFunction[];
  quotes: Quote[];
  workspaces: Workspace[];
  scenarios: Scenario[];
  timezone: string;
  broker_state: string;
  as_of: string;
}
export interface RunResult extends Row {
  source: string;
  as_of: string;
  quality: string;
  warnings: string[];
  calculation_version: string;
  state?: string;
  factor_contributions?: Row[];
  pre_nav?: number;
  loss?: number;
  impact?: number;
  post_nav?: number;
  worst_position?: string;
  currency_impact?: number;
  contributions?: Row[];
  equity_curve?: CurvePoint[];
  metrics?: Metrics;
  trades?: Row[];
  final_equity?: number;
  initial_capital?: number;
}
export interface Run {
  id: string;
  kind: string;
  name: string;
  status: string;
  parameters: Row;
  result: RunResult | null;
  error: string | null;
  history: { state: string; at: string; message: string }[];
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
}
export interface Health {
  items: {
    service: string;
    state: string;
    latency_ms?: number | null;
    as_of: string;
    detail: string;
  }[];
  commit: string;
  version: string;
  as_of: string;
  environment: string;
}
export interface Prices {
  items: {
    date: string;
    as_of?: string;
    open: number;
    high: number;
    low: number;
    close: number;
    volume: number;
  }[];
  source: string;
  as_of: string;
  quality: string;
  symbol: string;
}
export interface Financials {
  items: Row[];
  source: string;
  as_of: string;
  quality: string;
  symbol: string;
  unit: string;
  fair_value?: number;
  enterprise_value?: number;
  equity_value?: number;
  forecast?: Row[];
}
export interface UploadPreview {
  upload_id: string;
  name: string;
  size: number;
  hash: string;
  columns: { name: string; type: string }[];
  preview: Row[];
  row_count: number;
  missing: number;
  duplicates: number;
  source: string;
  as_of: string;
  quality: string;
}
export type { MacroDashboardPayload, ProviderPayload, TerminalFunction };
