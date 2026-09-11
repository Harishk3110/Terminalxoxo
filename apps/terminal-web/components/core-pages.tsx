"use client";
import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { knkApi } from "@knk/api-client";
import {
  ArrowDownToLine,
  Copy,
  Play,
  Plus,
  RefreshCw,
  Save,
  Shield,
  X,
} from "lucide-react";
import { records, usePortfolio, useTabState, useTerminal } from "./context";
import { macroProvenance, macroRange } from "./macro-data";
import {
  Badge,
  Chart,
  COLORS,
  DataTable,
  Empty,
  Field,
  IconButton,
  Kpis,
  LineChart,
  Panel,
  exportCsv,
  money,
  number,
  pct,
  timestamp,
  tone,
  type Column,
} from "./ui";
import type {
  Health,
  MacroDashboardPayload,
  PortfolioData,
  Row,
  Run,
  Scenario,
} from "./types";

const positionColumns: Column[] = [
  { key: "symbol", label: "Security", size: 85 },
  { key: "quantity", label: "Quantity", numeric: true, size: 85 },
  { key: "market_price", label: "Last", numeric: true, size: 90 },
  { key: "market_value", label: "Value (SGD)", numeric: true, size: 125 },
  { key: "weight", label: "Weight", numeric: true, percent: true, size: 85 },
  {
    key: "unrealised_pnl",
    label: "Unrealised P&L",
    numeric: true,
    money: true,
    size: 125,
  },
  { key: "sector", label: "Sector", size: 155 },
  { key: "currency", label: "CCY", size: 60 },
  { key: "source", label: "Source", size: 110 },
  {
    key: "as_of",
    label: "Data as of",
    size: 170,
    format: (v) => timestamp(String(v)),
  },
];
const macroColumns: Column[] = [
  { key: "series_id", label: "Series", size: 100 },
  { key: "latest_value", label: "Latest", numeric: true, size: 86 },
  {
    key: "change",
    label: "Change",
    numeric: true,
    size: 85,
    format: (v) => <span className={tone(v)}>{number(v)}</span>,
  },
  { key: "unit", label: "Unit", size: 125 },
  { key: "latest_observation_date", label: "Date", size: 96 },
  {
    key: "quality",
    label: "State",
    size: 100,
    format: (v) => <Badge>{String(v)}</Badge>,
  },
];
export function PageTitle({
  code,
  title,
  children,
}: {
  code: string;
  title: string;
  children?: React.ReactNode;
}) {
  return (
    <div className="page-toolbar">
      <span className="page-code">{code}</span>
      <h1>{title}</h1>
      <span className="spacer" />
      {children}
    </div>
  );
}
export function useApi<T>(key: string, path: string, enabled = true) {
  return useQuery({
    queryKey: [key, path],
    enabled,
    queryFn: ({ signal }) => knkApi.get<T>(path, signal),
  });
}
function Positions({
  data,
  id = "holdings",
  compact = false,
}: {
  data?: PortfolioData;
  id?: string;
  compact?: boolean;
}) {
  const { open, selectSecurity } = useTerminal();
  return (
    <DataTable
      id={id}
      compact={compact}
      rows={records(data?.positions ?? [])}
      columns={positionColumns}
      onSelect={(row) => {
        selectSecurity(String(row.symbol));
        open(
          `/security/${row.symbol}`,
          `${row.symbol} DES`,
          false,
          String(row.symbol),
        );
      }}
    />
  );
}

