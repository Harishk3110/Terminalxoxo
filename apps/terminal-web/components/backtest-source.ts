import type { Tab } from "./types";

const BACKTEST_DEFAULTS = {
  additional_symbols: "",
  source_mode: "SOURCE_AWARE",
  base_currency: "SGD",
  strategy: "SMA",
  weighting: "EQUAL",
  direction: "LONG_ONLY",
  frequency: "WEEKLY",
  gross_limit: 0.95,
  position_limit: 0.95,
  sector_limit: 1,
  minimum_cash: 0.05,
  top_n: 3,
  spread_bps: 0,
  short_borrow_rate: 0.03,
  fast: 20,
  slow: 50,
  capital: 0,
  fee_bps: 5,
  slippage_bps: 5,
  start: "2020-01-01",
  end: "",
};

type BacktestForm = typeof BACKTEST_DEFAULTS &
  ReturnType<typeof initialBacktestSource>;

export function backtestForm(
  tab: Pick<Tab, "route" | "security">,
  saved: Partial<BacktestForm> = {},
): BacktestForm {
  return { ...BACKTEST_DEFAULTS, ...initialBacktestSource(tab), ...saved };
}

export function initialBacktestSource(tab: Pick<Tab, "route" | "security">) {
  const parts = tab.route.split("/");
  const dataset = parts[1] === "backtests" && parts[2] === "dataset";
  return {
    symbol: tab.security?.trim() || (dataset ? "" : "SPY"),
    dataset_id: dataset ? parts[3] || "" : "",
    dataset_version_id: dataset && parts[4] === "version" ? parts[5] || "" : "",
  };
}

export function normalizedPreviewSecurity(
  preview: readonly Record<string, unknown>[] = [],
) {
  const symbols = new Set(
    preview.map((row) =>
      typeof row.symbol === "string" ? row.symbol.trim() : "",
    ),
  );
  return symbols.size === 1 && !symbols.has("") ? [...symbols][0] : undefined;
}
