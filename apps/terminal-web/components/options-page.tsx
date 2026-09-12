"use client";

import { useMutation } from "@tanstack/react-query";
import { knkApi } from "@knk/api-client";
import {
  Clock,
  Download,
  FlaskConical,
  Play,
  Plus,
  Trash2,
} from "lucide-react";
import { PageTitle, useApi } from "./core-pages";
import { useTabState, useTerminal } from "./context";
import {
  Badge,
  Chart,
  COLORS,
  DataTable,
  Empty,
  Field,
  Kpis,
  Panel,
  download,
  number,
  pct,
} from "./ui";
import type { Column } from "./ui";
import type { Row } from "./types";

interface ChainData {
  items: Row[];
  as_of: string;
  symbols: string[];
  provenance: { source: string; quality: string; schema: Row };
}
interface OptionsReport {
  id: string;
  symbol: string;
  items: Row[];
  by_strike: Row[];
  by_expiry: Row[];
  spot_profile: Row[];
  iv_surface: Row[];
  max_pain: Row[];
  expected_moves: Row[];
  skew: Row[];
  summary: Row;
  coverage: Row;
  spot: number;
  gamma_flip: number | null;
  quality: string;
  source: string;
  as_of: string;
  state: string;
  input_hash: string;
  warnings: string[];
  greek_units: Record<string, string>;
  positions: {
    items: Row[];
    totals: Row;
    payoff: Row[];
    state: string;
    payoff_state: string;
    warnings: string[];
  };
  position_source: string;
}
interface SavedRun {
  id: string;
  name: string;
  parameters: Row;
  result: OptionsReport;
}
const name = (key: string) => key.replaceAll("_", " ");
const numeric = (keys: string[], precision = 2): Column[] =>
  keys.map((key) => ({
    key,
    label: name(key),
    numeric: true,
    size: 115,
    format: (value) => number(value, precision),
  }));
const sections = [
  "CHAIN",
  "GEX",
  "GREEKS",
  "VOLATILITY",
  "PAYOFF",
  "POSITIONS",
];
function chart(rows: Row[], x: string, keys: string[], bar = false) {
  return {
    grid: { left: 8, right: 16, top: 24, bottom: 8, containLabel: true },
    legend: { top: 0, textStyle: { color: COLORS.text, fontSize: 10 } },
    xAxis: {
      type: "category" as const,
      data: rows.map((row) => String(row[x])),
    },
    series: keys.map((key) => ({
      name: name(key),
      type: (bar ? "bar" : "line") as "bar" | "line",
      symbol: "none",
      data: rows.map((row) => (row[key] == null ? null : Number(row[key]))),
    })),
  };
}

