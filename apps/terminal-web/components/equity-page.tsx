"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { knkApi } from "@knk/api-client";
import { Download, Play } from "lucide-react";
import { PageTitle, useApi } from "./core-pages";
import { useTabState, useTerminal } from "./context";
import {
  Badge,
  Chart,
  DataTable,
  Empty,
  Field,
  Kpis,
  Panel,
  download,
  number,
  pct,
} from "./ui";
import type { Column } from "./ui";
import type { Row } from "./types";

interface FinancialReport {
  symbol: string;
  currency: string;
  unit: string;
  source: string;
  quality: string;
  as_of: string | null;
  items: Row[];
  ratios: Row[];
  quote: Row;
  warnings: string[];
  state: string;
}
interface Scenario extends Row {
  name: string;
  forecast: Row[];
  growth_sensitivity: Row[];
  exit_sensitivity: Row[];
  fair_value: string;
  enterprise_value: string;
  equity_value: string;
  upside: string | null;
  terminal_share: string | null;
}
interface DcfReport {
  id: string;
  symbol: string;
  currency: string;
  source: string;
  quality: string;
  as_of: string | null;
  scenarios: Scenario[];
  warnings: string[];
  input_hash: string;
}
interface CompReport {
  id: string;
  items: Row[];
  statistics: Row[];
  warnings: string[];
  quality: string;
}
interface Saved<T> {
  id: string;
  name: string;
  parameters: Row;
  result: T;
}
const labels = (key: string) => key.replaceAll("_", " ");
const numericColumns = (keys: string[]): Column[] =>
  keys.map((key) => ({ key, label: labels(key), numeric: true, size: 120 }));
const percentKeys = [
  "gross_margin",
  "ebit_margin",
  "net_margin",
  "fcf_margin",
  "roe",
  "roa",
  "roic",
  "revenue_growth",
  "earnings_growth",
  "fcf_yield",
  "earnings_yield",
  "dividend_yield",
];
const statementGroups: Record<string, string[]> = {
  Income: [
    "revenue",
    "gross_profit",
    "ebit",
    "ebitda",
    "depreciation",
    "interest_expense",
    "tax_expense",
    "net_income",
  ],
  Balance: [
    "assets",
    "current_assets",
    "cash",
    "liabilities",
    "current_liabilities",
    "debt",
    "equity",
    "working_capital",
    "shares",
  ],
  Cash: ["operating_cash_flow", "capex", "free_cash_flow", "dividends"],
  Ratios: [
    "gross_margin",
    "ebit_margin",
    "net_margin",
    "fcf_margin",
    "roe",
    "roa",
    "current_ratio",
    "debt_to_equity",
    "revenue_growth",
    "earnings_growth",
  ],
  Valuation: [
    "market_cap",
    "enterprise_value",
    "eps",
    "pe",
    "forward_pe",
    "pb",
    "ps",
    "ev_sales",
    "ev_ebitda",
    "ev_ebit",
    "fcf_yield",
    "earnings_yield",
    "dividend_yield",
    "historical_percentile",
  ],
};
const defaults = () => [
  {
    name: "BULL",
    growth: "12,12,10,10,8",
    margins: "27,28,29,30,30",
    tax: "21",
    depreciation: "3",
    capex: "5",
    workingCapital: "10",
    wacc: "9",
    terminalGrowth: "3",
    multiple: "14",
    method: "PERPETUITY",
  },
  {
    name: "BASE",
    growth: "8,8,8,8,8",
    margins: "25,25,25,25,25",
    tax: "21",
    depreciation: "3",
    capex: "5",
    workingCapital: "10",
    wacc: "10",
    terminalGrowth: "2.5",
    multiple: "12",
    method: "PERPETUITY",
  },
  {
    name: "BEAR",
    growth: "3,3,3,3,3",
    margins: "20,20,20,20,20",
    tax: "21",
    depreciation: "3",
    capex: "6",
    workingCapital: "12",
    wacc: "12",
    terminalGrowth: "2",
    multiple: "10",
    method: "PERPETUITY",
  },
];
type Assumption = ReturnType<typeof defaults>[number];
const rate = (value: string) => String(Number(value) / 100);
function FiscalChart({
  rows,
  keys,
  label,
}: {
  rows: Row[];
  keys: string[];
  label: string;
}) {
  return (
    <Chart
      label={label}
      option={{
        legend: { top: 0 },
        xAxis: { type: "category", data: rows.map((r) => String(r.year)) },
        series: keys.map((key) => ({
          type: "line",
          name: labels(key),
          data: rows.map((r) => (r[key] == null ? null : Number(r[key]))),
          symbol: "none",
        })),
      }}
    />
  );
}

