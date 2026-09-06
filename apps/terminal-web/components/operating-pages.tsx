"use client";
import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { knkApi } from "@knk/api-client";
import {
  ArrowDownToLine,
  Check,
  Plus,
  RefreshCw,
  Upload,
  X,
} from "lucide-react";
import { records, usePortfolio, useTerminal } from "./context";
import { PageTitle, useApi } from "./core-pages";
import {
  Badge,
  COLORS,
  DataTable,
  Empty,
  Field,
  IconButton,
  LineChart,
  Panel,
  money,
  number,
  pct,
  timestamp,
  tone,
  type Column,
} from "./ui";
import type { PortfolioData, Row } from "./types";

type OperatingData = PortfolioData & {
  portfolio: PortfolioData["portfolio"] & Row;
  exposures: Record<string, Row[]>;
  attribution: Row[];
  breaches: Row[];
  reconciliation: Row;
  freshness: Row;
  calculated_at: string;
  broker_state: string;
};
interface FileRecord extends Row {
  id: string;
  filename: string;
  state: string;
  hash: string;
  source: string;
  profile_id: string | null;
  dataset_version_id: string | null;
  metadata: {
    columns?: string[];
    preview?: Row[];
    normalized_preview?: Row[];
    row_count?: number;
    mapping_profile?: string;
    dataset_id?: string;
  };
  mapping: Record<string, string>;
  validation: { errors?: string[]; warnings?: string[]; import_error?: string };
  history: Row[];
}
interface Profile {
  id: string;
  code: string;
  version: number;
  dataset_type: string;
  rules: { aliases: Record<string, string[]>; required: string[] };
}
const holdingColumns: Column[] = [
  { key: "symbol", label: "Security", size: 78 },
  { key: "quantity", label: "Qty", numeric: true, size: 72 },
  { key: "market_price", label: "Price", numeric: true, size: 84 },
  {
    key: "market_value",
    label: "Value / SGD",
    money: true,
    numeric: true,
    size: 110,
  },
  { key: "weight", label: "Weight", percent: true, numeric: true, size: 77 },
  { key: "daily_pnl", label: "Day P&L", money: true, numeric: true, size: 100 },
  {
    key: "unrealised_pnl",
    label: "Unrealised",
    money: true,
    numeric: true,
    size: 100,
  },
  { key: "quality", label: "Price state", size: 130 },
];
const tradeColumns: Column[] = [
  { key: "trade_date", label: "Trade date", size: 94 },
  { key: "type", label: "Event", size: 90 },
  { key: "symbol", label: "Security", size: 77 },
  { key: "quantity", label: "Qty", numeric: true, size: 70 },
  { key: "price", label: "Fill", numeric: true, size: 83 },
  { key: "currency", label: "CCY", size: 58 },
  { key: "source", label: "Source", size: 128 },
  { key: "review_state", label: "Review", size: 148 },
];
function Notice({ error }: { error: unknown }) {
  return error ? (
    <div role="alert" className="operation-notice negative">
      {error instanceof Error ? error.message : String(error)}
    </div>
  ) : null;
}
function OperatingRibbon({ data }: { data?: OperatingData }) {
  const p = data?.portfolio,
    perf = data?.performance,
    r = data?.risk;
  const items = [
    ["NAV", money(p?.nav)],
    ["Day P&L", money(p?.daily_pnl)],
    ["Day return", pct(perf?.daily)],
    ["MTD", pct(perf?.mtd)],
    ["YTD", pct(perf?.ytd)],
    ["Inception", pct(perf?.twr)],
    ["Cash", money(p?.cash)],
    ["Gross assets", money(p?.gross_asset_value)],
    ["Net exposure", pct(r?.net_exposure)],
    ["Beta", number(r?.beta)],
    ["VaR 95%", money(r?.var_95)],
    ["Drawdown", pct(perf?.current_drawdown)],
    ["Data as of", data?.as_of ? timestamp(data.as_of) : "--"],
  ];
  return (
    <div className="operating-ribbon">
      {items.map(([label, value]) => (
        <div key={label}>
          <span>{label}</span>
          <strong title={value}>{value}</strong>
        </div>
      ))}
    </div>
  );
}
export function PortfolioHomePage() {
  const query = usePortfolio();
  const data = query.data as OperatingData | undefined;
  const { open, selectSecurity } = useTerminal();
  const trades = useApi<{ items: Row[] }>(
    "operating-trades",
    "/api/v1/operations/trades",
  );
  const quant = useApi<{ strategies: Row[]; runs: Row[] }>(
    "operating-quant",
    "/api/v1/desks/quant",
  );
  const agents = useApi<{ items: Row[] }>(
    "operating-agents",
    "/api/v1/data-drop/agents",
  );
  const [curve, setCurve] = useState("equity");
  return (
    <>
      <PageTitle code="HOME" title="Portfolio Command Centre">
        <span className="secondary mono">KNK_MAIN / SGD</span>
        <Badge>{data?.quality ?? "LOADING"}</Badge>
        <IconButton
          label="Export portfolio workbook"
          onClick={() =>
            window.open("/backend/api/v1/operations/export", "_blank")
          }
        >
          <ArrowDownToLine size={13} />
        </IconButton>
        <IconButton label="Refresh portfolio" onClick={() => query.refetch()}>
          <RefreshCw size={13} />
        </IconButton>
      </PageTitle>
      <OperatingRibbon data={data} />
      <Notice error={query.error} />
      <div className="page-grid portfolio-command-grid">
        <Panel
          title="KnK Capital / NAV and benchmark"
          source={data?.source}
          quality={data?.quality}
          asOf={data?.as_of}
          loading={query.isLoading}
          actions={
            <div className="segmented">
              {[
                ["equity", "NAV"],
                ["drawdown", "DD"],
                ["external_flow", "Flows"],
              ].map(([key, title]) => (
                <button
                  key={key}
                  aria-pressed={curve === key}
                  onClick={() => setCurve(key)}
                >
                  {title}
                </button>
              ))}
            </div>
          }
        >
          <LineChart
            label="KnK main portfolio NAV"
            rows={records(data?.curve ?? [])}
            keys={
              curve === "equity"
                ? [
                    { key: "equity", name: "KnK Main", color: COLORS.amber },
                    { key: "benchmark", name: "SPY / SGD", color: COLORS.blue },
                  ]
                : [
                    {
                      key: curve,
                      name:
                        curve === "drawdown"
                          ? "Flow-adjusted drawdown"
                          : "External flows",
                      color: COLORS.amber,
                    },
                  ]
            }
          />
        </Panel>
        <Panel
          title="Risk / limits"
          source="INTERNAL LEDGER"
          quality={data?.quality}
        >
          <dl className="operating-facts">
            {[
              ["Gross exposure", pct(data?.risk.gross_exposure)],
              ["Largest position", pct(data?.risk.max_position_weight)],
              ["Currency concentration", pct(data?.risk.max_currency_weight)],
              ["CVaR 95%", money(data?.risk.cvar_95)],
              ["Limit breaches", String(data?.breaches.length ?? 0)],
              [
                "NAV reconciliation",
                String(data?.reconciliation.state ?? "--"),
              ],
            ].map(([label, value]) => (
              <div key={label}>
                <dt>{label}</dt>
                <dd>{value}</dd>
              </div>
            ))}
          </dl>
          <button
            className="text-link"
            onClick={() => open("/risk-trade-monitor", "RISKMON")}
          >
            Risk &amp; Trade
          </button>
        </Panel>
        <Panel
          title="Positions / ledger-derived"
          source={data?.source}
          quality={data?.quality}
        >
          <DataTable
            id="main-holdings"
            compact
            rows={records(data?.positions ?? [])}
            columns={holdingColumns}
            onSelect={(r) => {
              selectSecurity(String(r.symbol));
              open("/security/" + r.symbol, String(r.symbol) + " DES");
            }}
          />
        </Panel>
        <Panel
          title="P&L / inception attribution"
          source={data?.source}
          quality={data?.quality}
        >
          <DataTable
            id="main-attribution"
            compact
            rows={data?.attribution ?? []}
            columns={[
              { key: "symbol", label: "Security", size: 75 },
              { key: "realised", label: "Realised", numeric: true, size: 88 },
              {
                key: "unrealised",
                label: "Unrealised",
                numeric: true,
                size: 94,
              },
              { key: "total_pnl", label: "Net P&L", numeric: true, size: 88 },
            ]}
          />
        </Panel>
        <Panel
          title="Trade monitor / recent ledger events"
          source="RECORDED EVENTS"
          actions={
            <IconButton
              label="Open trade monitor"
              onClick={() => open("/trade-monitor", "TRADES")}
            >
              <Plus size={12} />
            </IconButton>
          }
        >
          <DataTable
            id="main-trades"
            compact
            rows={trades.data?.items ?? []}
            columns={tradeColumns}
          />
        </Panel>
        <Panel
          title="Quant / jobs and strategy registry"
          source="PERSISTED RUNS"
        >
          <DataTable
            id="main-strategies"
            compact
            rows={quant.data?.strategies ?? []}
            columns={[
              { key: "name", label: "Strategy", size: 185 },
              { key: "state", label: "State", size: 155 },
            ]}
            onSelect={() => open("/quant-dashboard", "QMON")}
          />
        </Panel>
        <Panel
          title="Operations / freshness and exceptions"
          source="INTERNAL DIAGNOSTICS"
          quality={data?.quality}
        >
          <div className="operation-health">
            <span>
              Price coverage{" "}
              <strong>{number(data?.freshness.price_coverage_pct, 0)}%</strong>
            </span>
            <span>
              Stale NAV <strong>{pct(data?.freshness.stale_nav_pct)}</strong>
            </span>
            <span>
              Agent{" "}
              <strong>
                {agents.data?.items.some((a) => a.state === "ONLINE")
                  ? "ONLINE"
                  : "OFFLINE"}
              </strong>
            </span>
            <span>
              Broker{" "}
              <strong className="warning">
                {data?.broker_state ?? "CHECKING"}
              </strong>
            </span>
            <span>
              NAV calculated{" "}
              <strong className="valuation-timestamp">
                {timestamp(data?.calculated_at)}
              </strong>
            </span>
          </div>
          <div className="operation-warnings">
            {data?.warnings.map((w) => (
              <div key={w} className="warning">
                {w}
              </div>
            ))}
          </div>
        </Panel>
      </div>
    </>
  );
}

