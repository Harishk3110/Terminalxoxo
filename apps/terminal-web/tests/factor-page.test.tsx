// @vitest-environment jsdom
import { useState } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
} from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { knkApi } from "@knk/api-client";
import type { Row } from "../components/types";

vi.mock("../components/context", async (original) => ({
  ...(await original<object>()),
  useTabState: <T,>(_key: string, initial: T) => useState(initial),
}));
vi.mock("../components/ui", async (original) => ({
  ...(await original<object>()),
  Chart: () => <div role="img" aria-label="Factor rank chart" />,
  LineChart: () => <div role="img" aria-label="Factor diagnostic chart" />,
  DataTable: ({ rows, id }: { rows: Row[]; id: string }) => (
    <div aria-label={id}>{rows.map((row) => row.symbol).join(",")}</div>
  ),
}));

import { FactorPage } from "../components/lab-pages";

const clients: QueryClient[] = [];
function mount() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: Infinity } },
  });
  clients.push(client);
  return render(
    <QueryClientProvider client={client}>
      <FactorPage />
    </QueryClientProvider>,
  );
}
async function settle() {
  await act(() => vi.advanceTimersByTimeAsync(301));
  await act(() => vi.advanceTimersByTimeAsync(1));
}
beforeEach(() => {
  vi.useFakeTimers();
  vi.spyOn(knkApi, "get").mockResolvedValue({
    items: [{ symbol: "IWM", factor: 0.2 }],
    source: "Test history",
    as_of: "2026-01-08T20:00:00Z",
    quality: "DEMO DATA",
    warnings: [],
    diagnostics: { state: "CALCULATED", in_sample: {}, out_of_sample: {} },
  });
});
afterEach(() => {
  cleanup();
  clients.splice(0).forEach((client) => client.clear());
  vi.useRealTimers();
  vi.restoreAllMocks();
});

it("coalesces rapid initial controls and retains explicit zero cost", async () => {
  mount();
  fireEvent.change(screen.getByLabelText("Factor type"), {
    target: { value: "VOLATILITY" },
  });
  fireEvent.change(screen.getByLabelText("Factor horizon", { exact: true }), {
    target: { value: "21" },
  });
  fireEvent.change(screen.getByLabelText("Factor cost"), {
    target: { value: "0" },
  });
  expect(knkApi.get).not.toHaveBeenCalled();
  await settle();
  expect(knkApi.get).toHaveBeenCalledTimes(1);
  expect(knkApi.get).toHaveBeenCalledWith(
    "/api/v1/factors?lookback=21&factor=VOLATILITY&horizon=5&cost_bps=0",
    expect.any(AbortSignal),
  );
  expect(screen.getByLabelText("factor-values").textContent).toBe("IWM");
});

it("hides previous results while changed controls settle", async () => {
  mount();
  await settle();
  expect(screen.getByLabelText("factor-values").textContent).toBe("IWM");
  fireEvent.change(screen.getByLabelText("Factor type"), {
    target: { value: "BETA" },
  });
  expect(screen.getByLabelText("factor-values").textContent).toBe("");
  expect(screen.queryByText("CALCULATED")).toBeNull();
  await settle();
  expect(knkApi.get).toHaveBeenCalledTimes(2);
  expect(screen.getByLabelText("factor-values").textContent).toBe("IWM");
});

it("cancels an obsolete in-flight request immediately on control change", async () => {
  vi.mocked(knkApi.get).mockImplementation(() => new Promise(() => {}));
  mount();
  await settle();
  const signal = vi.mocked(knkApi.get).mock.calls[0][1];
  expect(signal?.aborted).toBe(false);
  fireEvent.change(screen.getByLabelText("Factor type"), {
    target: { value: "BETA" },
  });
  expect(signal?.aborted).toBe(true);
  await settle();
  expect(knkApi.get).toHaveBeenCalledTimes(2);
});

it("does not start a delayed request after leaving the page", async () => {
  const view = mount();
  view.unmount();
  await settle();
  expect(knkApi.get).not.toHaveBeenCalled();
});
