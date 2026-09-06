"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { knkApi } from "@knk/api-client";
import {
  ArrowDownToLine,
  Ban,
  Check,
  Database,
  ExternalLink,
  Plug,
  RefreshCw,
  Search,
} from "lucide-react";
import { useTerminal } from "./context";
import { PageTitle, useApi } from "./core-pages";
import { Badge, DataTable, Field, Panel, timestamp } from "./ui";
import type { Row } from "./types";

interface Connection extends Row {
  key: string | null;
  name: string;
  configured: boolean;
  enabled: boolean;
  connection_state: string;
  capabilities: string[];
  last_success: string | null;
  last_failure: string | null;
  last_data_sync: string | null;
  data_freshness: string;
  latency_ms: number | null;
  rate_limit: string;
  last_error: string | null;
}
interface MappingResult extends Row {
  dataset_version_id: string;
  items: Array<{
    request: Row;
    result: { data?: Row[]; error?: string; warning?: string };
  }>;
}

export function ConnectionsWorkspace({
  filingsOnly = false,
}: {
  filingsOnly?: boolean;
}) {
  const terminal = useTerminal();
  const [tab, setTab] = useState(filingsOnly ? "FILINGS" : "CONNECTIONS");
  const [provider, setProvider] = useState("sec");
  const [cik, setCik] = useState("0000320193");
  const [kind, setKind] = useState("submissions");
  const [symbol, setSymbol] = useState(terminal.security);
  const [start, setStart] = useState("2020-01-01");
  const [series, setSeries] = useState("FEDFUNDS,DGS2,DGS10");
  const [message, setMessage] = useState("");
  const [lastVersion, setLastVersion] = useState("");
  const [idType, setIdType] = useState("TICKER");
  const [idValue, setIdValue] = useState(terminal.security);
  const [exchange, setExchange] = useState("US");
  const [mapping, setMapping] = useState<MappingResult | null>(null);
  const [instrumentId, setInstrumentId] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const [pendingToggle, setPendingToggle] = useState<{
    key: string;
    value: boolean;
  } | null>(null);
  const connections = useApi<{ items: Connection[] }>(
    "connections",
    "/api/v1/connections",
  );
  const filings = useApi<{ items: Row[] }>(
    "sec-filings",
    "/api/v1/connections/sec/filings",
  );
  const instruments = useApi<{ items: Array<{ id: string; symbol: string }> }>(
    "connection-instruments",
    "/api/v1/instruments?limit=1000",
  );
  const action = useMutation({
    mutationFn: ({ path, body }: { path: string; body?: unknown }) =>
      knkApi.post<Row>(path, body),
    onSuccess: async (result) => {
      setMessage(
        String(
          result.error ??
            result.state ??
            result.connection_state ??
            result.status ??
            "RECORDED",
        ),
      );
      if (result.dataset_version_id)
        setLastVersion(String(result.dataset_version_id));
      await connections.refetch();
      setPendingToggle(null);
      filings.refetch();
    },
    onError: (error) => {
      setPendingToggle(null);
      setMessage(error.message);
    },
  });
  const map = useMutation({
    mutationFn: () =>
      knkApi.post<MappingResult>("/api/v1/connections/openfigi/mapping", {
        jobs: [
          { idType, idValue, ...(exchange ? { exchCode: exchange } : {}) },
        ],
      }),
    onSuccess: (result) => {
      setMapping(result.items ? result : null);
      setConfirmed(false);
      setMessage(String(result.error ?? result.state));
      connections.refetch();
    },
    onError: (error) => setMessage(error.message),
  });
  const selected = connections.data?.items.find((row) => row.key === provider);
  const busy = action.isPending || map.isPending;
  const run = (path: string, body?: unknown) => action.mutate({ path, body });
  const backfill = () => {
    if (provider === "sec")
      run("/api/v1/connections/sec/import", { cik, kind });
    else if (provider === "fred")
      run("/api/v1/macro/backfills", {
        series_ids: series
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean),
        observation_start: start,
      });
    else
      run(`/api/v1/connections/${provider}/backfill`, {
        symbol,
        start: start || null,
      });
  };
  const candidates =
    mapping?.items.flatMap((item, index) =>
      (item.result.data ?? []).map((row) => ({ ...row, job_index: index })),
    ) ?? [];
  return (
    <div className="research-page connections-workspace">
      <PageTitle
        code={filingsOnly ? "FILINGS" : "CONN"}
        title={
          filingsOnly
            ? "SEC Filings / Internal Archive"
            : "Connections / Data Sources"
        }
      >
        <button
          title="Refresh connection records"
          aria-label="Refresh connection records"
          onClick={() => connections.refetch()}
        >
          <RefreshCw size={13} />
        </button>
      </PageTitle>
      <div
        className="research-tabs"
        role="tablist"
        aria-label="Connection views"
      >
        {["CONNECTIONS", "FILINGS", "IDENTIFIERS"].map((name) => (
          <button
            key={name}
            role="tab"
            aria-selected={tab === name}
            onClick={() => setTab(name)}
          >
            {name}
          </button>
        ))}
      </div>
      {message && (
        <p role="status" className="warning-note">
          {message}
        </p>
      )}
      {connections.error && <p role="alert">{connections.error.message}</p>}
      {tab === "CONNECTIONS" && (
        <>
          <div className="connection-grid">
            {(connections.data?.items ?? []).map((row) => (
              <article
                className="connection-item"
                key={row.name}
                aria-label={row.name + " connection"}
              >
                <header>
                  <h2>{row.name}</h2>
                  <Badge>{row.connection_state}</Badge>
                </header>
                <dl>
                  <div>
                    <dt>Configured</dt>
                    <dd>{row.configured ? "YES" : "NO"}</dd>
                  </div>
                  <div>
                    <dt>Latency</dt>
                    <dd>
                      {row.latency_ms == null ? "--" : `${row.latency_ms} ms`}
                    </dd>
                  </div>
                  <div>
                    <dt>Last success</dt>
                    <dd>{timestamp(row.last_success ?? "")}</dd>
                  </div>
                  <div>
                    <dt>Last failure</dt>
                    <dd>{timestamp(row.last_failure ?? "")}</dd>
                  </div>
                  <div>
                    <dt>Last sync</dt>
                    <dd>{timestamp(row.last_data_sync ?? "")}</dd>
                  </div>
                  <div>
                    <dt>Freshness</dt>
                    <dd>{row.data_freshness}</dd>
                  </div>
                  <div>
                    <dt>Rate limit</dt>
                    <dd>{row.rate_limit}</dd>
                  </div>
                </dl>
                <p className="source-note">{row.capabilities.join(" / ")}</p>
                {row.last_error && (
                  <p className="warning-note">{row.last_error}</p>
                )}
                {row.key && (
                  <footer>
                    <label className="connection-toggle">
                      <input
                        aria-label={`Enable ${row.name}`}
                        type="checkbox"
                        checked={
                          pendingToggle?.key === row.key
                            ? pendingToggle.value
                            : row.enabled
                        }
                        disabled={busy || (!row.configured && !row.enabled)}
                        onChange={(event) => {
                          setPendingToggle({
                            key: row.key!,
                            value: event.target.checked,
                          });
                          run(`/api/v1/connections/${row.key}/control`, {
                            action: event.target.checked ? "ENABLE" : "DISABLE",
                          });
                        }}
                      />{" "}
                      Enabled
                    </label>
                    <button
                      aria-label={`Test ${row.name} connection`}
                      title={`Test ${row.name} connection`}
                      disabled={busy || !row.enabled || !row.configured}
                      onClick={() => run(`/api/v1/connections/${row.key}/test`)}
                    >
                      <Plug size={13} />
                    </button>
                    <button
                      aria-label={`Revoke ${row.name} local access`}
                      title="Revoke local access; vendor key is not deleted"
                      disabled={busy || !row.enabled}
                      onClick={() =>
                        run(`/api/v1/connections/${row.key}/control`, {
                          action: "REVOKE",
                        })
                      }
                    >
                      <Ban size={13} />
                    </button>
                  </footer>
                )}
              </article>
            ))}
          </div>
          <Panel
            title="Provider backfill / Import"
            source="Explicit read-only request"
            quality="PROVIDER DATA"
          >
            <div className="research-controls">
              <Field label="Provider">
                <select
                  aria-label="Backfill provider"
                  value={provider}
                  onChange={(e) => setProvider(e.target.value)}
                >
                  <option value="sec">SEC EDGAR</option>
                  <option value="fred">FRED</option>
                  <option value="market">Market provider</option>
                  <option value="options">Options provider</option>
                </select>
              </Field>
              {provider === "sec" ? (
                <>
                  <Field label="CIK">
                    <input
                      aria-label="SEC CIK"
                      value={cik}
                      onChange={(e) => setCik(e.target.value)}
                    />
                  </Field>
                  <Field label="SEC dataset">
                    <select
                      aria-label="SEC dataset"
                      value={kind}
                      onChange={(e) => setKind(e.target.value)}
                    >
                      <option value="submissions">Recent filings</option>
                      <option value="company_facts">Company XBRL facts</option>
                    </select>
                  </Field>
                </>
              ) : (
                <>
                  <Field label={provider === "fred" ? "Series IDs" : "Symbol"}>
                    <input
                      aria-label={
                        provider === "fred"
                          ? "FRED series IDs"
                          : "Backfill symbol"
                      }
                      value={provider === "fred" ? series : symbol}
                      onChange={(e) =>
                        provider === "fred"
                          ? setSeries(e.target.value)
                          : setSymbol(e.target.value)
                      }
                    />
                  </Field>
                  <Field label="Start">
                    <input
                      aria-label="Backfill start"
                      type="date"
                      value={start}
                      onChange={(e) => setStart(e.target.value)}
                    />
                  </Field>
                </>
              )}
              <button
                disabled={busy || !selected?.configured || !selected.enabled}
                onClick={backfill}
              >
                <ArrowDownToLine size={13} /> Run Backfill
              </button>
              {lastVersion && (
                <span className="mono">Version {lastVersion}</span>
              )}
            </div>
          </Panel>
        </>
      )}
      {tab === "FILINGS" && (
        <Panel
          className="page-grid"
          title="Filing documents"
          source="SEC EDGAR / Saved dataset versions"
          quality={filings.data?.items.length ? "PROVIDER DATA" : "UNAVAILABLE"}
          error={filings.error}
          loading={filings.isLoading}
          onRefresh={() => filings.refetch()}
        >
          <DataTable
            id="sec-filings"
            rows={filings.data?.items ?? []}
            columns={[
              { key: "cik", label: "CIK", size: 110 },
              { key: "form", label: "Form", size: 90 },
              { key: "filing_date", label: "Filed", size: 110 },
              { key: "accession", label: "Accession", size: 200 },
              {
                key: "document",
                label: "Document",
                size: 240,
                format: (value, row) => (
                  <a
                    href={String(row.url)}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    {String(value)} <ExternalLink size={10} />
                  </a>
                ),
              },
              { key: "dataset_version_id", label: "Version", size: 270 },
              {
                key: "ingested_at",
                label: "Ingested",
                size: 180,
                format: (value) => timestamp(String(value)),
              },
            ]}
          />
        </Panel>
      )}
      {tab === "IDENTIFIERS" && (
        <>
          <div className="research-controls">
            <Field label="Identifier type">
              <select
                aria-label="Identifier type"
                value={idType}
                onChange={(e) => setIdType(e.target.value)}
              >
                {["TICKER", "ID_ISIN", "ID_CUSIP", "ID_BB_GLOBAL"].map(
                  (value) => (
                    <option key={value}>{value}</option>
                  ),
                )}
              </select>
            </Field>
            <Field label="Identifier">
              <input
                aria-label="Identifier value"
                value={idValue}
                onChange={(e) => setIdValue(e.target.value)}
              />
            </Field>
            <Field label="Exchange code">
              <input
                aria-label="Mapping exchange"
                value={exchange}
                onChange={(e) => setExchange(e.target.value)}
              />
            </Field>
            <button
              disabled={
                busy ||
                !connections.data?.items.find((row) => row.key === "openfigi")
                  ?.enabled
              }
              onClick={() => map.mutate()}
            >
              <Search size={13} /> Lookup FIGI
            </button>
            <Field label="Internal security">
              <select
                aria-label="Mapping internal security"
                value={instrumentId}
                onChange={(e) => {
                  setInstrumentId(e.target.value);
                  setConfirmed(false);
                }}
              >
                <option value="">Select security</option>
                {instruments.data?.items.map((row) => (
                  <option key={row.id} value={row.id}>
                    {row.symbol}
                  </option>
                ))}
              </select>
            </Field>
            <label className="connection-toggle">
              <input
                type="checkbox"
                aria-label="Confirm reviewed mapping"
                checked={confirmed}
                onChange={(e) => setConfirmed(e.target.checked)}
              />{" "}
              Reviewed mapping
            </label>
          </div>
          {mapping?.items.map((item, index) =>
            item.result.error || item.result.warning ? (
              <p key={index} className="warning-note">
                {item.result.error ?? item.result.warning}
              </p>
            ) : null,
          )}
          <Panel
            className="page-grid"
            title="Mapping candidates / Explicit approval"
            source="OpenFIGI"
            quality={mapping ? "REVIEW REQUIRED" : "UNAVAILABLE"}
          >
            <DataTable
              id="figi-candidates"
              rows={candidates}
              columns={[
                { key: "figi", label: "FIGI", size: 170 },
                { key: "ticker", label: "Ticker", size: 100 },
                { key: "name", label: "Name", size: 220 },
                { key: "exchCode", label: "Exchange", size: 100 },
                { key: "securityType", label: "Security type", size: 150 },
                {
                  key: "approve",
                  label: "Review",
                  size: 90,
                  format: (_, row) => (
                    <button
                      title="Approve this FIGI mapping"
                      aria-label={`Approve ${row.figi}`}
                      disabled={!confirmed || !instrumentId || busy}
                      onClick={() =>
                        run("/api/v1/connections/openfigi/accept", {
                          dataset_version_id: mapping?.dataset_version_id,
                          job_index: row.job_index,
                          figi: row.figi,
                          instrument_id: instrumentId,
                          confirm: true,
                        })
                      }
                    >
                      <Check size={13} />
                    </button>
                  ),
                },
              ]}
            />
          </Panel>
        </>
      )}
      <div className="research-controls">
        <button onClick={() => terminal.open("/data-drop", "DATA DROP")}>
          <Database size={13} /> Data Drop
        </button>
        <button onClick={() => terminal.open("/system-health", "HEALTH")}>
          <Plug size={13} /> System Health
        </button>
      </div>
    </div>
  );
}
