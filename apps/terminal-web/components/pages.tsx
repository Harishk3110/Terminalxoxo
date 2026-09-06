"use client";
import dynamic from "next/dynamic";
import {
  OverviewPage,
  PortfolioPage,
  PerformancePage,
  RiskPage,
  StressPage,
  MacroPage,
  HedgePage,
} from "./core-pages";
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
const DataDropPage = dynamic(() =>
  import("./lab-pages").then((m) => m.DataDropPage),
);
const CataloguePage = dynamic(() =>
  import("./lab-pages").then((m) => m.CataloguePage),
);
const JobsPage = dynamic(() => import("./lab-pages").then((m) => m.JobsPage));
const ResearchPage = dynamic(() =>
  import("./lab-pages").then((m) => m.ResearchPage),
);
const PinePage = dynamic(() => import("./lab-pages").then((m) => m.PinePage));
const ExcelPage = dynamic(() => import("./lab-pages").then((m) => m.ExcelPage));

export function PageRouter({ route }: { route: string }) {
  if (["/overview", "/home", "/"].includes(route)) return <OverviewPage />;
  if (["/portfolio", "/positions"].includes(route)) return <PortfolioPage />;
  if (route === "/performance") return <PerformancePage />;
  if (route === "/risk") return <RiskPage />;
  if (route === "/stress-tests") return <StressPage />;
  if (route === "/macro") return <MacroPage />;
  if (route === "/hedge") return <HedgePage />;
  if (route.startsWith("/backtests")) return <BacktestPage />;
  if (route === "/factor-lab") return <FactorPage />;
  if (["/quant", "/strategies"].includes(route)) return <QuantPage />;
  if (route === "/data-drop") return <DataDropPage />;
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
