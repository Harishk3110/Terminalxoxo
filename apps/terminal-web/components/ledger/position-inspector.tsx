"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { knkApi } from "@knk/api-client";
import { Activity, Database, Layers, Scale } from "lucide-react";
import { Badge, Field, number, pct, timestamp } from "../ui";
import { LedgerError, LedgerLoading } from "./dialog";
import { portfolioPath } from "./contracts";
import type {
  MarkProvenance,
  NumericValue,
  PositionSnapshot,
} from "./position-contracts";

type View = "valuation" | "daily" | "sources" | "lots";
type Measure = [
  string,
  NumericValue | undefined,
  "amount" | "percent" | "ratio",
];

function Measures({ items }: { items: Measure[] }) {
  return (
    <dl className="ledger-totals ledger-position-measures">
      {items.map(([label, value, kind]) => (
        <div key={label}>
          <dt>{label}</dt>
          <dd>
            {kind === "percent"
              ? pct(value)
              : number(value, kind === "ratio" ? 6 : 8)}
          </dd>
        </div>
      ))}
    </dl>
  );
}

function Provenance({ label, data }: { label: string; data: MarkProvenance }) {
  return (
    <section
      className="ledger-position-source"
      aria-label={label + " provenance"}
    >
      <h3>
        {label} <Badge>{data.data_state}</Badge>
      </h3>
      <dl className="ledger-totals ledger-audit-fields">
        <div>
          <dt>Source</dt>
          <dd>{data.source}</dd>
        </div>
        <div>
          <dt>Observed / SGT</dt>
          <dd>{timestamp(data.as_of)}</dd>
        </div>
        <div>
          <dt>Value</dt>
          <dd>{number(data.value, 8)}</dd>
        </div>
        <div>
          <dt>Source category</dt>
          <dd>{data.source_category ?? "Not recorded"}</dd>
        </div>
        <div>
          <dt>Observation</dt>
          <dd>{data.observation_id ?? "Not recorded"}</dd>
        </div>
        <div>
          <dt>Age / hours</dt>
          <dd>{number(data.age_hours, 2)}</dd>
        </div>
        <div>
          <dt>Source file</dt>
          <dd>{data.source_file_id ?? "Not recorded"}</dd>
        </div>
        <div>
          <dt>Dataset version</dt>
          <dd>{data.dataset_version_id ?? "Not recorded"}</dd>
        </div>
        <div>
          <dt>Ingested / SGT</dt>
          <dd>{timestamp(data.ingested_at)}</dd>
        </div>
        <div>
          <dt>Adjustment state</dt>
          <dd>{data.adjustment_state ?? "Not recorded"}</dd>
        </div>
      </dl>
      {data.inverse && <Badge>INVERSE FX</Badge>}
      {data.conflict && (
        <div className="ledger-error" role="status">
          Material same-date source conflict
        </div>
      )}
      {data.stale && (
        <div className="ledger-error" role="status">
          Selected mark is stale
        </div>
      )}
    </section>
  );
}

