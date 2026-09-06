"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { knkApi } from "@knk/api-client";
import { Copy, Download, Play } from "lucide-react";
import { PageTitle, useApi } from "./core-pages";
import { useTabState } from "./context";
import { Badge, DataTable, Field, Kpis, Panel, download, pct } from "./ui";
import type { Row } from "./types";

interface Template {
  id: string;
  pine_source: string;
  source_hash: string;
  compilation: string;
  warnings: string[];
}
interface Comparison {
  id: string;
  state: string;
  compared: number;
  warmup_excluded: number;
  missing_signals: number;
  match_rate: number;
  mismatch_count: number;
  items: Row[];
  warnings: string[];
}
const defaults = {
  strategy: "SMA",
  fast: 20,
  slow: 50,
  direction: "LONG_ONLY",
  commission_pct: 0.05,
  slippage_ticks: 1,
  allocation_pct: 95,
  start: "2020-01-01",
  end: "2030-01-01",
  session: "0000-0000",
  stop_pct: 0,
  profit_pct: 0,
  trailing_ticks: 0,
  activation_ticks: 1,
};

export function PineWorkspace() {
  const [form, setForm] = useTabState("pine-settings", defaults);
  const [template, setTemplate] = useTabState<Template | null>(
    "pine-template",
    null,
  );
  const [comparison, setComparison] = useTabState<Comparison | null>(
    "pine-comparison",
    null,
  );
  const [copied, setCopied] = useState(false);
  const [copyError, setCopyError] = useState("");
  const history = useApi<{
    items: {
      id: string;
      name: string;
      parameters: typeof defaults;
      result: Template;
    }[];
  }>("pine-history", "/api/v1/terminal/runs?kind=pine");
  const create = useMutation({
    mutationFn: () => knkApi.post<Template>("/api/v1/pine/generate", form),
    onSuccess: (value) => {
      setTemplate(value);
      setComparison(null);
      setCopied(false);
      void history.refetch();
    },
  });
  const compare = useMutation({
    mutationFn: async (file: File) => {
      const data = new FormData();
      data.append("file", file);
      const response = await fetch(
        `/backend/api/v1/pine/${template!.id}/compare`,
        { method: "POST", body: data },
      );
      const result = await response.json();
      if (!response.ok)
        throw new Error(
          typeof result.detail === "string"
            ? result.detail
            : "Comparison failed",
        );
      return result as Comparison;
    },
    onSuccess: setComparison,
  });
  return (
    <>
      <PageTitle code="PINE" title="TradingView research">
        <Badge>{template?.compilation ?? "NOT GENERATED"}</Badge>
        <button
          title="Generate and save Pine template"
          disabled={create.isPending}
          onClick={() => create.mutate()}
        >
          <Play size={12} /> Generate
        </button>
        <button
          title={copied ? "Copied" : "Copy Pine source"}
          aria-label="Copy Pine source"
          disabled={!template}
          onClick={() => {
            navigator.clipboard
              .writeText(template!.pine_source)
              .then(() => {
                setCopied(true);
                setCopyError("");
              })
              .catch(() =>
                setCopyError(
                  "Clipboard unavailable. Download the source instead.",
                ),
              );
          }}
        >
          <Copy size={12} />
        </button>
        <button
          title="Download Pine source"
          aria-label="Download Pine source"
          disabled={!template}
          onClick={() =>
            download(`knk-${template!.id}.pine`, template!.pine_source)
          }
        >
          <Download size={12} />
        </button>
      </PageTitle>
      <div className="pine-layout">
        <Panel
          title="Template parameters"
          source="KnK Pine v6"
          quality="RESEARCH TEMPLATE"
        >
          <div className="section-pad pine-controls">
            <Field label="Strategy">
              <select
                value={form.strategy}
                onChange={(e) => setForm({ ...form, strategy: e.target.value })}
              >
                {["SMA", "RSI", "MACD", "BREAKOUT"].map((v) => (
                  <option key={v}>{v}</option>
                ))}
              </select>
            </Field>
            <Field label="Direction">
              <select
                value={form.direction}
                onChange={(e) =>
                  setForm({ ...form, direction: e.target.value })
                }
              >
                <option value="LONG_ONLY">Long only</option>
                <option value="LONG_SHORT">Long / short</option>
              </select>
            </Field>
            {(
              [
                ["fast", "Fast window"],
                ["slow", "Slow window"],
                ["commission_pct", "Commission %"],
                ["slippage_ticks", "Slippage ticks"],
                ["allocation_pct", "Allocation %"],
                ["stop_pct", "Fixed stop %"],
                ["profit_pct", "Profit target %"],
                ["trailing_ticks", "Trailing ticks"],
                ["activation_ticks", "Activation ticks"],
              ] as const
            ).map(([key, label]) => (
              <Field key={key} label={label}>
                <input
                  type="number"
                  step={key.endsWith("pct") ? "0.01" : "1"}
                  min="0"
                  value={form[key]}
                  onChange={(e) =>
                    setForm({ ...form, [key]: Number(e.target.value) })
                  }
                />
              </Field>
            ))}
            <Field label="Start UTC">
              <input
                type="date"
                value={form.start}
                onChange={(e) => setForm({ ...form, start: e.target.value })}
              />
            </Field>
            <Field label="End UTC (exclusive)">
              <input
                type="date"
                value={form.end}
                onChange={(e) => setForm({ ...form, end: e.target.value })}
              />
            </Field>
            <Field label="Exchange session">
              <input
                value={form.session}
                onChange={(e) => setForm({ ...form, session: e.target.value })}
              />
            </Field>
            <Field label="Saved template">
              <select
                value={template?.id ?? ""}
                onChange={(e) => {
                  const run = history.data?.items.find(
                    (r) => r.id === e.target.value,
                  );
                  if (run) {
                    setTemplate({ ...run.result, id: run.id });
                    setForm(run.parameters);
                    setComparison(null);
                  }
                }}
              >
                <option value="">Select run</option>
                {history.data?.items.map((run) => (
                  <option key={run.id} value={run.id}>
                    {run.name} / {run.id.slice(0, 8)}
                  </option>
                ))}
              </select>
            </Field>
          </div>
        </Panel>
        <Panel
          title="Saved Pine source"
          source={template?.source_hash.slice(0, 16) ?? "UNAVAILABLE"}
          quality={template?.compilation ?? "NOT GENERATED"}
          error={create.error ?? (copyError ? new Error(copyError) : null)}
          loading={create.isPending}
        >
          <pre className="code-output pine-source">{template?.pine_source}</pre>
        </Panel>
      </div>
      {template?.warnings.map((warning) => (
        <p key={warning} className="warning-note section-pad">
          {warning}
        </p>
      ))}
      <Panel
        title="Observed signal comparison"
        source="TradingView CSV / KnK indicator engine"
        quality={comparison?.state ?? "NOT COMPARED"}
        error={compare.error}
        loading={compare.isPending}
      >
        <div className="section-pad">
          <Field label="TradingView chart export">
            <input
              aria-label="TradingView chart export"
              type="file"
              accept=".csv"
              disabled={!template || compare.isPending}
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) compare.mutate(file);
                e.target.value = "";
              }}
            />
          </Field>
        </div>
        {comparison && (
          <>
            <Kpis
              items={[
                { label: "Compared bars", value: String(comparison.compared) },
                { label: "Match rate", value: pct(comparison.match_rate) },
                {
                  label: "Mismatches",
                  value: String(comparison.mismatch_count),
                },
                {
                  label: "Missing signals",
                  value: String(comparison.missing_signals),
                },
                {
                  label: "Warm-up excluded",
                  value: String(comparison.warmup_excluded),
                },
              ]}
            />
            <DataTable
              id="pine-comparison"
              rows={comparison.items}
              columns={[
                { key: "time", label: "Timestamp", size: 200 },
                { key: "close", label: "Close", numeric: true },
                { key: "knk", label: "KnK", numeric: true },
                { key: "tradingview", label: "TradingView", numeric: true },
                {
                  key: "match",
                  label: "Match",
                  format: (v) => (v ? "MATCH" : "MISMATCH"),
                },
              ]}
            />
            {comparison.warnings.map((warning) => (
              <p key={warning} className="warning-note section-pad">
                {warning}
              </p>
            ))}
          </>
        )}
      </Panel>
    </>
  );
}
