"use client";
import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { knkApi } from "@knk/api-client";
import {
  ArrowDownToLine,
  Check,
  Copy,
  Play,
  Plus,
  Save,
  Upload,
  X,
} from "lucide-react";
import { records, usePortfolio, useTabState, useTerminal } from "./context";
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
  download,
  number,
  pct,
  timestamp,
  type Column,
} from "./ui";
import { PageTitle, useApi } from "./core-pages";
import type { Row, Run, UploadPreview, MacroDashboardPayload } from "./types";

export function BacktestPage() {
  const { bootstrap, config, setConfig, activeTab } = useTerminal();
  const portfolio = usePortfolio();
  const client = useQueryClient();
  const [form, setForm] = useTabState("backtest-config", {
    symbol: "SPY",
    fast: 20,
    slow: 50,
    capital: 0,
    fee_bps: 5,
    slippage_bps: 5,
    dataset_id: activeTab.route.startsWith("/backtests/dataset/")
      ? activeTab.route.split("/")[3]
      : "",
    start: "",
    end: "",
  });
  const [runId, setRunId] = useTabState(
    "backtest-run",
    activeTab.route.startsWith("/backtests/run/")
      ? activeTab.route.split("/")[3]
      : "",
  );
  const datasets = useApi<{ items: Row[] }>("datasets", "/api/v1/datasets");
  const recent = useApi<{ items: Run[] }>(
    "backtest-runs",
    "/api/v1/terminal/runs?kind=backtest",
  );
  const current = useQuery({
    queryKey: ["run", runId],
    queryFn: ({ signal }) =>
      knkApi.get<Run>(`/api/v1/terminal/runs/${runId}`, signal),
    enabled: !!runId,
    refetchInterval: (q) =>
      ["RUNNING", "QUEUED"].includes(q.state.data?.status ?? "") ? 600 : false,
  });
  useEffect(() => {
    if (!runId && recent.data?.items[0]) setRunId(recent.data.items[0].id);
  }, [recent.data, runId, setRunId]);
  useEffect(() => {
    if (runId && config.inspectRunId !== runId)
      setConfig((c) => ({ ...c, inspectRunId: runId }));
  }, [runId, config.inspectRunId, setConfig]);
  const mutation = useMutation({
    mutationFn: () =>
      knkApi.post<Run>("/api/v1/terminal/runs", {
        kind: "backtest",
        name: `${form.symbol} / MA ${form.fast}:${form.slow}`,
        parameters: {
          ...form,
          capital:
            form.capital || Number(portfolio.data?.portfolio.reference_capital),
        },
      }),
    onSuccess: (r) => {
      setRunId(r.id);
      client.setQueryData(["run", r.id], r);
      setConfig((c) => ({ ...c, inspectRunId: r.id, inspector: true }));
      recent.refetch();
    },
  });
  const result = current.data?.result;
  const active = ["QUEUED", "RUNNING"].includes(current.data?.status ?? "");
  const exportRun = async () => {
    const report = await knkApi.get<{ download_url: string }>(
      `/api/v1/terminal/runs/${runId}/export`,
    );
    window.open(knkApi.downloadUrl(report.download_url), "_blank", "noopener");
  };
  return (
    <>
      <PageTitle code="BACKTEST" title="Backtest Lab">
        <Badge>{current.data?.status ?? "TEMPLATE READY"}</Badge>
        <button
          className="primary-button"
          disabled={active || mutation.isPending || !portfolio.data}
          onClick={() => mutation.mutate()}
        >
          <Play size={12} />
          {active ? "Running" : "Run backtest"}
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
          <button onClick={exportRun}>
            <ArrowDownToLine size={12} />
            Export Excel
          </button>
        )}
      </PageTitle>
      <Panel
        title="Moving-average crossover / approved template"
        source="Versioned strategy parameters"
        asOf={bootstrap.as_of}
        quality="ASSUMPTIONS"
      >
        <div
          className="compact-form"
          style={{ gridTemplateColumns: "repeat(5,minmax(0,1fr))" }}
        >
          <Field label="Security">
            <select
              aria-label="Backtest security"
              value={form.symbol}
              onChange={(e) => setForm({ ...form, symbol: e.target.value })}
            >
              {bootstrap.quotes
                .filter(
                  (q) => q.asset_class === "Equity" || q.asset_class === "ETF",
                )
                .map((q) => (
                  <option key={q.id}>{q.symbol}</option>
                ))}
            </select>
          </Field>
          <Field label="Dataset">
            <select
              aria-label="Backtest dataset"
              value={form.dataset_id}
              onChange={(e) => setForm({ ...form, dataset_id: e.target.value })}
            >
              <option value="">DemoProvider daily prices</option>
              {datasets.data?.items
                .filter((d) => d.source === "USER_UPLOAD")
                .map((d) => (
                  <option key={String(d.id)} value={String(d.id)}>
                    {String(d.name)}
                  </option>
                ))}
            </select>
          </Field>
          {(
            ["fast", "slow", "capital", "fee_bps", "slippage_bps"] as const
          ).map((k) => (
            <Field key={k} label={k.replaceAll("_", " ")}>
              <input
                aria-label={`Backtest ${k}`}
                className="assumption"
                type="number"
                min={k.includes("bps") ? 0 : 1}
                value={
                  k === "capital"
                    ? form.capital ||
                      portfolio.data?.portfolio.reference_capital ||
                      ""
                    : form[k]
                }
                onChange={(e) =>
                  setForm({ ...form, [k]: Number(e.target.value) })
                }
              />
            </Field>
          ))}
          <Field label="Start">
            <input
              type="date"
              value={form.start}
              onChange={(e) => setForm({ ...form, start: e.target.value })}
            />
          </Field>
          <Field label="End">
            <input
              type="date"
              value={form.end}
              onChange={(e) => setForm({ ...form, end: e.target.value })}
            />
          </Field>
          <Field label="Saved run">
            <select
              aria-label="Saved backtest"
              value={runId}
              onChange={(e) => setRunId(e.target.value)}
            >
              <option value="">Select run</option>
              {recent.data?.items.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.name} / {r.status}
                </option>
              ))}
            </select>
          </Field>
        </div>
        {mutation.error && (
          <p className="error-state" role="alert">
            {mutation.error.message}
          </p>
        )}
      </Panel>
      <Kpis
        source={result?.source}
        asOf={result?.as_of}
        items={[
          { label: "Total return", value: pct(result?.metrics?.total_return) },
          { label: "CAGR", value: pct(result?.metrics?.cagr) },
          { label: "Sharpe", value: number(result?.metrics?.sharpe) },
          {
            label: "Max drawdown",
            value: pct(result?.metrics?.max_drawdown),
            className: "negative",
          },
          { label: "Trades", value: number(result?.metrics?.trade_count, 0) },
        ]}
      />
      <div className="page-grid analytics-grid">
        <Panel
          title="Strategy equity / buy-and-hold benchmark"
          source={result?.source}
          asOf={result?.as_of}
          quality={result?.quality}
          loading={active}
          error={current.data?.error || current.error}
        >
          {result ? (
            <LineChart
              label="Backtest equity curve"
              rows={records(result.equity_curve ?? [])}
              keys={[
                { key: "equity", name: "MA crossover" },
                { key: "benchmark", name: "Buy and hold", color: COLORS.blue },
              ]}
            />
          ) : (
            <Empty
              title="No completed backtest"
              detail="Run the selected template to calculate a persisted result."
            />
          )}
        </Panel>
        <Panel
          title="Drawdown"
          source={result?.source}
          asOf={result?.as_of}
          quality={result?.quality}
        >
          {result ? (
            <LineChart
              label="Backtest drawdown"
              percent
              rows={records(result.equity_curve ?? [])}
              keys={[{ key: "drawdown", name: "Drawdown", color: COLORS.red }]}
            />
          ) : (
            <Empty title="Awaiting result" />
          )}
        </Panel>
        <Panel
          className="wide-panel"
          title="Closed trades / simulation only"
          source={result?.source}
          asOf={result?.as_of}
          quality={result?.quality}
          rows={result?.trades}
        >
          <DataTable
            id="backtest-trades"
            rows={result?.trades ?? []}
            columns={[
              { key: "entry", label: "Entry date", size: 160 },
              { key: "exit", label: "Exit date", size: 160 },
              { key: "quantity", label: "Quantity", numeric: true },
              { key: "entry_price", label: "Entry", numeric: true },
              { key: "exit_price", label: "Exit", numeric: true },
              { key: "pnl", label: "P&L", numeric: true, money: true },
            ]}
          />
        </Panel>
      </div>
    </>
  );
}

