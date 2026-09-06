"use client";
import { useEffect } from "react";

import { useMutation, useQuery } from "@tanstack/react-query";
import { knkApi } from "@knk/api-client";
import { ArrowDownToLine, Play, X } from "lucide-react";
import { records, useTabState } from "./context";
import { PageTitle, useApi } from "./core-pages";
import {
  Badge,
  DataTable,
  Empty,
  Field,
  LineChart,
  Panel,
  download,
  number,
} from "./ui";
import type { Row, Run } from "./types";

const rows = (value: unknown): Row[] =>
  Array.isArray(value) ? records(value as Row[]) : [];

export function ModelWorkspace() {
  const [form, setForm] = useTabState("model-settings", {
    symbol: "SPY",
    source_mode: "SOURCE_AWARE",
    dataset_version_id: "",
    start: "",
    end: "",
    model: "RIDGE",
    horizon: 5,
    regularisation: 1,
    train_fraction: 0.6,
    validation_fraction: 0.2,
    folds: 3,
    seed: 3110,
    trees: 100,
    depth: 4,
    fee_bps: 5,
    slippage_bps: 5,
  });
  const [runId, setRunId] = useTabState("model-run", "");
  const [partition, setPartition] = useTabState("model-partition", "TEST");
  const history = useApi<{ items: Run[] }>(
    "model-history",
    "/api/v1/terminal/runs?kind=model",
  );
  const current = useQuery({
    queryKey: ["model-run", runId],
    queryFn: ({ signal }) =>
      knkApi.get<Run>(`/api/v1/terminal/runs/${runId}`, signal),
    enabled: !!runId,
    refetchInterval: (q) =>
      ["QUEUED", "RUNNING"].includes(q.state.data?.status ?? "") ? 1000 : false,
  });
  const active = ["QUEUED", "RUNNING"].includes(current.data?.status ?? "");
  const run = useMutation({
    mutationFn: () => {
      const {
        symbol,
        source_mode,
        dataset_version_id,
        start,
        end,
        ...settings
      } = form;
      return knkApi.post<Run>("/api/v1/terminal/runs", {
        kind: "model",
        name: `${form.symbol} / ${form.model}`,
        parameters: {
          symbol,
          source_mode,
          dataset_version_id,
          start,
          end,
          settings,
        },
      });
    },
    onSuccess: (data) => {
      setRunId(data.id);
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
  const metrics = rows(result?.metrics);
  const predictions = rows(result?.predictions).filter(
    (row) => row.partition === partition,
  );
  const clustering = result?.model === "KMEANS";
  const classification = result?.model === "LOGISTIC";
  const chooseRun = (id: string) => {
    setRunId(id);
    const saved = history.data?.items.find((row) => row.id === id);
    if (saved) {
      const p = saved.parameters;
      setForm({ ...form, ...p, ...(p.settings as Row) } as typeof form);
    }
  };
  return (
    <div className="research-page">
      <PageTitle code="MODEL" title="Model Lab">
        <Badge>{current.data?.status ?? "NOT RUN"}</Badge>
        <button
          className="primary-button"
          disabled={active || run.isPending}
          onClick={() => run.mutate()}
        >
          <Play size={12} />
          Train model
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
                `model-${runId}.json`,
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
        title="Chronological training / purged partitions"
        source="Approved scikit-learn pipeline"
        quality="RESEARCH"
      >
        <div className="performance-controls">
          <Field label="Security">
            <input
              aria-label="Model security"
              value={form.symbol}
              onChange={(e) =>
                setForm({ ...form, symbol: e.target.value.toUpperCase() })
              }
            />
          </Field>
          <Field label="Price source">
            <select
              aria-label="Model source"
              value={form.source_mode}
              onChange={(e) =>
                setForm({ ...form, source_mode: e.target.value })
              }
            >
              <option value="SOURCE_AWARE">Source-aware history</option>
              <option value="DEMO_RESEARCH">Independent DEMO research</option>
            </select>
          </Field>
          <Field label="Dataset version">
            <input
              value={form.dataset_version_id}
              onChange={(e) =>
                setForm({ ...form, dataset_version_id: e.target.value })
              }
            />
          </Field>
          <Field label="Estimator">
            <select
              aria-label="Model estimator"
              value={form.model}
              onChange={(e) => setForm({ ...form, model: e.target.value })}
            >
              {[
                "LINEAR",
                "LOGISTIC",
                "RIDGE",
                "LASSO",
                "ELASTIC_NET",
                "TREE",
                "FOREST",
                "GRADIENT_BOOSTING",
                "ENSEMBLE",
                "KMEANS",
              ].map((name) => (
                <option key={name}>{name}</option>
              ))}
            </select>
          </Field>
          {(
            [
              "horizon",
              "regularisation",
              "train_fraction",
              "validation_fraction",
              "folds",
              "seed",
              "trees",
              "depth",
              "fee_bps",
              "slippage_bps",
            ] as const
          ).map((key) => (
            <Field key={key} label={key.replaceAll("_", " ")}>
              <input
                type="number"
                step={
                  key.includes("fraction") || key === "regularisation"
                    ? 0.05
                    : 1
                }
                value={form[key]}
                onChange={(e) =>
                  setForm({ ...form, [key]: Number(e.target.value) })
                }
              />
            </Field>
          ))}
          {(["start", "end"] as const).map((key) => (
            <Field key={key} label={key}>
              <input
                type="date"
                value={form[key]}
                onChange={(e) => setForm({ ...form, [key]: e.target.value })}
              />
            </Field>
          ))}
          <Field label="Saved model">
            <select
              aria-label="Saved model"
              value={runId}
              onChange={(e) => chooseRun(e.target.value)}
            >
              <option value="">Select run</option>
              {history.data?.items.map((row) => (
                <option key={row.id} value={row.id}>
                  {row.name} / {row.status}
                </option>
              ))}
            </select>
          </Field>
        </div>
        {(run.error || current.data?.error || current.error) && (
          <p role="alert" className="error-state">
            {run.error?.message ||
              current.data?.error ||
              current.error?.message}
          </p>
        )}
      </Panel>
      <div className="page-grid model-grid">
        <Panel
          title={
            clustering
              ? "Cluster assignments"
              : classification
                ? "Direction probability / observed return"
                : "Predicted / observed forward return"
          }
          source={result?.source}
          quality={result?.quality}
          asOf={result?.as_of}
          loading={active}
          actions={
            <select
              aria-label="Model partition"
              value={partition}
              onChange={(e) => setPartition(e.target.value)}
            >
              {["TRAIN", "VALIDATION", "TEST"].map((value) => (
                <option key={value}>{value}</option>
              ))}
            </select>
          }
        >
          {result ? (
            <LineChart
              label="Model predictions"
              rows={predictions}
              keys={
                clustering
                  ? [{ key: "prediction", name: "Cluster" }]
                  : classification
                    ? [{ key: "probability", name: "Up probability" }]
                    : [
                        { key: "prediction", name: "Prediction" },
                        { key: "actual", name: "Observed" },
                      ]
              }
            />
          ) : (
            <Empty title="No fitted model" />
          )}
        </Panel>
        <Panel
          title="Partition diagnostics"
          source="Held-out validation / test"
          quality="RESEARCH"
        >
          <DataTable
            id="model-partitions"
            rows={metrics}
            columns={[
              { key: "partition", label: "Partition" },
              { key: "observations", label: "N", numeric: true },
              {
                key: "rmse",
                label: "RMSE",
                numeric: true,
                format: (value) => number(value, 5),
              },
              {
                key: "r_squared",
                label: "R2",
                numeric: true,
                format: (value) => number(value, 3),
              },
              { key: "accuracy", label: "Accuracy", numeric: true },
              { key: "auc", label: "AUC", numeric: true },
              { key: "rank_ic", label: "Rank IC", numeric: true },
            ]}
          />
        </Panel>
        <Panel
          title="Expanding-window evaluation"
          source="TimeSeriesSplit / horizon purge"
          quality="RESEARCH"
        >
          <DataTable
            id="model-walk"
            rows={rows(result?.walk_forward)}
            columns={[
              { key: "fold", label: "Fold" },
              { key: "train_end", label: "Train end" },
              { key: "test_start", label: "Test start" },
              { key: "test_observations", label: "N", numeric: true },
              { key: "gap", label: "Purge", numeric: true },
              {
                key: "rmse",
                label: "RMSE",
                numeric: true,
                format: (value) => number(value, 5),
              },
              { key: "accuracy", label: "Accuracy", numeric: true },
            ]}
          />
        </Panel>
        <Panel
          title="Fitted coefficients / feature importance"
          source={String(result?.feature_version ?? "NOT RUN")}
          quality="RESEARCH"
        >
          <DataTable
            id="model-features"
            rows={rows(result?.feature_importance)}
            columns={[
              { key: "feature", label: "Feature" },
              {
                key: "value",
                label: "Value",
                numeric: true,
                format: (value) => number(value, 6),
              },
            ]}
          />
        </Panel>
      </div>
      {result && (
        <Panel
          className="research-table-panel"
          title="Held-out cost-adjusted trading diagnostics"
          source="Positive-signal next-open simulation / native currency"
          quality="RESEARCH"
        >
          <DataTable
            id="model-cost-backtests"
            rows={rows(result.cost_backtests).map((row) => ({
              partition: row.partition,
              currency: row.currency,
              ...(row.metrics as Row),
            }))}
            columns={[
              { key: "partition", label: "Partition" },
              { key: "currency", label: "Currency" },
              {
                key: "total_return",
                label: "Net return",
                percent: true,
                numeric: true,
              },
              { key: "sharpe", label: "Sharpe", numeric: true },
              {
                key: "max_drawdown",
                label: "Drawdown",
                percent: true,
                numeric: true,
              },
              { key: "turnover", label: "Turnover", numeric: true },
              { key: "commission", label: "Fees", numeric: true },
              { key: "fill_count", label: "Fills", numeric: true },
            ]}
          />
        </Panel>
      )}
      {result && (
        <Panel
          title="Model evidence"
          source={result.calculation_version}
          quality={result.quality}
        >
          <p className="muted">
            Dataset: {String((result.inputs as Row)?.dataset_version_id)} /
            SHA256: {String((result.inputs as Row)?.content_hash)}
          </p>
          <p className="muted">
            Artifact SHA256: {String((result.artifact as Row)?.content_hash)}
          </p>
          {result.warnings.map((warning) => (
            <p className="warning" key={warning}>
              {warning}
            </p>
          ))}
        </Panel>
      )}
    </div>
  );
}