export function OverviewPage() {
  const query = usePortfolio();
  const data = query.data;
  const macro = useApi<MacroDashboardPayload>(
    "macro",
    "/api/v1/macro/dashboard",
  );
  const alerts = useApi<{ items: Row[] }>("alerts", "/api/v1/alerts");
  const health = useApi<Health>("overview-health", "/api/v1/terminal/health");
  const { open } = useTerminal();
  const p = data?.portfolio,
    r = data?.risk,
    perf = data?.performance;
  return (
    <>
      <PageTitle code="HOME" title="Market Pulse">
        <span className="secondary mono">KNK REFERENCE / SGD</span>
        <Badge>DEMO DATA</Badge>
        <IconButton label="Refresh overview" onClick={() => query.refetch()}>
          <RefreshCw size={13} />
        </IconButton>
      </PageTitle>
      <Kpis
        source={data?.source}
        asOf={data?.as_of}
        items={[
          { label: "Reference NAV", value: money(p?.nav) },
          { label: "Cash", value: money(p?.cash) },
          {
            label: "Since inception",
            value: pct(perf?.twr),
            className: tone(perf?.twr),
          },
          { label: "Gross exposure", value: pct(r?.gross_exposure) },
          { label: "Portfolio beta", value: number(r?.beta) },
          {
            label: "VaR / 95%",
            value: money(r?.var_95),
            className: "negative",
          },
        ]}
      />
      <div className="page-grid overview-grid">
        <Panel
          title="Portfolio equity / SPY benchmark"
          source={data?.source}
          asOf={data?.as_of}
          quality={data?.quality}
          loading={query.isLoading}
          error={query.error}
          onRefresh={() => query.refetch()}
          rows={records(data?.curve ?? [])}
        >
          <LineChart
            label="Portfolio equity versus benchmark"
            rows={records(data?.curve ?? [])}
            keys={[
              { key: "equity", name: "KnK reference", color: COLORS.amber },
              { key: "benchmark", name: "SPY benchmark", color: COLORS.blue },
            ]}
          />
        </Panel>
        <Panel
          title="Allocation / current positions"
          source={data?.source}
          asOf={data?.as_of}
          quality={data?.quality}
        >
          <Chart
            label="Portfolio allocation"
            option={{
              tooltip: { trigger: "item", formatter: "{b}: {d}%" },
              legend: {
                orient: "vertical",
                right: 12,
                top: "center",
                textStyle: { color: COLORS.text, fontSize: 10 },
              },
              series: [
                {
                  type: "pie",
                  radius: ["45%", "72%"],
                  center: ["35%", "52%"],
                  label: { show: false },
                  itemStyle: { borderColor: COLORS.panel, borderWidth: 2 },
                  data: [
                    ...(data?.positions ?? []).map((p) => ({
                      name: p.symbol,
                      value: Number(p.market_value),
                    })),
                    { name: "Cash", value: Number(p?.cash ?? 0) },
                  ],
                },
              ],
            }}
          />
        </Panel>
        <Panel
          title="Holdings / reference ledger"
          source={data?.source}
          asOf={data?.as_of}
          quality={data?.quality}
          actions={
            <button
              className="icon-button action"
              title="Open Portfolio"
              aria-label="Open Portfolio"
              onClick={() => open("/portfolio", "PORT")}
            >
              <Plus size={12} />
            </button>
          }
        >
          <Positions data={data} id="overview-holdings" compact />
        </Panel>
        <Panel
          title="Macro monitor"
          {...macroProvenance(macro.data?.items.slice(0, 8) ?? [])}
          error={macro.error}
          loading={macro.isLoading}
        >
          <DataTable
            id="macro-monitor"
            compact
            rows={records(macro.data?.items.slice(0, 8) ?? [])}
            columns={macroColumns}
            onSelect={() => open("/macro", "MACRO")}
          />
        </Panel>
        <Panel
          title="Alerts / risk observations"
          source="KnK alert records"
          asOf={data?.as_of}
          quality="DEMO DATA"
        >
          {alerts.data?.items.map((a, i) => (
            <div className="list-record" key={String(a.id ?? i)}>
              <strong>
                <Badge>{String(a.severity)}</Badge> {String(a.title)}
              </strong>
              <p>{String(a.message ?? a.state ?? "")}</p>
            </div>
          ))}
        </Panel>
        <Panel
          title="Operations / current probes"
          source="Live service probes"
          asOf={health.data?.as_of}
          quality="OBSERVED"
        >
          <DataTable
            id="overview-operations"
            compact
            rows={records(health.data?.items.slice(0, 5) ?? [])}
            columns={[
              { key: "service", label: "Service", size: 145 },
              {
                key: "state",
                label: "State",
                size: 125,
                format: (v) => <Badge>{String(v)}</Badge>,
              },
            ]}
            onSelect={() => open("/system-health", "HEALTH")}
          />
        </Panel>
      </div>
    </>
  );
}