export function FactorPage() {
  const [lookback, setLookback] = useTabState("factor-lookback", 63);
  const query = useApi<{
    items: Row[];
    source: string;
    as_of: string;
    quality: string;
    warnings: string[];
  }>("factor", `/api/v1/factors?lookback=${lookback}`);
  const d = query.data;
  return (
    <>
      <PageTitle code="FACTOR" title="Factor Lab / Momentum">
        <select
          aria-label="Factor horizon"
          value={lookback}
          onChange={(e) => setLookback(Number(e.target.value))}
        >
          {[
            [21, "1M"],
            [63, "3M"],
            [126, "6M"],
            [252, "12M"],
          ].map(([v, l]) => (
            <option key={v} value={v}>
              {l} momentum
            </option>
          ))}
        </select>
        <Badge>CALCULATED</Badge>
      </PageTitle>
      <div className="page-grid analytics-grid">
        <Panel
          title="Cross-sectional momentum rank"
          source={d?.source}
          asOf={d?.as_of}
          quality={d?.quality}
          loading={query.isLoading}
          error={query.error}
        >
          <Chart
            label="Factor rank chart"
            option={{
              xAxis: {
                type: "category",
                data: d?.items.map((r) => String(r.symbol)),
                axisLabel: { rotate: 35, fontSize: 9 },
              },
              yAxis: {
                type: "value",
                splitLine: { lineStyle: { color: COLORS.grid } },
                axisLabel: {
                  formatter: (v: number) => `${(v * 100).toFixed(0)}%`,
                },
              },
              series: [
                {
                  type: "bar",
                  data: d?.items.map((r) => ({
                    value: r.factor as number,
                    itemStyle: {
                      color: Number(r.factor) >= 0 ? COLORS.amber : COLORS.red,
                    },
                  })),
                },
              ],
            }}
          />
        </Panel>
        <Panel
          title="Coverage / methodology"
          source={d?.source}
          asOf={d?.as_of}
          quality={d?.quality}
        >
          <dl className="detail-list section-pad">
            <dt>Universe</dt>
            <dd>Stored equities and ETFs</dd>
            <dt>Coverage</dt>
            <dd>{d?.items.length ?? "--"} securities</dd>
            <dt>Window</dt>
            <dd>{lookback} trading days</dd>
            <dt>Transform</dt>
            <dd>Cross-sectional z-score</dd>
            <dt>Quantiles</dt>
            <dd>Five equal-count groups</dd>
            <dt>Forward IC</dt>
            <dd>Not observable for latest signal</dd>
          </dl>
          {d?.warnings.map((w) => (
            <p className="warning-note section-pad" key={w}>
              {w}
            </p>
          ))}
        </Panel>
        <Panel
          className="wide-panel"
          title="Factor observations"
          source={d?.source}
          asOf={d?.as_of}
          quality={d?.quality}
          rows={d?.items}
        >
          <DataTable
            id="factor-values"
            rows={d?.items ?? []}
            columns={[
              { key: "symbol", label: "Security", size: 90 },
              {
                key: "factor",
                label: "Momentum",
                numeric: true,
                percent: true,
              },
              { key: "zscore", label: "Z-score", numeric: true },
              { key: "rank", label: "Rank", numeric: true, size: 70 },
              { key: "quantile", label: "Quantile", numeric: true, size: 80 },
              {
                key: "volatility",
                label: "Volatility",
                numeric: true,
                percent: true,
              },
              { key: "sector", label: "Sector", size: 175 },
              { key: "source", label: "Source" },
            ]}
          />
        </Panel>
      </div>
    </>
  );
}