export function TradeMonitorPage({ risk = false }: { risk?: boolean }) {
  const { open } = useTerminal();
  const query = useApi<{ items: Row[] }>(
    "operating-trades",
    "/api/v1/operations/trades",
  );
  const portfolio = usePortfolio();
  const data = portfolio.data as OperatingData | undefined;
  const client = useQueryClient();
  const [selected, setSelected] = useState<Row | null>(null);
  const [note, setNote] = useState("");
  const [state, setState] = useState("REVIEWED");
  const [form, setForm] = useState(false);
  const [details, setDetails] = useState<Record<string, string>>({
    to_currency: "USD",
    to_amount: "",
    ratio: "2",
    cost_allocation: "",
    child_symbol: "",
    reason: "",
    direction: "CREDIT",
  });
  const [draft, setDraft] = useState<Record<string, string>>({
    transaction_type: "BUY",
    trade_date: new Date().toISOString().slice(0, 10),
    symbol: "AAPL",
    quantity: "1",
    price: "",
    currency: "USD",
    amount: "",
    commission: "0",
    fee: "0",
    tax: "0",
    notes: "",
    fx_rate_to_base: "",
  });
  const save = useMutation({
    mutationFn: () =>
      knkApi.post<Row>("/api/v1/operations/transactions", {
        ...Object.fromEntries(
          Object.entries(draft).filter(([, v]) => v !== ""),
        ),
        metadata: details,
        child_symbol: details.child_symbol || undefined,
      }),
    onSuccess: () => {
      setForm(false);
      client.invalidateQueries({ queryKey: ["operating-trades"] });
      client.invalidateQueries({ queryKey: ["terminal-portfolio"] });
    },
  });
  const review = useMutation({
    mutationFn: () =>
      knkApi.post("/api/v1/operations/trades/" + selected?.id + "/review", {
        state,
        note,
      }),
    onSuccess: () => {
      query.refetch();
      setSelected(null);
      setNote("");
    },
  });
  const reconcile = useMutation({
    mutationFn: () => knkApi.post<Row>("/api/v1/operations/reconciliation", {}),
  });
  return (
    <>
      <PageTitle
        code={risk ? "RISKMON" : "TRADES"}
        title={risk ? "Risk & Trade Monitor" : "Trade Monitor"}
      >
        <Badge>READ ONLY BROKER</Badge>
        {risk && (
          <>
            <button onClick={() => open("/stress-tests", "STRESS")}>
              Stress test
            </button>
            <button onClick={() => open("/hedge", "HEDGE")}>
              Hedge review
            </button>
          </>
        )}
        <button onClick={() => setForm(true)}>
          <Plus size={12} /> Record transaction
        </button>
        <IconButton label="Refresh trades" onClick={() => query.refetch()}>
          <RefreshCw size={13} />
        </IconButton>
      </PageTitle>
      {risk && <OperatingRibbon data={data} />}
      <div
        className={
          risk
            ? "page-grid risk-trade-dashboard-grid"
            : "page-grid operation-two-column"
        }
      >
        <Panel
          title="Ledger events / manual, file and broker records"
          loading={query.isLoading}
          error={query.error}
          source="RECORDED EVENTS"
        >
          <DataTable
            id="trade-monitor"
            rows={query.data?.items ?? []}
            columns={[
              ...tradeColumns,
              { key: "commission", label: "Commission", numeric: true },
              { key: "pre_beta", label: "Pre beta", numeric: true },
              { key: "post_beta", label: "Post beta", numeric: true },
            ]}
            onSelect={setSelected}
            selectedKey={String(selected?.id ?? "")}
          />
        </Panel>
        <Panel
          title={
            selected
              ? "Trade review / " + String(selected.symbol ?? selected.type)
              : "Risk / reconciliation"
          }
          source="AUDITED INTERNAL LEDGER"
        >
          {selected ? (
            <div className="operation-form">
              <dl className="operating-facts">
                {[
                  "trade_date",
                  "type",
                  "source",
                  "review_state",
                  "pre_beta",
                  "post_beta",
                  "rationale",
                ].map((k) => (
                  <div key={k}>
                    <dt>{k.replaceAll("_", " ")}</dt>
                    <dd>{String(selected[k] ?? "--")}</dd>
                  </div>
                ))}
              </dl>
              <Field label="Review state">
                <select
                  value={state}
                  onChange={(e) => setState(e.target.value)}
                >
                  {["REVIEWED", "FLAGGED", "REQUIRES_REVIEW"].map((v) => (
                    <option key={v}>{v}</option>
                  ))}
                </select>
              </Field>
              <Field label="Review note">
                <textarea
                  value={note}
                  onChange={(e) => setNote(e.target.value)}
                  rows={4}
                />
              </Field>
              <Notice error={review.error} />
              <button
                disabled={!note.trim() || review.isPending}
                onClick={() => review.mutate()}
              >
                <Check size={13} /> Record review
              </button>
              <div className="operation-warnings">
                {Array.isArray(selected.breaches) &&
                  selected.breaches.map((b: Row, i: number) => (
                    <div key={i} className="warning">
                      {String(b.metric)}
                    </div>
                  ))}
              </div>
            </div>
          ) : (
            <div className="operation-form">
              <dl className="operating-facts">
                {[
                  ["Portfolio beta", number(data?.risk.beta)],
                  ["Gross exposure", pct(data?.risk.gross_exposure)],
                  ["Cash", money(data?.portfolio.cash)],
                  ["Limit breaches", String(data?.breaches.length ?? 0)],
                ].map(([k, v]) => (
                  <div key={k}>
                    <dt>{k}</dt>
                    <dd>{v}</dd>
                  </div>
                ))}
              </dl>
              <button
                disabled={reconcile.isPending}
                onClick={() => reconcile.mutate()}
              >
                <RefreshCw size={12} /> Reconcile records
              </button>
              <Notice error={reconcile.error} />
              {reconcile.data && <Badge>{String(reconcile.data.state)}</Badge>}
              <div className="operation-warnings">
                {data?.breaches.map((b, i) => (
                  <div className="warning" key={i}>
                    {String(b.metric)}: {number(b.value)} /{" "}
                    {number(b.threshold)}
                  </div>
                ))}
              </div>
            </div>
          )}
        </Panel>
      </div>
      {risk && (
        <div className="page-grid risk-exposure-grid">
          <Panel
            title="Position risk contributions"
            source={data?.source}
            quality={data?.quality}
          >
            <DataTable
              id="risk-monitor-positions"
              compact
              rows={records(data?.positions ?? [])}
              columns={[
                { key: "symbol", label: "Security", size: 85 },
                {
                  key: "weight",
                  label: "Weight",
                  numeric: true,
                  percent: true,
                },
                { key: "beta", label: "Beta", numeric: true },
                {
                  key: "risk_contribution",
                  label: "Risk contribution",
                  numeric: true,
                  percent: true,
                  size: 135,
                },
                { key: "currency", label: "CCY", size: 60 },
              ]}
            />
          </Panel>
          <Panel
            title="Currency exposure / cash included"
            source={data?.source}
            quality={data?.quality}
          >
            <DataTable
              id="risk-monitor-currency"
              compact
              rows={data?.exposures.currency ?? []}
              columns={[
                { key: "name", label: "Currency" },
                {
                  key: "value",
                  label: "Value / SGD",
                  numeric: true,
                  money: true,
                  size: 130,
                },
                {
                  key: "weight",
                  label: "Weight",
                  numeric: true,
                  percent: true,
                },
              ]}
            />
          </Panel>
        </div>
      )}
      {form && (
        <div className="modal-backdrop">
          <section
            className="modal"
            role="dialog"
            aria-label="Record ledger transaction"
          >
            <header className="modal-title">
              <h2>Record ledger transaction / KNK_MAIN</h2>
              <IconButton
                label="Close transaction"
                onClick={() => setForm(false)}
              >
                <X size={14} />
              </IconButton>
            </header>
            <div className="modal-body operation-form">
              <div className="operation-fields">
                <Field label="Transaction type">
                  <select
                    value={draft.transaction_type}
                    onChange={(e) =>
                      setDraft((d) => ({
                        ...d,
                        transaction_type: e.target.value,
                      }))
                    }
                  >
                    {[
                      "BUY",
                      "SELL",
                      "SHORT",
                      "COVER",
                      "DEPOSIT",
                      "WITHDRAWAL",
                      "DIVIDEND",
                      "INTEREST",
                      "COMMISSION",
                      "FEE",
                      "TAX",
                      "TRANSFER_IN",
                      "TRANSFER_OUT",
                      "FX_CONVERSION",
                      "SPLIT",
                      "SPINOFF",
                      "OTHER_ADJUSTMENT",
                    ].map((v) => (
                      <option key={v}>{v}</option>
                    ))}
                  </select>
                </Field>
                {Object.entries(draft)
                  .filter(([k]) => !["transaction_type", "notes"].includes(k))
                  .map(([key, value]) => (
                    <Field key={key} label={key.replaceAll("_", " ")}>
                      <input
                        type={key === "trade_date" ? "date" : "text"}
                        value={value}
                        onChange={(e) =>
                          setDraft((d) => ({ ...d, [key]: e.target.value }))
                        }
                      />
                    </Field>
                  ))}
              </div>
              {[
                ...(draft.transaction_type === "FX_CONVERSION"
                  ? ["to_currency", "to_amount"]
                  : []),
                ...(draft.transaction_type === "SPLIT" ? ["ratio"] : []),
                ...(draft.transaction_type === "SPINOFF"
                  ? ["child_symbol", "cost_allocation"]
                  : []),
                ...(draft.transaction_type === "OTHER_ADJUSTMENT"
                  ? ["reason", "direction"]
                  : []),
              ].map((key) => (
                <Field key={key} label={key.replaceAll("_", " ")}>
                  <input
                    value={details[key]}
                    onChange={(e) =>
                      setDetails((d) => ({ ...d, [key]: e.target.value }))
                    }
                  />
                </Field>
              ))}
              <Field label="Rationale / notes">
                <textarea
                  value={draft.notes}
                  onChange={(e) =>
                    setDraft((d) => ({ ...d, notes: e.target.value }))
                  }
                />
              </Field>
              <Notice error={save.error} />
              <button disabled={save.isPending} onClick={() => save.mutate()}>
                <Check size={13} /> Record transaction
              </button>
            </div>
          </section>
        </div>
      )}
    </>
  );
}