export function OptionsWorkspace({ route }: { route: string }) {
  const { security, open } = useTerminal();
  const initial = /gex|gamma|dex/.test(route)
    ? "GEX"
    : /greek|delta|theta|vega|rho/.test(route)
      ? "GREEKS"
      : /ivs|iv|skew|pcr|maxpain|emove/.test(route)
        ? "VOLATILITY"
        : /payoff|optstrat/.test(route)
          ? "PAYOFF"
          : "CHAIN";
  const [section, setSection] = useTabState(
    "options-section",
    route.includes("port-greeks") ? "POSITIONS" : initial,
  );
  const [form, setForm] = useTabState("options-config", {
    dataset: "",
    spot: "",
    asOf: "",
    riskFree: "3",
    dividend: "0",
    source: "CALCULATED",
    sign: "DEALER_SHORT",
    american: false,
    maxAge: "72",
    expiry: "",
    portfolio: "",
    profileLow: "80",
    profileHigh: "120",
  });
  const [legs, setLegs] = useTabState<
    { option_symbol: string; quantity: string; premium: string }[]
  >("options-legs", []);
  const [report, setReport] = useTabState<OptionsReport | null>(
    "options-result",
    null,
  );
  const versions = useApi<{ items: Row[] }>(
    "option-datasets",
    "/api/v1/options/datasets",
  );
  const dataset = useApi<ChainData>(
    "option-chain",
    `/api/v1/options/datasets/${form.dataset}`,
    Boolean(form.dataset),
  );
  const history = useApi<{ items: SavedRun[] }>(
    "option-history",
    "/api/v1/terminal/runs?kind=options",
  );
  const portfolios = useApi<{ items: Row[] }>(
    "option-portfolios",
    "/api/v1/portfolios",
  );
  const set = (key: keyof typeof form, value: string | boolean) =>
    setForm({ ...form, [key]: value });
  const demo = useMutation({
    mutationFn: () =>
      knkApi.post<{ id: string; spot: number; as_of: string }>(
        "/api/v1/options/demo",
        { symbol: security, spot: 100 },
      ),
    onSuccess: (r) => {
      setForm({
        ...form,
        dataset: r.id,
        spot: String(r.spot),
        asOf: r.as_of,
        expiry: "",
      });
      versions.refetch();
    },
  });
  const calculate = useMutation({
    mutationFn: () =>
      knkApi.post<OptionsReport>("/api/v1/options/calculate", {
        symbol: security,
        dataset_version_id: form.dataset || null,
        spot_override: form.spot ? Number(form.spot) : null,
        as_of: form.asOf || null,
        risk_free: Number(form.riskFree) / 100,
        dividend_yield: Number(form.dividend) / 100,
        greek_source: form.source,
        dealer_sign: form.sign,
        allow_american_approximation: form.american,
        max_age_hours: Number(form.maxAge),
        expiry: form.expiry || null,
        profile_low: Number(form.profileLow) / 100,
        profile_high: Number(form.profileHigh) / 100,
        portfolio: form.portfolio || null,
        legs: form.portfolio
          ? []
          : legs.map((leg) => ({
              option_symbol: leg.option_symbol,
              quantity: Number(leg.quantity),
              premium: leg.premium ? Number(leg.premium) : null,
            })),
      }),
    onSuccess: (r) => {
      setReport(r);
      history.refetch();
    },
  });
  function load(run: SavedRun) {
    const p = run.parameters;
    setReport(run.result);
    setForm({
      dataset: String(p.dataset_version_id ?? ""),
      spot: p.spot_override == null ? "" : String(p.spot_override),
      asOf: String(p.as_of ?? ""),
      riskFree: String(Number(p.risk_free) * 100),
      dividend: String(Number(p.dividend_yield) * 100),
      source: String(p.greek_source),
      sign: String(p.dealer_sign),
      american: Boolean(p.allow_american_approximation),
      maxAge: String(p.max_age_hours),
      expiry: String(p.expiry ?? ""),
      portfolio: String(p.portfolio ?? ""),
      profileLow: String(Number(p.profile_low) * 100),
      profileHigh: String(Number(p.profile_high) * 100),
    });
    setLegs(
      ((p.legs as Row[]) ?? []).map((leg) => ({
        option_symbol: String(leg.option_symbol),
        quantity: String(leg.quantity),
        premium: leg.premium == null ? "" : String(leg.premium),
      })),
    );
  }
  const current = report?.symbol === security ? report : null;
  const contracts =
    dataset.data?.items.filter((row) => row.symbol === security) ?? [];
  const source = {
    source: current?.source,
    quality: current?.quality,
    asOf: current?.as_of,
  };
  const chainColumns: Column[] = [
    { key: "option_symbol", label: "Contract", size: 240 },
    { key: "expiry", label: "Expiry", size: 110 },
    { key: "right", label: "Side", size: 70 },
    ...numeric(["strike", "bid", "ask", "mid", "last"]),
    { key: "iv", label: "IV", numeric: true, percent: true },
    ...numeric(["open_interest", "volume", "multiplier"], 0),
    { key: "state", label: "State", size: 170 },
  ];
  return (
    <div className="research-page options-workspace">
      <PageTitle code="OPT" title={`${security} / Options Analytics`}>
        <Badge>{current?.quality ?? "NO ANALYSIS"}</Badge>
        <Badge>{current?.state ?? "DATA REQUIRED"}</Badge>
        <button
          className="primary-button"
          disabled={calculate.isPending}
          onClick={() => calculate.mutate()}
        >
          <Play size={13} />
          {calculate.isPending ? "Calculating..." : "Calculate & Save"}
        </button>
        <button
          className="toolbar-button"
          title="Create synthetic European demo chain"
          disabled={demo.isPending}
          onClick={() => demo.mutate()}
        >
          <FlaskConical size={14} />
        </button>
        {current && (
          <button
            className="toolbar-button"
            title="Download saved options JSON"
            onClick={() =>
              download(
                `options-${current.id}.json`,
                JSON.stringify(current, null, 2),
                "application/json",
              )
            }
          >
            <Download size={14} />
          </button>
        )}
      </PageTitle>
      <div className="performance-controls">
        <Field label="Chain version">
          <select
            aria-label="Options dataset"
            value={form.dataset}
            onChange={(e) =>
              setForm({ ...form, dataset: e.target.value, expiry: "" })
            }
          >
            <option value="">Latest matching chain</option>
            {versions.data?.items.map((row) => (
              <option key={String(row.id)} value={String(row.id)}>
                {String(row.name)} / {String(row.quality)} / v
                {String(row.version)}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Spot assumption">
          <input
            aria-label="Options spot"
            type="number"
            step="any"
            value={form.spot}
            onChange={(e) => set("spot", e.target.value)}
          />
        </Field>
        <Field label="As of / ISO timestamp">
          <input
            aria-label="Options as of"
            value={form.asOf}
            onChange={(e) => set("asOf", e.target.value)}
          />
        </Field>
        <button
          title="Use chain observation timestamp"
          className="toolbar-button"
          disabled={!dataset.data}
          onClick={() => set("asOf", dataset.data!.as_of)}
        >
          <Clock size={14} />
        </button>
        <Field label="Risk-free %">
          <input
            aria-label="Options risk free"
            type="number"
            step="any"
            value={form.riskFree}
            onChange={(e) => set("riskFree", e.target.value)}
          />
        </Field>
        <Field label="Dividend yield %">
          <input
            aria-label="Options dividend yield"
            type="number"
            step="any"
            value={form.dividend}
            onChange={(e) => set("dividend", e.target.value)}
          />
        </Field>
        <Field label="Greek source">
          <select
            aria-label="Options Greek source"
            value={form.source}
            onChange={(e) => set("source", e.target.value)}
          >
            <option>CALCULATED</option>
            <option>PROVIDER</option>
          </select>
        </Field>
        <Field label="OI sign assumption">
          <select
            aria-label="Dealer sign convention"
            value={form.sign}
            onChange={(e) => set("sign", e.target.value)}
          >
            <option value="DEALER_SHORT">Dealer short all options</option>
            <option value="NEUTRAL">Unsigned analytical OI</option>
            <option value="CALL_POSITIVE_PUT_NEGATIVE">
              Calls positive / puts negative
            </option>
          </select>
        </Field>
        <Field label="Max quote age / hours">
          <input
            aria-label="Options max age"
            type="number"
            value={form.maxAge}
            onChange={(e) => set("maxAge", e.target.value)}
          />
        </Field>
        <Field label="Expiry">
          <select
            aria-label="Options expiry"
            value={form.expiry}
            onChange={(e) => set("expiry", e.target.value)}
          >
            <option value="">All expiries</option>
            {[...new Set(contracts.map((row) => String(row.expiry)))]
              .sort()
              .map((expiry) => (
                <option key={expiry}>{expiry}</option>
              ))}
          </select>
        </Field>
        <label className="options-check">
          <input
            aria-label="Allow American approximation"
            type="checkbox"
            checked={form.american}
            onChange={(e) => set("american", e.target.checked)}
          />
          American BSM approximation
        </label>
        <Field label="Saved analyses">
          <select
            aria-label="Saved options analysis"
            value=""
            onChange={(e) => {
              const run = history.data?.items.find(
                (r) => r.id === e.target.value,
              );
              if (run) load(run);
            }}
          >
            <option value="">Select analysis</option>
            {history.data?.items
              .filter((run) => run.result.symbol === security)
              .map((run) => (
                <option key={run.id} value={run.id}>
                  {run.name} / {run.id.slice(0, 8)}
                </option>
              ))}
          </select>
        </Field>
        <button
          className="toolbar-button"
          onClick={() => open("/data-drop", "DATA DROP")}
        >
          Import chain
        </button>
      </div>
      <Kpis
        items={[
          { label: "Spot", value: number(current?.spot) },
          {
            label: "Net GEX / 1% move",
            value: number(current?.summary.net_gex),
          },
          { label: "DEX", value: number(current?.summary.dex) },
          { label: "GEX coverage", value: pct(current?.coverage.gex_fraction) },
          {
            label: "Missing contracts",
            value: number(current?.coverage.missing_gex, 0),
          },
          { label: "Gamma flip estimate", value: number(current?.gamma_flip) },
        ]}
      />
      <div className="toolbar" role="tablist" aria-label="Options views">
        {sections.map((key) => (
          <button
            key={key}
            role="tab"
            aria-selected={section === key}
            className={`toolbar-button ${section === key ? "active" : ""}`}
            onClick={() => setSection(key)}
          >
            {key}
          </button>
        ))}
      </div>
      {!current && (
        <Empty
          title="No saved analysis selected"
          detail={
            versions.data?.items.length
              ? "DATA REQUIRED"
              : "PROVIDER REQUIRED / IMPORT REQUIRED"
          }
        />
      )}
      {section === "CHAIN" && (
        <Panel
          title="Normalized option chain"
          {...source}
          rows={current?.items}
        >
          <DataTable
            id="options-chain"
            rows={current?.items ?? []}
            columns={chainColumns}
            onSelect={(row) => {
              setLegs([
                ...legs,
                {
                  option_symbol: String(row.option_symbol),
                  quantity: "1",
                  premium: "",
                },
              ]);
              setSection("PAYOFF");
            }}
          />
        </Panel>
      )}
      {section === "GEX" && (
        <>
          <Kpis
            items={[
              { label: "Call GEX", value: number(current?.summary.call_gex) },
              { label: "Put GEX", value: number(current?.summary.put_gex) },
              {
                label: "Call wall estimate",
                value: number(current?.summary.call_wall),
              },
              {
                label: "Put wall estimate",
                value: number(current?.summary.put_wall),
              },
              {
                label: "Largest contract share",
                value: pct(current?.summary.gamma_concentration),
              },
            ]}
          />
          <div className="performance-controls">
            {(
              [
                ["profileLow", "Spot profile low %"],
                ["profileHigh", "Spot profile high %"],
              ] as const
            ).map(([key, label]) => (
              <Field key={key} label={label}>
                <input
                  aria-label={label}
                  type="number"
                  value={form[key]}
                  onChange={(e) => set(key, e.target.value)}
                />
              </Field>
            ))}
          </div>
          <div className="page-grid">
            <Panel title="Gamma exposure by strike" {...source}>
              <Chart
                label="GEX by strike"
                option={chart(
                  current?.by_strike ?? [],
                  "strike",
                  ["call_gex", "put_gex", "net_gex"],
                  true,
                )}
              />
            </Panel>
            <Panel title="Fixed-IV spot-scenario gamma profile" {...source}>
              <Chart
                label="Gamma spot profile"
                option={chart(current?.spot_profile ?? [], "spot", [
                  "call_gex",
                  "put_gex",
                  "net_gex",
                ])}
              />
            </Panel>
            <Panel title="Gamma exposure by expiry" {...source}>
              <Chart
                label="GEX by expiry"
                option={chart(
                  current?.by_expiry ?? [],
                  "expiry",
                  ["call_gex", "put_gex"],
                  true,
                )}
              />
            </Panel>
            <Panel title="Exposure / coverage" {...source}>
              <DataTable
                id="gex-coverage"
                rows={current?.by_expiry ?? []}
                columns={[
                  { key: "expiry", label: "Expiry" },
                  ...numeric(["net_gex", "dex", "contracts", "included"]),
                ]}
              />
            </Panel>
          </div>
        </>
      )}
      {section === "GREEKS" && (
        <>
          <Panel title="Standard Greeks / per option unit" {...source}>
            <DataTable
              id="standard-greeks"
              rows={current?.items ?? []}
              columns={[
                { key: "option_symbol", label: "Contract", size: 250 },
                ...numeric(
                  [
                    "delta",
                    "gamma",
                    "theta",
                    "vega",
                    "rho",
                    "contract_gamma",
                    "dollar_gamma",
                  ],
                  6,
                ),
                { key: "greek_source", label: "Greek source", size: 150 },
                { key: "state", label: "State", size: 180 },
              ]}
            />
          </Panel>
          <Panel
            title="Advanced Greeks / numerical BSM sensitivities"
            {...source}
          >
            <DataTable
              id="advanced-greeks"
              rows={current?.items ?? []}
              columns={[
                { key: "option_symbol", label: "Contract", size: 250 },
                ...numeric(
                  [
                    "vanna",
                    "charm",
                    "vomma",
                    "speed",
                    "color",
                    "veta",
                    "zomma",
                    "ultima",
                  ],
                  6,
                ),
              ]}
            />
          </Panel>
          <Panel title="Greek units">
            <DataTable
              id="greek-units"
              rows={Object.entries(current?.greek_units ?? {}).map(
                ([greek, unit]) => ({ greek, unit }),
              )}
              columns={[
                { key: "greek", label: "Greek", size: 100 },
                { key: "unit", label: "Unit", size: 460 },
              ]}
            />
          </Panel>
        </>
      )}
      {section === "VOLATILITY" && (
        <>
          <Kpis
            items={[
              {
                label: "Put/call OI",
                value: number(current?.summary.put_call_oi),
              },
              {
                label: "Put/call volume",
                value: number(current?.summary.put_call_volume),
              },
              {
                label: "Profile contracts",
                value: number(current?.coverage.spot_profile_contracts, 0),
              },
            ]}
          />
          <div className="page-grid">
            <Panel title="Observed IV surface / no interpolation" {...source}>
              <Chart
                label="Implied volatility surface"
                option={{
                  tooltip: {
                    formatter: (value: unknown) => {
                      const row = (value as { value: number[] }).value;
                      return `Strike ${row[0]} / Days ${number(row[1])} / IV ${pct(row[2])}`;
                    },
                  },
                  xAxis: { type: "value", name: "Strike", scale: true },
                  yAxis: { type: "value", name: "Days", scale: true },
                  series: [
                    {
                      type: "scatter",
                      symbolSize: 12,
                      data: (current?.iv_surface ?? []).map((row) => [
                        Number(row.strike),
                        Number(row.days),
                        Number(row.iv),
                      ]),
                    },
                  ],
                  visualMap: {
                    show: false,
                    dimension: 2,
                    min: 0,
                    max: 1,
                    inRange: { color: ["#25B7E9", "#FFD400", "#FF4D4F"] },
                  },
                }}
              />
            </Panel>
            <Panel title="IV by strike / expiry" {...source}>
              <DataTable
                id="iv-surface"
                rows={current?.iv_surface ?? []}
                columns={[
                  { key: "expiry", label: "Expiry" },
                  { key: "right", label: "Side" },
                  ...numeric(["strike", "days"]),
                  { key: "iv", label: "IV", numeric: true, percent: true },
                ]}
              />
            </Panel>
            <Panel title="ATM IV move estimate" {...source}>
              <DataTable
                id="expected-move"
                rows={current?.expected_moves ?? []}
                columns={[
                  { key: "expiry", label: "Expiry" },
                  ...numeric(["atm_strike", "move"]),
                  { key: "iv", label: "IV", numeric: true, percent: true },
                ]}
              />
            </Panel>
            <Panel title="Nearest observed 25-delta skew" {...source}>
              <DataTable
                id="options-skew"
                rows={current?.skew ?? []}
                columns={[
                  { key: "expiry", label: "Expiry" },
                  ...numeric(["call_delta", "put_delta"], 4),
                  {
                    key: "risk_reversal",
                    label: "Risk reversal",
                    numeric: true,
                    percent: true,
                  },
                  {
                    key: "butterfly",
                    label: "Butterfly",
                    numeric: true,
                    percent: true,
                  },
                  { key: "state", label: "Coverage", size: 220 },
                ]}
              />
            </Panel>
            <Panel title="Open-interest settlement payout minimum" {...source}>
              <DataTable
                id="max-pain"
                rows={current?.max_pain ?? []}
                columns={[
                  { key: "expiry", label: "Expiry" },
                  ...numeric(["strike", "payout"]),
                  { key: "state", label: "State", size: 190 },
                ]}
              />
            </Panel>
          </div>
        </>
      )}
      {(section === "PAYOFF" || section === "POSITIONS") && (
        <>
          <div className="performance-controls">
            <Field label="Position source">
              <select
                aria-label="Options position source"
                value={form.portfolio}
                onChange={(e) => set("portfolio", e.target.value)}
              >
                <option value="">Hypothetical legs</option>
                {portfolios.data?.items.map((row) => (
                  <option key={String(row.id)} value={String(row.id)}>
                    {String(row.code)} / internal ledger
                  </option>
                ))}
              </select>
            </Field>
            <Badge>{current?.position_source ?? "HYPOTHETICAL"}</Badge>
            <button
              className="toolbar-button"
              title="Add hypothetical option leg"
              disabled={
                Boolean(form.portfolio) ||
                !contracts.length ||
                legs.length >= 20
              }
              onClick={() =>
                setLegs([
                  ...legs,
                  {
                    option_symbol: String(contracts[0].option_symbol),
                    quantity: "1",
                    premium: "",
                  },
                ])
              }
            >
              <Plus size={14} />
            </button>
          </div>
          {!form.portfolio &&
            legs.map((leg, index) => (
              <div className="options-leg" key={index}>
                <Field label="Contract">
                  <select
                    aria-label={`Leg ${index + 1} contract`}
                    value={leg.option_symbol}
                    onChange={(e) =>
                      setLegs(
                        legs.map((row, i) =>
                          i === index
                            ? { ...row, option_symbol: e.target.value }
                            : row,
                        ),
                      )
                    }
                  >
                    {contracts.map((row) => (
                      <option key={String(row.option_symbol)}>
                        {String(row.option_symbol)}
                      </option>
                    ))}
                  </select>
                </Field>
                <Field label="Signed contracts">
                  <input
                    aria-label={`Leg ${index + 1} quantity`}
                    type="number"
                    step="any"
                    value={leg.quantity}
                    onChange={(e) =>
                      setLegs(
                        legs.map((row, i) =>
                          i === index
                            ? { ...row, quantity: e.target.value }
                            : row,
                        ),
                      )
                    }
                  />
                </Field>
                <Field label="Entry premium / unit">
                  <input
                    aria-label={`Leg ${index + 1} premium`}
                    type="number"
                    step="any"
                    value={leg.premium}
                    onChange={(e) =>
                      setLegs(
                        legs.map((row, i) =>
                          i === index
                            ? { ...row, premium: e.target.value }
                            : row,
                        ),
                      )
                    }
                  />
                </Field>
                <button
                  className="toolbar-button"
                  title={`Remove leg ${index + 1}`}
                  onClick={() => setLegs(legs.filter((_, i) => i !== index))}
                >
                  <Trash2 size={14} />
                </button>
              </div>
            ))}
          <Kpis
            items={[
              {
                label: "Position delta",
                value: number(current?.positions.totals.delta, 4),
              },
              {
                label: "Position gamma",
                value: number(current?.positions.totals.gamma, 6),
              },
              {
                label: "Theta / day",
                value: number(current?.positions.totals.theta),
              },
              {
                label: "Vega / 1 vol point",
                value: number(current?.positions.totals.vega),
              },
              {
                label: "Dollar delta",
                value: number(current?.positions.totals.dollar_delta),
              },
            ]}
          />
          <div className="page-grid">
            <Panel title="Expiry payoff / selected quote currency" {...source}>
              <Chart
                label="Options expiry payoff"
                option={chart(current?.positions.payoff ?? [], "spot", ["pnl"])}
              />
            </Panel>
            <Panel title="Position Greeks / selected underlying" {...source}>
              <DataTable
                id="position-greeks"
                rows={current?.positions.items ?? []}
                columns={[
                  { key: "option_symbol", label: "Contract", size: 200 },
                  ...numeric(
                    [
                      "quantity",
                      "delta",
                      "gamma",
                      "theta",
                      "vega",
                      "rho",
                      "dollar_delta",
                      "gamma_1pct",
                    ],
                    4,
                  ),
                  { key: "state", label: "State", size: 180 },
                ]}
              />
            </Panel>
          </div>
          <div className="muted section-pad">
            {current?.positions.warnings.map((w) => <p key={w}>{w}</p>)}
          </div>
        </>
      )}
      {(calculate.error || demo.error || dataset.error) && (
        <p role="alert" className="negative section-pad">
          {String(calculate.error ?? demo.error ?? dataset.error)}
        </p>
      )}
      {current && (
        <div className="muted section-pad">
          <p>
            {String(current.coverage.confidence)} | {current.source} |{" "}
            {current.as_of}
          </p>
          <p>
            Run {current.id} | SHA256 {current.input_hash}
          </p>
          {current.warnings.map((w) => (
            <p key={w}>{w}</p>
          ))}
        </div>
      )}
    </div>
  );
}
