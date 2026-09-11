import type { Tab } from "./types";

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
