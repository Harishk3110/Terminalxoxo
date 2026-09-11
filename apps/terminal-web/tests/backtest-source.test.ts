import { describe, expect, it } from "vitest";
import {
  backtestForm,
  initialBacktestSource,
  normalizedPreviewSecurity,
} from "../components/backtest-source";

describe("file backtest launch", () => {
  it("fills missing persisted controls without changing saved inputs", () => {
    const saved = { symbol: "MSFT", fast: 10, start: "2025-01-01" };
    const form = backtestForm({ route: "/backtests" }, saved);
    expect(form).toMatchObject({
      ...saved,
      additional_symbols: "",
      fee_bps: 5,
      slippage_bps: 5,
      frequency: "WEEKLY",
    });
    expect(saved).toEqual({ symbol: "MSFT", fast: 10, start: "2025-01-01" });
  });
  it("preserves explicitly zero assumptions", () => {
    expect(
      backtestForm(
        { route: "/backtests" },
        { fee_bps: 0, slippage_bps: 0, minimum_cash: 0 },
      ),
    ).toMatchObject({ fee_bps: 0, slippage_bps: 0, minimum_cash: 0 });
  });
  it("preserves an explicit unresolved security instead of selecting a benchmark", () => {
    expect(
      backtestForm(
        { route: "/backtests/dataset/id", security: "QQQ" },
        { symbol: "" },
      ).symbol,
    ).toBe("");
  });
  it("pins the uploaded version and resolved security", () => {
    expect(
      initialBacktestSource({
        route: "/backtests/dataset/data-1/version/version-2",
        security: "QQQ",
      }),
    ).toEqual({
      symbol: "QQQ",
      dataset_id: "data-1",
      dataset_version_id: "version-2",
    });
  });
  it("never substitutes SPY for an unresolved uploaded security", () => {
    expect(
      initialBacktestSource({
        route: "/backtests/dataset/data-1/version/version-2",
      }).symbol,
    ).toBe("");
  });
  it("keeps the ordinary research default", () => {
    expect(initialBacktestSource({ route: "/backtests" })).toEqual({
      symbol: "SPY",
      dataset_id: "",
      dataset_version_id: "",
    });
  });
  it("keeps explicit security context for a new research tab", () => {
    expect(
      initialBacktestSource({ route: "/backtests", security: "MSFT" }).symbol,
    ).toBe("MSFT");
  });
  it("supports catalogue links without treating the dataset ID as a version", () => {
    expect(
      initialBacktestSource({ route: "/backtests/dataset/data-1" }),
    ).toEqual({ symbol: "", dataset_id: "data-1", dataset_version_id: "" });
  });
  it("uses normalized symbols, not filename guesses", () => {
    expect(
      normalizedPreviewSecurity([{ symbol: "QQQ" }, { symbol: "QQQ" }]),
    ).toBe("QQQ");
  });
  it.each([
    undefined,
    [],
    [{ symbol: "" }],
    [{ symbol: 1 }],
    [{ symbol: "QQQ" }, { symbol: "SPY" }],
  ])(
    "requires a selection for missing or ambiguous previews: %j",
    (preview) => {
      expect(normalizedPreviewSecurity(preview)).toBeUndefined();
    },
  );
});