export function PortfolioPage() {
  const query = usePortfolio();
  const data = query.data;
  const { open } = useTerminal();
  const client = useQueryClient();
  const [tab, setTab] = useTabState("portfolio-tab", "Holdings");
  const [modal, setModal] = useState(false);
  const [error, setError] = useState("");
  const [form, setForm] = useState({
    transaction_type: "BUY",
    symbol: "AAPL",
    quantity: "1",
    price: "",
    currency: "USD",
    fx_rate_to_base: "",
    fee: "0",
    trade_date: new Date().toISOString().slice(0, 10),
    notes: "Manual demo ledger entry",
  });
  const { bootstrap } = useTerminal();
  const mutate = useMutation({
    onMutate: () => client.cancelQueries({ queryKey: ["terminal-portfolio"] }),
    mutationFn: () =>
      knkApi.post("/api/v1/portfolios/default/transactions", form),
    onSuccess: async () => {
      await client.invalidateQueries();
      setModal(false);
      setError("");
    },
    onError: (e: Error) => setError(e.message),
  });
  function showTransaction() {
    const q = bootstrap.quotes.find((q) => q.symbol === form.symbol);
    setForm((f) => ({
      ...f,
      price: String(q?.price ?? ""),
      fx_rate_to_base: String(
        data?.positions.find((p) => p.symbol === f.symbol)?.fx_rate ?? "1",
      ),
    }));
    setModal(true);
  }
  return (
    <>
      <PageTitle code="PORT" title="Portfolio / Reference Ledger">
        <button disabled={!data || query.isFetching} onClick={showTransaction}>
          <Plus size={12} />
          Add manual transaction
        </button>
        <button
          onClick={() => {
            knkApi
              .post("/api/v1/portfolios/default/recalculate")
              .then(() => client.invalidateQueries())
              .catch((e) => setError(e.message));
          }}
        >
          <RefreshCw size={12} />
          Recalculate
        </button>
        <IconButton
          label="Export holdings"
          onClick={() => exportCsv("holdings", records(data?.positions ?? []))}
        >
          <ArrowDownToLine size={13} />
        </IconButton>
      </PageTitle>
      <Kpis
        source={data?.source}
        asOf={data?.as_of}
        items={[
          { label: "Reference NAV", value: money(data?.portfolio.nav) },
          { label: "Broker NAV", value: "NOT CONNECTED" },
          { label: "Invested", value: money(data?.portfolio.market_value) },
          { label: "Cash", value: money(data?.portfolio.cash) },
          { label: "Positions", value: number(data?.positions.length, 0) },
          {
            label: "Unrealised P&L",
            value: money(
              data?.positions.reduce((a, p) => a + Number(p.unrealised_pnl), 0),
            ),
          },
        ]}
      />
      <div className="segmented" role="tablist" aria-label="Portfolio views">
        {["Holdings", "Transactions", "Cash", "Allocation", "Broker View"].map(
          (t) => (
            <button
              role="tab"
              aria-selected={tab === t}
              className={tab === t ? "active" : ""}
              key={t}
              onClick={() => setTab(t)}
            >
              {t}
            </button>
          ),
        )}
      </div>
      {error && (
        <p className="negative" role="alert">
          {error}
        </p>
      )}
      <Panel
        className="page-grid"
        title={tab}
        source={data?.source}
        asOf={data?.as_of}
        quality={data?.quality}
        loading={query.isLoading}
        error={query.error}
        onRefresh={() => query.refetch()}
      >
        {tab === "Holdings" ? (
          <Positions data={data} />
        ) : tab === "Transactions" ? (
          <DataTable
            id="transactions"
            rows={records(data?.transactions ?? [])}
            columns={[
              { key: "trade_date", label: "Date", size: 100 },
              { key: "type", label: "Type", size: 85 },
              { key: "symbol", label: "Security", size: 90 },
              { key: "quantity", label: "Quantity", numeric: true },
              { key: "price", label: "Price", numeric: true },
              { key: "fee", label: "Fee", numeric: true },
              { key: "currency", label: "CCY", size: 65 },
              { key: "fx_rate_to_base", label: "FX to SGD", numeric: true },
              { key: "source", label: "Source" },
              { key: "notes", label: "Notes", size: 240 },
            ]}
          />
        ) : tab === "Cash" ? (
          <DataTable
            id="cash"
            rows={records(data?.cash ?? [])}
            columns={[
              { key: "currency", label: "Currency" },
              { key: "amount", label: "Balance", numeric: true },
              { key: "as_of", label: "As of", size: 220 },
            ]}
          />
        ) : tab === "Broker View" ? (
          <Empty
            title="IBKR paper account not connected"
            detail="Reference ledger balances are shown separately from broker balances."
          >
            <button onClick={() => open("/settings/connections", "CONN")}>
              Connections
            </button>
          </Empty>
        ) : (
          <Chart
            label="Portfolio position weights"
            option={{
              xAxis: {
                type: "category",
                data: data?.positions.map((p) => p.symbol),
              },
              yAxis: {
                type: "value",
                axisLabel: { formatter: (v: number) => `${v}%` },
                splitLine: { lineStyle: { color: COLORS.grid } },
              },
              series: [
                {
                  type: "bar",
                  data: data?.positions.map((p) => Number(p.weight) * 100),
                  barMaxWidth: 40,
                },
              ],
            }}
          />
        )}
      </Panel>
      <div className="control-row">
        <button onClick={() => open("/risk", "RISK")}>Risk</button>
        <button onClick={() => open("/stress-tests", "STRESS")}>
          Stress tests
        </button>
        <button onClick={() => open("/hedge", "HEDGE")}>Hedge analysis</button>
        <span className="spacer" />
        <Badge>MANUAL LEDGER</Badge>
        <span className="source-note">{timestamp(data?.as_of)} SGT</span>
      </div>
      {modal && (
        <div className="modal-backdrop">
          <section
            role="dialog"
            aria-label="Manual transaction"
            className="modal"
          >
            <header className="modal-title">
              <h2>ADD MANUAL DEMO TRANSACTION</h2>
              <IconButton
                label="Close transaction"
                onClick={() => setModal(false)}
              >
                <X size={14} />
              </IconButton>
            </header>
            <form
              onSubmit={(e) => {
                e.preventDefault();
                mutate.mutate();
              }}
            >
              <div className="compact-form">
                <Field label="Transaction type">
                  <select
                    value={form.transaction_type}
                    onChange={(e) =>
                      setForm({ ...form, transaction_type: e.target.value })
                    }
                  >
                    {["BUY", "SELL", "DIVIDEND", "FEE"].map((t) => (
                      <option key={t}>{t}</option>
                    ))}
                  </select>
                </Field>
                <Field label="Security">
                  <select
                    aria-label="Transaction security"
                    value={form.symbol}
                    onChange={(e) => {
                      const q = bootstrap.quotes.find(
                        (q) => q.symbol === e.target.value,
                      );
                      setForm({
                        ...form,
                        symbol: e.target.value,
                        price: String(q?.price ?? ""),
                        currency: q?.currency ?? "USD",
                      });
                    }}
                  >
                    {bootstrap.quotes.map((q) => (
                      <option key={q.id}>{q.symbol}</option>
                    ))}
                  </select>
                </Field>
                {(["quantity", "price", "fx_rate_to_base", "fee"] as const).map(
                  (k) => (
                    <Field key={k} label={k.replaceAll("_", " ")}>
                      <input
                        aria-label={`Transaction ${k}`}
                        required
                        type="number"
                        min={k === "fee" ? 0 : 0.000001}
                        step="any"
                        value={form[k]}
                        onChange={(e) =>
                          setForm({ ...form, [k]: e.target.value })
                        }
                      />
                    </Field>
                  ),
                )}
                <Field label="Trade date">
                  <input
                    required
                    type="date"
                    value={form.trade_date}
                    onChange={(e) =>
                      setForm({ ...form, trade_date: e.target.value })
                    }
                  />
                </Field>
                <Field label="Currency">
                  <input value={form.currency} readOnly />
                </Field>
              </div>
              <div className="form-actions">
                <Badge>DEMO DATA</Badge>
                <span className="spacer" />
                <button
                  className="primary-button"
                  disabled={mutate.isPending}
                  type="submit"
                >
                  {mutate.isPending ? "Recording..." : "Record transaction"}
                </button>
              </div>
              {error && (
                <p className="error-state" role="alert">
                  {error}
                </p>
              )}
            </form>
          </section>
        </div>
      )}
    </>
  );
}

