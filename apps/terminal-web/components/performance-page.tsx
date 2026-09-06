"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { knkApi } from "@knk/api-client";
import { RefreshCw, Save } from "lucide-react";
import { PageTitle, useApi } from "./core-pages";
import {
  Badge,
  COLORS,
  DataTable,
  Field,
  IconButton,
  Kpis,
  LineChart,
  Panel,
  number,
  pct,
} from "./ui";
import type { Row } from "./types";

interface Metric {
  value: string | number | null;
  state: string;
  reason: string | null;
  unit: string;
  observations: number;
}
interface PerformanceReport {
  state: string;
  source_quality: string;
  calculated_at: string;
  valuation_run_id: string;
  source_precision: string;
  calculation_version: string;
  warnings: string[];
  summary: Record<string, Metric>;
  series: Row[];
  monthly: Row[];
  rolling: Row[];
}
const display = (metric?: Metric) =>
  metric?.unit === "RETURN" ? pct(metric?.value) : number(metric?.value);

export function PerformanceWorkspace() {
  const [portfolio, setPortfolio] = useState("KNK_MAIN");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [frequency, setFrequency] = useState("DAILY");
  const [basis, setBasis] = useState("NET");
  const [riskFree, setRiskFree] = useState("0");
  const [window, setWindow] = useState("60");
  const books = useApi<{ items: Row[] }>(
    "performance-books",
    "/api/v1/portfolios",
  );
  const parameters = new URLSearchParams({
    frequency,
    fee_basis: basis,
    risk_free_rate: String(Number(riskFree) / 100),
    rolling_window: window,
  });
  if (start) parameters.set("start", start);
  if (end) parameters.set("end", end);
  const path = `/api/v1/performance/portfolios/${encodeURIComponent(portfolio)}`;
  const query = useApi<PerformanceReport>(
    "performance-report",
    `${path}/report?${parameters}`,
  );
  const data = query.data;
  const save = useMutation({
    mutationFn: () =>
      knkApi.post<{ analysis_run_id: string }>(`${path}/calculate`, {
        settings: {
          frequency,
          fee_basis: basis,
          risk_free_rate: String(Number(riskFree) / 100),
          rolling_window: Number(window),
          ...(start ? { start } : {}),
          ...(end ? { end } : {}),
        },
        valuation_run_id: data?.valuation_run_id,
      }),
  });
  const metrics = Object.entries(data?.summary ?? {}).map(([key, metric]) => ({
    metric: key.replaceAll("_", " "),
    value: metric.value,
    unit: metric.unit,
    state: metric.state,
    observations: metric.observations,
    reason: metric.reason,
  }));
  return (
    <>
      <PageTitle code="PERF" title="Performance / Internal Ledger">
        <Badge>{data?.source_quality ?? "UNAVAILABLE"}</Badge>
        <IconButton
          label="Save performance calculation"
          disabled={!data || save.isPending}
          onClick={() => save.mutate()}
        >
          <Save size={13} />
        </IconButton>
        <IconButton label="Refresh performance" onClick={() => query.refetch()}>
          <RefreshCw size={13} />
        </IconButton>
      </PageTitle>
      <div className="performance-controls">
        <Field label="Portfolio">
          <select
            aria-label="Portfolio"
            value={portfolio}
            onChange={(event) => setPortfolio(event.target.value)}
          >
            {books.data?.items?.map((row) => (
              <option key={String(row.id)} value={String(row.code ?? row.id)}>
                {String(row.code ?? row.name)}
              </option>
            )) ?? <option>KNK_MAIN</option>}
          </select>
        </Field>
        <Field label="From">
          <input
            aria-label="From"
            type="date"
            value={start}
            onChange={(event) => setStart(event.target.value)}
          />
        </Field>
        <Field label="To">
          <input
            aria-label="To"
            type="date"
            value={end}
            onChange={(event) => setEnd(event.target.value)}
          />
        </Field>
        <Field label="Frequency">
          <select
            aria-label="Frequency"
            value={frequency}
            onChange={(event) => setFrequency(event.target.value)}
          >
            {["DAILY", "WEEKLY", "MONTHLY"].map((value) => (
              <option key={value}>{value}</option>
            ))}
          </select>
        </Field>
        <Field label="Fees">
          <select
            aria-label="Fees"
            value={basis}
            onChange={(event) => setBasis(event.target.value)}
          >
            <option>NET</option>
            <option>GROSS</option>
          </select>
        </Field>
        <Field label="Risk-free %">
          <input
            aria-label="Risk-free %"
            type="number"
            min="-99"
            max="100"
            step="0.1"
            value={riskFree}
            onChange={(event) => setRiskFree(event.target.value)}
          />
        </Field>
        <Field label="Rolling window">
          <input
            aria-label="Rolling window"
            type="number"
            min="2"
            max="1260"
            value={window}
            onChange={(event) => setWindow(event.target.value)}
          />
        </Field>
      </div>
      {(query.error || save.error) && (
        <div role="alert" className="operation-notice negative">
          {String(query.error ?? save.error)}
        </div>
      )}
      {save.data && (
        <div role="status" className="operation-notice">
          Saved calculation: {save.data.analysis_run_id}
        </div>
      )}
      <Kpis
        source={`INTERNAL LEDGER / ${data?.source_precision ?? "UNAVAILABLE"}`}
        asOf={data?.calculated_at}
        items={[
          "twr",
          "mwr",
          "alpha",
          "volatility",
          "sharpe",
          "max_drawdown",
        ].map((key) => ({
          label: key.replaceAll("_", " "),
          value: display(data?.summary[key]),
        }))}
      />
      <div className="page-grid analytics-grid">
        <Panel
          title="Linked returns / benchmark"
          source="INTERNAL LEDGER"
          quality={data?.source_quality}
          asOf={data?.calculated_at}
          loading={query.isLoading}
        >
          <LineChart
            label="Flow-adjusted performance index"
            rows={data?.series.map((row) => ({ ...row, date: row.end })) ?? []}
            keys={[
              { key: "return_index", name: "Portfolio" },
              { key: "benchmark_index", name: "Benchmark", color: COLORS.blue },
            ]}
          />
        </Panel>
        <Panel
          title="Metrics / calculation state"
          source={data?.calculation_version}
        >
          <DataTable
            id="performance-metrics"
            rows={metrics}
            columns={[
              { key: "metric", label: "Metric", size: 150 },
              {
                key: "value",
                label: "Value",
                numeric: true,
                size: 100,
                format: (value, row) =>
                  row.unit === "RETURN" ? pct(value) : number(value),
              },
              { key: "state", label: "State", size: 145 },
              { key: "observations", label: "N", numeric: true, size: 45 },
              { key: "reason", label: "Reason", size: 320 },
            ]}
          />
        </Panel>
        <Panel title="Monthly returns" source="INTERNAL LEDGER">
          <DataTable
            id="performance-months"
            rows={data?.monthly ?? []}
            columns={[
              { key: "start", label: "Start" },
              { key: "end", label: "End" },
              { key: "value", label: "Return", percent: true, numeric: true },
              {
                key: "benchmark",
                label: "Benchmark",
                percent: true,
                numeric: true,
              },
              { key: "state", label: "State", size: 150 },
            ]}
          />
        </Panel>
        <Panel title="Rolling volatility" source="INTERNAL LEDGER">
          <LineChart
            label="Rolling annualised volatility"
            rows={data?.rolling ?? []}
            percent
            keys={[
              { key: "volatility", name: "Volatility", color: COLORS.blue },
            ]}
          />
        </Panel>
      </div>
      <div className="source-note">{data?.warnings.join(" | ")}</div>
    </>
  );
}
