"use client";
import { useEffect } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { knkApi } from "@knk/api-client";
import { ArrowDownToLine, Play, X } from "lucide-react";
import { useTabState } from "./context";
import { PageTitle, useApi } from "./core-pages";
import {
  Badge,
  Chart,
  COLORS,
  Field,
  Kpis,
  LineChart,
  Panel,
  download,
  pct,
} from "./ui";
import type { Row, Run } from "./types";

export function MonteCarloWorkspace() {
  const [form, setForm] = useTabState("mc-settings", {
    portfolio: "KNK_MAIN",
    backtest_run_id: "",
    method: "BLOCK_BOOTSTRAP",
    paths: 2000,
    horizon: 252,
    block_length: 5,
    seed: 3110,
    capital: 100000,
    drawdown_threshold: 0.2,
    loss_threshold: 0.1,
    ruin_fraction: 0.5,
  });
  const [runId, setRunId] = useTabState("mc-run", "");
  const backtests = useApi<{ items: Run[] }>(
    "mc-backtests",
    "/api/v1/terminal/runs?kind=backtest",
  );
  const history = useApi<{ items: Run[] }>(
    "mc-history",
    "/api/v1/terminal/runs?kind=monte_carlo",
  );
  const current = useQuery({
    queryKey: ["mc-run", runId],
    queryFn: ({ signal }) =>
      knkApi.get<Run>(`/api/v1/terminal/runs/${runId}`, signal),
    enabled: !!runId,
    refetchInterval: (query) =>
      ["QUEUED", "RUNNING"].includes(query.state.data?.status ?? "")
        ? 1000
        : false,
  });
  const active = ["QUEUED", "RUNNING"].includes(current.data?.status ?? "");
  const run = useMutation({
    mutationFn: () => {
      const { portfolio, backtest_run_id, ...settings } = form;
      return knkApi.post<Run>("/api/v1/terminal/runs", {
        kind: "monte_carlo",
        name: `${form.method} / ${form.paths} paths`,
        parameters: { portfolio, backtest_run_id, settings },
      });
    },
    onSuccess: (result) => {
      setRunId(result.id);
      history.refetch();
    },
  });
  const result = current.data?.result;
  const refetchHistory = history.refetch;
  useEffect(() => {
    if (
      ["SUCCEEDED", "FAILED", "CANCELLED"].includes(current.data?.status ?? "")
    )
      void refetchHistory();
  }, [current.data?.status, refetchHistory]);
  const fan = Array.isArray(result?.fan) ? (result.fan as Row[]) : [];
  const distribution = Array.isArray(result?.terminal_distribution)
    ? (result.terminal_distribution as Row[])
    : [];
  return (
    <div className="research-page">
      <PageTitle code="MC" title="Monte Carlo">
        <Badge>{current.data?.status ?? "NOT RUN"}</Badge>
        <button
          className="primary-button"
          disabled={active || run.isPending}
          onClick={() => run.mutate()}
        >
          <Play size={12} />
          Run simulation
        </button>
        {active && (
          <button
            onClick={() =>
              knkApi
                .post(`/api/v1/terminal/runs/${runId}/cancel`)
                .then(() => current.refetch())
            }
          >
            <X size={12} />
            Cancel
          </button>
        )}
        {result && (
          <button
            onClick={() =>
              download(
                `mc-${runId}.json`,
                JSON.stringify(result, null, 2),
                "application/json",
              )
            }
          >
            <ArrowDownToLine size={12} />
            Export result
          </button>
        )}
      </PageTitle>
      <Panel
        title="Conditional return-path assumptions"
        quality="RESEARCH"
        source="Pinned portfolio or strategy returns"
      >
        <div className="performance-controls">
          <Field label="Portfolio">
            <input
              value={form.portfolio}
              onChange={(e) => setForm({ ...form, portfolio: e.target.value })}
            />
          </Field>
          <Field label="Return source">
            <select
              aria-label="Monte Carlo return source"
              value={form.backtest_run_id}
              onChange={(e) =>
                setForm({ ...form, backtest_run_id: e.target.value })
              }
            >
              <option value="">Internal portfolio / NET</option>
              {backtests.data?.items
                .filter((row) => row.status === "SUCCEEDED")
                .map((row) => (
                  <option value={row.id} key={row.id}>
                    {row.name}
                  </option>
                ))}
            </select>
          </Field>
          <Field label="Method">
            <select
              aria-label="Monte Carlo method"
              value={form.method}
              onChange={(e) => setForm({ ...form, method: e.target.value })}
            >
              {["BOOTSTRAP", "BLOCK_BOOTSTRAP", "NORMAL", "SHUFFLE"].map(
                (value) => (
                  <option key={value}>{value}</option>
                ),
              )}
            </select>
          </Field>
          {(
            [
              "paths",
              "horizon",
              "block_length",
              "seed",
              "capital",
              "drawdown_threshold",
              "loss_threshold",
              "ruin_fraction",
            ] as const
          ).map((key) => (
            <Field key={key} label={key.replaceAll("_", " ")}>
              <input
                aria-label={`Monte Carlo ${key}`}
                type="number"
                step={
                  key.includes("threshold") || key.includes("fraction")
                    ? 0.01
                    : 1
                }
                value={form[key]}
                onChange={(e) =>
                  setForm({ ...form, [key]: Number(e.target.value) })
                }
              />
            </Field>
          ))}
          <Field label="Saved simulation">
            <select
              value={runId}
              onChange={(e) => {
                setRunId(e.target.value);
                const saved = history.data?.items.find(
                  (row) => row.id === e.target.value,
                );
                if (saved)
                  setForm({
                    ...form,
                    ...saved.parameters,
                    ...(saved.parameters.settings as Row),
                  } as typeof form);
              }}
            >
              <option value="">Select run</option>
              {history.data?.items.map((row) => (
                <option value={row.id} key={row.id}>
                  {row.name} / {row.status}
                </option>
              ))}
            </select>
          </Field>
        </div>
        {(run.error || current.data?.error) && (
          <p className="error-state" role="alert">
            {run.error?.message || current.data?.error}
          </p>
        )}
      </Panel>
      <Kpis
        source={result?.source}
        asOf={result?.as_of}
        items={[
          {
            label: "Median return",
            value: pct(result?.metrics?.median_return),
          },
          {
            label: "5th percentile return",
            value: pct(result?.metrics?.return_p05),
          },
          {
            label: "Loss threshold probability",
            value: pct(result?.metrics?.loss_probability),
          },
          {
            label: "Drawdown threshold probability",
            value: pct(result?.metrics?.drawdown_probability),
          },
          {
            label: "Ruin threshold probability",
            value: pct(result?.metrics?.ruin_probability),
          },
          {
            label: "Loss probability MC error",
            value: pct(result?.metrics?.loss_probability_mc_se),
          },
        ]}
      />
      <div className="page-grid model-grid">
        <Panel
          title="Conditional wealth quantiles"
          source={result?.source}
          quality={result?.quality}
          asOf={result?.as_of}
          loading={active}
          error={current.error}
        >
          <LineChart
            label="Monte Carlo quantiles"
            rows={fan}
            keys={[
              { key: "p05", name: "5%", color: COLORS.red },
              { key: "p50", name: "Median" },
              { key: "p95", name: "95%", color: COLORS.green },
            ]}
          />
        </Panel>
        <Panel
          title="Terminal return distribution"
          source={result?.source}
          quality={result?.quality}
        >
          <Chart
            label="Monte Carlo distribution"
            option={{
              xAxis: {
                type: "category",
                data: distribution.map((row) => pct(row.bin_low)),
              },
              yAxis: { type: "value" },
              series: [
                {
                  type: "bar",
                  data: distribution.map((row) => Number(row.count)),
                  itemStyle: { color: COLORS.amber },
                },
              ],
            }}
          />
        </Panel>
      </div>
      {result && (
        <Panel
          title="Simulation evidence"
          source={result.calculation_version}
          quality={result.quality}
        >
          {result.warnings.map((warning) => (
            <p className="warning-note section-pad" key={warning}>
              {warning}
            </p>
          ))}
        </Panel>
      )}
    </div>
  );
}