export function RiskPage() {
  const query = usePortfolio();
  const d = query.data;
  const { open } = useTerminal();
  const hasVariance = d?.positions.some((p) =>
    Number.isFinite(p.risk_contribution),
  );
  const correlationCells =
    d?.correlation.values.flatMap((row, y) =>
      row.flatMap((value, x) =>
        value !== null && Number.isFinite(value) ? [[x, y, value]] : [],
      ),
    ) ?? [];
  return (
    <>
      <PageTitle code="RISK" title="Portfolio Risk / Historical Simulation">
        <button onClick={() => open("/stress-tests", "STRESS")}>
          <Shield size={12} />
          Stress portfolio
        </button>
      </PageTitle>
      <Kpis
        source={d?.source}
        asOf={d?.as_of}
        items={[
          { label: "Volatility", value: pct(d?.risk.volatility) },
          { label: "Portfolio beta", value: number(d?.risk.beta) },
          {
            label: "VaR 95% / 1D",
            value: money(d?.risk.var_95),
            className: "negative",
          },
          {
            label: "VaR 99% / 1D",
            value: money(d?.risk.var_99),
            className: "negative",
          },
          {
            label: "CVaR 95%",
            value: money(d?.risk.cvar_95),
            className: "negative",
          },
          { label: "Concentration", value: pct(d?.risk.concentration) },
        ]}
      />
      <div className="page-grid equal-grid">
        <Panel
          title="Position variance contribution"
          source={d?.source}
          asOf={d?.as_of}
          quality={d?.quality}
          error={query.error}
          loading={query.isLoading}
        >
          {hasVariance ? (
            <Chart
              label="Position variance contribution"
              option={{
                xAxis: {
                  type: "category",
                  data: d?.positions.map((p) => p.symbol),
                },
                yAxis: {
                  type: "value",
                  axisLabel: {
                    formatter: (value: number) =>
                      `${(value * 100).toFixed(0)}%`,
                  },
                  splitLine: { lineStyle: { color: COLORS.grid } },
                },
                series: [
                  {
                    type: "bar",
                    barMaxWidth: 40,
                    data: d?.positions.map((p) =>
                      Number.isFinite(p.risk_contribution)
                        ? p.risk_contribution
                        : null,
                    ),
                  },
                ],
              }}
            />
          ) : (
            <Empty
              title="INSUFFICIENT DATA"
              detail="Variance contributions are unavailable for this snapshot."
            />
          )}
        </Panel>
        <Panel
          title="Daily return correlation"
          source={d?.source}
          asOf={d?.as_of}
          quality={d?.quality}
          error={query.error}
          loading={query.isLoading}
        >
          {correlationCells.length ? (
            <Chart
              label="Correlation matrix"
              option={{
                tooltip: {
                  position: "top",
                  formatter: (p: unknown) => {
                    const v = (p as { data: number[] }).data;
                    return `${d?.correlation.symbols[v[0]]} / ${d?.correlation.symbols[v[1]]}: ${number(v[2])}`;
                  },
                },
                grid: { left: 50, right: 12, top: 12, bottom: 30 },
                xAxis: { type: "category", data: d?.correlation.symbols },
                yAxis: { type: "category", data: d?.correlation.symbols },
                visualMap: {
                  show: false,
                  min: -1,
                  max: 1,
                  inRange: { color: [COLORS.red, COLORS.panel, COLORS.blue] },
                },
                series: [
                  {
                    type: "heatmap",
                    label: {
                      show: true,
                      fontSize: 10,
                      formatter: (p: unknown) =>
                        number((p as { data: number[] }).data[2]),
                    },
                    data: correlationCells,
                  },
                ],
              }}
            />
          ) : (
            <Empty
              title="INSUFFICIENT DATA"
              detail="No eligible return pairs are available for this snapshot."
            />
          )}
        </Panel>
        <Panel
          title="Risk exposure decomposition"
          source={d?.source}
          asOf={d?.as_of}
          quality={d?.quality}
        >
          <DataTable
            id="risk-contribution"
            rows={records(d?.positions ?? [])}
            columns={[
              { key: "symbol", label: "Security", size: 90 },
              {
                key: "weight",
                label: "Weight",
                numeric: true,
                percent: true,
                size: 85,
              },
              { key: "beta", label: "Beta", numeric: true, size: 85 },
              {
                key: "risk_contribution",
                label: "Variance share",
                numeric: true,
                percent: true,
                size: 125,
              },
              { key: "sector", label: "Sector", size: 155 },
              { key: "currency", label: "CCY", size: 65 },
            ]}
          />
        </Panel>
        <Panel
          title="Drawdown history"
          source={d?.source}
          asOf={d?.as_of}
          quality={d?.quality}
        >
          <LineChart
            label="Risk drawdown history"
            rows={records(d?.curve ?? [])}
            keys={[{ key: "drawdown", name: "Drawdown", color: COLORS.red }]}
            percent
          />
        </Panel>
      </div>
      <p className="source-note">
        Current weights / daily horizon / empirical 5th and 1st percentiles /
        spot FX. {d?.warnings[1]}
      </p>
    </>
  );
}