export function DataDropPage() {
  const { open } = useTerminal();
  const [preview, setPreview] = useTabState<UploadPreview | null>(
    "upload-preview",
    null,
  );
  const [mapping, setMapping] = useTabState("upload-mapping", {
    date: "date",
    close: "close",
  });
  const [name, setName] = useTabState("upload-name", "");
  const [licence, setLicence] = useTabState("upload-licence", "");
  const [validation, setValidation] = useState<{
    valid: boolean;
    errors: string[];
    row_count: number;
  } | null>(null);
  const [imported, setImported] = useState<{
    dataset_id: string;
    row_count: number;
  } | null>(null);
  const client = useQueryClient();
  const upload = useMutation({
    mutationFn: (file: File) => {
      const body = new FormData();
      body.append("file", file);
      return knkApi.post<UploadPreview>("/api/v1/uploads/preview", body);
    },
    onSuccess: (r) => {
      setPreview(r);
      setName(r.name.replace(/\.[^.]+$/, ""));
      setValidation(null);
      setImported(null);
      setMapping({
        date: r.columns.find((c) => /date|time/i.test(c.name))?.name ?? "",
        close: r.columns.find((c) => /close|price/i.test(c.name))?.name ?? "",
      });
    },
  });
  const validate = useMutation({
    mutationFn: () =>
      knkApi.post<{ valid: boolean; errors: string[]; row_count: number }>(
        "/api/v1/uploads/validate",
        { upload_id: preview?.upload_id, mapping, name, licence },
      ),
    onSuccess: setValidation,
  });
  const ingest = useMutation({
    mutationFn: () =>
      knkApi.post<{ dataset_id: string; row_count: number }>(
        "/api/v1/uploads/import",
        { upload_id: preview?.upload_id, mapping, name, licence },
      ),
    onSuccess: (r) => {
      setImported(r);
      client.invalidateQueries({ queryKey: ["datasets"] });
    },
  });
  const step = imported ? 4 : validation?.valid ? 3 : preview ? 1 : 0;
  return (
    <>
      <PageTitle code="DROP" title="Data Drop / Import Workspace">
        <Badge>USER PROVIDED</Badge>
      </PageTitle>
      <div className="step-strip">
        {["Upload", "Preview & map", "Validate", "Import", "Catalogue"].map(
          (s, i) => (
            <span className={i <= step ? "active" : ""} key={s}>
              {i < step ? <Check size={10} /> : i + 1} {s}
            </span>
          ),
        )}
      </div>
      <div className="two-column">
        <Panel
          title="File / schema mapping"
          source={preview?.source ?? "User file"}
          asOf={preview?.as_of}
          quality={preview?.quality ?? "UNVERIFIED"}
        >
          <div className="section-pad">
            <Field label="Source file / CSV, JSON or XLSX">
              <input
                className="file-input"
                type="file"
                accept=".csv,.json,.xlsx"
                aria-label="Upload dataset"
                disabled={upload.isPending}
                onChange={(e) =>
                  e.target.files?.[0] && upload.mutate(e.target.files[0])
                }
              />
            </Field>
          </div>
          {preview && (
            <div className="modal-body">
              <Field label="Dataset name">
                <input
                  aria-label="Dataset name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                />
              </Field>
              {(["date", "close"] as const).map((role) => (
                <Field key={role} label={`${role} column`}>
                  <select
                    aria-label={`Map ${role}`}
                    value={mapping[role]}
                    onChange={(e) => {
                      setMapping({ ...mapping, [role]: e.target.value });
                      setValidation(null);
                    }}
                  >
                    <option value="">Select column</option>
                    {preview.columns.map((c) => (
                      <option key={c.name}>{c.name}</option>
                    ))}
                  </select>
                </Field>
              ))}
              <Field label="Licence / permitted use">
                <textarea
                  aria-label="Licence note"
                  rows={3}
                  value={licence}
                  onChange={(e) => {
                    setLicence(e.target.value);
                    setValidation(null);
                  }}
                />
              </Field>
              <button
                disabled={!licence || !name || validate.isPending}
                onClick={() => validate.mutate()}
              >
                <Check size={12} />
                Validate
              </button>
              <button
                className="primary-button"
                disabled={!validation?.valid || ingest.isPending || !!imported}
                onClick={() => ingest.mutate()}
              >
                <Upload size={12} />
                {ingest.isPending ? "Importing..." : "Import dataset"}
              </button>
            </div>
          )}
          {[upload.error, validate.error, ingest.error]
            .filter(Boolean)
            .map((e, i) => (
              <p className="error-state" role="alert" key={i}>
                {(e as Error).message}
              </p>
            ))}
        </Panel>
        <div className="stress-main">
          <Kpis
            source={preview?.source}
            asOf={preview?.as_of}
            items={[
              { label: "Rows", value: number(preview?.row_count, 0) },
              { label: "Columns", value: number(preview?.columns.length, 0) },
              { label: "Missing", value: number(preview?.missing, 0) },
              { label: "Duplicates", value: number(preview?.duplicates, 0) },
            ]}
          />
          <Panel
            className="page-grid"
            title="File preview / first 30 rows"
            source={preview?.source}
            asOf={preview?.as_of}
            quality={preview?.quality}
            loading={upload.isPending}
          >
            {preview ? (
              <DataTable
                id="upload-preview"
                rows={preview.preview}
                columns={preview.columns.map((c) => ({
                  key: c.name,
                  label: c.name,
                  numeric: c.type === "number",
                }))}
              />
            ) : (
              <Empty
                title="No file selected"
                detail="CSV, JSON and XLSX are parsed and validated before import."
              />
            )}
          </Panel>
          <Panel
            title="Validation / import result"
            source={preview?.source}
            asOf={preview?.as_of}
            quality={imported ? "USER PROVIDED" : "UNVERIFIED"}
          >
            <div className="section-pad">
              {preview && (
                <p className="source-note" style={{ overflowWrap: "anywhere" }}>
                  SHA-256 {preview.hash}
                </p>
              )}
              {validation && (
                <>
                  <Badge>{validation.valid ? "VALIDATED" : "FAILED"}</Badge>
                  {validation.errors.map((e) => (
                    <p className="negative" key={e}>
                      {e}
                    </p>
                  ))}
                </>
              )}
              {imported ? (
                <div className="control-row">
                  <Badge>IMPORTED</Badge>
                  <span>{imported.row_count} rows</span>
                  <button
                    onClick={() =>
                      open(`/data-catalogue/${imported.dataset_id}`, "DATASET")
                    }
                  >
                    Open Data Catalogue
                  </button>
                  <button
                    onClick={() =>
                      open(
                        `/backtests/dataset/${imported.dataset_id}`,
                        "DATA BACKTEST",
                      )
                    }
                  >
                    Backtest dataset
                  </button>
                </div>
              ) : (
                <p className="source-note">
                  Point-in-time availability and licence ownership remain user
                  supplied.
                </p>
              )}
            </div>
          </Panel>
        </div>
      </div>
    </>
  );
}

