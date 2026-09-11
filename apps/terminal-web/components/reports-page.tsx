"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { knkApi } from "@knk/api-client";
import { Download, Play, RefreshCw } from "lucide-react";
import { PageTitle, useApi } from "./core-pages";
import { usePortfolio, useTabState } from "./context";
import { Badge, Field, Panel, timestamp } from "./ui";

interface ReportJob {
  id: string;
  kind: string;
  format: string;
  status: string;
  progress: number;
  source: string;
  quality: string;
  as_of: string | null;
  created_at: string;
  content_hash: string | null;
  snapshot_hash: string;
  error_message: string | null;
  download_url: string | null;
  source_url: string;
}

export function ReportsWorkspace({ deck = false }: { deck?: boolean }) {
  const [kind, setKind] = useTabState("private-report-kind", "portfolio");
  const [format, setFormat] = useTabState(
    "private-report-format",
    deck ? "pptx" : "xlsx",
  );
  const [runId, setRunId] = useTabState("private-report-run", "");
  const [symbol, setSymbol] = useTabState("private-report-symbol", "AAPL");
  const [asOf, setAsOf] = useTabState("private-report-date", "");
  const portfolio = usePortfolio();
  const templates = useApi<{ items: { kind: string; formats: string[] }[] }>(
    "report-templates",
    "/api/v1/report-jobs/templates",
  );
  const jobs = useQuery({
    queryKey: ["private-report-jobs"],
    queryFn: () => knkApi.get<{ items: ReportJob[] }>("/api/v1/report-jobs"),
    refetchInterval: 3000,
  });
  const runs = useApi<{
    items: { id: string; kind: string; name: string; status: string }[];
  }>("report-source-runs", "/api/v1/terminal/runs");
  const [selectedId, setSelectedId] = useTabState<string | null>(
    "private-report-selected",
    null,
  );
  const selected =
    jobs.data?.items.find((job) => job.id === selectedId) ??
    jobs.data?.items[0];
  const formats =
    templates.data?.items.find((item) => item.kind === kind)?.formats ?? [];
  const needsRun = !["portfolio", "risk", "macro", "equity"].includes(kind);
  const create = useMutation({
    mutationFn: () =>
      knkApi.post<ReportJob>("/api/v1/report-jobs", {
        kind,
        format,
        symbol,
        portfolio: portfolio.data?.portfolio.id ?? "KNK_MAIN",
        analysis_run_id: needsRun ? runId || null : null,
        as_of: ["portfolio", "risk"].includes(kind) ? asOf || null : null,
      }),
    onSuccess: (job) => {
      setSelectedId(job.id);
      void jobs.refetch();
    },
  });
  return (
    <>
      <PageTitle
        code={deck ? "DECK" : "EXCEL"}
        title={deck ? "Deck Builder" : "Excel Studio"}
      >
        <button
          title="Refresh report jobs"
          aria-label="Refresh report jobs"
          onClick={() => void jobs.refetch()}
        >
          <RefreshCw size={13} />
        </button>
        <button
          className="primary-button"
          disabled={
            create.isPending ||
            !formats.includes(format) ||
            (needsRun && !runId)
          }
          onClick={() => create.mutate()}
        >
          <Play size={12} />
          Generate {format === "xlsx" ? "workbook" : format.toUpperCase()}
        </button>
      </PageTitle>
      <div className="two-column report-workspace">
        <Panel
          title="Report selection"
          source="KnK private reports"
          quality={portfolio.data?.quality}
        >
          <div className="modal-body">
            <Field label="Report type">
              <select
                aria-label="Report type"
                value={kind}
                onChange={(event) => {
                  const next = event.target.value;
                  setKind(next);
                  setRunId("");
                  const available =
                    templates.data?.items.find((item) => item.kind === next)
                      ?.formats ?? [];
                  if (!available.includes(format))
                    setFormat(available[0] ?? "xlsx");
                }}
              >
                {templates.data?.items.map((item) => (
                  <option key={item.kind} value={item.kind}>
                    {item.kind}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Format">
              <select
                aria-label="Report format"
                value={format}
                onChange={(event) => setFormat(event.target.value)}
              >
                {formats.map((value) => (
                  <option key={value} value={value}>
                    {value.toUpperCase()}
                  </option>
                ))}
              </select>
            </Field>
            {["portfolio", "risk"].includes(kind) && (
              <>
                <Field label="Portfolio">
                  <input
                    readOnly
                    value={portfolio.data?.portfolio.name ?? "KNK_MAIN"}
                  />
                </Field>
                <Field label="Valuation date">
                  <input
                    aria-label="Report valuation date"
                    type="date"
                    value={asOf}
                    onChange={(event) => setAsOf(event.target.value)}
                  />
                </Field>
              </>
            )}
            {kind === "equity" && (
              <Field label="Security">
                <input
                  aria-label="Report security"
                  value={symbol}
                  onChange={(event) =>
                    setSymbol(event.target.value.toUpperCase())
                  }
                />
              </Field>
            )}
            {needsRun && (
              <Field label="Saved analysis">
                <select
                  aria-label="Report analysis"
                  value={runId}
                  onChange={(event) => setRunId(event.target.value)}
                >
                  <option value="">Select completed analysis</option>
                  {runs.data?.items
                    .filter(
                      (run) =>
                        run.status === "SUCCEEDED" &&
                        (kind === "quant"
                          ? [
                              "backtest",
                              "alpha",
                              "factor",
                              "model",
                              "montecarlo",
                            ].includes(run.kind)
                          : run.kind ===
                            (kind === "comps" ? "comparables" : kind)),
                    )
                    .map((run) => (
                      <option key={run.id} value={run.id}>
                        {run.name} | {run.id.slice(0, 8)}
                      </option>
                    ))}
                </select>
              </Field>
            )}
            {(create.error || templates.error) && (
              <p className="negative" role="alert">
                {create.error?.message ?? templates.error?.message}
              </p>
            )}
          </div>
        </Panel>
        <Panel
          title="Report details"
          source={selected?.source}
          quality={selected?.quality}
          asOf={selected?.as_of}
          loading={jobs.isLoading}
          error={jobs.error}
        >
          {selected && (
            <div className="modal-body report-details">
              <Badge>{selected.status}</Badge>
              <progress
                aria-label="Report progress"
                max={1}
                value={selected.progress}
              />
              <dl>
                <dt>Report ID</dt>
                <dd>{selected.id}</dd>
                <dt>Requested</dt>
                <dd>{timestamp(selected.created_at)}</dd>
                <dt>Source hash</dt>
                <dd>{selected.snapshot_hash}</dd>
                <dt>File hash</dt>
                <dd>{selected.content_hash ?? "Pending"}</dd>
              </dl>
              {selected.error_message && (
                <p className="negative" role="alert">
                  {selected.error_message}
                </p>
              )}
              <div className="toolbar">
                {selected.download_url && (
                  <a href={knkApi.downloadUrl(selected.download_url)}>
                    <Download size={12} /> Download{" "}
                    {selected.format.toUpperCase()}
                  </a>
                )}
                <a href={knkApi.downloadUrl(selected.source_url)}>
                  <Download size={12} /> Source snapshot
                </a>
              </div>
            </div>
          )}
        </Panel>
      </div>
      <Panel
        title="Report history"
        source="Owned report jobs"
        quality="AUDITED"
        loading={jobs.isLoading}
        error={jobs.error}
      >
        <div className="report-history">
          {jobs.data?.items.map((job) => (
            <button
              key={job.id}
              onClick={() => setSelectedId(job.id)}
              aria-pressed={selected?.id === job.id}
            >
              <span>
                {job.kind.toUpperCase()} / {job.format.toUpperCase()}
              </span>
              <Badge>{job.status}</Badge>
              <span>{timestamp(job.created_at)}</span>
              <span>{job.quality}</span>
            </button>
          ))}
        </div>
      </Panel>
    </>
  );
}
