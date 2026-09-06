"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { knkApi } from "@knk/api-client";
import { Clock3, Scale, Table2 } from "lucide-react";
import { Badge, Field, number, pct, timestamp } from "../ui";
import { LedgerError, LedgerLoading } from "./dialog";
import { portfolioPath } from "./contracts";
import {
  exposureDimensions,
  type ExposureDimension,
  type ExposureSnapshot,
  type ExposureFreshness,
} from "./exposure-contracts";
import type { NumericValue } from "./position-contracts";

type View = "groups" | "freshness" | "balances";

function Freshness({ data, base }: { data: ExposureFreshness; base: string }) {
  const measures: [
    string,
    NumericValue | undefined,
    "amount" | "ratio" | "coverage" | "count",
  ][] = [
    [`Stale positions / ${base}`, data.stale_market_value, "amount"],
    [`Stale cash / ${base}`, data.stale_cash_value, "amount"],
    [`Stale balances / ${base}`, data.stale_balance_value, "amount"],
    [`Total stale value / ${base}`, data.stale_total_value, "amount"],
    ["Stale value / absolute NAV", data.stale_nav_pct, "ratio"],
    [
      `Known absolute marked value / ${base}`,
      data.known_marked_value,
      "amount",
    ],
    ["Position mark coverage", data.price_coverage_pct, "coverage"],
    ["Cash FX coverage", data.cash_fx_coverage_pct, "coverage"],
    ["Stale components", data.stale_items, "count"],
    ["Unavailable components", data.unavailable_items, "count"],
    ["Total components", data.item_count, "count"],
  ];
  return (
    <>
      <dl className="ledger-totals ledger-position-measures">
        {measures.map(([label, value, kind]) => (
          <div key={label}>
            <dt>{label}</dt>
            <dd>
              {kind === "ratio"
                ? pct(value)
                : kind === "coverage"
                  ? value == null
                    ? "--"
                    : `${number(value, 2)}%`
                  : number(value, kind === "count" ? 0 : 8)}
            </dd>
          </div>
        ))}
      </dl>
      {data.methodology && (
        <p className="ledger-methodology">{data.methodology}</p>
      )}
    </>
  );
}