export function CataloguePage({ route }: { route: string }) {
  const list = useApi<{ items: Row[] }>("datasets", "/api/v1/datasets");
  const [selected, setSelected] = useTabState(
    "selected-dataset",
    route.split("/")[2] ?? "",
  );
  const detail = useQuery({
    queryKey: ["dataset-detail", selected],
    queryFn: ({ signal }) =>
      knkApi.get<{
        name: string;
        source: string;
        quality: string;
        versions: {
          id: string;
          version: number;
          rows: number;
          hash: string;
          schema: {
            preview?: Row[];
            columns?: { name: string }[];
            licence?: string;
          };
          as_of: string;
        }[];
      }>(`/api/v1/datasets/${selected}`, signal),
    enabled: !!selected,
  });
  const version = detail.data?.versions[0];
  return (
    <>
      <PageTitle code="CATALOGUE" title="Data Catalogue" />
      <div className="page-grid analytics-grid">
        <Panel
          className="wide-panel"
          title="Dataset registry"
          source="KnK dataset catalogue"
          asOf={list.data?.items[0]?.created_at as string}
          quality="MIXED SOURCES"
          error={list.error}
          loading={list.isLoading}
        >
          <DataTable
            id="datasets"
            rows={list.data?.items ?? []}
            onSelect={(r) => setSelected(String(r.id))}
            columns={[
              { key: "name", label: "Dataset", size: 220 },
              { key: "dataset_type", label: "Type", size: 150 },
              { key: "source", label: "Source", size: 150 },
              {
                key: "quality",
                label: "Quality",
                size: 145,
                format: (v) => <Badge>{String(v)}</Badge>,
              },
              {
                key: "created_at",
                label: "Created",
                size: 180,
                format: (v) => timestamp(String(v)),
              },
            ]}
          />
        </Panel>
        <Panel
          title={detail.data?.name ?? "Dataset preview"}
          source={detail.data?.source}
          asOf={version?.as_of}
          quality={detail.data?.quality}
          error={detail.error}
        >
          {version ? (
            <DataTable
              id="dataset-version"
              rows={version.schema.preview ?? []}
              columns={(version.schema.columns ?? []).map((c) => ({
                key: c.name,
                label: c.name,
              }))}
            />
          ) : (
            <Empty title="Select a dataset" />
          )}
        </Panel>
        <Panel
          title="Version / lineage"
          source={detail.data?.source}
          asOf={version?.as_of}
          quality={detail.data?.quality}
        >
          {version ? (
            <dl className="detail-list section-pad">
              <dt>Version</dt>
              <dd>{version.version}</dd>
              <dt>Rows</dt>
              <dd>{version.rows}</dd>
              <dt>Content hash</dt>
              <dd>{version.hash}</dd>
              <dt>Licence</dt>
              <dd>{version.schema.licence ?? "Seed fixture"}</dd>
              <dt>Availability</dt>
              <dd>Point-in-time unverified</dd>
            </dl>
          ) : (
            <Empty title="No version selected" />
          )}
        </Panel>
      </div>
    </>
  );
}

