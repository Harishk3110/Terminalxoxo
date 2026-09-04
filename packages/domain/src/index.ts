export type DataQualityState =
  | "DEMO DATA"
  | "PAPER"
  | "CONNECTED"
  | "LIVE DATA"
  | "DELAYED DATA"
  | "EOD DATA"
  | "ESTIMATE"
  | "CALCULATED"
  | "AI GENERATED"
  | "STALE DATA"
  | "PROVIDER UNAVAILABLE";

export type Currency = "SGD" | "USD" | "EUR" | "JPY" | "HKD";

export interface DataTrace {
  provider: string;
  dataset: string;
  effectiveTimestamp: string;
  ingestionTimestamp: string;
  currency: Currency;
  methodology: string;
  quality: DataQualityState;
}

export interface Security {
  id: string;
  ticker: string;
  name: string;
  exchange: string;
  sector: string;
  currency: Currency;
  lastPrice: number;
  dayChangePercent: number;
  trace: DataTrace;
}

export interface Position {
  instrumentId: string;
  ticker: string;
  quantity: number;
  averageCost: number;
  marketPrice: number;
  marketValue: number;
  unrealisedPnl: number;
  weight: number;
  trace: DataTrace;
}

export interface PortfolioSnapshot {
  name: string;
  baseCurrency: Currency;
  referenceCapital: number;
  nav: number;
  cash: number;
  positions: Position[];
  trace: DataTrace;
}

export interface RiskSnapshot {
  beta: number;
  annualVolatility: number;
  valueAtRisk95: number;
  conditionalValueAtRisk95: number;
  maxDrawdown: number;
  grossExposure: number;
  netExposure: number;
  topRiskContributors: Array<{ label: string; contribution: number }>;
  trace: DataTrace;
}

export const LOCAL_DEMO_TRACE: DataTrace = {
  provider: "KnK deterministic fixture",
  dataset: "local-demo-fixtures",
  effectiveTimestamp: "2026-09-05T09:00:00+08:00",
  ingestionTimestamp: "2026-09-05T09:01:00+08:00",
  currency: "SGD",
  methodology: "Deterministic synthetic data for product demonstration only.",
  quality: "DEMO DATA"
};

export const demoSecurities: Security[] = [
  {
    id: "sec-aapl-us",
    ticker: "AAPL",
    name: "Apple Inc.",
    exchange: "NASDAQ",
    sector: "Information Technology",
    currency: "USD",
    lastPrice: 231.42,
    dayChangePercent: 0.84,
    trace: { ...LOCAL_DEMO_TRACE, currency: "USD", dataset: "demo-equity-prices" }
  },
  {
    id: "sec-msft-us",
    ticker: "MSFT",
    name: "Microsoft Corporation",
    exchange: "NASDAQ",
    sector: "Information Technology",
    currency: "USD",
    lastPrice: 418.31,
    dayChangePercent: -0.21,
    trace: { ...LOCAL_DEMO_TRACE, currency: "USD", dataset: "demo-equity-prices" }
  },
  {
    id: "sec-spy-us",
    ticker: "SPY",
    name: "SPDR S&P 500 ETF Trust",
    exchange: "NYSE Arca",
    sector: "ETF",
    currency: "USD",
    lastPrice: 558.72,
    dayChangePercent: 0.31,
    trace: { ...LOCAL_DEMO_TRACE, currency: "USD", dataset: "demo-etf-prices" }
  },
  {
    id: "sec-es-fut",
    ticker: "ES",
    name: "E-mini S&P 500 Futures",
    exchange: "CME",
    sector: "Index Futures",
    currency: "USD",
    lastPrice: 5628.5,
    dayChangePercent: 0.28,
    trace: { ...LOCAL_DEMO_TRACE, currency: "USD", dataset: "demo-futures-prices" }
  }
];

