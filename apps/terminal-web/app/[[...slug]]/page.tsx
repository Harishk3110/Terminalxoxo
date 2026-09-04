"use client";

import { knkApi, type BacktestPayload, type MacroDashboardPayload, type PerformancePayload, type PortfolioPayload, type ProviderPayload, type RiskPayload, type SystemHealthPayload } from "@knk/api-client";
import { ModeBadge, StatBlock } from "@knk/design-system";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import dynamic from "next/dynamic";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useMemo, useState } from "react";
import { Bell, BookOpen, BriefcaseBusiness, ChartCandlestick, Database, HeartPulse, Lock, Search, Settings, ShieldCheck, Upload } from "lucide-react";

const ReactECharts = dynamic(() => import("echarts-for-react"), { ssr: false });

function routeFromParams(slug?: string[]) {
  return `/${slug?.join("/") ?? "overview"}`.replace(/\/$/, "");
}

const groups = [
  { label: "Markets", icon: ChartCandlestick, items: [["Overview", "/overview"], ["Macro", "/macro"], ["Markets", "/markets"], ["Security Master", "/screener"]] },
  { label: "Portfolio", icon: BriefcaseBusiness, items: [["Portfolio", "/portfolio"], ["Positions", "/positions"], ["Performance", "/performance"], ["Risk", "/risk"], ["Stress Tests", "/stress-tests"], ["Hedge", "/hedge"]] },
  { label: "Research", icon: BookOpen, items: [["Strategies", "/strategies"], ["Backtests", "/backtests"], ["Factor Lab", "/factor-lab"], ["TradingView", "/tradingview"]] },
  { label: "Data", icon: Database, items: [["Data Drop", "/data-drop"], ["Data Catalogue", "/data-catalogue"], ["Data Jobs", "/data-jobs"], ["API Monitor", "/api-monitor"]] },
  { label: "System", icon: Settings, items: [["Connections", "/settings/connections"], ["Security", "/settings/security"], ["System Health", "/system-health"]] }
];

function usePortfolio() {
  return useQuery({ queryKey: ["portfolio"], queryFn: () => knkApi.portfolio() });
}

function useRisk() {
  return useQuery({ queryKey: ["risk"], queryFn: () => knkApi.risk() });
}

function usePerformance() {
  return useQuery({ queryKey: ["performance"], queryFn: () => knkApi.performance() });
}

function Header() {
  const [query, setQuery] = useState("");
  const functionsQuery = useQuery({ queryKey: ["functions"], queryFn: () => knkApi.get<{ items: Array<{ code: string; title: string; route: string; status: string }> }>("/api/v1/functions") });
  const matches = useMemo(() => {
    const items = functionsQuery.data?.items ?? [];
    return items.filter((item) => `${item.code} ${item.title}`.toLowerCase().includes(query.toLowerCase())).slice(0, 6);
  }, [functionsQuery.data, query]);
  return (
    <header className="sticky top-0 z-30 border-b border-slate-700 bg-slate-950 px-4 py-3">
      <div className="grid gap-3 lg:grid-cols-[250px_1fr_auto] lg:items-center">
        <div>
          <p className="text-xs font-semibold uppercase text-cyan-300">KnK Capital</p>
          <h1 className="text-lg font-semibold tracking-normal text-white">Terminal</h1>
        </div>
        <div className="relative">
          <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
          <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search functions and workflows" className="h-10 w-full rounded-md border border-slate-700 bg-slate-900 pl-9 pr-3 text-sm text-slate-100 outline-none ring-cyan-500 focus:ring-2" />
          {query ? (
            <div className="absolute left-0 right-0 top-12 z-40 rounded-md border border-slate-700 bg-slate-950 p-2 shadow-xl">
              {matches.map((item) => (
                <Link key={item.code} href={item.route} className="flex items-center justify-between rounded px-3 py-2 text-sm text-slate-200 hover:bg-slate-800">
                  <span><span className="font-semibold text-cyan-300">{item.code}</span> {item.title}</span>
                  <span className="text-xs text-slate-500">{item.status}</span>
                </Link>
              ))}
            </div>
          ) : null}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <ModeBadge>DEMO DATA</ModeBadge>
          <ModeBadge tone="paper">PAPER</ModeBadge>
          <ModeBadge tone="ok">CALCULATED</ModeBadge>
        </div>
      </div>
    </header>
  );
}

