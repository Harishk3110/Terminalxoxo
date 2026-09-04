"use client";

import { DataTraceLine, ModeBadge, StatBlock } from "@knk/design-system";
import { demoEquityCurve, demoOptionChain, demoPortfolio, demoRisk, demoSecurities } from "@knk/domain";
import { findTerminalFunctions, terminalFunctions } from "@knk/terminal-functions";
import { rankSearch } from "@knk/search";
import { createColumnHelper, flexRender, getCoreRowModel, useReactTable } from "@tanstack/react-table";
import dynamic from "next/dynamic";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useMemo, useState } from "react";
import { Activity, Bell, BookOpen, BriefcaseBusiness, ChartCandlestick, ChevronRight, Database, FileSpreadsheet, HeartPulse, Lock, Search, Settings, ShieldCheck } from "lucide-react";
import { create } from "zustand";
import { isTerminalRoute } from "../../lib/routes";

const ReactECharts = dynamic(() => import("echarts-for-react"), { ssr: false });

type AppState = {
  activeSecurityId: string;
  setActiveSecurityId: (id: string) => void;
};

const useAppStore = create<AppState>((set) => ({
  activeSecurityId: "sec-aapl-us",
  setActiveSecurityId: (id) => set({ activeSecurityId: id })
}));

type RouteGroup = {
  label: string;
  icon: React.ReactNode;
  items: Array<{ label: string; href: string }>;
};

const routeGroups: RouteGroup[] = [
  {
    label: "Markets",
    icon: <ChartCandlestick className="h-4 w-4" />,
    items: [
      { label: "Home", href: "/home" },
      { label: "Markets", href: "/markets" },
      { label: "AAPL Security", href: "/security/sec-aapl-us" },
      { label: "AAPL Chart", href: "/chart/sec-aapl-us" },
      { label: "Options", href: "/options/sec-aapl-us" }
    ]
  },
  {
    label: "Portfolio",
    icon: <BriefcaseBusiness className="h-4 w-4" />,
    items: [
      { label: "Portfolio", href: "/portfolio" },
      { label: "Positions", href: "/positions" },
      { label: "Performance", href: "/performance" },
      { label: "Risk", href: "/risk" },
      { label: "Hedge", href: "/hedge" }
    ]
  },
  {
    label: "Research",
    icon: <BookOpen className="h-4 w-4" />,
    items: [
      { label: "Research", href: "/research" },
      { label: "Theses", href: "/theses" },
      { label: "Edge Lab", href: "/edge-lab" },
      { label: "Factor Lab", href: "/factor-lab" },
      { label: "Backtests", href: "/backtests" }
    ]
  },
  {
    label: "Reports",
    icon: <FileSpreadsheet className="h-4 w-4" />,
    items: [
      { label: "Reports", href: "/reports" },
      { label: "Excel Studio", href: "/excel-studio" },
      { label: "Deck Builder", href: "/deck-builder" },
      { label: "Publishing", href: "/publishing" }
    ]
  },
  {
    label: "System",
    icon: <Settings className="h-4 w-4" />,
    items: [
      { label: "Data Drop", href: "/data-drop" },
      { label: "Connections", href: "/settings/connections" },
      { label: "API Monitor", href: "/api-monitor" },
      { label: "System Health", href: "/system-health" },
      { label: "Broker Agent", href: "/settings/broker-agent" }
    ]
  }
];

function routeFromParams(slug?: string[]) {
  return `/${slug?.join("/") ?? "overview"}`.replace(/\/$/, "");
}

function Header() {
  const [query, setQuery] = useState("");
  const matches = useMemo(() => findTerminalFunctions(query).slice(0, 6), [query]);
  const activeSecurityId = useAppStore((state) => state.activeSecurityId);
  const activeSecurity = demoSecurities.find((item) => item.id === activeSecurityId) ?? demoSecurities[0];

  return (
    <header className="sticky top-0 z-30 border-b border-slate-700 bg-slate-950 px-4 py-3">
      <div className="grid gap-3 lg:grid-cols-[260px_1fr_auto] lg:items-center">
        <div>
          <p className="text-xs font-semibold uppercase text-cyan-300">KnK Capital</p>
          <h1 className="text-lg font-semibold tracking-normal text-white">Terminal</h1>
        </div>
        <div className="relative">
          <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search functions, securities, workflows"
            className="h-10 w-full rounded-md border border-slate-700 bg-slate-900 pl-9 pr-3 text-sm text-slate-100 outline-none ring-cyan-500 focus:ring-2"
          />
          {query ? (
            <div className="absolute left-0 right-0 top-12 z-40 rounded-md border border-slate-700 bg-slate-950 p-2 shadow-xl">
              {matches.map((item) => (
                <Link key={item.code} href={item.route} className="flex items-center justify-between rounded px-3 py-2 text-sm text-slate-200 hover:bg-slate-800">
                  <span>
                    <span className="font-semibold text-cyan-300">{item.code}</span> {item.title}
                  </span>
                  <ChevronRight className="h-4 w-4" />
                </Link>
              ))}
            </div>
          ) : null}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <ModeBadge>DEMO DATA</ModeBadge>
          <ModeBadge tone="paper">PAPER</ModeBadge>
          <ModeBadge tone="ok">CALCULATED</ModeBadge>
          <span className="rounded-md border border-slate-700 px-2 py-1 text-xs text-slate-300">{activeSecurity?.ticker ?? "AAPL"} active</span>
        </div>
      </div>
    </header>
  );
}