export function DataDropOperationsPage() {
  const { open } = useTerminal();
  const inbox = useApi<{ items: FileRecord[] }>(
    "data-drop-inbox",
    "/api/v1/data-drop/files",
  );
  const profiles = useApi<{ items: Profile[] }>(
    "data-drop-profiles",
    "/api/v1/data-drop/profiles",
  );
  const agents = useApi<{ items: Row[] }>(
    "data-drop-agents",
    "/api/v1/data-drop/agents",
  );
  const [fileId, setFileId] = useState("");
  const selected = inbox.data?.items.find((f) => f.id === fileId);
  const [profileId, setProfileId] = useState("");
  const [mapping, setMapping] = useState<Record<string, string>>({});
  const [defaults, setDefaults] = useState("{}");
  const [resolution, setResolution] = useState("");
  const [name, setName] = useState("");
  const [licence, setLicence] = useState("");
  const [approved, setApproved] = useState(false);
  const [view, setView] = useState("Preview");
  const [brokerScope, setBrokerScope] = useState(false);
  const [uploadError, setUploadError] = useState("");
  const [uploading, setUploading] = useState(false);
  const client = useQueryClient();
  const activeProfile = profiles.data?.items.find((p) => p.id === profileId);
  function choose(f: FileRecord) {
    setFileId(f.id);
    setProfileId(
      f.profile_id ??
        profiles.data?.items.find((p) => p.code === "KOYFIN_PRICE_HISTORY")
          ?.id ??
        "",
    );
    setMapping(f.mapping);
    setName(f.filename.replace(/\.[^.]+$/, ""));
    setApproved(false);
  }
  async function uploadFiles(files: FileList | null) {
    if (!files) return;
    setUploading(true);
    setUploadError("");
    try {
      for (const file of Array.from(files)) {
        const body = new FormData();
        body.append("file", file);
        const response = await fetch("/backend/api/v1/data-drop/files", {
          method: "POST",
          body,
        });
        const result = await response.json();
        if (!response.ok)
          throw new Error(String(result.detail ?? "Upload failed"));
        choose(result as FileRecord);
      }
      await inbox.refetch();
    } catch (error) {
      setUploadError(error instanceof Error ? error.message : String(error));
    } finally {
      setUploading(false);
    }
  }
  const validate = useMutation({
    mutationFn: () =>
      knkApi.post<FileRecord>(
        "/api/v1/data-drop/files/" + fileId + "/validate",
        {
          profile_id: profileId,
          mapping: Object.keys(mapping).length ? mapping : null,
          defaults: JSON.parse(defaults),
          symbol_resolution: resolution || null,
        },
      ),
    onSuccess: (result) => {
      setMapping(result.mapping);
      inbox.refetch();
    },
  });
  const importFile = useMutation({
    mutationFn: () =>
      knkApi.post<FileRecord>("/api/v1/data-drop/files/" + fileId + "/import", {
        name,
        licence,
        approve: approved,
      }),
    onSuccess: () => {
      inbox.refetch();
      client.invalidateQueries({ queryKey: ["terminal-portfolio"] });
      client.invalidateQueries({ queryKey: ["bootstrap"] });
    },
  });
  const pairing = useMutation({
    mutationFn: () =>
      knkApi.post<{ code: string; expires_at: string }>(
        "/api/v1/data-drop/agents/pair?broker=" + brokerScope,
        {},
      ),
  });
  return (
    <>
      <PageTitle code="DATADROP" title="External Data Drop">
        <button onClick={() => open("/broker-monitor", "BROKER")}>
          Paper broker
        </button>
        <button onClick={() => open("/price-sources", "SOURCE")}>
          Price sources
        </button>
        <Badge>KOYFIN FILE</Badge>
        <label className="upload-command">
          <Upload size={13} /> {uploading ? "Uploading" : "Upload files"}
          <input
            aria-label="Upload data files"
            type="file"
            multiple
            accept=".csv,.xlsx,.json"
            disabled={uploading}
            onChange={(e) => uploadFiles(e.target.files)}
          />
        </label>
        <IconButton
          label="Refresh inbox"
          onClick={() => {
            inbox.refetch();
            agents.refetch();
          }}
        >
          <RefreshCw size={13} />
        </IconButton>
      </PageTitle>
      <Notice error={uploadError || inbox.error} />
      <div
        className="page-grid data-drop-operating-grid"
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => {
          e.preventDefault();
          uploadFiles(e.dataTransfer.files);
        }}
      >
        <Panel
          title="File inbox / immutable raw"
          source="EXTERNAL FILES"
          loading={inbox.isLoading}
        >
          <DataTable
            id="data-drop-inbox"
            rows={records(inbox.data?.items ?? [])}
            columns={[
              { key: "filename", label: "File", size: 200 },
              { key: "state", label: "State", size: 176 },
              { key: "source", label: "Source", size: 110 },
            ]}
            onSelect={(r) => choose(r as FileRecord)}
            selectedKey={fileId}
          />
        </Panel>
        <Panel
          title={selected?.filename ?? "File details"}
          source={selected?.source}
          quality={selected?.state}
        >
          {selected ? (
            <>
              <div className="operation-tabs" role="tablist">
                {["Preview", "Mapping", "Validation", "Lineage"].map((v) => (
                  <button
                    role="tab"
                    aria-selected={view === v}
                    key={v}
                    onClick={() => setView(v)}
                  >
                    {v}
                  </button>
                ))}
              </div>
              {view === "Preview" && (
                <DataTable
                  id={"file-preview-" + selected.id}
                  rows={
                    selected.metadata.normalized_preview ??
                    selected.metadata.preview ??
                    []
                  }
                  columns={Object.keys(
                    (selected.metadata.normalized_preview ??
                      selected.metadata.preview)?.[0] ?? {},
                  ).map((key) => ({ key, label: key, size: 120 }))}
                />
              )}
              {view === "Mapping" && (
                <div className="operation-form">
                  <Field label="Mapping profile">
                    <select
                      value={profileId}
                      onChange={(e) => {
                        setProfileId(e.target.value);
                        setMapping({});
                      }}
                    >
                      {profiles.data?.items.map((p) => (
                        <option value={p.id} key={p.id}>
                          {p.code} / v{p.version}
                        </option>
                      ))}
                    </select>
                  </Field>
                  <div className="operation-fields">
                    {Object.keys(activeProfile?.rules.aliases ?? {}).map(
                      (role) => (
                        <Field
                          key={role}
                          label={
                            role +
                            (activeProfile?.rules.required.includes(role)
                              ? " *"
                              : "")
                          }
                        >
                          <select
                            value={mapping[role] ?? ""}
                            onChange={(e) =>
                              setMapping((m) => ({
                                ...m,
                                [role]: e.target.value,
                              }))
                            }
                          >
                            <option value="">Unmapped</option>
                            {selected.metadata.columns?.map((c) => (
                              <option key={c}>{c}</option>
                            ))}
                          </select>
                        </Field>
                      ),
                    )}
                  </div>
                  <Field label="Explicit defaults / JSON">
                    <textarea
                      rows={3}
                      value={defaults}
                      onChange={(e) => setDefaults(e.target.value)}
                    />
                  </Field>
                  <Field label="Filename / symbol conflict resolution">
                    <select
                      value={resolution}
                      onChange={(e) => setResolution(e.target.value)}
                    >
                      <option value="">Require review</option>
                      <option value="CONTENT">Use file content</option>
                      <option value="FILENAME">Use filename</option>
                    </select>
                  </Field>
                  <button
                    disabled={!profileId || validate.isPending}
                    onClick={() => validate.mutate()}
                  >
                    <Check size={13} /> Validate mapping
                  </button>
                  <Notice error={validate.error} />
                </div>
              )}
              {view === "Validation" && (
                <div className="operation-form">
                  <Badge>{selected.state}</Badge>
                  {selected.validation.errors?.map((e) => (
                    <div className="negative" key={e}>
                      {e}
                    </div>
                  ))}
                  {selected.validation.warnings?.map((w) => (
                    <div className="warning" key={w}>
                      {w}
                    </div>
                  ))}
                  <Notice error={selected.validation.import_error} />
                </div>
              )}
              {view === "Lineage" && (
                <>
                  <dl className="operating-facts">
                    <div>
                      <dt>SHA-256</dt>
                      <dd className="hash-value">{selected.hash}</dd>
                    </div>
                    <div>
                      <dt>Version</dt>
                      <dd>{selected.dataset_version_id ?? "--"}</dd>
                    </div>
                    <div>
                      <dt>Profile</dt>
                      <dd>{selected.metadata.mapping_profile ?? "--"}</dd>
                    </div>
                  </dl>
                  <DataTable
                    id="file-lineage"
                    rows={selected.history}
                    columns={[
                      { key: "state", label: "State", size: 180 },
                      { key: "at", label: "Time", size: 190 },
                      { key: "message", label: "Record", size: 260 },
                    ]}
                  />
                </>
              )}
            </>
          ) : (
            <Empty title="No file selected" />
          )}
        </Panel>
        <Panel title="Import approval / agent status" source="MANUAL APPROVAL">
          <div className="operation-form">
            <Field label="Dataset name">
              <input value={name} onChange={(e) => setName(e.target.value)} />
            </Field>
            <Field label="Licence / permitted use">
              <textarea
                value={licence}
                onChange={(e) => setLicence(e.target.value)}
                rows={2}
              />
            </Field>
            <label className="checkbox">
              <input
                type="checkbox"
                checked={approved}
                onChange={(e) => setApproved(e.target.checked)}
              />{" "}
              Approve this validated version
            </label>
            <button
              disabled={
                !approved ||
                !licence.trim() ||
                selected?.state !== "AWAITING_APPROVAL" ||
                importFile.isPending
              }
              onClick={() => importFile.mutate()}
            >
              <Check size={13} /> Import approved file
            </button>
            {selected?.dataset_version_id && (
              <>
                <button
                  onClick={() =>
                    open(
                      `/backtests/dataset/${selected.metadata.dataset_id}/version/${selected.dataset_version_id}`,
                      "FILE BACKTEST",
                      true,
                    )
                  }
                >
                  Backtest dataset
                </button>
                <button
                  onClick={() =>
                    open(
                      `/data-catalogue/${selected.metadata.dataset_id}`,
                      "DATASET",
                      true,
                    )
                  }
                >
                  Dataset lineage
                </button>
              </>
            )}
            <Notice error={importFile.error} />
            <div className="operation-health">
              <span>
                Agent{" "}
                <strong>
                  {agents.data?.items.some((a) => a.state === "ONLINE")
                    ? "ONLINE"
                    : "OFFLINE"}
                </strong>
              </span>
              <button
                disabled={pairing.isPending}
                onClick={() => pairing.mutate()}
              >
                Create agent pairing
              </button>
              <label className="checkbox">
                <input
                  type="checkbox"
                  checked={brokerScope}
                  onChange={(e) => setBrokerScope(e.target.checked)}
                />{" "}
                Include read-only paper broker scope
              </label>
            </div>
            <Notice error={pairing.error} />
            {pairing.data && (
              <div>
                <label>One-time pairing code</label>
                <input
                  readOnly
                  value={pairing.data.code}
                  aria-label="One-time pairing code"
                />
                <div className="secondary">
                  Expires {timestamp(pairing.data.expires_at)}
                </div>
              </div>
            )}
          </div>
        </Panel>
      </div>
    </>
  );
}

