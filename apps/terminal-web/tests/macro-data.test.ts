import { expect, it } from "vitest";
import type { MacroDashboardPayload } from "@knk/api-client";
import { macroProvenance, macroRange } from "../components/macro-data";

const observation = (
  overrides: Partial<MacroDashboardPayload["items"][number]> = {},
) => ({
  series_id: "DGS10",
  title: "Ten-year yield",
  latest_value: "3.5",
  previous_value: "3.4",
  change: "0.1",
  latest_observation_date: "2026-08-28",
  ingestion_timestamp: "2026-09-12T00:00:00Z",
  unit: "Percent",
  frequency: "Daily",
  source: "FRED",
  quality: "EOD",
  revision_state: "CURRENT",
  ...overrides,
});

it("uses observation dates rather than ingestion timestamps", () => {
  expect(macroProvenance([observation()])).toEqual({
    source: "FRED",
    quality: "EOD",
    asOf: "2026-08-28",
  });
});
it("does not label actual or unavailable observations as demo", () => {
  expect(macroProvenance([]).quality).toBe("UNAVAILABLE");
  expect(macroProvenance([observation({ latest_value: null })]).quality).toBe(
    "UNAVAILABLE",
  );
  expect(macroProvenance([observation()]).quality).toBe("EOD");
});
it("preserves genuine zero and explicit demo provenance", () => {
  expect(
    macroProvenance([
      observation({
        latest_value: "0",
        source: "DemoProvider",
        quality: "DEMO DATA",
      }),
    ]),
  ).toEqual({
    source: "DemoProvider",
    quality: "DEMO DATA",
    asOf: "2026-08-28",
  });
});
it("shows mixed states and the oldest contributing date", () => {
  expect(
    macroProvenance([
      observation(),
      observation({
        source: "FILE fixture",
        quality: "FILE IMPORT",
        latest_observation_date: "2026-08-27",
      }),
    ]),
  ).toEqual({
    source: "FRED / FILE fixture",
    quality: "MIXED SOURCES",
    asOf: "2026-08-27",
  });
});
it.each([null, "bad-date", "2026-02-30"])(
  "does not infer a missing observation date from ingestion: %s",
  (latest_observation_date) => {
    expect(
      macroProvenance([observation({ latest_observation_date })]).asOf,
    ).toBeNull();
  },
);
it("one-year and five-year views select calendar intervals, not row counts", () => {
  const rows = Array.from({ length: 1300 }, (_, i) => ({
    date: new Date(Date.UTC(2022, 0, 1 + i)).toISOString().slice(0, 10),
    value: i,
  }));
  expect(macroRange(rows, "1Y")).toHaveLength(366);
  expect(macroRange(rows, "5Y")).toHaveLength(1300);
  expect(macroRange(rows, "MAX")).toHaveLength(1300);
});
it("retains inclusive leap-year boundaries and original values without mutation", () => {
  const rows = [
    { observation_date: "2023-02-28", value: null },
    { observation_date: "2024-02-29", value: 0 },
  ];
  const before = structuredClone(rows);
  expect(macroRange(rows, "1Y")).toEqual(
    rows.map((row) => ({ ...row, date: row.observation_date })),
  );
  expect(rows).toEqual(before);
});
it("does not derive range dates from malformed values", () => {
  expect(macroRange([{ date: "invalid", value: 0 }], "1Y")).toEqual([]);
});
