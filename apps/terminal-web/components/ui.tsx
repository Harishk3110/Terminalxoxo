"use client";

import { useContext, useMemo, useRef, useState, type ReactNode } from "react";
import { TerminalContext } from "./context";
import {
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getSortedRowModel,
  useReactTable,
  type ColumnDef,
  type SortingState,
  type VisibilityState,
} from "@tanstack/react-table";
import { useVirtualizer } from "@tanstack/react-virtual";
import {
  ArrowDownToLine,
  Columns3,
  Maximize2,
  Minimize2,
  RefreshCw,
  Search,
  X,
  ChevronDown,
  ArrowUpDown,
  Info,
  LoaderCircle,
} from "lucide-react";
import dynamic from "next/dynamic";
import type { EChartsOption } from "echarts";
import type { Row } from "./types";

export const COLORS = {
  bg: "#000000",
  panel: "#0A0A0A",
  grid: "#1D1D1D",
  text: "#A8A8A8",
  amber: "#FF9D00",
  blue: "#25B7E9",
  green: "#00C875",
  red: "#FF4D4F",
  purple: "#B28DFF",
  yellow: "#FFD400",
};
const EChart = dynamic(() => import("echarts-for-react"), {
  ssr: false,
  loading: () => (
    <div className="loading-state">
      <LoaderCircle size={16} className="spin" />
      Loading chart
    </div>
  ),
});
export const number = (v: unknown, places = 2) =>
  v === null || v === undefined || v === "" || !Number.isFinite(Number(v))
    ? "--"
    : Number(v).toLocaleString("en-SG", {
        minimumFractionDigits: places,
        maximumFractionDigits: places,
      });
export const pct = (v: unknown) =>
  v === null || v === undefined
    ? "--"
    : `${Number(v) > 0 ? "+" : ""}${number(Number(v) * 100)}%`;
export const money = (v: unknown) => `S$${number(v)}`;
export const utcDate = (v: string) =>
  new Date(v.includes("T") && !/(Z|[+-]\d\d:\d\d)$/.test(v) ? `${v}Z` : v);
export const timestamp = (v?: string | null) =>
  v
    ? utcDate(v).toLocaleString("en-SG", {
        timeZone: "Asia/Singapore",
        day: "2-digit",
        month: "short",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
        hour12: false,
      })
    : "Not observed";
export const tone = (v: unknown) =>
  Number(v) > 0 ? "positive" : Number(v) < 0 ? "negative" : "";

