"use client";

import { useMutation } from "@tanstack/react-query";
import { knkApi } from "@knk/api-client";
import { Download, Plus, Save } from "lucide-react";
import { PageTitle, useApi } from "./core-pages";
import { useTabState, useTerminal } from "./context";
import { Badge, Field, download, number, pct } from "./ui";
import type { Row } from "./types";

const fields = [
  "title",
  "one_sentence",
  "full_thesis",
  "variant_perception",
  "bull_case",
  "base_case",
  "bear_case",
  "catalysts",
  "risks",
  "invalidation",
  "monitoring_indicators",
  "holding_period",
  "exit_thesis",
  "post_mortem",
];
const fresh = (symbol: string): Record<string, string> => ({
  ...Object.fromEntries(fields.map((key) => [key, ""])),
  title: `${symbol} investment thesis`,
  bull_probability: "25",
  base_probability: "50",
  bear_probability: "25",
  fair_value_low: "",
  fair_value_high: "",
  target_weight: "0",
  maximum_weight: "10",
  confidence: "LOW",
  review_date: "",
  sources: "",
  attachment_ids: "",
  dcf_run_id: "",
  state: "DRAFT",
});

export function ThesisWorkspace() {
  const { security, bootstrap, open, selectSecurity } = useTerminal();
  const [form, setForm] = useTabState("structured-thesis", fresh(security));
  const [parent, setParent] = useTabState<string | null>("thesis-parent", null);
  const [saved, setSaved] = useTabState<Row | null>("saved-thesis", null);
  const theses = useApi<{ items: Row[] }>(
    "equity-theses",
    `/api/v1/equity/theses?symbol=${security}`,
  );
  const notes = useApi<{ items: Row[] }>("equity-notes", "/api/v1/research");
  const dcf = useApi<{ items: { id: string; name: string; result: Row }[] }>(
    "thesis-dcf",
    "/api/v1/terminal/runs?kind=dcf",
  );
  const files = useApi<{ items: Row[] }>(
    "thesis-files",
    "/api/v1/data-drop/files",
  );
  const portfolio = useApi<{ positions: Row[] }>(
    "thesis-position",
    "/api/v1/terminal/portfolio",
  );
  const quote = bootstrap.quotes.find((q) => q.symbol === security);
  const position = portfolio.data?.positions.find(
    (row) => row.symbol === security || row.instrument_id === quote?.id,
  );
  const set = (key: string, value: string) =>
    setForm({ ...form, [key]: value });
  const save = useMutation({
    mutationFn: () =>
      knkApi.post<Row>("/api/v1/equity/theses", {
        symbol: security,
        parent_id: parent,
        ...Object.fromEntries(fields.map((key) => [key, form[key]])),
        ...Object.fromEntries(
          [
            "bull_probability",
            "base_probability",
            "bear_probability",
            "target_weight",
            "maximum_weight",
          ].map((key) => [key, String(Number(form[key]) / 100)]),
        ),
        fair_value_low: form.fair_value_low || null,
        fair_value_high: form.fair_value_high || null,
        confidence: form.confidence,
        review_date: form.review_date || null,
        state: form.state,
        sources: form.sources
          .split("\n")
          .map((v) => v.trim())
          .filter(Boolean),
        attachment_ids: form.attachment_ids
          .split(",")
          .map((v) => v.trim())
          .filter(Boolean),
        dcf_run_id: form.dcf_run_id || null,
      }),
    onSuccess: (result) => {
      setSaved(result);
      setParent(String(result.id));
      theses.refetch();
    },
  });
  function load(row: Row) {
    const next = fresh(security);
    Object.keys(next).forEach((key) => {
      next[key] = row[key] == null ? "" : String(row[key]);
    });
    [
      "bull_probability",
      "base_probability",
      "bear_probability",
      "target_weight",
      "maximum_weight",
    ].forEach((key) => {
      next[key] = String(Number(row[key]) * 100);
    });
    next.sources = (row.sources as string[]).join("\n");
    next.attachment_ids = (row.attachment_ids as string[]).join(",");
    setForm(next);
    setParent(String(row.id));
    setSaved(row);
  }
  return (
    <div className="research-page thesis-workspace">
      <PageTitle
        code="THESIS"
        title={`${security} / Private Investment Thesis`}
      >
        <Badge>{saved ? `SAVED v${saved.version}` : "PRIVATE DRAFT"}</Badge>
        <button
          className="toolbar-button"
          onClick={() => {
            setForm(fresh(security));
            setParent(null);
            setSaved(null);
          }}
        >
          <Plus size={13} />
          New thesis
        </button>
        <button
          className="primary-button"
          disabled={save.isPending || !form.title || !form.one_sentence}
          onClick={() => save.mutate()}
        >
          <Save size={13} />
          {save.isPending ? "Saving..." : "Save version"}
        </button>
        {saved && (
          <button
            title="Download saved thesis JSON"
            className="toolbar-button"
            onClick={() =>
              download(
                `thesis-${saved.id}.json`,
                JSON.stringify(saved, null, 2),
                "application/json",
              )
            }
          >
            <Download size={14} />
          </button>
        )}
      </PageTitle>
      <div className="thesis-layout">
        <aside className="thesis-sidebar">
          <h3>Coverage</h3>
          <select
            aria-label="Thesis security"
            value={security}
            onChange={(e) => {
              selectSecurity(e.target.value);
              setForm(fresh(e.target.value));
              setParent(null);
              setSaved(null);
            }}
          >
            {bootstrap.quotes.map((q) => (
              <option key={q.symbol}>{q.symbol}</option>
            ))}
          </select>
          <h3>Thesis versions</h3>
          {theses.data?.items.map((row) => (
            <button
              key={String(row.id)}
              className="scenario-row"
              onClick={() => load(row)}
            >
              <span>{String(row.title)}</span>
              <span className="muted">
                v{String(row.version)} / {String(row.state)}
              </span>
            </button>
          ))}
          <h3>Research notes</h3>
          {notes.data?.items
            .filter((row) => row.instrument_id === quote?.id)
            .map((row) => (
              <button
                key={String(row.id)}
                className="scenario-row"
                onClick={() => open("/ideas", "Private notes")}
              >
                {String(row.title)}
              </button>
            ))}
          <button
            className="toolbar-button"
            onClick={() => open("/ideas", "Private notes")}
          >
            All notes
          </button>
        </aside>
        <main className="thesis-editor">
          <div className="performance-controls">
            <Field label="State">
              <select
                aria-label="Thesis state"
                value={form.state}
                onChange={(e) => set("state", e.target.value)}
              >
                {["DRAFT", "ACTIVE", "REVIEW", "EXITED", "ARCHIVED"].map(
                  (v) => (
                    <option key={v}>{v}</option>
                  ),
                )}
              </select>
            </Field>
            <Field label="Confidence">
              <select
                aria-label="Thesis confidence"
                value={form.confidence}
                onChange={(e) => set("confidence", e.target.value)}
              >
                {["LOW", "MEDIUM", "HIGH"].map((v) => (
                  <option key={v}>{v}</option>
                ))}
              </select>
            </Field>
            <Field label="Review date">
              <input
                aria-label="Thesis review date"
                type="date"
                value={form.review_date}
                onChange={(e) => set("review_date", e.target.value)}
              />
            </Field>
          </div>
          {fields.map((key) => (
            <Field key={key} label={key.replaceAll("_", " ")}>
              {["title", "one_sentence", "holding_period"].includes(key) ? (
                <input
                  aria-label={`Thesis ${key}`}
                  value={form[key]}
                  onChange={(e) => set(key, e.target.value)}
                />
              ) : (
                <textarea
                  aria-label={`Thesis ${key}`}
                  rows={key === "full_thesis" ? 9 : 3}
                  value={form[key]}
                  onChange={(e) => set(key, e.target.value)}
                />
              )}
            </Field>
          ))}
          <div className="performance-controls">
            {[
              "bull_probability",
              "base_probability",
              "bear_probability",
              "target_weight",
              "maximum_weight",
              "fair_value_low",
              "fair_value_high",
            ].map((key) => (
              <Field
                key={key}
                label={`${key.replaceAll("_", " ")}${key.includes("probability") || key.includes("weight") ? " %" : ""}`}
              >
                <input
                  type="number"
                  step="any"
                  aria-label={`Thesis ${key}`}
                  value={form[key]}
                  onChange={(e) => set(key, e.target.value)}
                />
              </Field>
            ))}
          </div>
          <Field label="Sources">
            <textarea
              aria-label="Thesis sources"
              rows={4}
              value={form.sources}
              onChange={(e) => set("sources", e.target.value)}
            />
          </Field>
          <Field label="Attachment file IDs">
            <input
              aria-label="Thesis attachment IDs"
              value={form.attachment_ids}
              onChange={(e) => set("attachment_ids", e.target.value)}
            />
          </Field>
          <Field label="Linked valuation">
            <select
              aria-label="Thesis linked DCF"
              value={form.dcf_run_id}
              onChange={(e) => set("dcf_run_id", e.target.value)}
            >
              <option value="">None</option>
              {dcf.data?.items
                .filter((row) => row.result.symbol === security)
                .map((row) => (
                  <option key={row.id} value={row.id}>
                    {row.name} / {row.id.slice(0, 8)}
                  </option>
                ))}
            </select>
          </Field>
          {save.error && (
            <p role="alert" className="negative">
              {String(save.error)}
            </p>
          )}
        </main>
        <aside className="thesis-sidebar">
          <h3>{security}</h3>
          <dl className="detail-list">
            <dt>Price</dt>
            <dd>
              {number(quote?.price)} {quote?.currency}
            </dd>
            <dt>Source</dt>
            <dd>{quote?.source}</dd>
            <dt>Quality</dt>
            <dd>{quote?.quality}</dd>
            <dt>Weight</dt>
            <dd>{pct(position?.weight)}</dd>
            <dt>Market value</dt>
            <dd>{number(position?.market_value)}</dd>
            <dt>Beta</dt>
            <dd>{number(position?.beta)}</dd>
          </dl>
          <h3>Security analysis</h3>
          {[
            ["FIN", "financials"],
            ["DCF", "dcf"],
            ["COMP", "comparables"],
          ].map(([code, path]) => (
            <button
              key={code}
              className="scenario-row"
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
            className="scenario-row"
            onClick={() => open("/factor-lab", "FACTORS")}
          >
            Factors
          </button>
          <button
            className="scenario-row"
            onClick={() => open("/risk", "RISK")}
          >
            Risk contribution
          </button>
          <button
            className="scenario-row"
            onClick={() => open("/trade-monitor", "TRADES")}
          >
            Trade history
          </button>
          <h3>Datasets</h3>
          {files.data?.items.slice(0, 8).map((row) => (
            <button
              key={String(row.id)}
              className="scenario-row"
              onClick={() => open("/data-catalogue", "DATA")}
            >
              {String(row.filename ?? row.original_filename ?? row.id)}
            </button>
          ))}
          {saved && (
            <p className="muted">
              Run {String(saved.id)}
              <br />
              SHA256 {String(saved.input_hash)}
            </p>
          )}
        </aside>
      </div>
    </div>
  );
}
