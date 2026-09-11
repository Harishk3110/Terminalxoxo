// @vitest-environment jsdom
import { cleanup, render, screen, within } from "@testing-library/react";
import type { EChartsOption } from "echarts";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

const state = vi.hoisted(() => ({
  charts: new Map<string, EChartsOption>(),
  loading: false,
  error: null as Error | null,
  data: {
    source: "Dated test observations",
    as_of: "2026-01-08T20:00:00Z",
    quality: "CALCULATED WITH STALE DATA",
    risk: { volatility: null, beta: null, concentration: 0.25 },
    positions: [] as { symbol: string; risk_contribution: number | null }[],
    correlation: { symbols: ["AAA", "BBB"], values: [] as (number | null)[][] },
    curve: [],
    warnings: ["Insufficient return history"],
  },
}));

vi.mock("../components/context", async (original) => ({
  ...(await original<object>()),
  usePortfolio: () => ({
    data: state.data,
    isLoading: state.loading,
    error: state.error,
  }),
  useTerminal: () => ({ open: vi.fn() }),
}));
vi.mock("../components/ui", async (original) => ({
  ...(await original<object>()),
  Chart: ({ option, label }: { option: EChartsOption; label: string }) => {
    state.charts.set(label, option);
    return <div role="img" aria-label={label} />;
  },
  LineChart: () => <div>Drawdown history fixture</div>,
}));

import { RiskPage } from "../components/core-pages";

beforeEach(() => {
  state.charts.clear();
  state.loading = false;
  state.error = null;
  state.data.positions = [{ symbol: "AAA", risk_contribution: null }];
  state.data.correlation.values = [
    [null, null],
    [null, null],
  ];
});
afterEach(cleanup);

it("shows unavailable states instead of blank variance and correlation charts", () => {
  render(<RiskPage />);
  for (const title of [
    "Position variance contribution",
    "Daily return correlation",
  ]) {
    const panel = within(screen.getByRole("region", { name: title }));
    expect(panel.getByText("INSUFFICIENT DATA")).toBeTruthy();
    expect(panel.queryByRole("img")).toBeNull();
    expect(panel.getByText("Dated test observations")).toBeTruthy();
  }
  expect(state.charts.size).toBe(0);
});

it("retains genuine zero contributions and zero correlations", () => {
  state.data.positions = [{ symbol: "AAA", risk_contribution: 0 }];
  state.data.correlation.values = [
    [1, 0],
    [0, 1],
  ];
  render(<RiskPage />);
  expect(screen.queryByText("INSUFFICIENT DATA")).toBeNull();
  expect(
    state.charts.get("Position variance contribution")?.series,
  ).toMatchObject([{ data: [0] }]);
  expect(state.charts.get("Correlation matrix")?.series).toMatchObject([
    {
      data: [
        [0, 0, 1],
        [1, 0, 0],
        [0, 1, 0],
        [1, 1, 1],
      ],
    },
  ]);
});

it("omits missing correlation cells without changing their coordinates", () => {
  state.data.correlation.values = [
    [1, null],
    [null, 0],
  ];
  render(<RiskPage />);
  expect(state.charts.get("Correlation matrix")?.series).toMatchObject([
    {
      data: [
        [0, 0, 1],
        [1, 1, 0],
      ],
    },
  ]);
});

it("does not draw nonfinite variance or correlation values", () => {
  state.data.positions = [{ symbol: "AAA", risk_contribution: Number.NaN }];
  state.data.correlation.values = [[Number.NaN, Number.POSITIVE_INFINITY]];
  render(<RiskPage />);
  expect(screen.getAllByText("INSUFFICIENT DATA")).toHaveLength(2);
  expect(state.charts.size).toBe(0);
});

it("uses loading and failure states before interpreting unavailable data", () => {
  state.loading = true;
  const view = render(<RiskPage />);
  for (const title of [
    "Position variance contribution",
    "Daily return correlation",
  ]) {
    expect(
      within(screen.getByRole("region", { name: title })).getByText(
        "Loading data",
      ),
    ).toBeTruthy();
  }
  expect(screen.queryByText("INSUFFICIENT DATA")).toBeNull();
  state.loading = false;
  state.error = new Error("Portfolio service unavailable");
  view.rerender(<RiskPage />);
  expect(screen.getAllByRole("alert")).toHaveLength(2);
  expect(screen.queryByText("INSUFFICIENT DATA")).toBeNull();
});