export const demoPortfolio: PortfolioSnapshot = {
  name: "KnK Capital Reference Portfolio",
  baseCurrency: "SGD",
  referenceCapital: 70000,
  nav: 71482.35,
  cash: 18420.5,
  trace: LOCAL_DEMO_TRACE,
  positions: [
    {
      instrumentId: "sec-aapl-us",
      ticker: "AAPL",
      quantity: 55,
      averageCost: 218.12,
      marketPrice: 231.42,
      marketValue: 16972.61,
      unrealisedPnl: 974.03,
      weight: 0.2374,
      trace: { ...LOCAL_DEMO_TRACE, currency: "USD", dataset: "demo-portfolio-positions" }
    },
    {
      instrumentId: "sec-msft-us",
      ticker: "MSFT",
      quantity: 34,
      averageCost: 402.5,
      marketPrice: 418.31,
      marketValue: 18932.17,
      unrealisedPnl: 716.58,
      weight: 0.2648,
      trace: { ...LOCAL_DEMO_TRACE, currency: "USD", dataset: "demo-portfolio-positions" }
    },
    {
      instrumentId: "sec-spy-us",
      ticker: "SPY",
      quantity: 18,
      averageCost: 541.8,
      marketPrice: 558.72,
      marketValue: 13351.07,
      unrealisedPnl: 404.55,
      weight: 0.1868,
      trace: { ...LOCAL_DEMO_TRACE, currency: "USD", dataset: "demo-portfolio-positions" }
    }
  ]
};

export const demoRisk: RiskSnapshot = {
  beta: 1.08,
  annualVolatility: 0.183,
  valueAtRisk95: -2130.42,
  conditionalValueAtRisk95: -3184.77,
  maxDrawdown: -0.087,
  grossExposure: 0.689,
  netExposure: 0.689,
  trace: { ...LOCAL_DEMO_TRACE, dataset: "demo-risk-calculations", methodology: "Parametric and historical fixture blend for local demo." },
  topRiskContributors: [
    { label: "AAPL", contribution: 0.31 },
    { label: "MSFT", contribution: 0.28 },
    { label: "SPY", contribution: 0.18 }
  ]
};

export const demoEquityCurve = [
  { date: "2026-06-01", value: 70000 },
  { date: "2026-06-15", value: 69250 },
  { date: "2026-07-01", value: 70640 },
  { date: "2026-07-15", value: 72120 },
  { date: "2026-08-01", value: 71380 },
  { date: "2026-08-15", value: 72840 },
  { date: "2026-09-05", value: 71482.35 }
];

export const demoOptionChain = [
  { strike: 210, callDelta: 0.82, putDelta: -0.17, impliedVolatility: 0.28, openInterest: 14820, gammaExposure: 1840000 },
  { strike: 220, callDelta: 0.67, putDelta: -0.31, impliedVolatility: 0.25, openInterest: 22410, gammaExposure: 2325000 },
  { strike: 230, callDelta: 0.51, putDelta: -0.48, impliedVolatility: 0.24, openInterest: 31100, gammaExposure: 2910000 },
  { strike: 240, callDelta: 0.36, putDelta: -0.62, impliedVolatility: 0.26, openInterest: 19760, gammaExposure: 1764000 }
];

export const publicResearch = [
  {
    slug: "demo-quality-growth-framework",
    title: "Quality Growth Framework",
    summary: "A sanitized example of how KnK Capital evaluates durable compounding businesses.",
    publishedAt: "2026-09-05",
    status: "Published demo"
  },
  {
    slug: "demo-risk-first-portfolio-construction",
    title: "Risk-First Portfolio Construction",
    summary: "A public methodology note using only non-private fixture data.",
    publishedAt: "2026-09-05",
    status: "Published demo"
  }
];

export function calculateSimpleReturn(startValue: number, endValue: number): number {
  if (startValue <= 0) {
    throw new Error("startValue must be positive");
  }
  return (endValue - startValue) / startValue;
}

export function calculateMaxDrawdown(values: number[]): number {
  if (values.length === 0) return 0;
  let peak = values[0] ?? 0;
  let maxDrawdown = 0;
  for (const value of values) {
    peak = Math.max(peak, value);
    if (peak > 0) {
      maxDrawdown = Math.min(maxDrawdown, (value - peak) / peak);
    }
  }
  return maxDrawdown;
}

export function roundHedgeUnits(targetNotional: number, contractMultiplier: number, price: number): number {
  if (contractMultiplier <= 0 || price <= 0) {
    throw new Error("contractMultiplier and price must be positive");
  }
  return Math.round(targetNotional / (contractMultiplier * price));
}

export function calculateResidualNotional(targetNotional: number, units: number, contractMultiplier: number, price: number): number {
  return targetNotional - units * contractMultiplier * price;
}