export function OperatingDeskPage({
  desk,
}: {
  desk: "equity" | "quant" | "edge";
}) {
  const { open } = useTerminal();
  const equity = useApi<{
    coverage: Row[];
    theses: Row[];
    quality: string;
    source: string;
    as_of: string;
  }>("equity-desk", "/api/v1/desks/equity", desk === "equity");
  const quant = useApi<{ strategies: Row[]; runs: Row[]; candidates: Row[] }>(
    "operating-quant",
    "/api/v1/desks/quant",
    desk !== "equity",
  );
  const [name, setName] = useState(""),
    [hypothesis, setHypothesis] = useState(""),
    [version, setVersion] = useState("");
  const files = useApi<{ items: FileRecord[] }>(
    "data-drop-inbox",
    "/api/v1/data-drop/files",
    desk === "edge",
  );
  const candidate = useMutation({
    mutationFn: () =>
      knkApi.post("/api/v1/desks/candidates", {
        name,
        hypothesis,
        dataset_version_id: version,
      }),
    onSuccess: () => {
      quant.refetch();
      setName("");
      setHypothesis("");
    },
  });
  return (
    <>
      <PageTitle
        code={desk === "equity" ? "EQUITY" : desk === "edge" ? "EDGE" : "QMON"}
        title={
          desk === "equity"
            ? "Equity Research Desk"
            : desk === "edge"
              ? "Candidate Edge Lab"
              : "Quant Research Monitor"
        }
      >
        <Badge>
          {desk === "equity"
            ? (equity.data?.quality ?? "LOADING")
            : "RESEARCH ONLY"}
        </Badge>
        <button
          onClick={() =>
            open(
              desk === "equity" ? "/research" : "/backtests",
              desk === "equity" ? "RES" : "BT",
            )
          }
        >
          {desk === "equity" ? "Research notes" : "Backtests"}
        </button>
      </PageTitle>
      <div className="page-grid operation-two-column">
        {desk === "equity" ? (
          <>
            <Panel
              title="Portfolio coverage"
              loading={equity.isLoading}
              error={equity.error}
              source={equity.data?.source}
              asOf={equity.data?.as_of}
            >
              <DataTable
                id="equity-coverage"
                rows={equity.data?.coverage ?? []}
                columns={[
                  { key: "symbol", label: "Security" },
                  {
                    key: "weight",
                    label: "Weight",
                    numeric: true,
                    percent: true,
                  },
                  { key: "price", label: "Price", numeric: true },
                  { key: "source", label: "Source", size: 185 },
                  { key: "thesis_count", label: "Theses" },
                  { key: "filings_state", label: "Filings", size: 155 },
                  { key: "latest_file", label: "Latest file", size: 190 },
                ]}
                onSelect={(r) =>
                  open("/security/" + r.symbol, String(r.symbol) + " DES")
                }
              />
            </Panel>
            <Panel title="Investment theses" source="INTERNAL RESEARCH">
              <DataTable
                id="equity-theses"
                rows={equity.data?.theses ?? []}
                columns={[
                  { key: "title", label: "Thesis", size: 240 },
                  { key: "state", label: "State" },
                ]}
                onSelect={() => open("/research", "RES")}
              />
            </Panel>
          </>
        ) : (
          <>
            <Panel
              title={
                desk === "edge"
                  ? "Candidate registry / no automatic promotion"
                  : "Strategy registry"
              }
              loading={quant.isLoading}
              error={quant.error}
              source="PERSISTED RESEARCH"
            >
              <DataTable
                id="quant-registry"
                rows={
                  (desk === "edge"
                    ? quant.data?.candidates
                    : quant.data?.strategies) ?? []
                }
                columns={[
                  { key: "name", label: "Name", size: 240 },
                  { key: "state", label: "State", size: 180 },
                  {
                    key: desk === "edge" ? "hypothesis" : "version",
                    label: desk === "edge" ? "Hypothesis" : "Version",
                    size: 230,
                  },
                ]}
              />
            </Panel>
            {desk === "edge" ? (
              <Panel
                title="Record research candidate"
                source="VERSION-PINNED DATASET"
              >
                <div className="operation-form">
                  <Field label="Candidate name">
                    <input
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                    />
                  </Field>
                  <Field label="Hypothesis">
                    <textarea
                      rows={5}
                      value={hypothesis}
                      onChange={(e) => setHypothesis(e.target.value)}
                    />
                  </Field>
                  <Field label="Dataset version">
                    <select
                      value={version}
                      onChange={(e) => setVersion(e.target.value)}
                    >
                      <option value="">Select imported version</option>
                      {files.data?.items
                        .filter((f) => f.dataset_version_id)
                        .map((f) => (
                          <option value={f.dataset_version_id!} key={f.id}>
                            {f.filename} / {f.dataset_version_id?.slice(0, 8)}
                          </option>
                        ))}
                    </select>
                  </Field>
                  <button
                    disabled={
                      !version ||
                      hypothesis.length < 15 ||
                      name.length < 3 ||
                      candidate.isPending
                    }
                    onClick={() => candidate.mutate()}
                  >
                    <Plus size={13} /> Record candidate
                  </button>
                  <Notice error={candidate.error} />
                  <Badge>OOS / PAPER VALIDATION REQUIRED</Badge>
                </div>
              </Panel>
            ) : (
              <Panel
                title="Analytical jobs / persisted results"
                source="WORKER RUNS"
              >
                <DataTable
                  id="quant-jobs"
                  rows={quant.data?.runs ?? []}
                  columns={[
                    { key: "name", label: "Run", size: 210 },
                    { key: "kind", label: "Type" },
                    { key: "status", label: "Status" },
                  ]}
                  onSelect={(r) =>
                    open(
                      r.kind === "stress" ? "/stress-tests" : "/backtests",
                      String(r.kind).toUpperCase(),
                    )
                  }
                />
              </Panel>
            )}
          </>
        )}
      </div>
    </>
  );
}
