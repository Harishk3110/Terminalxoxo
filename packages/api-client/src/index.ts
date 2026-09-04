export type KnkId = string;

export interface PortfolioPayload {
  portfolio: {
    id: KnkId;
    name: string;
    base_currency: string;
    reference_capital: string;
    nav: string;
    cash: string;
    market_value: string;
    quality: string;
  };
  positions: Array<{
    id: KnkId;
    instrument_id: KnkId;
    symbol: string;
    name: string;
    quantity: string;
    average_cost: string;
    market_price: string;
    market_value: string;
    unrealised_pnl: string;
    realised_pnl: string;
    weight: string;
    quality: string;
  }>;
  cash: Array<{ currency: string; amount: string; as_of: string; quality: string }>;
  transactions: Array<{ id: KnkId; type: string; symbol: string | null; trade_date: string; quantity: string; price: string; currency: string; fx_rate_to_base: string; fee: string; source: string; quality: string; notes: string | null }>;
}

export interface MacroDashboardPayload {
  items: Array<{
    series_id: string;
    title: string;
    latest_value: string | null;
    latest_observation_date: string | null;
    previous_value: string | null;
    change: string | null;
    unit: string;
    frequency: string;
    source: string;
    quality: string;
    ingestion_timestamp: string | null;
    revision_state: string;
  }>;
}

export interface RiskPayload {
  beta: string;
  volatility: string;
  var_95: string;
  cvar_95: string;
  max_drawdown: string;
  gross_exposure: string;
  net_exposure: string;
  concentration: string;
  quality: string;
}

export interface PerformancePayload {
  twr: string;
  cagr: string;
  volatility: string;
  sharpe: string;
  sortino: string;
  max_drawdown: string;
  quality: string;
}

export interface ProviderPayload {
  items: Array<{
    name: string;
    type: string;
    enabled: boolean;
    configured: boolean;
    connection_state: string;
    capabilities: string[];
    masked_identifier: string | null;
    last_success: string | null;
    last_failure: string | null;
    last_error: string | null;
    last_data_sync: string | null;
    data_freshness: string | null;
  }>;
}

export interface SystemHealthPayload {
  environment: string;
  application_version: string;
  current_commit: string;
  checks: Record<string, string>;
  provider_state: ProviderPayload["items"];
  counts: Record<string, number>;
}

export interface BacktestPayload {
  id: string;
  status: string;
  initial_capital: string;
  final_equity: string;
  parameters: Record<string, unknown>;
  quality: string;
  metrics: Record<string, string>;
  equity_curve: Array<{ date: string; equity: string; drawdown: string }>;
}

export interface ApiList<T> {
  items: T[];
}

const defaultBaseUrl = "http://127.0.0.1:8000";

export class KnkApiClient {
  constructor(private readonly baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? defaultBaseUrl) {}

  async get<T>(path: string): Promise<T> {
    const response = await fetch(`${this.baseUrl}${path}`, { cache: "no-store" });
    if (!response.ok) {
      throw new Error(`${path} failed with ${response.status}`);
    }
    return (await response.json()) as T;
  }

  async post<T>(path: string, body?: unknown): Promise<T> {
    const response = await fetch(`${this.baseUrl}${path}`, {
      method: "POST",
      headers: body instanceof FormData ? undefined : { "Content-Type": "application/json" },
      body: body instanceof FormData ? body : body === undefined ? undefined : JSON.stringify(body)
    });
    if (!response.ok) {
      throw new Error(`${path} failed with ${response.status}`);
    }
    return (await response.json()) as T;
  }

  environment() {
    return this.get<Record<string, unknown>>("/api/v1/environment");
  }

  portfolio() {
    return this.get<PortfolioPayload>("/api/v1/portfolios/default");
  }

  performance() {
    return this.get<PerformancePayload>("/api/v1/performance/default");
  }

  risk() {
    return this.get<RiskPayload>("/api/v1/risk/default");
  }

  stress() {
    return this.get<ApiList<Record<string, unknown>>>("/api/v1/stress/default");
  }

  hedge() {
    return this.get<Record<string, unknown>>("/api/v1/hedge/default");
  }

  macroDashboard() {
    return this.get<MacroDashboardPayload>("/api/v1/macro/dashboard");
  }

  instruments() {
    return this.get<ApiList<Record<string, unknown>>>("/api/v1/instruments");
  }

  providers() {
    return this.get<ProviderPayload>("/api/v1/providers");
  }

  jobs() {
    return this.get<ApiList<Record<string, unknown>>>("/api/v1/jobs");
  }

  datasets() {
    return this.get<ApiList<Record<string, unknown>>>("/api/v1/datasets");
  }

  strategies() {
    return this.get<ApiList<Record<string, unknown>>>("/api/v1/strategies");
  }

  backtests() {
    return this.get<ApiList<BacktestPayload>>("/api/v1/backtests");
  }

  systemHealth() {
    return this.get<SystemHealthPayload>("/api/v1/system/health");
  }

  pine() {
    return this.get<Record<string, unknown>>("/api/v1/pine/export");
  }
}

export const knkApi = new KnkApiClient();