function Sidebar() {
  return (
    <aside className="border-r border-slate-800 bg-slate-950 p-3">
      <nav className="space-y-5">
        {groups.map((group) => {
          const Icon = group.icon;
          return (
            <section key={group.label}>
              <div className="mb-2 flex items-center gap-2 px-2 text-xs font-semibold uppercase text-slate-400"><Icon className="h-4 w-4" />{group.label}</div>
              <div className="space-y-1">
                {group.items.map(([label, href]) => (
                  <Link key={href} href={href} className="block rounded px-2 py-1.5 text-sm text-slate-300 hover:bg-slate-800 hover:text-white">{label}</Link>
                ))}
              </div>
            </section>
          );
        })}
      </nav>
    </aside>
  );
}

function Panel({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="rounded-md border border-slate-700 bg-slate-950 p-4">
      <h2 className="text-xl font-semibold text-white">{title}</h2>
      <div className="mt-4">{children}</div>
    </section>
  );
}

function LoadingPanel({ title }: { title: string }) {
  return <Panel title={title}><p className="text-sm text-slate-400">Loading backend data...</p></Panel>;
}

function ErrorPanel({ title, error }: { title: string; error: unknown }) {
  return <Panel title={title}><p className="text-sm text-rose-300">{error instanceof Error ? error.message : "Backend request failed"}</p></Panel>;
}

function Overview() {
  const portfolio = usePortfolio();
  const risk = useRisk();
  const performance = usePerformance();
  const macro = useQuery({ queryKey: ["macro-dashboard"], queryFn: () => knkApi.macroDashboard() });
  const backtests = useQuery({ queryKey: ["backtests"], queryFn: () => knkApi.backtests() });
  if (portfolio.isLoading || risk.isLoading || performance.isLoading) return <LoadingPanel title="Overview" />;
  if (portfolio.error || risk.error || performance.error) return <ErrorPanel title="Overview" error={portfolio.error ?? risk.error ?? performance.error} />;
  const p = portfolio.data as PortfolioPayload;
  const r = risk.data as RiskPayload;
  const perf = performance.data as PerformancePayload;
  return (
    <div className="space-y-5">
      <div className="grid gap-4 md:grid-cols-4">
        <StatBlock label="Reference NAV" value={`SGD ${Number(p.portfolio.nav).toLocaleString()}`} sublabel={p.portfolio.quality} tone="positive" />
        <StatBlock label="Cash" value={`SGD ${Number(p.portfolio.cash).toLocaleString()}`} sublabel="Calculated from ledger" />
        <StatBlock label="TWR" value={`${(Number(perf.twr) * 100).toFixed(2)}%`} sublabel="Database snapshot" />
        <StatBlock label="95% VaR" value={`SGD ${Math.abs(Number(r.var_95)).toLocaleString()}`} sublabel={r.quality} tone="negative" />
      </div>
      <div className="grid gap-4 lg:grid-cols-[1.3fr_0.7fr]">
        <Panel title="Backtest Equity Curve">
          <EquityChart runs={backtests.data?.items ?? []} />
        </Panel>
        <Panel title="Macro Watchlist">
          <MacroList data={macro.data} compact />
        </Panel>
      </div>
      <PositionsTable portfolio={p} />
    </div>
  );
}

