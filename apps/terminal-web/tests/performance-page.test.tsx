// @vitest-environment jsdom
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { cleanup, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { knkApi } from "@knk/api-client";
import { PerformanceWorkspace } from "../components/performance-page";
import { renderLedger } from "./ledger-render";

vi.mock("../components/ui", async (original) => ({
  ...(await original<object>()),
  LineChart: () => <div>Chart</div>,
  DataTable: () => <div>Metric table</div>,
}));

const report = {
  source_quality: "DEMO DATA",
  calculated_at: "2026-09-04T20:00:00Z",
  valuation_run_id: "pinned-nav",
  source_precision: "DECIMAL",
  calculation_version: "knk-performance-1.1",
  warnings: [],
  summary: {
    twr: { value: ".01", state: "AVAILABLE", unit: "RETURN", observations: 66 },
  },
  series: [],
  monthly: [],
  rolling: [],
};
beforeEach(() => {
  vi.spyOn(knkApi, "get").mockImplementation(async <T,>(path: string) => {
    if (path === "/api/v1/portfolios")
      return { items: [{ id: "main", code: "KNK_MAIN" }] } as T;
    return report as T;
  });
  vi.spyOn(knkApi, "post").mockResolvedValue({
    analysis_run_id: "saved-performance",
  });
});
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

it("labels calculation controls and refetches changed fee and frequency settings", async () => {
  const user = userEvent.setup();
  renderLedger(<PerformanceWorkspace />);
  await screen.findByText("+1.00%");
  await user.selectOptions(
    screen.getByLabelText("Fees", { exact: true }),
    "GROSS",
  );
  await user.selectOptions(
    screen.getByLabelText("Frequency", { exact: true }),
    "WEEKLY",
  );
  await waitFor(() =>
    expect(knkApi.get).toHaveBeenCalledWith(
      expect.stringContaining("frequency=WEEKLY&fee_basis=GROSS"),
      expect.anything(),
    ),
  );
});

it("saves an analysis pinned to the displayed valuation and reports the persisted ID", async () => {
  const user = userEvent.setup();
  renderLedger(<PerformanceWorkspace />);
  await screen.findByText("+1.00%");
  await user.click(
    screen.getByRole("button", { name: "Save performance calculation" }),
  );
  await screen.findByText("Saved calculation: saved-performance");
  expect(knkApi.post).toHaveBeenCalledWith(
    "/api/v1/performance/portfolios/KNK_MAIN/calculate",
    expect.objectContaining({
      valuation_run_id: "pinned-nav",
      settings: expect.objectContaining({
        fee_basis: "NET",
        rolling_window: 60,
      }),
    }),
  );
});

it("reports persistence failure instead of displaying a saved run", async () => {
  vi.mocked(knkApi.post).mockRejectedValue(new Error("Calculation not saved"));
  const user = userEvent.setup();
  renderLedger(<PerformanceWorkspace />);
  await screen.findByText("+1.00%");
  await user.click(
    screen.getByRole("button", { name: "Save performance calculation" }),
  );
  await waitFor(() =>
    expect(screen.getByRole("alert").textContent).toContain(
      "Calculation not saved",
    ),
  );
  expect(screen.queryByText(/Saved calculation:/)).toBeNull();
});
