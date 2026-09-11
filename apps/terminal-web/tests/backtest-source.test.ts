import { describe, expect, it } from "vitest";
import {
  initialBacktestSource,
  normalizedPreviewSecurity,
} from "../components/backtest-source";

describe("file backtest launch", () => {
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
