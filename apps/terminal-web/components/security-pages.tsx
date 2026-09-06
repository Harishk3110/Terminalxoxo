"use client";
import { useMemo } from "react";
import { useQueries } from "@tanstack/react-query";
import { knkApi } from "@knk/api-client";
import { Star } from "lucide-react";
import { records, useTabState, useTerminal } from "./context";
import {
  Badge,
  Chart,
  COLORS,
  DataTable,
  Empty,
  Field,
  Kpis,
  LineChart,
  Panel,
  number,
  pct,
  tone,
  type Column,
} from "./ui";
import { PageTitle, useApi } from "./core-pages";
import type { Financials, Prices, Row } from "./types";

export function MarketPage({ route }: { route: string }) {
  const { bootstrap, open, selectSecurity, config, setConfig } = useTerminal();
  const watch = route === "/watchlists";
  const quotes = watch
    ? bootstrap.quotes.filter((q) =>
        (config.watchlist ?? ["AAPL", "MSFT", "NVDA", "SPY", "D05"]).includes(
          q.symbol,
        ),
      )
    : bootstrap.quotes;
  return (
    <>
      <PageTitle
        code={watch ? "WATCH" : "SCREEN"}
        title={
          watch
            ? "Watchlist / Link Group 1"
            : "Security Master / Market Monitor"
        }
      >
        <Badge>DEMO DATA</Badge>
      </PageTitle>
      <Panel
        className="page-grid"
        title="Stored security universe"
        source="DemoProvider / security master"
        asOf={quotes[0]?.as_of}
        quality="DEMO DATA"
        rows={records(quotes)}
      >
        {route === "/heatmap" ? (
          <div className="coverage-grid">
            {quotes.map((q) => (
              <button
                key={q.id}
                className="market-tile"
                onClick={() => {
                  selectSecurity(q.symbol);
                  open(
                    `/security/${q.symbol}`,
                    `${q.symbol} DES`,
                    false,
                    q.symbol,
                  );
                }}
              >
                <strong className="mono">{q.symbol}</strong>
                <span className={tone(q.change_pct)}>{pct(q.change_pct)}</span>
                <span className="muted">{q.sector}</span>
              </button>
            ))}
          </div>
        ) : (
          <DataTable
            id="security-master"
            rows={records(quotes)}
            columns={[
              { key: "symbol", label: "Security", size: 90 },
              { key: "name", label: "Name", size: 220 },
              { key: "price", label: "Last", numeric: true, size: 95 },
              {
                key: "change_pct",
                label: "Change",
                numeric: true,
                percent: true,
                size: 95,
              },
              { key: "exchange", label: "Exchange", size: 90 },
              { key: "currency", label: "CCY", size: 65 },
              { key: "asset_class", label: "Asset", size: 90 },
              { key: "sector", label: "Sector", size: 180 },
              { key: "source", label: "Source", size: 110 },
              {
                key: "quality",
                label: "State",
                size: 110,
                format: (v) => <Badge>{String(v)}</Badge>,
              },
            ]}
            onSelect={(row) => {
              selectSecurity(String(row.symbol));
              open(
                `/security/${row.symbol}`,
                `${row.symbol} DES`,
                false,
                String(row.symbol),
              );
            }}
          />
        )}
      </Panel>
    </>
  );
}

