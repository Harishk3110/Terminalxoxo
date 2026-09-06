"use client";
import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { knkApi } from "@knk/api-client";
import { Check, RotateCcw } from "lucide-react";
import { useTerminal } from "./context";
import { PageTitle, useApi } from "./core-pages";
import { Badge, DataTable, Field, Panel, timestamp } from "./ui";
import type { Row } from "./types";

export function SourcePreferencesPage() {
  const { bootstrap } = useTerminal();
  const [symbol, setSymbol] = useState("AAPL");
  const query = useApi<{
    selected: Row;
    sources: Row[];
    rule: {
      priority: string[];
      preferred_source: string | null;
      stale_after_hours: number;
      reason: string;
    };
  }>("source-preferences", "/api/v1/operations/sources/" + symbol);
  const [preferred, setPreferred] = useState("");
  const [hours, setHours] = useState(72);
  const [reason, setReason] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const client = useQueryClient();
  const save = useMutation({
    mutationFn: () =>
      knkApi.post("/api/v1/operations/sources/" + symbol, {
        priority: query.data?.rule.priority ?? [
          "BROKER",
          "PROVIDER",
          "FILE",
          "DEMO",
        ],
        preferred_source: preferred || null,
        stale_after_hours: hours,
        reason,
      }),
    onSuccess: () => {
      query.refetch();
      client.invalidateQueries({ queryKey: ["terminal-portfolio"] });
    },
  });
  const reset = useMutation({
    mutationFn: () =>
      knkApi.post("/api/v1/operations/reset-demo", { confirmation }),
    onSuccess: () => {
      setConfirmation("");
      client.invalidateQueries({ queryKey: ["terminal-portfolio"] });
      client.invalidateQueries({ queryKey: ["operating-trades"] });
    },
  });
  return (
    <>
      <PageTitle code="SOURCE" title="Price Sources & Portfolio Controls">
        <Badge>ADMINISTRATIVE</Badge>
        <select
          aria-label="Source security"
          value={symbol}
          onChange={(e) => {
            setSymbol(e.target.value);
            setPreferred("");
          }}
        >
          {bootstrap.quotes.map((q) => (
            <option key={q.symbol}>{q.symbol}</option>
          ))}
        </select>
      </PageTitle>
      <div className="page-grid operation-two-column">
        <Panel
          title="Available price observations"
          source={String(query.data?.selected.source ?? "UNAVAILABLE")}
          quality={String(query.data?.selected.data_state ?? "UNAVAILABLE")}
          asOf={query.data?.selected.as_of as string}
          loading={query.isLoading}
          error={query.error}
        >
          <DataTable
            id="source-observations"
            rows={query.data?.sources ?? []}
            columns={[
              { key: "source", label: "Source", size: 200 },
              { key: "value", label: "Price", numeric: true },
              { key: "currency", label: "CCY", size: 60 },
              { key: "data_state", label: "State", size: 115 },
              {
                key: "as_of",
                label: "As of",
                size: 170,
                format: (v) => timestamp(String(v)),
              },
              { key: "source_file", label: "File", size: 200 },
              { key: "dataset_version_id", label: "Version", size: 240 },
            ]}
          />
        </Panel>
        <Panel
          title="Audited source preference"
          source="SOURCE PRECEDENCE RULE"
        >
          <div className="operation-form">
            <div className="secondary">
              Current preference:{" "}
              {query.data?.rule.preferred_source ?? "Automatic"} /{" "}
              {query.data?.rule.stale_after_hours ?? 72}h
            </div>
            <Field label="Preferred source">
              <select
                value={preferred}
                onChange={(e) => setPreferred(e.target.value)}
              >
                <option value="">Automatic precedence</option>
                {Array.from(
                  new Set(
                    query.data?.sources.map((s) => String(s.source)) ?? [],
                  ),
                ).map((s) => (
                  <option key={s}>{s}</option>
                ))}
              </select>
            </Field>
            <Field label="Stale after / hours">
              <input
                type="number"
                min={1}
                max={8760}
                value={hours}
                onChange={(e) => setHours(Number(e.target.value))}
              />
            </Field>
            <Field label="Override reason">
              <textarea
                value={reason}
                rows={3}
                onChange={(e) => setReason(e.target.value)}
              />
            </Field>
            <button
              disabled={reason.length < 5 || save.isPending}
              onClick={() => save.mutate()}
            >
              <Check size={13} /> Apply preference
            </button>
            {save.error && (
              <div role="alert" className="negative">
                {save.error.message}
              </div>
            )}
            {save.isSuccess && <Badge>RECORDED</Badge>}
            <hr />
            <Field label="Archive current demo and reset / confirmation">
              <input
                aria-label="Reset demo confirmation"
                placeholder="RESET KNK_MAIN DEMO"
                value={confirmation}
                onChange={(e) => setConfirmation(e.target.value)}
              />
            </Field>
            <button
              disabled={
                confirmation !== "RESET KNK_MAIN DEMO" || reset.isPending
              }
              onClick={() => reset.mutate()}
            >
              <RotateCcw size={13} /> Reset demo portfolio
            </button>
            {reset.error && (
              <div role="alert" className="negative">
                {reset.error.message}
              </div>
            )}
            {reset.isSuccess && <Badge>DEMO RESET / HISTORY ARCHIVED</Badge>}
          </div>
        </Panel>
      </div>
    </>
  );
}