export function ExposureInspector({
  portfolioKey,
  runId,
}: {
  portfolioKey: string;
  runId: string;
}) {
  const [dimension, setDimension] = useState<ExposureDimension>("currency");
  const [view, setView] = useState<View>("groups");
  const query = useQuery({
    queryKey: ["ledger-exposures", portfolioKey, runId],
    queryFn: ({ signal }) =>
      knkApi.get<ExposureSnapshot>(
        portfolioPath(portfolioKey) +
          "/exposures?" +
          new URLSearchParams({ run_id: runId }),
        signal,
      ),
  });
  const data = query.data;
  const rows = data?.groups[dimension] ?? [];
  return (
    <section aria-label="Portfolio exposure detail">
      <LedgerError error={query.error} />
      {query.isPending && <LedgerLoading />}
      {data && (
        <>
          <div className="ledger-toolbar">
            <div className="segmented" role="group" aria-label="Exposure view">
              <button
                aria-pressed={view === "groups"}
                onClick={() => setView("groups")}
              >
                <Table2 size={13} /> Groups
              </button>
              <button
                aria-pressed={view === "freshness"}
                onClick={() => setView("freshness")}
              >
                <Clock3 size={13} /> Freshness
              </button>
              <button
                aria-pressed={view === "balances"}
                onClick={() => setView("balances")}
              >
                <Scale size={13} /> Balance marks
              </button>
            </div>
            <Badge>{data.state}</Badge>
            <span className="ledger-position-context">
              {data.valuation_date} / {data.base_currency}
            </span>
          </div>
          {data.warnings.map((warning) => (
            <div role="status" className="ledger-error" key={warning}>
              {warning}
            </div>
          ))}
          {data.state === "INCOMPLETE" && (
            <div role="status" className="ledger-error">
              Incomplete marks; affected totals and NAV weights unavailable
            </div>
          )}
          {view === "groups" && (
            <>
              <div className="ledger-toolbar">
                <Field label="Exposure dimension">
                  <select
                    aria-label="Exposure dimension"
                    value={dimension}
                    onChange={(event) =>
                      setDimension(event.target.value as ExposureDimension)
                    }
                  >
                    {Object.entries(exposureDimensions).map(([key, label]) => (
                      <option key={key} value={key}>
                        {label}
                      </option>
                    ))}
                  </select>
                </Field>
                <dl className="ledger-totals ledger-exposure-nav">
                  <div>
                    <dt>NAV / {data.base_currency}</dt>
                    <dd>{number(data.nav, 8)}</dd>
                  </div>
                </dl>
              </div>
              {rows.length ? (
                <div className="ledger-table-scroll">
                  <table
                    className="ledger-table"
                    aria-label="Grouped portfolio exposures"
                  >
                    <thead>
                      <tr>
                        <th scope="col">{exposureDimensions[dimension]}</th>
                        <th scope="col">Net / {data.base_currency}</th>
                        <th scope="col">NAV weight</th>
                        <th scope="col">Long</th>
                        <th scope="col">Short</th>
                        <th scope="col">Cash</th>
                        <th scope="col">Balances</th>
                        <th scope="col">Gross</th>
                        <th scope="col">Gross / |NAV|</th>
                        <th scope="col">Known net</th>
                        <th scope="col">Missing</th>
                        <th scope="col">Stale</th>
                        <th scope="col">State</th>
                      </tr>
                    </thead>
                    <tbody>
                      {rows.map((row) => (
                        <tr key={row.name}>
                          <th scope="row">{row.name}</th>
                          <td>
                            {number(
                              data.state === "LEGACY_SNAPSHOT"
                                ? row.value
                                : row.net_value,
                              8,
                            )}
                          </td>
                          <td>{pct(row.weight)}</td>
                          <td>{number(row.long_value, 8)}</td>
                          <td>{number(row.short_value, 8)}</td>
                          <td>{number(row.cash_value, 8)}</td>
                          <td>{number(row.balance_value, 8)}</td>
                          <td>{number(row.gross_value, 8)}</td>
                          <td>{pct(row.gross_weight)}</td>
                          <td>{number(row.known_value, 8)}</td>
                          <td>{number(row.missing_count, 0)}</td>
                          <td>{number(row.stale_count, 0)}</td>
                          <td>
                            <Badge>{row.state ?? "NOT RECORDED"}</Badge>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div role="status" className="ledger-loading">
                  No {exposureDimensions[dimension].toLowerCase()} groups in
                  this valuation
                </div>
              )}
              {data.methodology && (
                <p className="ledger-methodology">{data.methodology}</p>
              )}
            </>
          )}
          {view === "freshness" &&
            (data.freshness ? (
              <Freshness data={data.freshness} base={data.base_currency} />
            ) : (
              <div role="status" className="ledger-loading">
                Freshness measurements not recorded
              </div>
            ))}
          {view === "balances" &&
            (data.balances.length ? (
              <div className="ledger-table-scroll">
                <table
                  className="ledger-table"
                  aria-label="Outstanding balance marks"
                >
                  <thead>
                    <tr>
                      <th scope="col">Bucket</th>
                      <th scope="col">CCY</th>
                      <th scope="col">Native amount</th>
                      <th scope="col">Signed / {data.base_currency}</th>
                      <th scope="col">FX</th>
                      <th scope="col">Source</th>
                      <th scope="col">Observed / SGT</th>
                      <th scope="col">State</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.balances.map((row) => (
                      <tr key={row.bucket + ":" + row.currency}>
                        <th scope="row">{row.bucket.replaceAll("_", " ")}</th>
                        <td>{row.currency}</td>
                        <td>{number(row.amount, 8)}</td>
                        <td>{number(row.base_value, 8)}</td>
                        <td>{number(row.fx_rate, 8)}</td>
                        <td>{row.fx_provenance.source}</td>
                        <td>{timestamp(row.fx_provenance.as_of)}</td>
                        <td>
                          <Badge>
                            {row.base_value === null
                              ? "UNAVAILABLE"
                              : row.fx_provenance.stale
                                ? "STALE"
                                : row.fx_provenance.data_state}
                          </Badge>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div role="status" className="ledger-loading">
                {data.state === "LEGACY_SNAPSHOT"
                  ? "Balance exposure components not recorded"
                  : "No outstanding manual balance adjustments"}
              </div>
            ))}
        </>
      )}
    </section>
  );
}