function Sidebar() {
  return (
    <aside className="border-r border-slate-800 bg-slate-950 p-3">
      <nav className="space-y-5">
        {routeGroups.map((group) => (
          <section key={group.label}>
            <div className="mb-2 flex items-center gap-2 px-2 text-xs font-semibold uppercase text-slate-400">
              {group.icon}
              {group.label}
            </div>
            <div className="space-y-1">
              {group.items.map((item) => (
                <Link key={item.href} href={item.href} className="block rounded px-2 py-1.5 text-sm text-slate-300 hover:bg-slate-800 hover:text-white">
                  {item.label}
                </Link>
              ))}
            </div>
          </section>
        ))}
      </nav>
    </aside>
  );
}

function MiniChart() {
  const option = {
    backgroundColor: "transparent",
    grid: { left: 42, right: 18, top: 24, bottom: 28 },
    xAxis: { type: "category", data: demoEquityCurve.map((point) => point.date), axisLabel: { color: "#94a3b8" } },
    yAxis: { type: "value", axisLabel: { color: "#94a3b8" }, splitLine: { lineStyle: { color: "#334155" } } },
    series: [
      {
        type: "line",
        data: demoEquityCurve.map((point) => point.value),
        smooth: true,
        lineStyle: { color: "#22d3ee", width: 3 },
        areaStyle: { color: "rgba(34, 211, 238, 0.15)" }
      }
    ],
    tooltip: { trigger: "axis" }
  };
  return <ReactECharts option={option} style={{ height: 300, width: "100%" }} />;
}

