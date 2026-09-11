"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { knkApi } from "@knk/api-client";
import { Play } from "lucide-react";
import { PageTitle, useApi } from "./core-pages";
import { useTabState } from "./context";
import {
  Badge,
  COLORS,
  DataTable,
  Field,
  Kpis,
  LineChart,
  Panel,
  number,
  pct,
} from "./ui";
import type { Row, Run } from "./types";
import { significant } from "./financial-format";

interface Regression {
  state: string;
  reason: string | null;
  annualised_alpha: number | null;
  p_value: number | null;
  r_squared: number | null;
  observations: number;
  raw_cumulative_excess_return: number | null;
  annualised_confidence_interval: (number | null)[] | null;
  coefficients: Row[];
  rolling: Row[];
  methodology: string;
  warnings: string[];
}
interface AlphaReport {
  id: string;
  model: string;
  source: string;
  quality: string;
  as_of: string | null;
  results: Record<string, Regression>;
  state: string;
  warnings: string[];
  settings?: Row;
}

export function AlphaWorkspace() {
  const [form, setForm] = useTabState("alpha-config", {
    portfolio: "KNK_MAIN",
    model: "CAPM",
    backtest: "",
    frequency: "DAILY",
    start: "",
    end: "",
    riskFree: "0",
    window: "60",
    lags: "5",
    confidence: ".95",
    costs: "0",
    factors: "",
    columns: "",
  });
  const [basis, setBasis] = useState("NET");
  const [runId, setRunId] = useTabState("alpha-run", "");
  const saved = useApi<{ id: string; result: AlphaReport }>(
    "alpha-saved-run",
    `/api/v1/terminal/runs/${encodeURIComponent(runId)}`,
    !!runId,
  );
  const report = saved.data
    ? { ...saved.data.result, id: saved.data.id }
    : null;
  const books = useApi<{ items: Row[] }>("alpha-books", "/api/v1/portfolios");
  const backtests = useApi<{ items: Run[] }>(
    "alpha-backtests",
    "/api/v1/terminal/runs?kind=backtest",
  );
  const datasets = useApi<{ items: Row[] }>(
    "alpha-datasets",
    "/api/v1/datasets",
  );
  const history = useApi<{
    items: { id: string; name: string; result: AlphaReport }[];
  }>("alpha-history", "/api/v1/terminal/runs?kind=alpha");
  const set = (key: keyof typeof form, value: string) =>
    setForm({ ...form, [key]: value });
  const calculate = useMutation({
    mutationFn: () =>
      knkApi.post<AlphaReport>("/api/v1/alpha/calculate", {
        portfolio: form.portfolio,
        model: form.model,
        ...(form.backtest ? { backtest_run_id: form.backtest } : {}),
        ...(form.factors ? { factor_dataset_version_id: form.factors } : {}),
        factor_columns: form.columns
          .split(",")
          .map((v) => v.trim())
          .filter(Boolean),
        performance: {
          frequency: form.frequency,
          risk_free_rate: String(Number(form.riskFree) / 100),
          ...(form.start ? { start: form.start } : {}),
          ...(form.end ? { end: form.end } : {}),
        },
        regression: {
          rolling_window: Number(form.window),
          hac_lags: Number(form.lags),
          confidence: Number(form.confidence),
        },
        estimated_cost_bps_per_period: Number(form.costs),
      }),
    onSuccess: (value) => {
      setRunId(value.id);
      history.refetch();
    },
  });
  const result = report?.results[basis];
  const interval = result?.annualised_confidence_interval;
  return (
    <div className="research-page">
      <PageTitle code="ALPHA" title="Alpha Analysis">
        <Badge>{report?.quality ?? "NOT RUN"}</Badge>
        <Badge>{result?.state ?? "NOT RUN"}</Badge>
        <button
          className="primary-button"
          disabled={calculate.isPending}
          onClick={() => calculate.mutate()}
        >
          <Play size={13} />
          {calculate.isPending ? "Calculating..." : "Calculate Alpha"}
        </button>
      </PageTitle>
      <div className="performance-controls">
        <Field label="Portfolio">
          <select
            aria-label="Alpha portfolio"
            value={form.portfolio}
            onChange={(e) => set("portfolio", e.target.value)}
          >
            {books.data?.items.map((row) => (
              <option key={String(row.id)} value={String(row.code)}>
                {String(row.code)}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Return source">
          <select
            aria-label="Alpha return source"
            value={form.backtest}
            onChange={(e) => set("backtest", e.target.value)}
          >
            <option value="">Internal portfolio</option>
            {backtests.data?.items
              .filter((row) => row.status === "SUCCEEDED")
              .map((row) => (
                <option key={row.id} value={row.id}>
                  {row.name}
                </option>
              ))}
          </select>
        </Field>
        <Field label="Model">
          <select
            aria-label="Alpha model"
            value={form.model}
            onChange={(e) => set("model", e.target.value)}
          >
            {["CAPM", "FF3", "FF5", "CARHART", "CUSTOM"].map((value) => (
              <option key={value}>{value}</option>
            ))}
          </select>
        </Field>
        <Field label="Frequency">
          <select
            aria-label="Alpha frequency"
            value={form.frequency}
            onChange={(e) => set("frequency", e.target.value)}
          >
            {["DAILY", "WEEKLY", "MONTHLY"].map((value) => (
              <option key={value}>{value}</option>
            ))}
          </select>
        </Field>
        <Field label="Start">
          <input
            aria-label="Alpha start"
            type="date"
            value={form.start}
            onChange={(e) => set("start", e.target.value)}
          />
        </Field>
        <Field label="End">
          <input
            aria-label="Alpha end"
            type="date"
            value={form.end}
            onChange={(e) => set("end", e.target.value)}
          />
        </Field>
        <Field label="Risk-free (% p.a.)">
          <input
            aria-label="Alpha risk-free rate"
            type="number"
            min="-99"
            max="100"
            step=".1"
            value={form.riskFree}
            onChange={(e) => set("riskFree", e.target.value)}
          />
        </Field>
        <Field label="Rolling observations">
          <input
            aria-label="Alpha rolling window"
            type="number"
            min="20"
            max="1000"
            value={form.window}
            onChange={(e) => set("window", e.target.value)}
          />
        </Field>
        <Field label="HAC lags">
          <input
            aria-label="Alpha HAC lags"
            type="number"
            min="0"
            max="63"
            value={form.lags}
            onChange={(e) => set("lags", e.target.value)}
          />
        </Field>
        <Field label="Confidence">
          <input
            aria-label="Alpha confidence"
            type="number"
            min=".8"
            max=".999"
            step=".01"
            value={form.confidence}
            onChange={(e) => set("confidence", e.target.value)}
          />
        </Field>
        <Field label="Additional costs (bp/period)">
          <input
            aria-label="Alpha cost assumption"
            type="number"
            min="0"
            max="100"
            value={form.costs}
            onChange={(e) => set("costs", e.target.value)}
          />
        </Field>
        {form.model !== "CAPM" && (
          <>
            <Field label="Factor-return version">
              <input
                aria-label="Factor dataset version"
                list="alpha-datasets"
                value={form.factors}
                onChange={(e) => set("factors", e.target.value)}
              />
              <datalist id="alpha-datasets">
                {datasets.data?.items
                  .filter((row) => row.latest_version_id)
                  .map((row) => (
                    <option
                      key={String(row.id)}
                      value={String(row.latest_version_id)}
                    >
                      {String(row.name)}
                    </option>
                  ))}
              </datalist>
            </Field>
            {form.model === "CUSTOM" && (
              <Field label="Excess-return columns">
                <input
                  aria-label="Custom factor columns"
                  value={form.columns}
                  onChange={(e) => set("columns", e.target.value)}
                />
              </Field>
            )}
          </>
        )}
        <Field label="Saved analysis">
          <select
            aria-label="Saved alpha analysis"
            value={runId}
            onChange={(e) => {
              const run = history.data?.items.find(
                (item) => item.id === e.target.value,
              );
              if (run?.result) {
                setRunId(run.id);
                const p = run.result.settings ?? {};
                const performance = (p.performance as Row) ?? {};
                const regression = (p.regression as Row) ?? {};
                setForm({
                  portfolio: String(p.portfolio ?? "KNK_MAIN"),
                  model: String(p.model ?? "CAPM"),
                  backtest: String(p.backtest_run_id ?? ""),
                  factors: String(p.factor_dataset_version_id ?? ""),
                  columns: Array.isArray(p.factor_columns)
                    ? p.factor_columns.join(",")
                    : "",
                  frequency: String(performance.frequency ?? "DAILY"),
                  start: String(performance.start ?? ""),
                  end: String(performance.end ?? ""),
                  riskFree: String(
                    Number(performance.risk_free_rate ?? 0) * 100,
                  ),
                  window: String(regression.rolling_window ?? 60),
                  lags: String(regression.hac_lags ?? 5),
                  confidence: String(regression.confidence ?? 0.95),
                  costs: String(p.estimated_cost_bps_per_period ?? 0),
                });
              }
            }}
          >
            <option value="">Select analysis</option>
            {history.data?.items.map((row) => (
              <option key={row.id} value={row.id}>
                {row.name}
              </option>
            ))}
          </select>
        </Field>
      </div>
      {(calculate.error || saved.error) && (
        <p className="error-state" role="alert">
          {(calculate.error || saved.error)?.message}
        </p>
      )}
      <div className="segmented">
        {["NET", "GROSS", "NET_AFTER_ESTIMATED_COSTS"].map((value) => (
          <button
            key={value}
            aria-pressed={basis === value}
            onClick={() => setBasis(value)}
          >
            {value.replaceAll("_", " ")}
          </button>
        ))}
      </div>
      <Kpis
        source={report?.source}
        asOf={report?.as_of ?? undefined}
        items={[
          {
            label: "Annualised intercept",
            value: pct(result?.annualised_alpha),
          },
          {
            label: "Raw excess return",
            value: pct(result?.raw_cumulative_excess_return),
          },
          { label: "p-value", value: number(result?.p_value, 4) },
          { label: "R squared", value: number(result?.r_squared, 4) },
          { label: "Observations", value: number(result?.observations, 0) },
          {
            label: "Confidence interval",
            value: interval
              ? `${pct(interval[0])} / ${pct(interval[1])}`
              : "--",
          },
        ]}
      />
      {result?.reason && (
        <p className="warning-note section-pad">{result.reason}</p>
      )}
      <div className="page-grid alpha-grid">
        <Panel
          title="Rolling alpha / confidence interval"
          source={report?.source}
          asOf={report?.as_of ?? undefined}
          quality={report?.quality}
        >
          <LineChart
            label="Rolling regression alpha"
            rows={result?.rolling ?? []}
            keys={[
              { key: "alpha", name: "Annual intercept" },
              { key: "lower", name: "Lower", color: COLORS.blue },
              { key: "upper", name: "Upper", color: COLORS.green },
            ]}
          />
        </Panel>
        <Panel
          title="Factor regression / HAC inference"
          source={report?.source}
          asOf={report?.as_of ?? undefined}
          quality={report?.quality}
          rows={result?.coefficients}
        >
          <DataTable
            id="alpha-coefficients"
            rows={result?.coefficients ?? []}
            columns={[
              { key: "factor", label: "Factor", size: 110 },
              {
                key: "coefficient",
                label: "Coefficient",
                numeric: true,
                format: (value) => significant(value),
              },
              {
                key: "standard_error",
                label: "Std error",
                numeric: true,
                format: (value) => significant(value),
              },
              { key: "t_statistic", label: "t", numeric: true },
              {
                key: "p_value",
                label: "p-value",
                numeric: true,
                format: (value) => significant(value),
              },
              {
                key: "lower",
                label: "Lower",
                numeric: true,
                format: (value) => significant(value),
              },
              {
                key: "upper",
                label: "Upper",
                numeric: true,
                format: (value) => significant(value),
              },
            ]}
          />
        </Panel>
      </div>
      {report && (
        <div className="section-pad">
          <p className="source-note">
            Run {report.id} / {report.model} / {result?.methodology}
          </p>
          {[...report.warnings, ...(result?.warnings ?? [])].map((warning) => (
            <p className="warning-note" key={warning}>
              {warning}
            </p>
          ))}
        </div>
      )}
    </div>
  );
}