export function JobsPage() {
  const jobs = useApi<{ items: Row[] }>("jobs", "/api/v1/jobs");
  const runs = useApi<{ items: Run[] }>("all-runs", "/api/v1/terminal/runs");
  return (
    <>
      <PageTitle code="JOBS" title="Data & Analytical Jobs" />
      <div className="page-grid" style={{ gridTemplateRows: "1fr 1fr" }}>
        <Panel
          title="Analytical run history"
          source="Persisted job lifecycle"
          asOf={runs.data?.items[0]?.created_at}
          quality="OBSERVED"
          rows={records(runs.data?.items ?? [])}
        >
          <DataTable
            id="analytical-jobs"
            rows={records(runs.data?.items ?? [])}
            columns={[
              { key: "name", label: "Run", size: 210 },
              { key: "kind", label: "Type", size: 90 },
              {
                key: "status",
                label: "State",
                size: 120,
                format: (v) => <Badge>{String(v)}</Badge>,
              },
              {
                key: "created_at",
                label: "Created",
                size: 180,
                format: (v) => timestamp(String(v)),
              },
              { key: "error", label: "Error", size: 300 },
            ]}
          />
        </Panel>
        <Panel
          title="Ingestion queue"
          source="Database ingestion records"
          quality="OBSERVED"
          error={jobs.error}
        >
          <DataTable
            id="data-jobs"
            rows={jobs.data?.items ?? []}
            columns={[
              { key: "job_type", label: "Job type", size: 200 },
              { key: "provider", label: "Provider", size: 150 },
              {
                key: "status",
                label: "State",
                format: (v) => <Badge>{String(v)}</Badge>,
              },
              {
                key: "progress",
                label: "Progress",
                numeric: true,
                percent: true,
              },
              { key: "records_accepted", label: "Accepted", numeric: true },
              { key: "error_message", label: "Error", size: 280 },
            ]}
          />
        </Panel>
      </div>
    </>
  );
}

