"use client";
import { PerformanceWorkspace } from "./performance-page";
import { HedgeWorkspace } from "./hedge-page";
import { MonteCarloWorkspace } from "./monte-carlo-page";
import dynamic from "next/dynamic";
import { SourcePreferencesPage } from "./source-preferences";
import { BrokerMonitorPage } from "./broker-monitor";
import {
  PortfolioHomePage,
  TradeMonitorPage,
  DataDropOperationsPage,
  OperatingDeskPage,
} from "./operating-pages";
import { PortfolioPage, RiskPage, StressPage, MacroPage } from "./core-pages";
import {
  AuthPage,
  AlertsPage,
  ConnectionsPage,
  FunctionDirectory,
  HealthPage,
  ReconciliationPage,
} from "./system-pages";
import { MarketPage, SecurityPage } from "./security-pages";
const BacktestPage = dynamic(() =>
  import("./lab-pages").then((m) => m.BacktestPage),
);
const FactorPage = dynamic(() =>
  import("./lab-pages").then((m) => m.FactorPage),
);
const QuantPage = dynamic(() => import("./lab-pages").then((m) => m.QuantPage));
const CataloguePage = dynamic(() =>
  import("./lab-pages").then((m) => m.CataloguePage),
);
const JobsPage = dynamic(() => import("./lab-pages").then((m) => m.JobsPage));
const ResearchPage = dynamic(() =>
  import("./lab-pages").then((m) => m.ResearchPage),
);
const PinePage = dynamic(() => import("./lab-pages").then((m) => m.PinePage));
const ExcelPage = dynamic(() => import("./lab-pages").then((m) => m.ExcelPage));
const AlphaWorkspace = dynamic(() =>
  import("./alpha-page").then((m) => m.AlphaWorkspace),
);
const ModelWorkspace = dynamic(() =>
  import("./model-page").then((m) => m.ModelWorkspace),
);

export function PageRouter({ route }: { route: string }) {
  if (route === "/broker-monitor") return <BrokerMonitorPage />;
  if (route === "/price-sources") return <SourcePreferencesPage />;
  if (["/overview", "/home", "/"].includes(route)) return <PortfolioHomePage />;
  if (route === "/trade-monitor") return <TradeMonitorPage />;
  if (route === "/risk-trade-monitor") return <TradeMonitorPage risk />;
  if (route === "/equity") return <OperatingDeskPage desk="equity" />;
  if (route === "/quant-dashboard") return <OperatingDeskPage desk="quant" />;
  if (route === "/edge-lab") return <OperatingDeskPage desk="edge" />;
  if (["/portfolio", "/positions"].includes(route)) return <PortfolioPage />;
  if (route === "/performance") return <PerformanceWorkspace />;
  if (route === "/alpha") return <AlphaWorkspace />;
  if (route === "/monte-carlo") return <MonteCarloWorkspace />;
  if (["/model-lab", "/walk-forward"].includes(route))
    return <ModelWorkspace />;
  if (route === "/risk") return <RiskPage />;
  if (route === "/stress-tests") return <StressPage />;
  if (route === "/macro") return <MacroPage />;
  if (route === "/hedge") return <HedgeWorkspace />;
  if (route.startsWith("/backtests")) return <BacktestPage />;
  if (route === "/factor-lab") return <FactorPage />;
  if (["/quant", "/strategies"].includes(route)) return <QuantPage />;
  if (route === "/data-drop") return <DataDropOperationsPage />;
  if (route.startsWith("/data-catalogue"))
    return <CataloguePage route={route} />;
  if (route === "/data-jobs") return <JobsPage />;
  if (["/research", "/thesis", "/ideas"].includes(route))
    return <ResearchPage />;
  if (route === "/tradingview") return <PinePage />;
  if (route === "/excel-studio") return <ExcelPage />;
  if (["/settings/connections", "/settings"].includes(route))
    return <ConnectionsPage />;
  if (["/system-health", "/api-monitor"].includes(route)) return <HealthPage />;
  if (route === "/alerts") return <AlertsPage />;
  if (["/settings/security", "/login"].includes(route)) return <AuthPage />;
  if (route === "/reconciliation") return <ReconciliationPage />;
  if (
    [
      "/markets",
      "/security-master",
      "/screener",
      "/watchlists",
      "/sectors",
      "/heatmap",
    ].includes(route)
  )
    return <MarketPage route={route} />;
  if (
    /^\/(security|quote|chart|technicals|financials|valuation|dcf|wacc|comparables)\//.test(
      route,
    )
  )
    return <SecurityPage route={route} />;
  return <FunctionDirectory route={route} />;
}
