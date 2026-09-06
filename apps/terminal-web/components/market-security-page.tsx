"use client";

import { useMemo } from "react";
import { PageTitle, useApi } from "./core-pages";
import { useTabState, useTerminal } from "./context";
import { Badge, Chart, DataTable, Field, Kpis, Panel, number, pct } from "./ui";
import type { Prices, Row } from "./types";

interface Snapshot extends Row {
  quote: Row;
  provenance: { source: string; as_of: string; data_state: string };
  mappings: Row[];
  warnings: string[];
}
export function MarketSecurityWorkspace({ route }: { route: string }) {
  const { security, open, bootstrap } = useTerminal();
  const kind = route.split("/")[1];
  const [range, setRange] = useTabState("security-range", 252);
  const [mode, setMode] = useTabState("security-chart-mode", "CANDLE");
  const [interval, setInterval] = useTabState("security-interval", "DAILY");
  const [comparison, setComparison] = useTabState("security-comparison", "");
  const prices = useApi<Prices>(
    "security-prices",
    `/api/v1/prices/${security}?limit=${range}`,
  );
  const compared = useApi<Prices>(
    "security-comparison",
    `/api/v1/prices/${comparison || security}?limit=${range}`,
    Boolean(comparison),
  );
  const snapshot = useApi<Snapshot>(
    "equity-snapshot",
    `/api/v1/equity/${security}/snapshot`,
  );
  const data = snapshot.data;
  const rows = useMemo(() => {
    const input = (prices.data?.items ?? []).filter(
      (r) =>
        !r.as_of ||
        String(r.as_of).slice(0, 10) === String(r.date).slice(0, 10),
    );
    if (interval === "DAILY") return input;
    const buckets = new Map<string, Row>();
    for (const row of input) {
      const date = new Date(`${String(row.date).slice(0, 10)}T00:00:00Z`);
      if (interval === "WEEKLY")
        date.setUTCDate(date.getUTCDate() - ((date.getUTCDay() + 6) % 7));
      const key =
        interval === "WEEKLY"
          ? date.toISOString().slice(0, 10)
          : String(row.date).slice(0, 7);
      const old = buckets.get(key);
      if (old) {
        old.high = Math.max(Number(old.high), Number(row.high));
        old.low = Math.min(Number(old.low), Number(row.low));
        old.close = row.close;
        old.volume =
          old.volume == null || row.volume == null
            ? null
            : Number(old.volume) + Number(row.volume);
      } else buckets.set(key, { ...row, date: key });
    }
    return [...buckets.values()];
  }, [prices.data, interval]);
  const other = new Map(
    (compared.data?.items ?? []).map((r) => [String(r.date), Number(r.close)]),
  );
  const aligned = rows.filter((r) => other.has(String(r.date)));
  const pairFirst = aligned[0];
  const primaryFirst = pairFirst ? Number(pairFirst.close) : null;
  const otherFirst = pairFirst ? other.get(String(pairFirst.date)) : null;
  const quote = data?.quote;
  return (
    <div className="research-page equity-workspace">
      <PageTitle
        code={
          kind === "security"
            ? "DES"
            : kind === "quote"
              ? "Q"
              : kind === "technicals"
                ? "TECH"
                : "GP"
        }
        title={`${security} / ${String(data?.name ?? "Security")}`}
      >
        <Badge>{data?.provenance.data_state ?? "LOADING"}</Badge>
      </PageTitle>
      <div className="toolbar">
        {[
          ["DES", "security"],
          ["Q", "quote"],
          ["GP", "chart"],
          ["TECH", "technicals"],
          ["FIN", "financials"],
          ["VAL", "valuation"],
          ["DCF", "dcf"],
          ["COMP", "comparables"],
        ].map(([code, path]) => (
          <button
            key={code}
            className="toolbar-button"
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
          className="toolbar-button"
          onClick={() => open("/thesis", `${security} THESIS`, false, security)}
        >
          THESIS
        </button>
      </div>
      <Kpis
        items={[
          { label: "Last", value: number(quote?.last) },
          { label: "Previous close", value: number(quote?.previous_close) },
          { label: "Bid", value: number(quote?.bid) },
          { label: "Ask", value: number(quote?.ask) },
          { label: "Volume", value: number(quote?.volume, 0) },
          { label: "VWAP", value: number(quote?.vwap) },
        ]}
      />
      <div className="performance-controls">
        <Field label="Range">
          <select
            aria-label="Security chart range"
            value={range}
            onChange={(e) => setRange(Number(e.target.value))}
          >
            {[
              [1, "1D"],
              [5, "1W"],
              [21, "1M"],
              [63, "3M"],
              [126, "6M"],
              [252, "1Y"],
              [1260, "5Y"],
              [2600, "MAX"],
            ].map(([v, label]) => (
              <option key={v} value={v}>
                {label}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Chart">
          <select
            aria-label="Security chart type"
            value={mode}
            onChange={(e) => setMode(e.target.value)}
          >
            {["CANDLE", "LINE", "AREA"].map((v) => (
              <option key={v}>{v}</option>
            ))}
          </select>
        </Field>
        <Field label="Interval">
          <select
            aria-label="Security chart interval"
            value={interval}
            onChange={(e) => {
              setInterval(e.target.value);
              setComparison("");
            }}
          >
            {["DAILY", "WEEKLY", "MONTHLY"].map((v) => (
              <option key={v}>{v}</option>
            ))}
          </select>
        </Field>
        <Field label="Comparison / daily return">
          <select
            aria-label="Security comparison"
            value={comparison}
            disabled={interval !== "DAILY"}
            onChange={(e) => setComparison(e.target.value)}
          >
            <option value="">None</option>
            {bootstrap.quotes
              .filter((q) => q.symbol !== security)
              .map((q) => (
                <option key={q.symbol}>{q.symbol}</option>
              ))}
          </select>
        </Field>
      </div>
      <div className="page-grid">
        <Panel
          className="wide-panel"
          title={`${security} / observed OHLC`}
          source={prices.data?.source}
          quality={prices.data?.quality}
          asOf={prices.data?.as_of}
          rows={rows}
        >
          <Chart
            label="Security price chart"
            option={{
              xAxis: {
                type: "category",
                data: (comparison ? aligned : rows).map((r) => String(r.date)),
              },
              dataZoom: [{ type: "inside" }],
              legend: { show: true, top: 0 },
              series: comparison
                ? [
                    {
                      name: security,
                      type: "line",
                      symbol: "none",
                      data: aligned.map((r) =>
                        primaryFirst
                          ? 100 * (Number(r.close) / primaryFirst - 1)
                          : null,
                      ),
                    },
                    {
                      name: comparison,
                      type: "line",
                      symbol: "none",
                      data: aligned.map((r) =>
                        otherFirst
                          ? 100 * (other.get(String(r.date))! / otherFirst - 1)
                          : null,
                      ),
                    },
                  ]
                : mode === "CANDLE"
                  ? [
                      {
                        type: "candlestick",
                        data: rows.map((r) => [
                          Number(r.open),
                          Number(r.close),
                          Number(r.low),
                          Number(r.high),
                        ]),
                        itemStyle: {
                          color: "#00C875",
                          color0: "#FF4D4F",
                          borderColor: "#00C875",
                          borderColor0: "#FF4D4F",
                        },
                      },
                    ]
                  : [
                      {
                        type: "line",
                        name: security,
                        symbol: "none",
                        areaStyle:
                          mode === "AREA" ? { opacity: 0.15 } : undefined,
                        data: rows.map((r) => Number(r.close)),
                      },
                    ],
            }}
          />
        </Panel>
        <Panel
          title="Security reference"
          source={data?.provenance.source}
          asOf={data?.provenance.as_of}
          quality={data?.provenance.data_state}
        >
          <div className="section-pad">
            <dl className="detail-list">
              {[
                "sector",
                "industry",
                "country",
                "currency",
                "asset_class",
                "market_cap",
                "enterprise_value",
                "shares",
                "float",
                "figi",
                "isin",
                "fifty_two_week_low",
                "fifty_two_week_high",
              ].map((key) => (
                <span key={key} style={{ display: "contents" }}>
                  <dt>{key.replaceAll("_", " ")}</dt>
                  <dd>
                    {data?.[key] == null
                      ? "Unavailable"
                      : typeof data[key] === "number"
                        ? number(data[key])
                        : String(data[key])}
                  </dd>
                </span>
              ))}
            </dl>
          </div>
        </Panel>
        <Panel
          title="Observed quote fields"
          source={data?.provenance.source}
          quality={data?.provenance.data_state}
        >
          <DataTable
            id="security-quote-fields"
            rows={Object.entries(quote ?? {}).map(([field, value]) => ({
              field,
              value,
            }))}
            columns={[
              { key: "field", label: "Field" },
              { key: "value", label: "Value", numeric: true },
            ]}
          />
        </Panel>
      </div>
      <Panel
        title="OHLCV history"
        rows={[...rows].reverse()}
        source={prices.data?.source}
        quality={prices.data?.quality}
      >
        <DataTable
          id="price-history"
          rows={[...rows].reverse()}
          columns={[
            { key: "date", label: "Date", size: 110 },
            ...["open", "high", "low", "close", "volume"].map((key) => ({
              key,
              label: key.toUpperCase(),
              numeric: true,
            })),
          ]}
        />
      </Panel>
      {kind === "technicals" && (
        <Panel title="Moving averages / selected interval">
          <Chart
            label="Security moving averages"
            option={{
              legend: { top: 0 },
              xAxis: {
                type: "category",
                data: rows.map((r) => String(r.date)),
              },
              series: [20, 50].map((window) => ({
                name: `SMA ${window}`,
                type: "line",
                symbol: "none",
                data: rows.map((_, i) =>
                  i + 1 < window
                    ? null
                    : rows
                        .slice(i + 1 - window, i + 1)
                        .reduce((sum, r) => sum + Number(r.close), 0) / window,
                ),
              })),
            }}
          />
        </Panel>
      )}
      {kind === "technicals" && (
        <Panel title="Historical close changes">
          <Chart
            label="Historical security returns"
            option={{
              xAxis: {
                type: "category",
                data: rows.slice(1).map((r) => String(r.date)),
              },
              yAxis: {
                type: "value",
                axisLabel: { formatter: (v: number) => pct(v) },
              },
              series: [
                {
                  type: "bar",
                  data: rows
                    .slice(1)
                    .map((r, i) => Number(r.close) / Number(rows[i].close) - 1),
                },
              ],
            }}
          />
        </Panel>
      )}
      {data?.mappings.length ? (
        <Panel title="Provider mappings">
          <DataTable
            id="security-mappings"
            rows={data.mappings}
            columns={[
              { key: "provider", label: "Provider" },
              { key: "symbol", label: "Provider symbol" },
            ]}
          />
        </Panel>
      ) : null}
      <div className="section-pad muted">
        {data?.warnings.map((w) => <p key={w}>{w}</p>)}
        <p>
          Intraday bars, event overlays and exchange-session status require
          connected market data. Aggregated weekly/monthly periods can be
          partial.
        </p>
      </div>
      {(snapshot.error || prices.error) && (
        <p role="alert" className="negative">
          {String(snapshot.error ?? prices.error)}
        </p>
      )}
    </div>
  );
}