export function download(name: string, content: string, type = "text/plain") {
  const url = URL.createObjectURL(new Blob([content], { type }));
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}
export function exportCsv(name: string, rows: Row[]) {
  if (!rows.length) return;
  const keys = Object.keys(rows[0]);
  const cell = (value: unknown) => {
    let text =
      typeof value === "object" ? JSON.stringify(value) : String(value ?? "");
    if (/^[=+@\t\r]/.test(text) || /^-\D/.test(text)) text = `'${text}`;
    return `"${text.replaceAll('"', '""')}"`;
  };
  download(
    `${name}.csv`,
    [
      keys.map(cell).join(","),
      ...rows.map((row) => keys.map((key) => cell(row[key])).join(",")),
    ].join("\r\n"),
    "text/csv",
  );
}
export function IconButton({
  label,
  children,
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & {
  label: string;
  children: ReactNode;
}) {
  return (
    <button
      type="button"
      {...props}
      className={`icon-button ${props.className ?? ""}`}
      title={label}
      aria-label={label}
    >
      {children}
    </button>
  );
}
export function Badge({
  children,
  state,
}: {
  children: ReactNode;
  state?: string;
}) {
  const text = state ?? String(children);
  const kind =
    /DEMO|STALE|UNVERIFIED|REQUIRED|DEVELOPMENT|NOT_|OFFLINE|WARNING/.test(
      text.toUpperCase(),
    )
      ? "warning"
      : /FAILED|ERROR|CANCELLED/.test(text)
        ? "negative"
        : /CALCULATED/.test(text)
          ? "calculated"
          : /PAPER|RUNNING|QUEUED/.test(text)
            ? "action"
            : /HEALTHY|SUCCEEDED|CONNECTED|READY/.test(text)
              ? "positive"
              : "muted";
  return <span className={`badge ${kind}`}>{children}</span>;
}

export function Panel({
  title,
  children,
  source,
  asOf,
  quality,
  loading,
  error,
  onRefresh,
  rows,
  actions,
  className = "",
}: {
  title: string;
  children: ReactNode;
  source?: string;
  asOf?: string | null;
  quality?: string;
  loading?: boolean;
  error?: unknown;
  onRefresh?: () => void;
  rows?: Row[];
  actions?: ReactNode;
  className?: string;
}) {
  const [expanded, setExpanded] = useState(false);
  const [info, setInfo] = useState(false);
  return (
    <section
      className={`terminal-panel ${expanded ? "panel-expanded" : ""} ${className}`}
      aria-label={title}
      onContextMenu={(event) => {
        event.preventDefault();
        setInfo(true);
      }}
    >
      <header className="panel-header">
        <h2>{title}</h2>
        <span className="panel-header-spacer" />
        {actions}
        {onRefresh && (
          <IconButton label={`Refresh ${title}`} onClick={onRefresh}>
            <RefreshCw size={12} />
          </IconButton>
        )}
        {rows && (
          <IconButton
            label={`Export ${title} CSV`}
            onClick={() => exportCsv(title, rows)}
          >
            <ArrowDownToLine size={12} />
          </IconButton>
        )}
        <IconButton
          label={`Source for ${title}`}
          onClick={() => setInfo(!info)}
        >
          <Info size={12} />
        </IconButton>
        <IconButton
          label={`${expanded ? "Restore" : "Expand"} ${title}`}
          onClick={() => setExpanded(!expanded)}
        >
          {expanded ? <Minimize2 size={12} /> : <Maximize2 size={12} />}
        </IconButton>
      </header>
      {info && (
        <div className="source-popover">
          <IconButton
            label="Close source details"
            onClick={() => setInfo(false)}
          >
            <X size={12} />
          </IconButton>
          <strong>{source ?? "No source available"}</strong>
          <span>{timestamp(asOf)} SGT</span>
          <span>{quality ?? "UNAVAILABLE"}</span>
          {onRefresh && <button onClick={onRefresh}>Refresh data</button>}
          {rows && (
            <button onClick={() => exportCsv(title, rows)}>Export CSV</button>
          )}
        </div>
      )}
      <div className="panel-content">
        {loading ? (
          <div className="loading-state">
            <LoaderCircle size={16} className="spin" />
            Loading data
          </div>
        ) : error ? (
          <div className="error-state" role="alert">
            {error instanceof Error ? error.message : String(error)}
            {onRefresh && <button onClick={onRefresh}>Retry</button>}
          </div>
        ) : (
          children
        )}
      </div>
      <footer className="panel-footer">
        <span title={source}>{source ?? "Source unavailable"}</span>
        <span className="panel-header-spacer" />
        {quality && <Badge>{quality}</Badge>}
        <time title={`${timestamp(asOf)} SGT`}>
          {asOf
            ? `${utcDate(asOf).toLocaleDateString("en-SG", { timeZone: "Asia/Singapore", day: "2-digit", month: "short", year: "2-digit" })}`
            : "Not observed"}
        </time>
      </footer>
    </section>
  );
}

export function Kpis({
  items,
  source,
  asOf,
}: {
  items: { label: string; value: string; className?: string }[];
  source?: string;
  asOf?: string;
}) {
  return (
    <div
      className="kpi-strip"
      title={`${source ?? ""} | ${timestamp(asOf)} SGT`}
    >
      {items.map((item) => (
        <div key={item.label} className="kpi">
          <span>{item.label}</span>
          <strong className={item.className}>{item.value}</strong>
        </div>
      ))}
    </div>
  );
}

export interface Column {
  key: string;
  label: string;
  numeric?: boolean;
  percent?: boolean;
  money?: boolean;
  size?: number;
  format?: (value: unknown, row: Row) => ReactNode;
}
export function DataTable({
  id,
  rows,
  columns,
  onSelect,
  selectedKey,
  compact = false,
}: {
  id: string;
  rows: Row[];
  columns: Column[];
  onSelect?: (row: Row) => void;
  selectedKey?: string;
  compact?: boolean;
}) {
  const scroll = useRef<HTMLDivElement>(null);
  const [sorting, setSorting] = useState<SortingState>([]);
  const [filter, setFilter] = useState("");
  const [visibility, setVisibility] = useState<VisibilityState>({});
  const [order, setOrder] = useState<string[]>([]);
  const [showColumns, setShowColumns] = useState(false);
  const [drag, setDrag] = useState("");
  const [pinned, setPinned] = useState(false);
  const [menu, setMenu] = useState<{
    symbol: string;
    x: number;
    y: number;
  } | null>(null);
  const terminal = useContext(TerminalContext);
  const defs = useMemo<ColumnDef<Row>[]>(
    () =>
      columns.map((c) => ({
        id: c.key,
        accessorKey: c.key,
        header: c.label,
        size: c.size ?? (c.key === "name" ? 200 : c.numeric ? 110 : 120),
        minSize: 60,
        cell: ({ getValue, row }) =>
          c.format ? (
            c.format(getValue(), row.original)
          ) : c.percent ? (
            <span className={tone(getValue())}>{pct(getValue())}</span>
          ) : c.money ? (
            <span className={tone(getValue())}>{money(getValue())}</span>
          ) : c.numeric ? (
            number(getValue(), c.key === "rank" || c.key === "quantile" ? 0 : 2)
          ) : (
            String(getValue() ?? "--")
          ),
      })),
    [columns],
  );
  const table = useReactTable({
    data: rows,
    columns: defs,
    state: {
      sorting,
      globalFilter: filter,
      columnVisibility: visibility,
      columnOrder: order,
    },
    onSortingChange: setSorting,
    onGlobalFilterChange: setFilter,
    onColumnVisibilityChange: setVisibility,
    onColumnOrderChange: setOrder,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    columnResizeMode: "onChange",
  });
  const data = table.getRowModel().rows;
  const virtual = useVirtualizer({
    count: data.length,
    getScrollElement: () => scroll.current,
    estimateSize: () => 28,
    overscan: 8,
  });
  const virtualRows = virtual.getVirtualItems();
  const visible = virtualRows.length
    ? virtualRows
    : data.slice(0, 20).map((_, index) => ({
        index,
        start: index * 28,
        end: (index + 1) * 28,
        size: 28,
        key: index,
      }));
  return (
    <div className="data-table" data-testid="data-table">
      {!compact && (
        <div className="table-toolbar">
          <Search size={12} />
          <input
            aria-label={`Filter ${id}`}
            placeholder="Filter rows"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
          />
          <span className="muted">{data.length} rows</span>
          <IconButton
            label={`Columns ${id}`}
            onClick={() => setShowColumns(!showColumns)}
          >
            <Columns3 size={13} />
          </IconButton>
          <IconButton
            label={`Export ${id}`}
            onClick={() =>
              exportCsv(
                id,
                data.map((r) => r.original),
              )
            }
          >
            <ArrowDownToLine size={13} />
          </IconButton>
        </div>
      )}
      {showColumns && (
        <div className="column-options">
          <label>
            <input
              type="checkbox"
              checked={pinned}
              onChange={(e) => setPinned(e.target.checked)}
            />
            Pin first column
          </label>
          {table.getAllLeafColumns().map((column) => (
            <label key={column.id}>
              <input
                type="checkbox"
                checked={column.getIsVisible()}
                onChange={column.getToggleVisibilityHandler()}
              />
              {column.columnDef.header as string}
            </label>
          ))}
          <button
            onClick={() => {
              localStorage.setItem(
                `knk-table-${id}`,
                JSON.stringify({ visibility, order, sorting, pinned }),
              );
              setShowColumns(false);
            }}
          >
            Save view
          </button>
          <button
            onClick={() => {
              const raw = localStorage.getItem(`knk-table-${id}`);
              if (raw) {
                const v = JSON.parse(raw);
                setVisibility(v.visibility);
                setOrder(v.order);
                setSorting(v.sorting);
                setPinned(Boolean(v.pinned));
              }
              setShowColumns(false);
            }}
          >
            Load view
          </button>
        </div>
      )}
      <div
        className="table-scroll"
        ref={scroll}
        tabIndex={0}
        aria-label={`${id} table`}
      >
        <table style={{ width: `max(100%, ${table.getTotalSize()}px)` }}>
          <thead>
            {table.getHeaderGroups().map((group) => (
              <tr key={group.id}>
                {group.headers.map((header, index) => (
                  <th
                    key={header.id}
                    style={{
                      width: header.getSize(),
                      ...(pinned && index === 0
                        ? ({
                            position: "sticky",
                            left: 0,
                            zIndex: 3,
                            background: "var(--panel-secondary)",
                          } as const)
                        : {}),
                    }}
                    draggable
                    onDragStart={() => setDrag(header.id)}
                    onDragOver={(e) => e.preventDefault()}
                    onDrop={() => {
                      const keys = table
                        .getVisibleLeafColumns()
                        .map((c) => c.id);
                      const from = keys.indexOf(drag);
                      const to = keys.indexOf(header.id);
                      if (from >= 0 && to >= 0) {
                        keys.splice(to, 0, keys.splice(from, 1)[0]);
                        setOrder(keys);
                      }
                    }}
                    className={
                      columns.find((c) => c.key === header.id)?.numeric
                        ? "numeric"
                        : ""
                    }
                  >
                    <button onClick={header.column.getToggleSortingHandler()}>
                      {flexRender(
                        header.column.columnDef.header,
                        header.getContext(),
                      )}
                      {header.column.getIsSorted() ? (
                        <ChevronDown size={10} />
                      ) : null}
                    </button>
                    <span
                      className="column-resize"
                      onMouseDown={header.getResizeHandler()}
                      onTouchStart={header.getResizeHandler()}
                    />
                  </th>
                ))}
              </tr>
            ))}
          </thead>
          <tbody>
            {visible[0]?.start > 0 && (
              <tr aria-hidden="true">
                <td
                  colSpan={columns.length}
                  style={{ height: visible[0].start, padding: 0 }}
                />
              </tr>
            )}
            {visible.map((v) => {
              const row = data[v.index];
              if (!row) return null;
              return (
                <tr
                  key={row.id}
                  className={
                    selectedKey &&
                    Object.values(row.original).includes(selectedKey)
                      ? "selected"
                      : ""
                  }
                  onClick={() => onSelect?.(row.original)}
                  onContextMenu={(e) => {
                    const symbol = String(row.original.symbol ?? "");
                    if (
                      terminal?.bootstrap.quotes.some(
                        (q) => q.symbol === symbol,
                      )
                    ) {
                      e.preventDefault();
                      setMenu({
                        symbol,
                        x: Math.min(e.clientX, window.innerWidth - 190),
                        y: Math.min(e.clientY, window.innerHeight - 270),
                      });
                    }
                  }}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") onSelect?.(row.original);
                    if ((e.ctrlKey || e.metaKey) && e.key === "c")
                      navigator.clipboard?.writeText(
                        row
                          .getVisibleCells()
                          .map((c) => String(c.getValue() ?? ""))
                          .join("\t"),
                      );
                  }}
                  tabIndex={0}
                >
                  {row.getVisibleCells().map((cell, index) => (
                    <td
                      key={cell.id}
                      tabIndex={0}
                      style={
                        pinned && index === 0
                          ? {
                              position: "sticky",
                              left: 0,
                              zIndex: 1,
                              background: "var(--panel-primary)",
                            }
                          : undefined
                      }
                      onKeyDown={(e) => {
                        if ((e.ctrlKey || e.metaKey) && e.key === "c") {
                          e.stopPropagation();
                          e.preventDefault();
                          navigator.clipboard?.writeText(
                            String(cell.getValue() ?? ""),
                          );
                        }
                        const delta =
                          e.key === "ArrowRight"
                            ? 1
                            : e.key === "ArrowLeft"
                              ? -1
                              : 0;
                        if (delta) {
                          e.preventDefault();
                          (
                            e.currentTarget.parentElement?.children[
                              index + delta
                            ] as HTMLElement
                          )?.focus();
                        }
                        if (e.key === "ArrowDown" || e.key === "ArrowUp") {
                          e.preventDefault();
                          const row = e.currentTarget.parentElement;
                          const next =
                            e.key === "ArrowDown"
                              ? row?.nextElementSibling
                              : row?.previousElementSibling;
                          (next?.children[index] as HTMLElement)?.focus();
                        }
                      }}
                      className={
                        columns.find((c) => c.key === cell.column.id)?.numeric
                          ? "numeric"
                          : ""
                      }
                      title={String(cell.getValue() ?? "")}
                    >
                      {flexRender(
                        cell.column.columnDef.cell,
                        cell.getContext(),
                      )}
                    </td>
                  ))}
                </tr>
              );
            })}
            {data.length > 0 &&
              visible.length > 0 &&
              virtual.getTotalSize() > visible[visible.length - 1].end && (
                <tr aria-hidden="true">
                  <td
                    colSpan={columns.length}
                    style={{
                      height:
                        virtual.getTotalSize() -
                        visible[visible.length - 1].end,
                      padding: 0,
                    }}
                  />
                </tr>
              )}
          </tbody>
        </table>
        {!data.length && <div className="empty-state">No matching records</div>}
      </div>
      {menu && terminal && (
        <div
          className="context-dismiss"
          onClick={() => setMenu(null)}
          onContextMenu={(e) => {
            e.preventDefault();
            setMenu(null);
          }}
        >
          <div
            role="menu"
            aria-label={`${menu.symbol} functions`}
            className="security-menu"
            style={{ left: menu.x, top: menu.y }}
          >
            <strong>{menu.symbol}</strong>
            {["DES", "Q", "GP", "FIN", "COMP", "RISK", "STRESS", "HEDGE"].map(
              (code) => {
                const fn = terminal.bootstrap.functions.find(
                  (f) => f.mnemonic === code,
                );
                return fn ? (
                  <button
                    key={code}
                    role="menuitem"
                    onClick={() => {
                      terminal.selectSecurity(menu.symbol);
                      terminal.open(
                        fn.route.replace("{instrumentId}", menu.symbol),
                        fn.requiresSecurity ? `${menu.symbol} ${code}` : code,
                        false,
                        fn.requiresSecurity ? menu.symbol : undefined,
                      );
                      setMenu(null);
                    }}
                  >
                    <span className="amber mono">{code}</span>
                    {fn.name}
                  </button>
                ) : null;
              },
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export function Chart({
  option,
  label,
}: {
  option: EChartsOption;
  label: string;
}) {
  const merged: EChartsOption = {
    backgroundColor: COLORS.panel,
    animation: false,
    color: [
      COLORS.amber,
      COLORS.blue,
      COLORS.green,
      COLORS.purple,
      COLORS.yellow,
    ],
    textStyle: {
      fontFamily: "Consolas, monospace",
      fontSize: 10,
      color: COLORS.text,
    },
    grid: { left: 56, right: 16, top: 24, bottom: 28 },
    tooltip: {
      trigger: "axis",
      axisPointer: { type: "cross" },
      backgroundColor: COLORS.panel,
      borderColor: COLORS.grid,
      textStyle: { color: "#F2F2F2", fontSize: 11 },
    },
    xAxis: {
      type: "category",
      axisLine: { lineStyle: { color: COLORS.grid } },
      axisTick: { show: false },
      axisLabel: { fontSize: 10 },
    },
    yAxis: {
      type: "value",
      scale: true,
      splitLine: { lineStyle: { color: COLORS.grid } },
      axisLabel: { fontSize: 10 },
    },
    toolbox: {
      right: 0,
      top: 0,
      itemSize: 11,
      iconStyle: { borderColor: COLORS.text },
      feature: {
        saveAsImage: { title: "Export PNG", pixelRatio: 2, name: label },
      },
    },
    ...option,
  };
  return (
    <div className="chart" role="img" aria-label={label}>
      <EChart
        option={merged}
        notMerge
        style={{ height: "100%", width: "100%" }}
        opts={{ renderer: "canvas" }}
      />
    </div>
  );
}

export function LineChart({
  rows,
  keys,
  label,
  percent = false,
}: {
  rows: Row[];
  keys: { key: string; name: string; color?: string }[];
  label: string;
  percent?: boolean;
}) {
  return (
    <Chart
      label={label}
      option={{
        xAxis: {
          type: "category",
          data: rows.map((r) => String(r.date)),
          axisLine: { lineStyle: { color: COLORS.grid } },
          axisLabel: { formatter: (v: string) => v.slice(5), fontSize: 10 },
        },
        yAxis: {
          type: "value",
          scale: true,
          splitLine: { lineStyle: { color: COLORS.grid } },
          axisLabel: {
            formatter: percent
              ? (v: number) => `${(v * 100).toFixed(0)}%`
              : undefined,
          },
        },
        legend: {
          top: 0,
          left: 45,
          textStyle: { color: COLORS.text, fontSize: 10 },
          itemWidth: 16,
          itemHeight: 2,
        },
        dataZoom: [{ type: "inside", filterMode: "none" }],
        series: keys.map((k) => ({
          name: k.name,
          type: "line",
          data: rows.map((r) => r[k.key] ?? null),
          symbol: "none",
          lineStyle: { width: 1.5, color: k.color },
          itemStyle: { color: k.color },
          connectNulls: false,
        })),
      }}
    />
  );
}

export function Empty({
  title,
  detail,
  children,
}: {
  title: string;
  detail?: string;
  children?: ReactNode;
}) {
  return (
    <div className="empty-state">
      <strong>{title}</strong>
      {detail && <p>{detail}</p>}
      {children}
    </div>
  );
}
export function Field({
  label,
  children,
}: {
  label: string;
  children: ReactNode;
}) {
  return (
    <label className="field">
      <span>{label}</span>
      {children}
    </label>
  );
}