export function StressPage() {
  const { bootstrap, config, setConfig } = useTerminal();
  const client = useQueryClient();
  const [scenario, setScenario] = useTabState<Scenario>(
    "scenario",
    bootstrap.scenarios[1],
  );
  const [search, setSearch] = useState("");
  const [view, setView] = useTabState("stress-view", "Positions");
  const [runId, setRunId] = useTabState("stress-run", "");
  const [saved, setSaved] = useTabState<Scenario[]>("saved-scenarios", []);
  const [compare, setCompare] = useState(false);
  const recent = useApi<{ items: Run[] }>(
    "stress-runs",
    "/api/v1/terminal/runs?kind=stress",
  );
  const current = useQuery({
    queryKey: ["run", runId],
    queryFn: ({ signal }) =>
      knkApi.get<Run>(`/api/v1/terminal/runs/${runId}`, signal),
    enabled: !!runId,
    refetchInterval: (q) =>
      ["QUEUED", "RUNNING"].includes(q.state.data?.status ?? "") ? 500 : false,
  });
  const run = useMutation({
    mutationFn: () =>
      knkApi.post<Run>("/api/v1/terminal/runs", {
        kind: "stress",
        name: scenario.name,
        parameters: scenario,
      }),
    onSuccess: (r) => {
      setRunId(r.id);
      setConfig((c) => ({ ...c, inspectRunId: r.id, inspector: true }));
      client.setQueryData(["run", r.id], r);
      recent.refetch();
    },
  });
  useEffect(() => {
    if (runId && config.inspectRunId !== runId)
      setConfig((c) => ({ ...c, inspectRunId: runId }));
  }, [runId, config.inspectRunId, setConfig]);
  const result = current.data?.result;
  const active = ["QUEUED", "RUNNING"].includes(current.data?.status ?? "");
  const contributions = useMemo(() => result?.contributions ?? [], [result]);
  const rows = useMemo(() => {
    if (view === "Positions" || view === "Contribution") return contributions;
    if (view === "Factors")
      return (result?.factor_contributions ?? []).map((row: Row) => ({
        ...row,
        group: row.factor,
      }));
    if (view === "Assumptions")
      return Object.entries(current.data?.parameters ?? scenario).map(
        ([factor, value]) => ({ factor, value: String(value) }),
      );
    const group =
      view === "Sectors"
        ? "sector"
        : view === "Countries"
          ? "country"
          : "currency";
    const map = new Map<string, Row>();
    for (const row of contributions) {
      const key = String(row[group]);
      const existing = map.get(key) ?? { group: key, pnl: 0, market_value: 0 };
      existing.pnl = Number(existing.pnl) + Number(row.pnl);
      existing.market_value =
        Number(existing.market_value) + Number(row.market_value);
      map.set(key, existing);
    }
    return [...map.values()];
  }, [view, contributions, current.data, scenario, result]);
  const exportRun = async () => {
    if (!runId) return;
    const r = await knkApi.get<{ download_url: string }>(
      `/api/v1/terminal/runs/${runId}/export`,
    );
    window.open(knkApi.downloadUrl(r.download_url), "_blank", "noopener");
  };
  return (
    <>
      <PageTitle code="STRESS" title="Stress Testing">
        <Badge>INTERNAL LEDGER</Badge>
        <Badge>{result?.quality ?? "ASSUMPTIONS"}</Badge>
        <Badge>{result?.state ?? "NOT RUN"}</Badge>
      </PageTitle>
      <div className="stress-layout">
        <Panel
          title="Scenario library"
          source="KnK scenario templates"
          asOf={bootstrap.as_of}
          quality="ASSUMPTIONS"
        >
          <div className="table-toolbar">
            <input
              aria-label="Search scenarios"
              placeholder="Search scenarios"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          <div className="scenario-library">
            {[...bootstrap.scenarios, ...saved]
              .filter((s) =>
                s.name.toLowerCase().includes(search.toLowerCase()),
              )
              .map((s) => (
                <button
                  className={`scenario-row ${scenario.id === s.id ? "selected" : ""}`}
                  key={s.id}
                  onClick={() => setScenario(s)}
                >
                  <span className="scenario-dot" />
                  {s.name}
                </button>
              ))}
            <div className="rail-top">Recent runs</div>
            {recent.data?.items.slice(0, 8).map((r) => (
              <button
                key={r.id}
                className="scenario-row"
                onClick={() => {
                  setRunId(r.id);
                  setScenario({ ...scenario, ...r.parameters } as Scenario);
                }}
              >
                <span
                  className={r.status === "SUCCEEDED" ? "positive" : "warning"}
                >
                  {r.status === "SUCCEEDED" ? "+" : "~"}
                </span>
                {r.name}
              </button>
            ))}
          </div>
        </Panel>
        <div className="stress-main">
          <Panel
            title={`Scenario configuration / ${scenario.name}`}
            source="Editable scenario assumptions"
            asOf={bootstrap.as_of}
            quality="ASSUMPTIONS"
          >
            <div className="scenario-config">
              <Field label="Valuation date">
                <input
                  aria-label="Stress valuation date"
                  type="date"
                  max={new Date().toISOString().slice(0, 10)}
                  value={String(scenario.valuation_date ?? "")}
                  onChange={(e) =>
                    setScenario({
                      ...scenario,
                      valuation_date: e.target.value || null,
                      valuation_run_id: null,
                    })
                  }
                />
              </Field>
              <Field label="Model">
                <select
                  aria-label="Stress model"
                  value={String(scenario.model ?? "LINEAR")}
                  onChange={(e) =>
                    setScenario({
                      ...scenario,
                      model: e.target.value,
                      scope: "All",
                      equity_shock: 0,
                      fx_shock: 0,
                      rates_bp: 0,
                    })
                  }
                >
                  <option value="LINEAR">Linear factors</option>
                  <option value="CORRELATION">Correlation convergence</option>
                  <option value="VOLATILITY">VIX mapping unavailable</option>
                </select>
              </Field>
              {scenario.model === "CORRELATION" && (
                <Field label="Correlation convergence (0-1)">
                  <input
                    aria-label="Correlation convergence"
                    type="number"
                    min="0"
                    max="1"
                    step=".1"
                    value={Number(scenario.correlation_convergence ?? 1)}
                    onChange={(e) =>
                      setScenario({
                        ...scenario,
                        correlation_convergence: Number(e.target.value),
                      })
                    }
                  />
                </Field>
              )}
              {(["equity_shock", "fx_shock", "rates_bp"] as const).map(
                (k, i) => (
                  <Field
                    key={k}
                    label={
                      [
                        "Equity shock (%)",
                        "USD/SGD shock (%)",
                        "Rates shock (bp)",
                      ][i]
                    }
                  >
                    <input
                      className="assumption"
                      aria-label={
                        ["Equity shock", "FX shock", "Rates shock"][i]
                      }
                      type="number"
                      disabled={
                        scenario.model === "CORRELATION" ||
                        scenario.model === "VOLATILITY"
                      }
                      step={k === "rates_bp" ? 25 : 1}
                      min={k === "rates_bp" ? -1000 : -95}
                      max={k === "rates_bp" ? 1000 : 200}
                      value={scenario[k]}
                      onChange={(e) =>
                        setScenario({
                          ...scenario,
                          [k]: Number(e.target.value),
                        })
                      }
                    />
                  </Field>
                ),
              )}
              <Field label="Scope">
                <select
                  aria-label="Shock scope"
                  className="assumption"
                  disabled={
                    scenario.model === "CORRELATION" ||
                    scenario.model === "VOLATILITY"
                  }
                  value={scenario.scope}
                  onChange={(e) =>
                    setScenario({ ...scenario, scope: e.target.value })
                  }
                >
                  {[
                    "All",
                    "Technology",
                    "Financials",
                    "Energy",
                    "Volatility",
                  ].map((s) => (
                    <option key={s}>{s}</option>
                  ))}
                </select>
              </Field>
            </div>
            <div className="form-actions">
              <button
                className="primary-button"
                disabled={run.isPending || active}
                onClick={() => run.mutate()}
              >
                <Play size={12} />
                {run.isPending
                  ? "Submitting..."
                  : active
                    ? current.data?.status
                    : "Run Scenario"}
              </button>
              <IconButton
                label="Save scenario"
                onClick={() =>
                  setSaved([
                    ...saved,
                    {
                      ...scenario,
                      id: crypto.randomUUID(),
                      name: `${scenario.name} / saved ${saved.length + 1}`,
                    },
                  ])
                }
              >
                <Save size={13} />
              </IconButton>
              <IconButton
                label="Duplicate scenario"
                onClick={() =>
                  setScenario({
                    ...scenario,
                    id: crypto.randomUUID(),
                    name: `${scenario.name} copy`,
                  })
                }
              >
                <Copy size={13} />
              </IconButton>
              <IconButton
                label="Reset scenario"
                onClick={() =>
                  setScenario(
                    bootstrap.scenarios.find((s) => s.id === scenario.id) ??
                      bootstrap.scenarios[1],
                  )
                }
              >
                <RefreshCw size={13} />
              </IconButton>
              <button
                onClick={() => {
                  recent.refetch();
                  setCompare(!compare);
                }}
              >
                Compare runs
              </button>
              <span className="spacer" />
              {current.data && <Badge>{current.data.status}</Badge>}
              {result && (
                <IconButton label="Export stress result" onClick={exportRun}>
                  <ArrowDownToLine size={13} />
                </IconButton>
              )}
            </div>
            {run.error && (
              <p className="error-state" role="alert">
                {run.error.message}
              </p>
            )}
          </Panel>
          <Kpis
            source={result?.source}
            asOf={result?.as_of}
            items={[
              { label: "Pre-stress NAV", value: money(result?.pre_nav) },
              {
                label: "Estimated P&L",
                value: money(result?.loss),
                className: tone(result?.loss),
              },
              {
                label: "NAV impact",
                value: pct(result?.impact),
                className: tone(result?.impact),
              },
              { label: "Post-stress NAV", value: money(result?.post_nav) },
            ]}
          />
          <div className="stress-results">
            <Panel
              title={
                compare
                  ? "Scenario comparison / persisted runs"
                  : "P&L contribution / positions"
              }
              source={result?.source}
              asOf={result?.as_of}
              quality={result?.quality}
              error={current.error || current.data?.error}
              loading={active}
            >
              {compare ? (
                <DataTable
                  id="scenario-comparison"
                  rows={(recent.data?.items ?? [])
                    .filter((r) => r.result)
                    .map((r) => ({
                      name: r.name,
                      pre_nav: r.result?.pre_nav,
                      pnl: r.result?.loss,
                      impact: r.result?.impact,
                      id: r.id,
                    }))}
                  columns={[
                    { key: "name", label: "Scenario", size: 180 },
                    { key: "pre_nav", label: "Pre NAV", numeric: true },
                    { key: "pnl", label: "P&L", numeric: true, money: true },
                    {
                      key: "impact",
                      label: "Impact",
                      numeric: true,
                      percent: true,
                    },
                  ]}
                  onSelect={(row) => setRunId(String(row.id))}
                />
              ) : result?.state === "UNAVAILABLE" ? (
                <Empty
                  title="Scenario unavailable"
                  detail={result.warnings[0]}
                />
              ) : result ? (
                <Chart
                  label="Stress position contribution chart"
                  option={{
                    grid: { left: 55, right: 20, top: 20, bottom: 28 },
                    xAxis: {
                      type: "category",
                      data: contributions.map((p) => String(p.symbol)),
                    },
                    yAxis: {
                      type: "value",
                      splitLine: { lineStyle: { color: COLORS.grid } },
                      axisLabel: {
                        formatter: (v: number) => `${(v / 1000).toFixed(1)}k`,
                      },
                    },
                    series: [
                      {
                        type: "bar",
                        barMaxWidth: 55,
                        data: contributions.map((p) => ({
                          value: Number(p.pnl),
                          itemStyle: {
                            color:
                              Number(p.pnl) < 0 ? COLORS.red : COLORS.green,
                          },
                        })),
                      },
                    ],
                  }}
                />
              ) : (
                <Empty
                  title="No scenario run selected"
                  detail="Select a scenario and run it against the current reference portfolio."
                />
              )}
            </Panel>
            <Panel
              title="Scenario contribution detail"
              source={result?.source}
              asOf={result?.as_of}
              quality={result?.quality}
              rows={rows}
            >
              <div className="segmented">
                {[
                  "Positions",
                  "Sectors",
                  "Countries",
                  "Currencies",
                  "Factors",
                  "Assumptions",
                ].map((t) => (
                  <button
                    key={t}
                    className={view === t ? "active" : ""}
                    onClick={() => setView(t)}
                  >
                    {t}
                  </button>
                ))}
              </div>
              <DataTable
                compact
                id="stress-contribution"
                rows={rows}
                columns={
                  view === "Assumptions"
                    ? [
                        { key: "factor", label: "Factor", size: 160 },
                        { key: "value", label: "Value", size: 200 },
                      ]
                    : view === "Positions"
                      ? [
                          { key: "symbol", label: "Position", size: 90 },
                          {
                            key: "market_value",
                            label: "Pre-value",
                            numeric: true,
                            size: 105,
                          },
                          {
                            key: "shock",
                            label: "Shock",
                            numeric: true,
                            percent: true,
                            size: 90,
                          },
                          {
                            key: "pnl",
                            label: "P&L (SGD)",
                            numeric: true,
                            money: true,
                            size: 120,
                          },
                          {
                            key: "post_value",
                            label: "Post-value",
                            numeric: true,
                            size: 105,
                          },
                          { key: "sector", label: "Sector", size: 150 },
                        ]
                      : [
                          { key: "group", label: view, size: 180 },
                          {
                            key: "market_value",
                            label: "Exposure",
                            numeric: true,
                          },
                          {
                            key: "pnl",
                            label: "P&L (SGD)",
                            numeric: true,
                            money: true,
                          },
                        ]
                }
              />
            </Panel>
          </div>
        </div>
      </div>
    </>
  );
}