function EquityChart({ runs }: { runs: BacktestPayload[] }) {
  const curve = runs[0]?.equity_curve ?? [];
  const option = {
    backgroundColor: "transparent",
    grid: { left: 42, right: 18, top: 24, bottom: 28 },
    xAxis: { type: "category", data: curve.map((point) => point.date), axisLabel: { color: "#94a3b8" } },
    yAxis: { type: "value", axisLabel: { color: "#94a3b8" }, splitLine: { lineStyle: { color: "#334155" } } },
    series: [{ type: "line", data: curve.map((point) => Number(point.equity)), smooth: true, lineStyle: { color: "#22d3ee", width: 3 }, areaStyle: { color: "rgba(34, 211, 238, 0.15)" } }],
    tooltip: { trigger: "axis" }
  };
  return curve.length ? <ReactECharts option={option} style={{ height: 300, width: "100%" }} /> : <p className="text-sm text-slate-400">No backtest curve available.</p>;
}

function PositionsTable({ portfolio }: { portfolio: PortfolioPayload }) {
  return (
    <div className="overflow-hidden rounded-md border border-slate-700">
      <table className="w-full border-collapse text-sm">
        <thead className="bg-slate-900 text-left text-xs uppercase text-slate-400">
          <tr><th className="px-3 py-3">Symbol</th><th className="px-3 py-3">Qty</th><th className="px-3 py-3">Avg Cost</th><th className="px-3 py-3">Price</th><th className="px-3 py-3">Market Value</th><th className="px-3 py-3">Unrealised P&L</th><th className="px-3 py-3">Weight</th></tr>
        </thead>
        <tbody>
          {portfolio.positions.map((row) => (
            <tr key={row.id} className="border-t border-slate-800">
              <td className="px-3 py-3 font-semibold text-white">{row.symbol}</td>
              <td className="px-3 py-3">{Number(row.quantity).toLocaleString()}</td>
              <td className="px-3 py-3">{Number(row.average_cost).toFixed(2)}</td>
              <td className="px-3 py-3">{Number(row.market_price).toFixed(2)}</td>
              <td className="px-3 py-3">SGD {Number(row.market_value).toLocaleString()}</td>
              <td className="px-3 py-3">SGD {Number(row.unrealised_pnl).toLocaleString()}</td>
              <td className="px-3 py-3">{(Number(row.weight) * 100).toFixed(1)}%</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function MacroList({ data, compact = false }: { data?: MacroDashboardPayload; compact?: boolean }) {
  if (!data) return <p className="text-sm text-slate-400">Loading macro data...</p>;
  return (
    <div className={compact ? "space-y-2" : "grid gap-3 md:grid-cols-2 xl:grid-cols-3"}>
      {data.items.slice(0, compact ? 6 : data.items.length).map((item) => (
        <div key={item.series_id} className="rounded-md border border-slate-700 bg-slate-900 p-3">
          <div className="flex items-start justify-between gap-2">
            <div>
              <p className="text-xs font-semibold text-cyan-300">{item.series_id}</p>
              <h3 className="mt-1 text-sm font-semibold text-white">{item.title}</h3>
            </div>
            <ModeBadge tone={item.quality === "DEMO DATA" ? "demo" : "ok"}>{item.quality}</ModeBadge>
          </div>
          <p className="mt-3 text-2xl font-semibold text-slate-100">{item.latest_value ?? "Data unavailable"}</p>
          <p className="text-xs text-slate-400">{item.unit} | {item.frequency} | {item.latest_observation_date}</p>
          <p className="mt-1 text-xs text-slate-500">{item.source} | {item.revision_state}</p>
        </div>
      ))}
    </div>
  );
}

function MacroPage() {
  const macro = useQuery({ queryKey: ["macro-dashboard"], queryFn: () => knkApi.macroDashboard() });
  const backfill = useMutation({ mutationFn: () => knkApi.post("/api/v1/macro/backfills", { series_ids: ["FEDFUNDS", "DGS2", "DGS10"], observation_start: "2020-01-01" }) });
  if (macro.isLoading) return <LoadingPanel title="Macro" />;
  if (macro.error) return <ErrorPanel title="Macro" error={macro.error} />;
  return (
    <Panel title="Macro Dashboard">
      <div className="mb-4 flex flex-wrap gap-2">
        {["1Y", "3Y", "5Y", "10Y", "MAX", "Normalised", "Dual-Series", "Export CSV"].map((label) => <span key={label} className="rounded border border-slate-700 px-2 py-1 text-xs text-slate-300">{label}</span>)}
        <button onClick={() => backfill.mutate()} className="rounded-md bg-cyan-600 px-3 py-1 text-xs font-semibold text-white">Refresh FRED</button>
      </div>
      <MacroList data={macro.data} />
      {backfill.data ? <p className="mt-3 text-sm text-slate-400">Backfill state: {JSON.stringify(backfill.data)}</p> : null}
    </Panel>
  );
}

function PortfolioPage() {
  const queryClient = useQueryClient();
  const portfolio = usePortfolio();
  const [form, setForm] = useState({ symbol: "AAPL", quantity: "1", price: "200", fx_rate_to_base: "1.33" });
  const mutation = useMutation({
    mutationFn: () => knkApi.post("/api/v1/portfolios/default/transactions", { transaction_type: "BUY", trade_date: "2026-09-05", symbol: form.symbol, quantity: form.quantity, price: form.price, currency: "USD", fx_rate_to_base: form.fx_rate_to_base, fee: "1.00", notes: "Manual demo ledger entry" }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["portfolio"] })
  });
  if (portfolio.isLoading) return <LoadingPanel title="Portfolio" />;
  if (portfolio.error) return <ErrorPanel title="Portfolio" error={portfolio.error} />;
  return (
    <div className="space-y-4">
      <Panel title="Portfolio Ledger">
        <div className="grid gap-3 md:grid-cols-4">
          {Object.entries(form).map(([key, value]) => <input key={key} value={value} onChange={(event) => setForm((current) => ({ ...current, [key]: event.target.value }))} className="rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white" aria-label={key} />)}
        </div>
        <button onClick={() => mutation.mutate()} className="mt-3 rounded-md bg-cyan-600 px-3 py-2 text-sm font-semibold text-white">Record manual transaction</button>
        {mutation.error ? <p className="mt-2 text-sm text-rose-300">{mutation.error.message}</p> : null}
      </Panel>
      <PositionsTable portfolio={portfolio.data as PortfolioPayload} />
    </div>
  );
}

function RiskPage({ mode }: { mode: "risk" | "stress" | "hedge" | "performance" }) {
  const risk = useRisk();
  const performance = usePerformance();
  const stress = useQuery({ queryKey: ["stress"], queryFn: () => knkApi.stress() });
  const hedge = useQuery({ queryKey: ["hedge"], queryFn: () => knkApi.hedge() });
  if (risk.isLoading || performance.isLoading) return <LoadingPanel title="Risk" />;
  if (risk.error || performance.error) return <ErrorPanel title="Risk" error={risk.error ?? performance.error} />;
  if (mode === "performance") {
    const p = performance.data as PerformancePayload;
    return <Panel title="Performance"><div className="grid gap-4 md:grid-cols-3"><StatBlock label="TWR" value={`${(Number(p.twr) * 100).toFixed(2)}%`} /><StatBlock label="CAGR" value={`${(Number(p.cagr) * 100).toFixed(2)}%`} /><StatBlock label="Sharpe" value={Number(p.sharpe).toFixed(2)} /></div></Panel>;
  }
  if (mode === "stress") return <Panel title="Stress Tests"><pre className="overflow-auto rounded bg-slate-900 p-3 text-sm text-slate-200">{JSON.stringify(stress.data?.items ?? [], null, 2)}</pre></Panel>;
  if (mode === "hedge") return <Panel title="Hedge Recommendations"><pre className="overflow-auto rounded bg-slate-900 p-3 text-sm text-slate-200">{JSON.stringify(hedge.data ?? {}, null, 2)}</pre><p className="mt-3 text-sm text-slate-400">Manual recommendations only. No broker action path exists.</p></Panel>;
  const r = risk.data as RiskPayload;
  return <Panel title="Risk"><div className="grid gap-4 md:grid-cols-4"><StatBlock label="Beta" value={Number(r.beta).toFixed(2)} /><StatBlock label="Volatility" value={`${(Number(r.volatility) * 100).toFixed(2)}%`} /><StatBlock label="VaR 95" value={`SGD ${Math.abs(Number(r.var_95)).toLocaleString()}`} tone="negative" /><StatBlock label="CVaR 95" value={`SGD ${Math.abs(Number(r.cvar_95)).toLocaleString()}`} tone="negative" /></div></Panel>;
}

function StrategiesPage({ route }: { route: string }) {
  const strategies = useQuery({ queryKey: ["strategies"], queryFn: () => knkApi.strategies() });
  const backtests = useQuery({ queryKey: ["backtests"], queryFn: () => knkApi.backtests() });
  if (route.includes("backtests")) return <Panel title="Backtests"><EquityChart runs={backtests.data?.items ?? []} /><pre className="mt-4 overflow-auto rounded bg-slate-900 p-3 text-sm text-slate-200">{JSON.stringify(backtests.data?.items?.[0]?.metrics ?? {}, null, 2)}</pre></Panel>;
  return <Panel title={route.includes("factor") ? "Factor Lab" : "Strategies"}><div className="grid gap-3 md:grid-cols-2">{(strategies.data?.items ?? []).map((item) => <div key={String(item.id)} className="rounded-md border border-slate-700 bg-slate-900 p-4"><h3 className="font-semibold text-white">{String(item.name)}</h3><p className="mt-2 text-sm text-slate-400">{String(item.description)}</p><ModeBadge tone="ok">{String(item.status)}</ModeBadge></div>)}</div></Panel>;
}

function DataPage({ route }: { route: string }) {
  const queryClient = useQueryClient();
  const datasets = useQuery({ queryKey: ["datasets"], queryFn: () => knkApi.datasets() });
  const jobs = useQuery({ queryKey: ["jobs"], queryFn: () => knkApi.jobs() });
  const upload = useMutation({
    mutationFn: async (file: File) => {
      const body = new FormData();
      body.append("file", file);
      return knkApi.post("/api/v1/uploads", body);
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["datasets"] })
  });
  if (route.includes("data-jobs")) return <Panel title="Data Jobs"><pre className="overflow-auto rounded bg-slate-900 p-3 text-sm text-slate-200">{JSON.stringify(jobs.data?.items ?? [], null, 2)}</pre></Panel>;
  if (route.includes("data-catalogue")) return <Panel title="Data Catalogue"><pre className="overflow-auto rounded bg-slate-900 p-3 text-sm text-slate-200">{JSON.stringify(datasets.data?.items ?? [], null, 2)}</pre></Panel>;
  return <Panel title="Data Drop"><label className="inline-flex cursor-pointer items-center gap-2 rounded-md bg-cyan-600 px-3 py-2 text-sm font-semibold text-white"><Upload className="h-4 w-4" />Upload CSV<input type="file" className="hidden" onChange={(event) => event.target.files?.[0] && upload.mutate(event.target.files[0])} /></label><pre className="mt-4 overflow-auto rounded bg-slate-900 p-3 text-sm text-slate-200">{JSON.stringify(upload.data ?? { state: "waiting_for_file" }, null, 2)}</pre></Panel>;
}

function SystemPage({ route }: { route: string }) {
  const health = useQuery({ queryKey: ["system-health"], queryFn: () => knkApi.systemHealth() });
  const providers = useQuery({ queryKey: ["providers"], queryFn: () => knkApi.providers() });
  if (route.includes("connections")) return <Connections providers={providers.data} />;
  if (route.includes("security")) return <Panel title="Security Settings"><p className="text-sm text-slate-300">Argon2 password hashing, TOTP setup, HTTP-only cookies, CORS restrictions, security headers, and audit logging are implemented in the API boundary.</p></Panel>;
  if (health.isLoading) return <LoadingPanel title="System Health" />;
  if (health.error) return <ErrorPanel title="System Health" error={health.error} />;
  return <SystemHealth data={health.data as SystemHealthPayload} />;
}

function Connections({ providers }: { providers?: ProviderPayload }) {
  return <Panel title="Connections"><div className="grid gap-3 md:grid-cols-3">{(providers?.items ?? []).map((item) => <div key={item.name} className="rounded-md border border-slate-700 bg-slate-900 p-4"><h3 className="font-semibold text-white">{item.name}</h3><p className="mt-2 text-sm text-slate-400">{item.type} | configured: {String(item.configured)}</p><ModeBadge tone={item.connection_state === "CONNECTED" ? "ok" : "warn"}>{item.connection_state}</ModeBadge><p className="mt-2 text-xs text-slate-500">{item.last_error ?? item.capabilities.join(", ")}</p></div>)}</div></Panel>;
}

function SystemHealth({ data }: { data: SystemHealthPayload }) {
  return <Panel title="System Health"><div className="grid gap-3 md:grid-cols-3">{Object.entries(data.checks).map(([name, state]) => <div key={name} className="rounded-md border border-slate-700 bg-slate-900 p-4"><HeartPulse className="h-4 w-4 text-emerald-300" /><h3 className="mt-2 font-semibold text-white">{name}</h3><p className="text-sm text-slate-400">{state}</p></div>)}</div><pre className="mt-4 overflow-auto rounded bg-slate-900 p-3 text-sm text-slate-200">{JSON.stringify(data.counts, null, 2)}</pre></Panel>;
}

function PinePage() {
  const pine = useQuery({ queryKey: ["pine"], queryFn: () => knkApi.pine() });
  return <Panel title="TradingView Pine Export"><pre className="overflow-auto rounded bg-slate-900 p-3 text-sm text-cyan-100">{String(pine.data?.source ?? "Loading Pine export...")}</pre><p className="mt-3 text-sm text-slate-400">Compatibility: {String(pine.data?.compatibility ?? "checking")}. Manual export only.</p></Panel>;
}

function MainPanel({ route }: { route: string }) {
  if (["/overview", "/home"].includes(route)) return <Overview />;
  if (route === "/macro") return <MacroPage />;
  if (["/portfolio", "/positions"].includes(route)) return <PortfolioPage />;
  if (route === "/performance") return <RiskPage mode="performance" />;
  if (route === "/risk") return <RiskPage mode="risk" />;
  if (route === "/stress-tests") return <RiskPage mode="stress" />;
  if (route === "/hedge") return <RiskPage mode="hedge" />;
  if (["/strategies", "/backtests", "/factor-lab"].includes(route) || route.startsWith("/backtests/")) return <StrategiesPage route={route} />;
  if (route === "/tradingview") return <PinePage />;
  if (["/data-drop", "/data-catalogue", "/data-jobs", "/api-monitor"].includes(route)) return <DataPage route={route} />;
  if (route.startsWith("/settings") || route === "/system-health") return <SystemPage route={route} />;
  if (["/markets", "/screener"].includes(route)) return <Panel title="Security Master"><Instruments /></Panel>;
  return <Overview />;
}

function Instruments() {
  const instruments = useQuery({ queryKey: ["instruments"], queryFn: () => knkApi.instruments() });
  return <pre className="overflow-auto rounded bg-slate-900 p-3 text-sm text-slate-200">{JSON.stringify(instruments.data?.items ?? [], null, 2)}</pre>;
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
            <div><p className="text-xs uppercase text-slate-500">Workspace</p><h2 className="font-semibold text-white">{pathname}</h2></div>
            <div className="flex items-center gap-2 text-xs text-slate-400"><Lock className="h-4 w-4" />Authenticated boundary <Bell className="ml-3 h-4 w-4" />Alerts <Database className="ml-3 h-4 w-4" />Database-backed <ShieldCheck className="ml-3 h-4 w-4" />Paper mode</div>
          </div>
          <MainPanel route={route} />
        </main>
      </div>
    </div>
  );
}