export function PositionInspector({
  portfolioKey,
  runId,
  positions,
}: {
  portfolioKey: string;
  runId: string;
  positions: { instrument_id: string; symbol: string }[];
}) {
  const [selected, setSelected] = useState("");
  const [view, setView] = useState<View>("valuation");
  const instrument =
    positions.find((item) => item.instrument_id === selected)?.instrument_id ??
    positions[0]?.instrument_id ??
    "";
  const query = useQuery({
    queryKey: ["ledger-position", portfolioKey, runId, instrument],
    queryFn: ({ signal }) =>
      knkApi.get<PositionSnapshot>(
        portfolioPath(portfolioKey) +
          "/positions/" +
          encodeURIComponent(instrument) +
          "?" +
          new URLSearchParams({ run_id: runId }),
        signal,
      ),
    enabled: !!instrument,
  });
  if (!positions.length)
    return (
      <div className="ledger-loading">No open positions in this valuation</div>
    );
  const position = query.data;
  const base = position?.base_currency ?? "Base";
  const native = position?.currency ?? "Native";
  const daily = position?.daily_pnl_details;
  return (
    <section
      aria-label="Position accounting detail"
      className="ledger-position-inspector"
    >
      <div className="ledger-toolbar">
        <Field label="Position">
          <select
            aria-label="Position"
            value={instrument}
            onChange={(event) => setSelected(event.target.value)}
          >
            {positions.map((item) => (
              <option key={item.instrument_id} value={item.instrument_id}>
                {item.symbol}
              </option>
            ))}
          </select>
        </Field>
        <div
          className="segmented"
          role="group"
          aria-label="Position detail view"
        >
          <button
            aria-pressed={view === "valuation"}
            onClick={() => setView("valuation")}
          >
            <Scale size={13} /> Valuation
          </button>
          <button
            aria-pressed={view === "daily"}
            onClick={() => setView("daily")}
          >
            <Activity size={13} /> Day P&amp;L
          </button>
          <button
            aria-pressed={view === "sources"}
            onClick={() => setView("sources")}
          >
            <Database size={13} /> Sources
          </button>
          <button
            aria-pressed={view === "lots"}
            onClick={() => setView("lots")}
          >
            <Layers size={13} /> Open lots
          </button>
        </div>
      </div>
      <LedgerError error={query.error} />
      {!position && !query.error && <LedgerLoading />}
      {position && (
        <>
          <div className="ledger-position-heading">
            <strong>
              {position.symbol} / {position.name}
            </strong>
            <Badge>{position.direction ?? "SIDE NOT RECORDED"}</Badge>
            <Badge>{position.quality}</Badge>
          </div>
          <div className="ledger-position-context">
            {position.valuation_date} | {position.sector} |{" "}
            {position.country ?? "Country not recorded"} |{" "}
            {position.asset_class}
          </div>
          {position.measurement_state === "LEGACY_SNAPSHOT" && (
            <div className="ledger-error" role="status">
              Detailed native values and price/FX components were not recorded
              in this valuation.
            </div>
          )}
          {view === "valuation" && (
            <>
              <Measures
                items={[
                  ["Quantity", position.quantity, "amount"],
                  [
                    "Contract multiplier",
                    position.contract_multiplier,
                    "ratio",
                  ],
                  ["FX / " + native + " to " + base, position.fx_rate, "ratio"],
                  ["Price / " + native, position.market_price, "amount"],
                  ["Average cost / " + native, position.average_cost, "amount"],
                  [
                    "Native cost basis / " + native,
                    position.cost_basis_native,
                    "amount",
                  ],
                  [
                    "Native market value / " + native,
                    position.market_value_native,
                    "amount",
                  ],
                  [
                    "Base market value / " + base,
                    position.market_value_base_exact === undefined
                      ? position.market_value
                      : position.market_value_base_exact,
                    "amount",
                  ],
                  [
                    "Base cost basis / " + base,
                    position.cost_basis_base,
                    "amount",
                  ],
                  ["Unrealised / " + base, position.unrealised_pnl, "amount"],
                  [
                    "Price component / " + base,
                    position.unrealised_price_pnl_base,
                    "amount",
                  ],
                  [
                    "FX component / " + base,
                    position.unrealised_fx_pnl_base,
                    "amount",
                  ],
                  ["Realised / " + base, position.realised_pnl, "amount"],
                  ["Income / " + base, position.income, "amount"],
                  ["Total P&L / " + base, position.total_pnl, "amount"],
                  [
                    "NAV weight",
                    position.nav_weight === undefined
                      ? position.weight
                      : position.nav_weight,
                    "percent",
                  ],
                  ["Sector NAV weight", position.sector_weight, "percent"],
                  ["Beta", position.beta, "ratio"],
                  ["Beta contribution", position.beta_contribution, "ratio"],
                  [
                    "Variance contribution",
                    position.risk_contribution,
                    "percent",
                  ],
                  [
                    "Expensed charges / " + base,
                    position.expensed_charges,
                    "amount",
                  ],
                ]}
              />
              {position.unrealised_decomposition_method && (
                <dl className="ledger-methodology">
                  <dt>Unrealised decomposition</dt>
                  <dd>{position.unrealised_decomposition_method}</dd>
                </dl>
              )}
              {position.valuation_warnings?.map((warning) => (
                <div role="status" className="ledger-error" key={warning}>
                  {warning}
                </div>
              ))}
            </>
          )}
          {view === "daily" &&
            (daily ? (
              <>
                <div className="ledger-toolbar">
                  <Badge>{daily.state}</Badge>
                  <span>{base}</span>
                </div>
                <Measures
                  items={[
                    ["Opening marked value", daily.opening_value, "amount"],
                    ["Closing marked value", daily.closing_value, "amount"],
                    ["Recorded economic cash", daily.economic_cash, "amount"],
                    [
                      "External security capital",
                      daily.external_security_flow,
                      "amount",
                    ],
                    [
                      "Internal corporate transfer",
                      daily.internal_transfer,
                      "amount",
                    ],
                    ["Position P&L", daily.pnl, "amount"],
                  ]}
                />
                <dl className="ledger-methodology">
                  <dt>Period methodology</dt>
                  <dd>{daily.methodology}</dd>
                </dl>
                {daily.warnings.map((warning) => (
                  <div role="status" className="ledger-error" key={warning}>
                    {warning}
                  </div>
                ))}
              </>
            ) : (
              <div className="ledger-loading">
                Daily component breakdown not recorded in this valuation
              </div>
            ))}
          {view === "sources" && (
            <>
              <Provenance label="Price" data={position.price_provenance} />
              <Provenance label="FX" data={position.fx_provenance} />
            </>
          )}
          {view === "lots" && (
            <div className="ledger-table-scroll">
              <table
                className="ledger-table"
                aria-label="Selected position lots"
              >
                <thead>
                  <tr>
                    <th scope="col">Acquired</th>
                    <th scope="col">Side</th>
                    <th scope="col">Quantity</th>
                    <th scope="col">Native basis</th>
                    <th scope="col">Base basis</th>
                    <th scope="col">Opening transaction</th>
                  </tr>
                </thead>
                <tbody>
                  {position.lots
                    .filter((lot) => Number(lot.quantity) !== 0)
                    .map((lot) => (
                      <tr key={lot.id}>
                        <th scope="row">{lot.opened}</th>
                        <td>{lot.direction}</td>
                        <td>{number(lot.quantity, 8)}</td>
                        <td>{number(lot.native_basis, 8)}</td>
                        <td>{number(lot.base_basis, 8)}</td>
                        <td>{lot.entry_id}</td>
                      </tr>
                    ))}
                </tbody>
              </table>
              {position.measurement_state === "LEGACY_SNAPSHOT" &&
                !position.lots.length && (
                  <div className="ledger-loading">
                    Lot snapshot not recorded
                  </div>
                )}
            </div>
          )}
          <div className="ledger-position-context">
            {position.accounting_policy?.method ?? "Cost policy not recorded"} |{" "}
            {position.calculation_version} | {timestamp(position.calculated_at)}
          </div>
        </>
      )}
    </section>
  );
}