export function QuantPage() {
  const strategies = useApi<{ items: Row[] }>(
    "strategies",
    "/api/v1/strategies",
  );
  const { open } = useTerminal();
  const [code, setCode] = useTabState(
    "quant-code",
    `# KnK Capital / approved moving-average template\n# Research source only; edits are not executed by the API.\n\nfast_window = 20\nslow_window = 50\n\nfast = close.rolling(fast_window).mean()\nslow = close.rolling(slow_window).mean()\nsignal = (fast > slow).astype(int)\n# The backtest engine fills signals at the next open.\n`,
  );
  return (
    <>
      <PageTitle code="QUANT" title="Quant Lab / Strategy Research">
        <button onClick={() => download("knk-strategy.py", code)}>
          <ArrowDownToLine size={12} />
          Export Python
        </button>
        <button
          className="primary-button"
          onClick={() => open("/backtests", "BACKTEST")}
        >
          <Play size={12} />
          Configure template run
        </button>
      </PageTitle>
      <div className="two-column">
        <Panel
          title="Strategy catalogue"
          source="KnK strategy registry"
          quality="DEMO DATA"
          error={strategies.error}
        >
          {strategies.data?.items.map((s) => (
            <div key={String(s.id)} className="list-record">
              <strong className="amber">{String(s.name)}</strong>
              <p>{String(s.description)}</p>
              <Badge>{String(s.status)}</Badge>
            </div>
          ))}
        </Panel>
        <Panel
          title="Research source / workspace draft"
          source="Workspace document"
          quality="DRAFT"
        >
          <textarea
            className="editor"
            aria-label="Strategy source"
            value={code}
            spellCheck={false}
            onChange={(e) => setCode(e.target.value)}
          />
          <div className="source-note">
            Custom Python execution is unavailable. Approved backtest templates
            run in separate worker processes.
          </div>
        </Panel>
      </div>
    </>
  );
}