export function SecurityPage({ route }: { route: string }) {
  const { bootstrap, security, config, setConfig, open } = useTerminal();
  const quote = bootstrap.quotes.find((q) => q.symbol === security);
  const kind = route.split("/")[1];
  const [range, setRange] = useTabState("price-range", 252);
  const prices = useApi<Prices>(
    "prices",
    `/api/v1/prices/${security}?limit=${range}`,
  );
  const financial = useApi<Financials>(
    "fundamentals",
    `/api/v1/fundamentals/${security}`,
    ["financials", "valuation", "dcf", "wacc", "comparables"].includes(kind),
  );
  const [growth, setGrowth] = useTabState("dcf-growth", 8);
  const [wacc, setWacc] = useTabState("dcf-wacc", 10);
  const [terminal, setTerminal] = useTabState("dcf-terminal", 2.5);
  const dcf = useApi<Financials>(
    "valuation",
    `/api/v1/valuation/${security}?growth=${growth / 100}&wacc=${wacc / 100}&terminal_growth=${terminal / 100}`,
    ["valuation", "dcf", "wacc"].includes(kind),
  );
  const comps = useQueries({
    queries: config.securities.map((symbol) => ({
      queryKey: ["comparables", symbol],
      enabled: kind === "comparables",
      queryFn: ({ signal }: { signal: AbortSignal }) =>
        knkApi.get<Financials>(`/api/v1/fundamentals/${symbol}`, signal),
    })),
  });
  const fn = bootstrap.functions.find((f) => f.route.split("/")[1] === kind);
  const data = financial.data;
  const columns: Column[] = [
    { key: "metric", label: "USD millions / except shares", size: 210 },
    ...(data?.items ?? []).map((row) => ({
      key: String(row.year),
      label: String(row.year),
      numeric: true,
      size: 125,
    })),
  ];
  const statementRows = data?.items.length
    ? Object.keys(data.items[0])
        .filter((k) => k !== "year")
        .map((metric) => ({
          metric: metric.replaceAll("_", " "),
          ...Object.fromEntries(
            data.items.map((r) => [String(r.year), r[metric]]),
          ),
        }))
    : [];
  const watched = (config.watchlist ?? []).includes(security);
  const priceRows = useMemo(() => prices.data?.items ?? [], [prices.data]);
  const technicalRows = useMemo(
    () =>
      priceRows.map((row, index) => ({
        ...row,
        sma20:
          index >= 19
            ? priceRows
                .slice(index - 19, index + 1)
                .reduce((sum, r) => sum + r.close, 0) / 20
            : null,
        sma50:
          index >= 49
            ? priceRows
                .slice(index - 49, index + 1)
                .reduce((sum, r) => sum + r.close, 0) / 50
            : null,
      })),
    [priceRows],
  );
  return (
    <>
      <PageTitle
        code={fn?.mnemonic ?? "DES"}
        title={`${security} / ${fn?.name ?? "Security"}`}
      >
        <button
          onClick={() =>
            setConfig((c) => ({
              ...c,
              watchlist: watched
                ? (c.watchlist ?? []).filter((s) => s !== security)
                : [...(c.watchlist ?? []), security],
            }))
          }
        >
          <Star size={12} />
          {watched ? "Watching" : "Watchlist"}
        </button>
        <Badge>{quote?.quality ?? "UNAVAILABLE"}</Badge>
      </PageTitle>
      <div className="segmented">
        {[
          "DES",
          "Q",
          "GP",
          "TECH",
          "FIN",
          "VAL",
          "DCF",
          "COMP",
          "NEWS",
          "OPT",
        ].map((code) => {
          const f = bootstrap.functions.find((f) => f.mnemonic === code)!;
          return (
            <button
              key={code}
              className={fn?.mnemonic === code ? "active" : ""}
              onClick={() =>
                open(
                  f.route.replace("{instrumentId}", security),
                  `${security} ${code}`,
                  false,
                  security,
                )
              }
            >
              {code}
            </button>
          );
        })}
      </div>
      {kind === "financials" ? (
        <>
          <Kpis
            source={data?.source}
            asOf={data?.as_of}
            items={[
              {
                label: "Revenue / MM",
                value: number(data?.items.at(-1)?.revenue),
              },
              {
                label: "Operating income / MM",
                value: number(data?.items.at(-1)?.ebit),
              },
              {
                label: "Net income / MM",
                value: number(data?.items.at(-1)?.net_income),
              },
              {
                label: "Free cash flow / MM",
                value: number(data?.items.at(-1)?.free_cash_flow),
              },
            ]}
          />
          <Panel
            className="page-grid"
            title="Annual financial statements / synthetic demonstration"
            source={data?.source}
            asOf={data?.as_of}
            quality={data?.quality}
            error={financial.error}
            loading={financial.isLoading}
            rows={statementRows}
          >
            <DataTable
              id="financial-statements"
              rows={statementRows}
              columns={columns}
            />
          </Panel>
        </>
      ) : ["valuation", "dcf", "wacc"].includes(kind) ? (
        <>
          <div className="control-row">
            <Field label="FCF growth (%)">
              <input
                className="assumption"
                aria-label="DCF growth"
                type="number"
                step=".5"
                value={growth}
                onChange={(e) => setGrowth(Number(e.target.value))}
              />
            </Field>
            <Field label="WACC (%)">
              <input
                className="assumption"
                aria-label="DCF WACC"
                type="number"
                step=".5"
                value={wacc}
                onChange={(e) => setWacc(Number(e.target.value))}
              />
            </Field>
            <Field label="Terminal growth (%)">
              <input
                className="assumption"
                aria-label="DCF terminal growth"
                type="number"
                step=".25"
                value={terminal}
                onChange={(e) => setTerminal(Number(e.target.value))}
              />
            </Field>
            <Badge>CALCULATED</Badge>
          </div>
          <Kpis
            source={dcf.data?.source}
            asOf={dcf.data?.as_of}
            items={[
              {
                label: "Fair value / share",
                value: number(dcf.data?.fair_value),
              },
              {
                label: "Enterprise value / MM",
                value: number(dcf.data?.enterprise_value),
              },
              {
                label: "Equity value / MM",
                value: number(dcf.data?.equity_value),
              },
              { label: "Last demo quote", value: number(quote?.price) },
            ]}
          />
          <div className="page-grid" style={{ gridTemplateRows: "1fr 1fr" }}>
            <Panel
              title="Discounted free cash flow / five years"
              source={dcf.data?.source}
              asOf={dcf.data?.as_of}
              quality={dcf.data?.quality}
              error={dcf.error}
            >
              <Chart
                label="DCF forecast"
                option={{
                  xAxis: {
                    type: "category",
                    data: dcf.data?.forecast?.map((r) => String(r.year)),
                  },
                  yAxis: {
                    type: "value",
                    splitLine: { lineStyle: { color: COLORS.grid } },
                  },
                  series: [
                    {
                      name: "FCF",
                      type: "bar",
                      data: dcf.data?.forecast?.map((r) => Number(r.fcf)),
                    },
                    {
                      name: "Present value",
                      type: "bar",
                      data: dcf.data?.forecast?.map((r) => Number(r.pv)),
                    },
                  ],
                }}
              />
            </Panel>
            <Panel
              title="Forecast / editable assumptions"
              source={dcf.data?.source}
              asOf={dcf.data?.as_of}
              quality={dcf.data?.quality}
            >
              <DataTable
                id="dcf-forecast"
                rows={dcf.data?.forecast ?? []}
                columns={[
                  { key: "year", label: "Year" },
                  { key: "fcf", label: "Free cash flow", numeric: true },
                  { key: "pv", label: "Present value", numeric: true },
                ]}
              />
            </Panel>
          </div>
        </>
      ) : kind === "comparables" ? (
        <Panel
          className="page-grid"
          title="Selected security comparison"
          source="DemoProvider synthetic financials"
          asOf={data?.as_of}
          quality="DEMO DATA"
        >
          <DataTable
            id="comparables"
            rows={comps.flatMap((c, i) => {
              const f = c.data?.items.at(-1);
              const q = bootstrap.quotes.find(
                (q) => q.symbol === config.securities[i],
              );
              return f && q
                ? [
                    {
                      symbol: q.symbol,
                      price: q.price,
                      pe: q.price / (Number(f.net_income) / Number(f.shares)),
                      fcf_yield:
                        Number(f.free_cash_flow) / (q.price * Number(f.shares)),
                      net_margin: Number(f.net_income) / Number(f.revenue),
                      source: c.data?.source,
                    },
                  ]
                : [];
            })}
            columns={[
              { key: "symbol", label: "Security" },
              { key: "price", label: "Price", numeric: true },
              { key: "pe", label: "P/E", numeric: true },
              {
                key: "fcf_yield",
                label: "FCF yield",
                numeric: true,
                percent: true,
              },
              {
                key: "net_margin",
                label: "Net margin",
                numeric: true,
                percent: true,
              },
              { key: "source", label: "Source", size: 240 },
            ]}
          />
        </Panel>
      ) : (
        <div className="page-grid analytics-grid">
          <Panel
            className={
              kind === "chart" || kind === "technicals" ? "wide-panel" : ""
            }
            title={`${security} / daily prices`}
            source={prices.data?.source}
            asOf={prices.data?.as_of}
            quality={prices.data?.quality}
            error={prices.error}
            loading={prices.isLoading}
            rows={records(priceRows)}
          >
            <div className="control-row">
              {[
                [63, "3M"],
                [126, "6M"],
                [252, "1Y"],
                [1260, "5Y"],
                [2600, "MAX"],
              ].map(([r, l]) => (
                <button
                  key={r}
                  className={range === r ? "amber" : ""}
                  onClick={() => setRange(Number(r))}
                >
                  {l}
                </button>
              ))}
            </div>
            <LineChart
              label={`${security} price history`}
              rows={records(kind === "technicals" ? technicalRows : priceRows)}
              keys={
                kind === "technicals"
                  ? [
                      { key: "close", name: `${security} close` },
                      { key: "sma20", name: "SMA 20", color: COLORS.blue },
                      { key: "sma50", name: "SMA 50", color: COLORS.purple },
                    ]
                  : [{ key: "close", name: `${security} close` }]
              }
            />
          </Panel>
          {kind !== "chart" && kind !== "technicals" && (
            <Panel
              title="Security reference"
              source={quote?.source}
              asOf={quote?.as_of}
              quality={quote?.quality}
            >
              <dl className="detail-list section-pad">
                <dt>Company</dt>
                <dd>{quote?.name}</dd>
                <dt>Internal ID</dt>
                <dd>{quote?.id}</dd>
                <dt>Exchange</dt>
                <dd>{quote?.exchange}</dd>
                <dt>Country</dt>
                <dd>{quote?.country}</dd>
                <dt>Asset class</dt>
                <dd>{quote?.asset_class}</dd>
                <dt>Currency</dt>
                <dd>{quote?.currency}</dd>
                <dt>Sector</dt>
                <dd>{quote?.sector}</dd>
                <dt>FIGI / ISIN</dt>
                <dd>Provider required</dd>
              </dl>
            </Panel>
          )}
          <Panel
            className="wide-panel"
            title="Price history / OHLCV"
            source={prices.data?.source}
            asOf={prices.data?.as_of}
            quality={prices.data?.quality}
          >
            <DataTable
              id="price-history"
              rows={records([...priceRows].reverse())}
              columns={[
                { key: "date", label: "Date", size: 100 },
                ...["open", "high", "low", "close", "volume"].map((k) => ({
                  key: k,
                  label: k.toUpperCase(),
                  numeric: true,
                })),
              ]}
            />
          </Panel>
        </div>
      )}
    </>
  );
}
