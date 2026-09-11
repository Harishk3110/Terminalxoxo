// @vitest-environment jsdom
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { cleanup, fireEvent, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { knkApi } from "@knk/api-client";
import { ReportsWorkspace } from "../components/reports-page";
import { renderLedger } from "./ledger-render";

vi.mock("../components/context", () => ({
  useTabState: (_key: string, initial: unknown) => useState(initial),
  usePortfolio: () => ({
    data: {
      portfolio: { id: "selected-book", name: "Selected book" },
      quality: "STALE",
    },
  }),
}));
vi.mock("../components/ui", () => ({
  Badge: ({ children }: { children: React.ReactNode }) => (
    <span>{children}</span>
  ),
  Field: ({
    children,
    label,
  }: {
    children: React.ReactNode;
    label: string;
  }) => (
    <label>
      {label}
      {children}
    </label>
  ),
  Panel: ({ children }: { children: React.ReactNode }) => (
    <section>{children}</section>
  ),
  timestamp: (value: string) => value,
}));
beforeEach(() => {
  vi.spyOn(knkApi, "get").mockImplementation(async (path: string) => {
    if (path.endsWith("/templates"))
      return {
        items: [
          { kind: "portfolio", formats: ["xlsx", "pdf", "pptx"] },
          { kind: "backtest", formats: ["xlsx", "pdf"] },
        ],
      };
    return { items: [] };
  });
  vi.spyOn(knkApi, "post").mockResolvedValue({ id: "new-job" });
});
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

it("pins the selected portfolio and explicit date on submission", async () => {
  renderLedger(<ReportsWorkspace />);
  await screen.findByRole("option", { name: "portfolio" });
  fireEvent.change(screen.getByLabelText("Report valuation date"), {
    target: { value: "2026-09-04" },
  });
  await userEvent.click(
    screen.getByRole("button", { name: "Generate workbook" }),
  );
  await waitFor(() =>
    expect(knkApi.post).toHaveBeenCalledWith("/api/v1/report-jobs", {
      kind: "portfolio",
      format: "xlsx",
      portfolio: "selected-book",
      symbol: "AAPL",
      analysis_run_id: null,
      as_of: "2026-09-04",
    }),
  );
});

it("requires a completed analysis selection for backtests", async () => {
  renderLedger(<ReportsWorkspace />);
  await screen.findByRole("option", { name: "backtest" });
  await userEvent.selectOptions(
    screen.getByLabelText("Report type"),
    "backtest",
  );
  expect(
    screen.getByRole("button", { name: "Generate workbook" }),
  ).toHaveProperty("disabled", true);
  expect(knkApi.post).not.toHaveBeenCalled();
});

it("shows queue rejection without inventing a successful download", async () => {
  vi.mocked(knkApi.post).mockRejectedValue(
    new Error("Four active reports already queued"),
  );
  renderLedger(<ReportsWorkspace />);
  await screen.findByRole("option", { name: "portfolio" });
  await userEvent.click(
    screen.getByRole("button", { name: "Generate workbook" }),
  );
  expect(await screen.findByRole("alert")).toHaveProperty(
    "textContent",
    "Four active reports already queued",
  );
  expect(screen.queryByRole("link", { name: "Download XLSX" })).toBeNull();
});
