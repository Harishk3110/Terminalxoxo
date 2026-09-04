export interface TerminalFunction {
  code: string;
  title: string;
  route: string;
  category: "Market" | "Portfolio" | "Research" | "Risk" | "Quant" | "Reports" | "System";
  description: string;
}

export const terminalFunctions: TerminalFunction[] = [
  { code: "HOME", title: "Home Dashboard", route: "/home", category: "Market", description: "Market overview, portfolio summary, alerts, and data-quality state." },
  { code: "DES", title: "Security Description", route: "/security/sec-aapl-us", category: "Market", description: "Instrument profile, identifiers, listings, and provenance." },
  { code: "GP", title: "Price Chart", route: "/chart/sec-aapl-us", category: "Market", description: "Price history with overlays and technical studies." },
  { code: "FIN", title: "Financials", route: "/financials/sec-aapl-us", category: "Research", description: "Income statement, balance sheet, cash flow, ratios, and source notes." },
  { code: "DCF", title: "DCF Builder", route: "/valuation/sec-aapl-us", category: "Research", description: "Deterministic demo valuation model with assumptions and audit trail." },
  { code: "OPT", title: "Options Chain", route: "/options/sec-aapl-us", category: "Market", description: "Option chain, volatility, Greeks, and exposure analytics." },
  { code: "PORT", title: "Portfolio", route: "/portfolio", category: "Portfolio", description: "Reference NAV, cash, positions, exposure, and broker comparison." },
  { code: "RISK", title: "Risk", route: "/risk", category: "Risk", description: "VaR, CVaR, drawdown, beta, stress, and contribution analysis." },
  { code: "HEDGE", title: "Hedge Recommendations", route: "/hedge", category: "Risk", description: "ETF and futures hedge sizing with residual notional." },
  { code: "EDGE", title: "Edge Lab", route: "/edge-lab", category: "Quant", description: "Idea discovery workflow with hypotheses, factors, and experiments." },
  { code: "BT", title: "Backtests", route: "/backtests", category: "Quant", description: "Non-blocking backtest jobs, trades, equity curves, and audit logs." },
  { code: "PINE", title: "TradingView Studio", route: "/tradingview", category: "Quant", description: "Pine export and alert comparison without broker action integration." },
  { code: "XLS", title: "Excel Studio", route: "/excel-studio", category: "Reports", description: "Workbook factory for DCF, comparable companies, risk, and backtests." },
  { code: "PPT", title: "Deck Builder", route: "/deck-builder", category: "Reports", description: "Internal and public research deck generation." },
  { code: "HEALTH", title: "System Health", route: "/system-health", category: "System", description: "Services, jobs, providers, data freshness, backup, and broker heartbeat." },
  { code: "CONN", title: "Connections", route: "/settings/connections", category: "System", description: "Provider modes, credential tests, entitlement notes, and backfill actions." }
];

export function findTerminalFunctions(query: string): TerminalFunction[] {
  const normalized = query.trim().toLowerCase();
  if (!normalized) return terminalFunctions;
  return terminalFunctions.filter((item) => {
    return [item.code, item.title, item.category, item.description].join(" ").toLowerCase().includes(normalized);
  });
}