export function ResearchPage() {
  const query = useApi<{ items: Row[] }>("research", "/api/v1/research");
  const { security, bootstrap } = useTerminal();
  const [id, setId] = useTabState<string | undefined>("research-id", undefined);
  const [title, setTitle] = useTabState(
    "research-title",
    `${security} / Investment thesis`,
  );
  const [body, setBody] = useTabState("research-body", "");
  const [status, setStatus] = useState("");
  const mutation = useMutation({
    mutationFn: () =>
      knkApi.post<{ id: string }>("/api/v1/research", {
        id,
        title,
        body,
        instrument_id: bootstrap.quotes.find((q) => q.symbol === security)?.id,
      }),
    onSuccess: (r) => {
      setId(r.id);
      setStatus("SAVED");
      query.refetch();
    },
  });
  return (
    <>
      <PageTitle code="RESEARCH" title="Research / Private Coverage">
        <Badge>{status || "PRIVATE DRAFT"}</Badge>
        <button
          onClick={() => {
            setId(undefined);
            setTitle(`${security} / Investment thesis`);
            setBody("");
            setStatus("");
          }}
        >
          <Plus size={12} />
          New note
        </button>
        <button
          className="primary-button"
          disabled={!title || mutation.isPending}
          onClick={() => mutation.mutate()}
        >
          <Save size={12} />
          Save note
        </button>
      </PageTitle>
      <div className="two-column">
        <Panel
          title="Coverage / notes"
          source="KnK private research records"
          asOf={query.data?.items[0]?.as_of as string}
          quality="PRIVATE"
        >
          {query.data?.items
            .filter((n) => n.visibility !== "PUBLIC")
            .map((note) => (
              <button
                key={String(note.id)}
                className="scenario-row"
                onClick={() => {
                  setId(String(note.id));
                  setTitle(String(note.title));
                  setBody(String(note.body));
                  setStatus("");
                }}
              >
                {String(note.title)}
              </button>
            ))}
        </Panel>
        <Panel
          title="Research document"
          source="User-authored research"
          quality="PRIVATE"
        >
          <div className="section-pad">
            <Field label="Title">
              <input
                aria-label="Research title"
                value={title}
                onChange={(e) => {
                  setTitle(e.target.value);
                  setStatus("");
                }}
              />
            </Field>
          </div>
          <textarea
            aria-label="Research document"
            className="editor document-editor"
            value={body}
            onChange={(e) => {
              setBody(e.target.value);
              setStatus("");
            }}
            placeholder="Thesis, variant perception, bull/base/bear cases, catalysts, risks, invalidation, sources..."
          />
          {mutation.error && (
            <p className="error-state" role="alert">
              {mutation.error.message}
            </p>
          )}
        </Panel>
      </div>
    </>
  );
}

export function PinePage() {
  const query = useApi<{
    source: string;
    compatibility: string;
    warnings?: string[];
  }>("pine", "/api/v1/pine/export");
  const [copied, setCopied] = useState(false);
  return (
    <>
      <PageTitle code="PINE" title="TradingView / Pine Script Studio">
        <Badge>{query.data?.compatibility ?? "CHECKING"}</Badge>
        <button
          disabled={!query.data}
          onClick={() => {
            navigator.clipboard
              .writeText(query.data!.source)
              .then(() => setCopied(true));
          }}
        >
          <Copy size={12} />
          {copied ? "Copied" : "Copy code"}
        </button>
        <button
          disabled={!query.data}
          onClick={() => download("knk-ma-crossover.pine", query.data!.source)}
        >
          <ArrowDownToLine size={12} />
          Download .pine
        </button>
      </PageTitle>
      <div className="two-column">
        <Panel
          title="Source / compatibility"
          source="KnK Pine generator"
          quality="CALCULATED"
        >
          <dl className="detail-list section-pad">
            <dt>Template</dt>
            <dd>Moving-average crossover</dd>
            <dt>Language</dt>
            <dd>Pine Script</dd>
            <dt>Compatibility</dt>
            <dd>{query.data?.compatibility}</dd>
            <dt>Deployment</dt>
            <dd>Manual TradingView import</dd>
            <dt>Broker actions</dt>
            <dd>Unavailable</dd>
          </dl>
          {query.data?.warnings?.map((w) => (
            <p className="warning-note section-pad" key={w}>
              {w}
            </p>
          ))}
        </Panel>
        <Panel
          title="Generated Pine source"
          source="Backend template generator"
          quality="CALCULATED"
          error={query.error}
          loading={query.isLoading}
        >
          <pre className="code-output">{query.data?.source}</pre>
        </Panel>
      </div>
    </>
  );
}