function PositionsTable() {
  const columnHelper = createColumnHelper<(typeof demoPortfolio.positions)[number]>();
  const columns = useMemo(
    () => [
      columnHelper.accessor("ticker", { header: "Ticker" }),
      columnHelper.accessor("quantity", { header: "Qty" }),
      columnHelper.accessor("marketPrice", { header: "Price", cell: (info) => `$${info.getValue().toFixed(2)}` }),
      columnHelper.accessor("marketValue", { header: "Market Value", cell: (info) => `SGD ${info.getValue().toLocaleString()}` }),
      columnHelper.accessor("unrealisedPnl", { header: "Unrealised P&L", cell: (info) => `SGD ${info.getValue().toLocaleString()}` }),
      columnHelper.accessor("weight", { header: "Weight", cell: (info) => `${(info.getValue() * 100).toFixed(1)}%` })
    ],
    [columnHelper]
  );
  const table = useReactTable({ data: demoPortfolio.positions, columns, getCoreRowModel: getCoreRowModel() });

  return (
    <div className="overflow-hidden rounded-md border border-slate-700">
      <table className="w-full border-collapse text-sm">
        <thead className="bg-slate-900 text-left text-xs uppercase text-slate-400">
          {table.getHeaderGroups().map((headerGroup) => (
            <tr key={headerGroup.id}>
              {headerGroup.headers.map((header) => (
                <th key={header.id} className="px-3 py-3">{flexRender(header.column.columnDef.header, header.getContext())}</th>
              ))}
            </tr>
          ))}
        </thead>
        <tbody>
          {table.getRowModel().rows.map((row) => (
            <tr key={row.id} className="border-t border-slate-800">
              {row.getVisibleCells().map((cell) => (
                <td key={cell.id} className="px-3 py-3 text-slate-200">{flexRender(cell.column.columnDef.cell, cell.getContext())}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Overview() {
  return (
    <div className="space-y-5">
      <section className="grid gap-4 md:grid-cols-4">
        <StatBlock label="Reference NAV" value={`SGD ${demoPortfolio.nav.toLocaleString()}`} sublabel="Synthetic demo portfolio" tone="positive" />
        <StatBlock label="Cash" value={`SGD ${demoPortfolio.cash.toLocaleString()}`} sublabel="Local demo account" />
        <StatBlock label="95% VaR" value={`SGD ${Math.abs(demoRisk.valueAtRisk95).toLocaleString()}`} sublabel="Calculated demo risk" tone="negative" />
        <StatBlock label="Max Drawdown" value={`${(demoRisk.maxDrawdown * 100).toFixed(1)}%`} sublabel="Fixture equity curve" tone="negative" />
      </section>
      <section className="grid gap-4 lg:grid-cols-[1.4fr_0.6fr]">
        <div className="rounded-md border border-slate-700 bg-slate-950 p-4">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-white">Equity Curve</h2>
            <ModeBadge>DEMO DATA</ModeBadge>
          </div>
          <MiniChart />
          <DataTraceLine provider={demoPortfolio.trace.provider} dataset={demoPortfolio.trace.dataset} timestamp={demoPortfolio.trace.effectiveTimestamp} quality={demoPortfolio.trace.quality} />
        </div>
        <div className="rounded-md border border-slate-700 bg-slate-950 p-4">
          <h2 className="text-lg font-semibold text-white">Provider State</h2>
          <div className="mt-4 space-y-3">
            {["Market data", "Fundamentals", "Macro", "Options", "Broker"].map((item) => (
              <div key={item} className="flex items-center justify-between border-b border-slate-800 pb-2 text-sm">
                <span className="text-slate-300">{item}</span>
                <ModeBadge>{item === "Broker" ? "PAPER" : "DEMO DATA"}</ModeBadge>
              </div>
            ))}
          </div>
        </div>
      </section>
      <PositionsTable />
    </div>
  );
}

function Markets() {
  const ranked = rankSearch(
    demoSecurities.map((security) => ({ id: security.id, title: security.ticker, subtitle: security.name, keywords: [security.exchange, security.sector] })),
    "a"
  );
  return (
    <section className="rounded-md border border-slate-700 bg-slate-950 p-4">
      <h2 className="text-xl font-semibold text-white">Market Data Terminal</h2>
      <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        {demoSecurities.map((security) => (
          <Link key={security.id} href={`/security/${security.id}`} className="rounded-md border border-slate-700 bg-slate-900 p-4">
            <div className="flex items-center justify-between">
              <span className="text-lg font-semibold text-white">{security.ticker}</span>
              <span className={security.dayChangePercent >= 0 ? "text-emerald-300" : "text-rose-300"}>{security.dayChangePercent.toFixed(2)}%</span>
            </div>
            <p className="mt-1 text-sm text-slate-400">{security.name}</p>
            <p className="mt-3 text-2xl font-semibold text-slate-100">{security.currency} {security.lastPrice.toFixed(2)}</p>
            <DataTraceLine provider={security.trace.provider} dataset={security.trace.dataset} timestamp={security.trace.effectiveTimestamp} quality={security.trace.quality} />
          </Link>
        ))}
      </div>
      <p className="mt-4 text-sm text-slate-400">Cached search sample: {ranked.map((item) => item.title).join(", ")}</p>
    </section>
  );
}

function SecurityPage({ route }: { route: string }) {
  const id = route.split("/").at(-1) ?? "sec-aapl-us";
  const security = demoSecurities.find((item) => item.id === id) ?? demoSecurities[0];
  const setActive = useAppStore((state) => state.setActiveSecurityId);
  return (
    <section className="rounded-md border border-slate-700 bg-slate-950 p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-sm font-semibold uppercase text-cyan-300">Security</p>
          <h2 className="text-3xl font-semibold text-white">{security?.ticker} | {security?.name}</h2>
        </div>
        <button onClick={() => security && setActive(security.id)} className="rounded-md border border-cyan-500 px-3 py-2 text-sm font-semibold text-cyan-100">
          Set Active
        </button>
      </div>
      <div className="mt-6 grid gap-4 md:grid-cols-4">
        <StatBlock label="Last Price" value={`${security?.currency} ${security?.lastPrice.toFixed(2)}`} />
        <StatBlock label="Exchange" value={security?.exchange ?? "Data unavailable"} />
        <StatBlock label="Sector" value={security?.sector ?? "Data unavailable"} />
        <StatBlock label="Quality" value={security?.trace.quality ?? "Data unavailable"} />
      </div>
      {security ? <DataTraceLine provider={security.trace.provider} dataset={security.trace.dataset} timestamp={security.trace.effectiveTimestamp} quality={security.trace.quality} /> : null}
    </section>
  );
}

function OptionsView() {
  return (
    <section className="rounded-md border border-slate-700 bg-slate-950 p-4">
      <h2 className="text-xl font-semibold text-white">Options Analytics</h2>
      <div className="mt-4 overflow-hidden rounded-md border border-slate-700">
        <table className="w-full text-sm">
          <thead className="bg-slate-900 text-left text-xs uppercase text-slate-400">
            <tr>
              <th className="px-3 py-3">Strike</th>
              <th className="px-3 py-3">Call Delta</th>
              <th className="px-3 py-3">Put Delta</th>
              <th className="px-3 py-3">IV</th>
              <th className="px-3 py-3">Open Interest</th>
              <th className="px-3 py-3">GEX</th>
            </tr>
          </thead>
          <tbody>
            {demoOptionChain.map((row) => (
              <tr key={row.strike} className="border-t border-slate-800">
                <td className="px-3 py-3">{row.strike}</td>
                <td className="px-3 py-3">{row.callDelta.toFixed(2)}</td>
                <td className="px-3 py-3">{row.putDelta.toFixed(2)}</td>
                <td className="px-3 py-3">{(row.impliedVolatility * 100).toFixed(1)}%</td>
                <td className="px-3 py-3">{row.openInterest.toLocaleString()}</td>
                <td className="px-3 py-3">{row.gammaExposure.toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="mt-4 text-sm text-slate-400">Volatility surface, skew, max pain, payoff, and expected-move panels use deterministic demo calculations until connected option data are configured.</p>
    </section>
  );
}

function QuantView({ route }: { route: string }) {
  const isTradingView = route.includes("tradingview");
  return (
    <section className="grid gap-4 lg:grid-cols-[0.75fr_1.25fr]">
      <div className="rounded-md border border-slate-700 bg-slate-950 p-4">
        <h2 className="text-xl font-semibold text-white">{isTradingView ? "TradingView Pine Script Studio" : "Quant Research Laboratory"}</h2>
        <p className="mt-3 text-sm leading-6 text-slate-400">
          Demo workflows support factor analysis, strategy hypotheses, non-blocking backtests, walk-forward analysis, Monte Carlo, and model validation.
        </p>
        <div className="mt-4 space-y-2 text-sm text-slate-300">
          {terminalFunctions.filter((item) => item.category === "Quant").map((item) => (
            <Link className="block rounded border border-slate-800 px-3 py-2 hover:bg-slate-900" key={item.code} href={item.route}>
              {item.code} | {item.title}
            </Link>
          ))}
        </div>
      </div>
      <div className="rounded-md border border-slate-700 bg-slate-950 p-4">
        <div className="mb-3 flex items-center justify-between">
          <h3 className="font-semibold text-white">{isTradingView ? "Pine Preview" : "Research Notebook"}</h3>
          <ModeBadge tone="ok">CALCULATED</ModeBadge>
        </div>
        <pre className="min-h-[320px] overflow-auto rounded-md bg-slate-900 p-4 text-sm leading-6 text-cyan-100">
{`// KnK Capital demo research artifact
dataset: local-demo-fixtures
quality: DEMO DATA
signal: quality_momentum_demo
risk_gate: max_drawdown <= 10%
broker_action: none
`}
        </pre>
      </div>
    </section>
  );
}

function ReportsView() {
  return (
    <section className="rounded-md border border-slate-700 bg-slate-950 p-4">
      <h2 className="text-xl font-semibold text-white">Report Factory</h2>
      <div className="mt-4 grid gap-3 md:grid-cols-4">
        {["DCF workbook", "Portfolio-risk workbook", "Internal research deck", "Public PDF"].map((item) => (
          <div key={item} className="rounded-md border border-slate-700 bg-slate-900 p-4">
            <FileSpreadsheet className="h-5 w-5 text-cyan-300" />
            <h3 className="mt-3 font-semibold text-white">{item}</h3>
            <p className="mt-2 text-sm text-slate-400">Queued through report-engine with source appendix and disclosure page.</p>
          </div>
        ))}
      </div>
    </section>
  );
}

function SystemView() {
  return (
    <section className="rounded-md border border-slate-700 bg-slate-950 p-4">
      <h2 className="text-xl font-semibold text-white">System Health</h2>
      <div className="mt-4 grid gap-3 md:grid-cols-3">
        {[
          ["Public web", "Healthy"],
          ["Terminal web", "Healthy"],
          ["API", "Healthy"],
          ["Data worker", "Ready"],
          ["Quant worker", "Ready"],
          ["Report engine", "Ready"],
          ["PostgreSQL", "Configured"],
          ["Redis", "Configured"],
          ["Object storage", "Configured"],
          ["Broker heartbeat", "Waiting for local paper agent"],
          ["Provider status", "Demo fixtures"],
          ["Backup", "Script available"]
        ].map(([name, state]) => (
          <div key={name} className="rounded-md border border-slate-700 bg-slate-900 p-4">
            <div className="flex items-center gap-2">
              <HeartPulse className="h-4 w-4 text-emerald-300" />
              <span className="font-semibold text-white">{name}</span>
            </div>
            <p className="mt-2 text-sm text-slate-400">{state}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

function ResearchView() {
  return (
    <section className="rounded-md border border-slate-700 bg-slate-950 p-4">
      <h2 className="text-xl font-semibold text-white">Research Workspace</h2>
      <div className="mt-4 grid gap-4 md:grid-cols-3">
        {["Investment thesis", "Koyfin bridge", "Publishing approval"].map((item) => (
          <div key={item} className="rounded-md border border-slate-700 bg-slate-900 p-4">
            <BookOpen className="h-5 w-5 text-cyan-300" />
            <h3 className="mt-3 font-semibold text-white">{item}</h3>
            <p className="mt-2 text-sm leading-6 text-slate-400">Private notes, source attachments, provenance, and sanitized public copy state.</p>
          </div>
        ))}
      </div>
    </section>
  );
}

function DefaultWorkflow({ route }: { route: string }) {
  return (
    <section className="rounded-md border border-slate-700 bg-slate-950 p-4">
      <div className="flex items-center gap-2">
        <Activity className="h-5 w-5 text-cyan-300" />
        <h2 className="text-xl font-semibold text-white">{route.replace("/", "").replaceAll("-", " ") || "overview"}</h2>
      </div>
      <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-400">
        This workflow is wired into the terminal shell with demo data, environment badges, provenance requirements, job streaming contracts, audit logging expectations, and safe read-only broker design.
      </p>
    </section>
  );
}

function MainPanel({ route }: { route: string }) {
  if (route === "/overview" || route === "/home" || route === "/portfolio" || route === "/positions" || route === "/performance" || route === "/risk" || route === "/stress-tests" || route === "/hedge") return <Overview />;
  if (route === "/markets" || route === "/market-data" || route === "/screener" || route === "/watchlists") return <Markets />;
  if (route.startsWith("/security/") || route.startsWith("/chart/") || route.startsWith("/financials/") || route.startsWith("/valuation/")) return <SecurityPage route={route} />;
  if (route.startsWith("/options/")) return <OptionsView />;
  if (["/research", "/theses", "/ideas", "/publishing"].some((prefix) => route.startsWith(prefix))) return <ResearchView />;
  if (["/edge-lab", "/factor-lab", "/model-lab", "/quant", "/notebooks", "/backtests", "/strategies", "/tradingview"].some((prefix) => route.startsWith(prefix))) return <QuantView route={route} />;
  if (["/reports", "/excel-studio", "/deck-builder"].includes(route)) return <ReportsView />;
  if (route.startsWith("/settings") || ["/api-monitor", "/data-jobs", "/system-health", "/data-drop", "/data-catalogue", "/reconciliation"].includes(route)) return <SystemView />;
  return <DefaultWorkflow route={route} />;
}

export default function TerminalPage({ params }: { params: { slug?: string[] } }) {
  const route = routeFromParams(params.slug);
  const pathname = usePathname();

  return (
    <div className="min-h-screen terminal-grid">
      <Header />
      <div className="grid min-h-[calc(100vh-73px)] grid-cols-1 lg:grid-cols-[260px_1fr]">
        <Sidebar />
        <main className="p-4">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-md border border-slate-800 bg-slate-950 px-4 py-3">
            <div>
              <p className="text-xs uppercase text-slate-500">Workspace</p>
              <h2 className="font-semibold text-white">{pathname}</h2>
            </div>
            <div className="flex items-center gap-2 text-xs text-slate-400">
              <Lock className="h-4 w-4" />
              Authenticated terminal boundary
              <Bell className="ml-3 h-4 w-4" />
              3 demo alerts
              <Database className="ml-3 h-4 w-4" />
              Traceable figures
              <ShieldCheck className="ml-3 h-4 w-4" />
              Paper mode
            </div>
          </div>
          <MainPanel route={isTerminalRoute(route) ? route : "/overview"} />
        </main>
      </div>
    </div>
  );
}