export function MacroPage() {
  const query = useApi<MacroDashboardPayload>(
    "macro",
    "/api/v1/macro/dashboard",
  );
  const [series, setSeries] = useTabState("macro-series", "DGS10");
  const [range, setRange] = useTabState("macro-range", "5Y");
  const observations = useApi<{
    items: Row[];
    observations?: Row[];
    source?: string;
    quality?: string;
    as_of?: string;
  }>("macro-series", `/api/v1/macro/series/${series}/observations?limit=10000`);
  const items = query.data?.items ?? [];
  const selected = items.find((i) => i.series_id === series);
  const raw = observations.data?.items ?? observations.data?.observations ?? [];
  const rows = macroRange(raw, range);
  const provenance = macroProvenance(items);
  const selectedProvenance = macroProvenance(selected ? [selected] : []);
  const treasuryProvenance = macroProvenance(
    items.filter((item) => ["DGS2", "DGS10", "DGS30"].includes(item.series_id)),
  );
  const refresh = useMutation({
    mutationFn: () => knkApi.post(`/api/v1/macro/series/${series}/refresh`),
    onSuccess: () => {
      query.refetch();
      observations.refetch();
    },
  });
  return (
    <>
      <PageTitle code="MACRO" title="Global Macro Monitor">
        <Badge>{provenance.quality}</Badge>
      </PageTitle>
      <Kpis
        source="Per-series source"
        asOf={macroProvenance(items.slice(0, 7)).asOf ?? undefined}
        items={items.slice(0, 7).map((i) => ({
          label: i.series_id,
          value: number(i.latest_value),
          className: tone(i.change),
        }))}
      />
      <div className="page-grid analytics-grid">
        <Panel
          title={`Economic series / ${series}`}
          {...selectedProvenance}
          error={observations.error}
          loading={observations.isLoading}
          rows={rows}
        >
          <div className="control-row">
            <select
              aria-label="Economic series"
              value={series}
              onChange={(e) => setSeries(e.target.value)}
            >
              {items.map((i) => (
                <option key={i.series_id} value={i.series_id}>
                  {i.series_id} / {i.title}
                </option>
              ))}
            </select>
            {["1Y", "5Y", "MAX"].map((r) => (
              <button
                key={r}
                className={range === r ? "amber" : ""}
                onClick={() => setRange(r)}
              >
                {r}
              </button>
            ))}
          </div>
          <LineChart
            label={`${series} economic series`}
            rows={rows}
            keys={[{ key: "value", name: series }]}
          />
        </Panel>
        <Panel title="US Treasury yield curve" {...treasuryProvenance}>
          <Chart
            label="US Treasury curve"
            option={{
              xAxis: { type: "category", data: ["2Y", "10Y", "30Y"] },
              yAxis: {
                type: "value",
                splitLine: { lineStyle: { color: COLORS.grid } },
                axisLabel: { formatter: (v: number) => `${v}%` },
              },
              series: [
                {
                  type: "line",
                  data: ["DGS2", "DGS10", "DGS30"].map((code) => {
                    const value = items.find(
                      (i) => i.series_id === code,
                    )?.latest_value;
                    return value === null || value === undefined
                      ? null
                      : Number(value);
                  }),
                  symbolSize: 5,
                  connectNulls: false,
                },
              ],
            }}
          />
        </Panel>
        <Panel
          title="Latest observations / all series"
          {...provenance}
          rows={records(items)}
        >
          <DataTable
            id="macro-series"
            rows={records(items)}
            columns={macroColumns}
            onSelect={(row) => setSeries(String(row.series_id))}
          />
        </Panel>
        <Panel title="Selected series / metadata" {...selectedProvenance}>
          <dl className="detail-list section-pad">
            <dt>Series</dt>
            <dd>{selected?.title}</dd>
            <dt>Unit</dt>
            <dd>{selected?.unit}</dd>
            <dt>Frequency</dt>
            <dd>{selected?.frequency}</dd>
            <dt>Observation</dt>
            <dd>{selected?.latest_observation_date}</dd>
            <dt>Ingested / SGT</dt>
            <dd>{timestamp(selected?.ingestion_timestamp)}</dd>
            <dt>Revision</dt>
            <dd>{selected?.revision_state}</dd>
            <dt>Source</dt>
            <dd>{selected?.source}</dd>
          </dl>
          <div className="control-row">
            <button
              disabled={refresh.isPending}
              onClick={() => refresh.mutate()}
            >
              <RefreshCw size={12} />
              Refresh FRED series
            </button>
          </div>
          {!!refresh.data && (
            <p className="source-note">
              Refresh request returned. Provider state remains source-specific.
            </p>
          )}
          {refresh.error && (
            <p className="warning-note section-pad">{refresh.error.message}</p>
          )}
          <p className="source-note">
            Release calendar and central-bank events require a configured event
            source.
          </p>
        </Panel>
      </div>
    </>
  );
}