export function ExcelPage() {
  const [kind, setKind] = useTabState("report-kind", "portfolio");
  const macro = useApi<MacroDashboardPayload>(
    "report-macro",
    "/api/v1/macro/dashboard",
    kind === "macro",
  );
  const runs = useApi<{ items: Run[] }>(
    "report-backtests",
    "/api/v1/terminal/runs?kind=backtest",
    kind === "backtest",
  );
  const latestRun = runs.data?.items.find((r) => r.status === "SUCCEEDED");
  const [report, setReport] = useState<{
    download_url: string;
    status?: string;
    report_id?: string;
  } | null>(null);
  const mutation = useMutation({
    mutationFn: () =>
      knkApi.post<{
        download_url: string;
        status?: string;
        report_id?: string;
      }>(`/api/v1/terminal/reports/${kind}`),
    onSuccess: setReport,
  });
  const portfolio = usePortfolio();
  return (
    <>
      <PageTitle code="EXCEL" title="Excel Studio">
        <button
          className="primary-button"
          disabled={mutation.isPending}
          onClick={() => mutation.mutate()}
        >
          <Play size={12} />
          {mutation.isPending ? "Generating..." : "Generate workbook"}
        </button>
        {report && (
          <a
            href={knkApi.downloadUrl(report.download_url)}
            target="_blank"
            rel="noreferrer"
          >
            Download XLSX
          </a>
        )}
      </PageTitle>
      <div className="two-column">
        <Panel
          title="Report selection"
          source="KnK workbook templates"
          quality="CALCULATED"
        >
          <div className="modal-body">
            <Field label="Workbook type">
              <select
                aria-label="Workbook type"
                value={kind}
                onChange={(e) => {
                  setKind(e.target.value);
                  setReport(null);
                }}
              >
                {["portfolio", "risk", "macro", "backtest"].map((k) => (
                  <option key={k} value={k}>
                    {k}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Portfolio">
              <input value="KnK Reference / SGD" readOnly />
            </Field>
            <Badge>DEMO DATA</Badge>
            {report && <Badge>SUCCEEDED</Badge>}
            {mutation.error && (
              <p className="negative" role="alert">
                {mutation.error.message}
              </p>
            )}
          </div>
        </Panel>
        <Panel
          title="Workbook source preview"
          source={
            kind === "macro"
              ? "Per-series provenance"
              : kind === "backtest"
                ? latestRun?.result?.source
                : portfolio.data?.source
          }
          asOf={
            kind === "macro"
              ? macro.data?.items[0]?.ingestion_timestamp
              : kind === "backtest"
                ? latestRun?.result?.as_of
                : portfolio.data?.as_of
          }
          quality={
            kind === "backtest"
              ? latestRun?.result?.quality
              : portfolio.data?.quality
          }
        >
          <DataTable
            id="report-preview"
            rows={
              kind === "macro"
                ? records(macro.data?.items ?? [])
                : kind === "backtest"
                  ? records(latestRun?.result?.equity_curve ?? [])
                  : kind === "risk"
                    ? Object.entries(portfolio.data?.risk ?? {}).map(
                        ([metric, value]) => ({ metric, value }),
                      )
                    : records(portfolio.data?.positions ?? [])
            }
            columns={
              kind === "macro"
                ? [
                    { key: "series_id", label: "Series" },
                    { key: "latest_value", label: "Latest", numeric: true },
                    { key: "source", label: "Source" },
                    { key: "quality", label: "Quality" },
                  ]
                : kind === "backtest"
                  ? [
                      { key: "date", label: "Date" },
                      { key: "equity", label: "Equity", numeric: true },
                      { key: "benchmark", label: "Benchmark", numeric: true },
                      {
                        key: "drawdown",
                        label: "Drawdown",
                        numeric: true,
                        percent: true,
                      },
                    ]
                  : kind === "risk"
                    ? [
                        { key: "metric", label: "Metric", size: 200 },
                        { key: "value", label: "Value", size: 250 },
                      ]
                    : [
                        { key: "symbol", label: "Security", size: 110 },
                        { key: "quantity", label: "Quantity", numeric: true },
                        { key: "market_price", label: "Price", numeric: true },
                        {
                          key: "market_value",
                          label: "Value (SGD)",
                          numeric: true,
                        },
                        {
                          key: "weight",
                          label: "Weight",
                          numeric: true,
                          percent: true,
                        },
                      ]
            }
          />
        </Panel>
      </div>
    </>
  );
}
