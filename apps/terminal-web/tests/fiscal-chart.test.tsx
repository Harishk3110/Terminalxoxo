// @vitest-environment jsdom
import { cleanup, render } from "@testing-library/react";
import type { EChartsOption } from "echarts";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

const captured = vi.hoisted(() => ({
  option: undefined as EChartsOption | undefined,
}));
vi.mock("../components/ui", async (original) => ({
  ...(await original<object>()),
  Chart: ({ option }: { option: EChartsOption }) => {
    captured.option = option;
    return null;
  },
}));

import { FiscalChart } from "../components/equity-page";

beforeEach(() => {
  captured.option = undefined;
});
afterEach(cleanup);

it("renders the actual lone zero and negative financial observations", () => {
  render(
    <FiscalChart
      rows={[{ year: "2025", revenue: 0, ebit: -2 }]}
      keys={["revenue", "ebit"]}
      label="Financial history"
    />,
  );
  expect(captured.option?.series).toMatchObject([
    { data: [0], symbol: "circle", symbolSize: 6, showAllSymbol: true },
    { data: [-2], symbol: "circle", symbolSize: 6, showAllSymbol: true },
  ]);
});

it("keeps isolated observations visible without filling missing periods", () => {
  render(
    <FiscalChart
      rows={[
        { year: "2023", revenue: null, ebit: 1 },
        { year: "2024", revenue: 20, ebit: null },
        { year: "2025", revenue: null, ebit: 3 },
      ]}
      keys={["revenue", "ebit"]}
      label="Financial history"
    />,
  );
  expect(captured.option?.series).toMatchObject([
    { data: [null, 20, null], symbol: "circle", connectNulls: false },
    { data: [1, null, 3], symbol: "circle", connectNulls: false },
  ]);
});

it("retains unmarked connected lines and original category/value ordering", () => {
  render(
    <FiscalChart
      rows={[
        { year: "2024", revenue: "100.25" },
        { year: "2025", revenue: "110.5" },
      ]}
      keys={["revenue"]}
      label="Financial history"
    />,
  );
  expect(captured.option?.xAxis).toMatchObject({ data: ["2024", "2025"] });
  expect(captured.option?.series).toMatchObject([
    { data: [100.25, 110.5], symbol: "none" },
  ]);
});

it("does not invent observations for missing or empty series", () => {
  const { rerender } = render(
    <FiscalChart
      rows={[{ year: "2025", revenue: null }]}
      keys={["revenue"]}
      label="Financial history"
    />,
  );
  expect(captured.option?.series).toMatchObject([
    { data: [null], symbol: "none" },
  ]);
  rerender(
    <FiscalChart rows={[]} keys={["revenue"]} label="Financial history" />,
  );
  expect(captured.option?.series).toMatchObject([{ data: [], symbol: "none" }]);
});