export function EquityWorkspace({ route }: { route: string }) {
  const { security, open } = useTerminal();
  const kind = route.split("/")[1];
  const dcfMode = kind === "dcf";
  const compMode = kind === "comparables";
  const waccMode = kind === "wacc";
  const [frequency, setFrequency] = useTabState("equity-frequency", "ANNUAL");
  const [actual, setActual] = useTabState("equity-actual", "ACTUAL");
  const [group, setGroup] = useState(
    kind === "valuation" ? "Valuation" : "Income",
  );
  const financial = useApi<FinancialReport>(
    "equity-financial",
    `/api/v1/equity/${security}/financials?frequency=${frequency}&actual_estimate=${actual}`,
  );
  const [assumptions, setAssumptions] = useTabState(
    "dcf-assumptions",
    defaults(),
  );
  const [scenario, setScenario] = useState("BASE");
  const [dcfReport, setDcfReport] = useTabState<DcfReport | null>(
    "fcff-result",
    null,
  );
  const [period, setPeriod] = useTabState("fcff-period", "");
  const [overrides, setOverrides] = useTabState("fcff-overrides", {
    wc: "",
    debt: "",
    cash: "",
    shares: "",
  });
  const [peers, setPeers] = useTabState("equity-peers", "MSFT,NVDA,GOOGL");
  const [compReport, setCompReport] = useTabState<CompReport | null>(
    "equity-comps",
    null,
  );
  const [waccInputs, setWaccInputs] = useTabState("equity-wacc", {
    risk_free: "3",
    beta: "1",
    equity_risk_premium: "5",
    cost_of_debt: "5",
    tax_rate: "21",
    equity_market_value: "80",
    debt_market_value: "20",
  });
  const [waccResult, setWaccResult] = useTabState<Row | null>(
    "equity-wacc-result",
    null,
  );
  const [useWacc, setUseWacc] = useTabState("dcf-apply-wacc", false);
  const savedKind = compMode ? "comparables" : waccMode ? "wacc" : "dcf";
  const history = useApi<{ items: Saved<DcfReport | CompReport | Row>[] }>(
    "equity-history",
    `/api/v1/terminal/runs?kind=${savedKind}`,
    dcfMode || compMode || waccMode,
  );
  const waccPayload = Object.fromEntries(
    Object.entries(waccInputs).map(([key, value]) => [
      key,
      ["risk_free", "equity_risk_premium", "cost_of_debt", "tax_rate"].includes(
        key,
      )
        ? rate(value)
        : value,
    ]),
  );
  const calculate = useMutation({
    mutationFn: async () => {
      if (waccMode) {
        const result = await knkApi.post<Row>(
          "/api/v1/equity/wacc",
          waccPayload,
        );
        setWaccResult(result);
      } else if (compMode) {
        const result = await knkApi.post<CompReport>(
          "/api/v1/equity/comparables",
          {
            symbol: security,
            peers: peers
              .split(",")
              .map((p) => p.trim())
              .filter(Boolean),
            frequency: frequency === "QUARTERLY" ? "ANNUAL" : frequency,
          },
        );
        setCompReport(result);
      } else {
        const result = await knkApi.post<DcfReport>("/api/v1/equity/dcf", {
          symbol: security,
          frequency: frequency === "QUARTERLY" ? "ANNUAL" : frequency,
          ...(period ? { period } : {}),
          ...(overrides.wc ? { initial_working_capital: overrides.wc } : {}),
          ...(overrides.debt ? { debt_override: overrides.debt } : {}),
          ...(overrides.cash ? { cash_override: overrides.cash } : {}),
          ...(overrides.shares ? { shares_override: overrides.shares } : {}),
          wacc_inputs: waccPayload,
          apply_calculated_wacc: useWacc,
          scenarios: assumptions.map((a) => ({
            name: a.name,
            revenue_growth: a.growth.split(",").map(rate),
            ebit_margins: a.margins.split(",").map(rate),
            tax_rate: rate(a.tax),
            depreciation_pct: rate(a.depreciation),
            capex_pct: rate(a.capex),
            working_capital_pct: rate(a.workingCapital),
            wacc: rate(a.wacc),
            terminal_growth: rate(a.terminalGrowth),
            exit_multiple: a.multiple,
            terminal_method: a.method,
          })),
        });
        setDcfReport(result);
      }
    },
    onSuccess: () => history.refetch(),
  });
  const data = financial.data;
  const latest = data?.ratios.at(-1);
  const active = assumptions.find((a) => a.name === scenario)!;
  const setAssumption = (key: keyof Assumption, value: string) =>
    setAssumptions(
      assumptions.map((a) =>
        a.name === scenario ? { ...a, [key]: value } : a,
      ),
    );
  const result =
    dcfReport?.symbol === security
      ? dcfReport.scenarios.find((a) => a.name === scenario)
      : undefined;
  const metricRows: Row[] = (
    statementGroups[kind === "valuation" ? "Valuation" : group] ?? []
  ).map((metric) => ({
    metric: labels(metric),
    ...Object.fromEntries(
      (data?.ratios ?? []).map((row) => [String(row.year), row[metric]]),
    ),
  }));
  const columns: Column[] = [
    { key: "metric", label: data?.unit ?? "Metric", size: 240 },
    ...(data?.items ?? []).map((row) => ({
      key: String(row.year),
      label: String(row.year),
      numeric: true,
      size: 125,
    })),
  ];
  const sources = {
    source: data?.source,
    asOf: data?.as_of,
    quality: data?.quality,
  };
  return (
    <div className="research-page equity-workspace">
      <PageTitle
        code={
          dcfMode
            ? "DCF"
            : compMode
              ? "COMP"
              : waccMode
                ? "WACC"
                : kind === "valuation"
                  ? "VAL"
                  : "FIN"
        }
        title={`${security} / ${dcfMode ? "Discounted Cash Flow" : compMode ? "Comparable Companies" : waccMode ? "Cost of Capital" : "Financial Analysis"}`}
      >
        <Badge>{data?.quality ?? "LOADING"}</Badge>
        {(dcfMode || compMode || waccMode) && (
          <button
            className="primary-button"
            disabled={calculate.isPending}
            onClick={() => calculate.mutate()}
          >
            <Play size={13} />
            {calculate.isPending ? "Calculating..." : "Calculate & Save"}
          </button>
        )}
        {dcfMode && dcfReport && (
          <button
            className="toolbar-button"
            title="Download saved DCF JSON"
            onClick={() =>
              download(
                `dcf-${dcfReport.id}.json`,
                JSON.stringify(dcfReport, null, 2),
                "application/json",
              )
            }
          >
            <Download size={14} />
          </button>
        )}
      </PageTitle>
      <div className="toolbar">
        {[
          ["DES", "security"],
          ["GP", "chart"],
          ["FIN", "financials"],
          ["VAL", "valuation"],
          ["DCF", "dcf"],
          ["WACC", "wacc"],
          ["COMP", "comparables"],
        ].map(([code, path]) => (
          <button
            className="toolbar-button"
            key={code}
            onClick={() =>
              open(
                `/${path}/${security}`,
                `${security} ${code}`,
                false,
                security,
              )
            }
          >
            {code}
          </button>
        ))}
        <button
          className="toolbar-button"
          onClick={() => open("/thesis", `${security} THESIS`, false, security)}
        >
          THESIS
        </button>
      </div>
      {!waccMode && (
        <div className="performance-controls">
          <Field label="Frequency">
            <select
              aria-label="Financial frequency"
              value={frequency}
              onChange={(e) => {
                setFrequency(e.target.value);
                setPeriod("");
              }}
            >
              <option>ANNUAL</option>
              {!dcfMode && !compMode && <option>QUARTERLY</option>}
              <option>TTM</option>
            </select>
          </Field>
          {!dcfMode && !compMode && (
            <Field label="Statement type">
              <select
                aria-label="Statement type"
                value={actual}
                onChange={(e) => setActual(e.target.value)}
              >
                <option>ACTUAL</option>
                <option>ESTIMATE</option>
              </select>
            </Field>
          )}
          {dcfMode && (
            <Field label="Base period">
              <select
                aria-label="DCF base period"
                value={period}
                onChange={(e) => setPeriod(e.target.value)}
              >
                <option value="">Latest actual</option>
                {data?.items.map((row) => (
                  <option key={String(row.year)}>{String(row.year)}</option>
                ))}
              </select>
            </Field>
          )}
          {compMode && (
            <Field label="Peers">
              <input
                aria-label="Comparable peers"
                value={peers}
                onChange={(e) => setPeers(e.target.value)}
              />
            </Field>
          )}
          {(dcfMode || compMode) && (
            <Field label="Saved runs">
              <select
                aria-label="Saved equity run"
                value=""
                onChange={(e) => {
                  const run = history.data?.items.find(
                    (r) => r.id === e.target.value,
                  );
                  if (!run) return;
                  if (compMode) {
                    setCompReport(run.result as CompReport);
                    setPeers((run.parameters.peers as string[]).join(","));
                  } else {
                    setDcfReport(run.result as DcfReport);
                    setAssumptions(
                      (run.parameters.scenarios as Row[]).map((a) => ({
                        name: String(a.name),
                        growth: (a.revenue_growth as string[])
                          .map((v) => Number(v) * 100)
                          .join(","),
                        margins: (a.ebit_margins as string[])
                          .map((v) => Number(v) * 100)
                          .join(","),
                        tax: String(Number(a.tax_rate) * 100),
                        depreciation: String(Number(a.depreciation_pct) * 100),
                        capex: String(Number(a.capex_pct) * 100),
                        workingCapital: String(
                          Number(a.working_capital_pct) * 100,
                        ),
                        wacc: String(Number(a.wacc) * 100),
                        terminalGrowth: String(Number(a.terminal_growth) * 100),
                        multiple: String(a.exit_multiple),
                        method: String(a.terminal_method),
                      })),
                    );
                    setPeriod(String(run.parameters.period ?? ""));
                    setFrequency(String(run.parameters.frequency));
                    setUseWacc(Boolean(run.parameters.apply_calculated_wacc));
                    if (run.parameters.wacc_inputs) {
                      const inputs = run.parameters.wacc_inputs as Row;
                      setWaccInputs(
                        Object.fromEntries(
                          Object.keys(waccInputs).map((key) => [
                            key,
                            String(
                              Number(inputs[key]) *
                                ([
                                  "risk_free",
                                  "equity_risk_premium",
                                  "cost_of_debt",
                                  "tax_rate",
                                ].includes(key)
                                  ? 100
                                  : 1),
                            ),
                          ]),
                        ) as typeof waccInputs,
                      );
                    }
                    setOverrides({
                      wc: String(run.parameters.initial_working_capital ?? ""),
                      debt: String(run.parameters.debt_override ?? ""),
                      cash: String(run.parameters.cash_override ?? ""),
                      shares: String(run.parameters.shares_override ?? ""),
                    });
                  }
                }}
              >
                <option value="">Select saved analysis</option>
                {history.data?.items
                  .filter((run) => run.parameters.symbol === security)
                  .map((run) => (
                    <option key={run.id} value={run.id}>
                      {run.name} / {run.id.slice(0, 8)}
                    </option>
                  ))}
              </select>
            </Field>
          )}
        </div>
      )}
      {(waccMode || dcfMode) && (
        <div className="performance-controls">
          {(waccMode || useWacc) &&
            Object.entries(waccInputs).map(([key, value]) => (
              <Field
                key={key}
                label={`${labels(key)}${["risk_free", "equity_risk_premium", "cost_of_debt", "tax_rate"].includes(key) ? " %" : ""}`}
              >
                <input
                  type="number"
                  step="any"
                  aria-label={`WACC ${key}`}
                  value={value}
                  onChange={(e) =>
                    setWaccInputs({ ...waccInputs, [key]: e.target.value })
                  }
                />
              </Field>
            ))}
          {dcfMode && (
            <label className="check-row">
              <input
                type="checkbox"
                checked={useWacc}
                onChange={(e) => setUseWacc(e.target.checked)}
              />
              Calculated WACC for all scenarios
            </label>
          )}
        </div>
      )}
      {waccMode && (
        <Kpis
          items={[
            { label: "WACC", value: pct(waccResult?.wacc) },
            { label: "Cost of equity", value: pct(waccResult?.cost_of_equity) },
            {
              label: "After-tax debt cost",
              value: pct(waccResult?.after_tax_cost_of_debt),
            },
            { label: "Equity weight", value: pct(waccResult?.equity_weight) },
          ]}
        />
      )}
      {waccMode && (
        <Panel
          title="Capital-cost history"
          source="User assumptions"
          quality="RESEARCH ASSUMPTIONS"
        >
          <DataTable
            id="wacc-history"
            rows={(history.data?.items ?? []).map((r) => ({
              ...r.result,
              id: r.id,
            }))}
            columns={[
              { key: "id", label: "Run", size: 180 },
              ...[
                "wacc",
                "cost_of_equity",
                "after_tax_cost_of_debt",
                "equity_weight",
              ].map((key) => ({
                key,
                label: labels(key),
                numeric: true,
                percent: true,
              })),
            ]}
            onSelect={(row) => {
              setWaccResult(row);
              const inputs = row.inputs as Row;
              setWaccInputs(
                Object.fromEntries(
                  Object.keys(waccInputs).map((key) => [
                    key,
                    String(
                      Number(inputs[key]) *
                        ([
                          "risk_free",
                          "equity_risk_premium",
                          "cost_of_debt",
                          "tax_rate",
                        ].includes(key)
                          ? 100
                          : 1),
                    ),
                  ]),
                ) as typeof waccInputs,
              );
            }}
          />
        </Panel>
      )}
      {dcfMode && (
        <>
          <div className="toolbar" role="tablist" aria-label="DCF scenarios">
            {assumptions.map((a) => (
              <button
                key={a.name}
                role="tab"
                aria-selected={scenario === a.name}
                className={`toolbar-button ${scenario === a.name ? "active" : ""}`}
                onClick={() => setScenario(a.name)}
              >
                {a.name}
              </button>
            ))}
          </div>
          <div className="performance-controls">
            {(
              [
                ["growth", "Revenue growth % by year"],
                ["margins", "EBIT margin % by year"],
                ["tax", "Tax %"],
                ["depreciation", "D&A / revenue %"],
                ["capex", "CapEx / revenue %"],
                ["workingCapital", "NWC / revenue %"],
                ["wacc", "WACC %"],
                ["terminalGrowth", "Terminal growth %"],
                ["multiple", "Exit EBITDA multiple"],
              ] as [keyof Assumption, string][]
            ).map(([key, label]) => (
              <Field key={key} label={label}>
                <input
                  aria-label={label}
                  value={active[key]}
                  onChange={(e) => setAssumption(key, e.target.value)}
                />
              </Field>
            ))}
            <Field label="Terminal method">
              <select
                aria-label="Terminal method"
                value={active.method}
                onChange={(e) => setAssumption("method", e.target.value)}
              >
                <option value="PERPETUITY">Perpetuity FCFF</option>
                <option value="EXIT_MULTIPLE">Exit EBITDA multiple</option>
              </select>
            </Field>
            {(
              [
                ["wc", "Initial NWC millions"],
                ["debt", "Debt override millions"],
                ["cash", "Cash override millions"],
                ["shares", "Shares override millions"],
              ] as const
            ).map(([key, label]) => (
              <Field key={key} label={label}>
                <input
                  type="number"
                  step="any"
                  aria-label={label}
                  value={overrides[key]}
                  onChange={(e) =>
                    setOverrides({ ...overrides, [key]: e.target.value })
                  }
                />
              </Field>
            ))}
          </div>
          <Kpis
            items={[
              {
                label: "Fair value / share",
                value: number(result?.fair_value),
              },
              { label: "Upside / downside", value: pct(result?.upside) },
              {
                label: "Enterprise value / millions",
                value: number(result?.enterprise_value),
              },
              {
                label: "Equity value / millions",
                value: number(result?.equity_value),
              },
              { label: "PV terminal / EV", value: pct(result?.terminal_share) },
            ]}
          />
          <div className="page-grid">
            <Panel
              title="FCFF forecast"
              source={dcfReport?.source}
              quality={dcfReport?.quality}
              asOf={dcfReport?.as_of}
            >
              <FiscalChart
                rows={result?.forecast ?? []}
                label="FCFF forecast chart"
                keys={["fcff", "present_value"]}
              />
            </Panel>
            <Panel
              title="WACC x terminal growth"
              source="Sensitivity / user assumptions"
            >
              <Chart
                label="DCF growth sensitivity"
                option={{
                  tooltip: {
                    formatter: (p: unknown) => {
                      const v = (p as { value: number[] }).value;
                      return `WACC ${v[0]}% / Growth ${v[1]}% / ${number(v[2])}`;
                    },
                  },
                  xAxis: { type: "value", name: "WACC %" },
                  yAxis: { type: "value", name: "Growth %" },
                  series: [
                    {
                      type: "scatter",
                      symbolSize: 16,
                      data: (result?.growth_sensitivity ?? [])
                        .filter((r) => r.fair_value !== null)
                        .map((r) => [
                          Number(r.wacc) * 100,
                          Number(r.terminal_growth) * 100,
                          Number(r.fair_value),
                        ]),
                    },
                  ],
                  visualMap: {
                    min: Math.min(
                      0,
                      ...(result?.growth_sensitivity ?? []).map((r) =>
                        Number(r.fair_value),
                      ),
                    ),
                    max: Math.max(
                      1,
                      ...(result?.growth_sensitivity ?? []).map((r) =>
                        Number(r.fair_value),
                      ),
                    ),
                    dimension: 2,
                    show: false,
                    inRange: { color: ["#FF4D4F", "#FFD400", "#00C875"] },
                  },
                }}
              />
            </Panel>
          </div>
          <Panel
            title="Annual operating forecast / millions"
            rows={result?.forecast}
          >
            <DataTable
              id="fcff-forecast"
              rows={result?.forecast ?? []}
              columns={[
                { key: "year", label: "Year", size: 60 },
                ...numericColumns([
                  "revenue",
                  "ebit",
                  "tax",
                  "depreciation",
                  "capex",
                  "working_capital",
                  "delta_working_capital",
                  "fcff",
                  "present_value",
                ]),
              ]}
            />
          </Panel>
          <Panel title="Exit-multiple sensitivity">
            <DataTable
              id="dcf-exit-sensitivity"
              rows={result?.exit_sensitivity ?? []}
              columns={[
                { key: "wacc", label: "WACC", numeric: true, percent: true },
                ...numericColumns(["exit_multiple", "fair_value"]),
              ]}
            />
          </Panel>
          {dcfReport && (
            <p className="muted section-pad">
              Run {dcfReport.id} | {dcfReport.currency} | SHA256{" "}
              {dcfReport.input_hash}
            </p>
          )}
        </>
      )}
      {compMode && (
        <>
          <Panel
            title="Selected companies / native currency millions"
            quality={compReport?.quality}
          >
            <DataTable
              id="equity-comps"
              rows={compReport?.items ?? []}
              columns={[
                { key: "symbol", label: "Symbol" },
                { key: "currency", label: "CCY", size: 65 },
                { key: "year", label: "Fiscal period" },
                ...numericColumns([
                  "market_cap",
                  "enterprise_value",
                  "revenue",
                  "ebitda",
                  "eps",
                  "pe",
                  "ev_ebitda",
                  "ev_sales",
                  "pb",
                ]),
                { key: "source", label: "Source", size: 160 },
              ]}
            />
          </Panel>
          <Panel title="Peer statistics / target excluded">
            <DataTable
              id="equity-peer-statistics"
              rows={compReport?.statistics ?? []}
              columns={[
                { key: "metric", label: "Metric" },
                ...numericColumns([
                  "count",
                  "mean",
                  "median",
                  "q1",
                  "q3",
                  "implied_price",
                ]),
                {
                  key: "outliers",
                  label: "Outliers",
                  format: (v) => (v as string[]).join(", ") || "None",
                },
              ]}
            />
          </Panel>
        </>
      )}
      {!dcfMode && !compMode && !waccMode && (
        <>
          <Kpis
            items={[
              { label: "Revenue / millions", value: number(latest?.revenue) },
              { label: "EBIT margin", value: pct(latest?.ebit_margin) },
              { label: "P/E", value: number(latest?.pe) },
              { label: "FCF yield", value: pct(latest?.fcf_yield) },
            ]}
          />
          {kind !== "valuation" && (
            <div
              className="toolbar"
              role="tablist"
              aria-label="Financial statements"
            >
              {Object.keys(statementGroups)
                .filter((key) => key !== "Valuation")
                .map((key) => (
                  <button
                    key={key}
                    role="tab"
                    aria-selected={group === key}
                    className={`toolbar-button ${group === key ? "active" : ""}`}
                    onClick={() => setGroup(key)}
                  >
                    {key}
                  </button>
                ))}
            </div>
          )}
          <Panel
            title={
              kind === "valuation"
                ? "Market multiples / latest price"
                : `${group} / ${frequency}`
            }
            {...sources}
            rows={metricRows}
          >
            {data?.items.length ? (
              <DataTable
                id={`financial-${group}`}
                rows={metricRows}
                columns={columns.map((col) =>
                  col.key === "metric"
                    ? col
                    : {
                        ...col,
                        format: (value, row) =>
                          percentKeys.some((key) => labels(key) === row.metric)
                            ? pct(value)
                            : number(value),
                      },
                )}
              />
            ) : (
              <Empty
                title="No matching statements"
                detail={data?.state ?? "Loading financials"}
              />
            )}
          </Panel>
          <div className="page-grid">
            <Panel title="Revenue / operating profit" {...sources}>
              <FiscalChart
                rows={data?.ratios ?? []}
                label="Financial history chart"
                keys={["revenue", "ebit"]}
              />
            </Panel>
            <Panel title="Source periods" {...sources}>
              <DataTable
                id="financial-source-periods"
                rows={data?.items ?? []}
                columns={[
                  { key: "year", label: "Period" },
                  { key: "frequency", label: "Frequency" },
                  { key: "actual_estimate", label: "Type" },
                  { key: "report_date", label: "Reported" },
                  { key: "dataset_version_id", label: "Version", size: 220 },
                ]}
              />
            </Panel>
          </div>
        </>
      )}
      {(calculate.error || financial.error) && (
        <p role="alert" className="negative section-pad">
          {String(calculate.error ?? financial.error)}
        </p>
      )}
      <div className="section-pad muted">
        {(dcfMode
          ? dcfReport?.warnings
          : compMode
            ? compReport?.warnings
            : data?.warnings
        )?.map((w) => <p key={w}>{w}</p>)}
      </div>
    </div>
  );
}
