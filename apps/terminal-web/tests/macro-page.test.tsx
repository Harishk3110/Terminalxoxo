// @vitest-environment jsdom
import { cleanup, render, screen, within } from "@testing-library/react";
import type { MacroDashboardPayload } from "@knk/api-client";
import type { EChartsOption } from "echarts";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import type { Row } from "../components/types";

const state = vi.hoisted(() => ({
  items: [] as MacroDashboardPayload["items"],
  observations: [] as Row[],
  rows: [] as Row[],
  charts: new Map<string, EChartsOption>(),
  range: "MAX",
}));

vi.mock("@tanstack/react-query", async (original) => ({
  ...(await original<object>()),
  useQuery: ({ queryKey }: { queryKey: string[] }) => ({
    data: { items: queryKey[0] === "macro" ? state.items : state.observations },
    isLoading: false,
    error: null,
    refetch: vi.fn(),
  }),
  useMutation: () => ({ mutate: vi.fn(), isPending: false }),
}));
vi.mock("../components/context", async (original) => ({
  ...(await original<object>()),
  useTabState: (key: string, initial: unknown) => [
    key === "macro-range" ? state.range : initial,
    vi.fn(),
  ],
}));
vi.mock("../components/ui", async (original) => ({
  ...(await original<object>()),
  Chart: ({ option, label }: { option: EChartsOption; label: string }) => {
    state.charts.set(label, option);
    return <div role="img" aria-label={label} />;
  },
  LineChart: ({ rows, label }: { rows: Row[]; label: string }) => {
    state.rows = rows;
    return <div role="img" aria-label={label} />;
  },
}));

import { MacroPage } from "../components/core-pages";

beforeEach(() => {
  state.items = [
    {
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
    },
  ];
  state.observations = Array.from({ length: 500 }, (_, i) => ({
    observation_date: new Date(Date.UTC(2026, 7, 28) - (499 - i) * 86_400_000)
      .toISOString()
      .slice(0, 10),
    value: i,
  }));
  state.range = "MAX";
  state.charts.clear();
  state.rows = [];
});
afterEach(cleanup);

it("labels economic-series data with its observation date", () => {
  render(<MacroPage />);
  const panel = screen.getByRole("region", { name: "Economic series / DGS10" });
  expect(panel.querySelector("footer time")?.textContent).toContain(
    "28 Aug 26",
  );
});
it("uses actual Treasury source quality rather than a demo constant", () => {
  render(<MacroPage />);
  const panel = within(
    screen.getByRole("region", { name: "US Treasury yield curve" }),
  );
  expect(panel.getByText("EOD")).toBeTruthy();
  expect(panel.queryByText("DEMO DATA")).toBeNull();
});
it("MAX retains all returned observations", () => {
  render(<MacroPage />);
  expect(state.rows).toHaveLength(500);
  expect(state.rows[0].value).toBe(0);
});
it("missing Treasury values remain gaps and unavailable", () => {
  state.items = [];
  render(<MacroPage />);
  expect(
    within(
      screen.getByRole("region", { name: "US Treasury yield curve" }),
    ).getByText("UNAVAILABLE"),
  ).toBeTruthy();
  expect(state.charts.get("US Treasury curve")?.series).toMatchObject([
    { data: [null, null, null] },
  ]);
});
