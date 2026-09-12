// @vitest-environment jsdom
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { cleanup, fireEvent, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { knkApi } from "@knk/api-client";
import { ReportsWorkspace } from "../components/reports-page";
import { renderLedger } from "./ledger-render";

const sourceRuns: { id: string; kind: string; name: string; status: string }[] =
  [];

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
  sourceRuns.length = 0;
  vi.spyOn(knkApi, "get").mockImplementation(async (path: string) => {
    if (path.endsWith("/templates"))
      return {
        items: [
          {
            kind: "portfolio",
            formats: ["xlsx", "pdf", "pptx"],
            analysis_kinds: [],
          },
          {
            kind: "backtest",
            formats: ["xlsx", "pdf"],
            analysis_kinds: ["backtest"],
          },
          {
            kind: "quant",
            formats: ["pptx"],
            analysis_kinds: [
              "backtest",
              "alpha",
              "factor",
              "model",
              "monte_carlo",
              "montecarlo",
            ],
          },
        ],
      };
    if (path === "/api/v1/terminal/runs") return { items: sourceRuns };
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

it("selects completed Monte Carlo research using the server template contract", async () => {
  sourceRuns.push(
    {
      id: "mc-complete",
      kind: "monte_carlo",
      name: "Completed simulation",
      status: "SUCCEEDED",
    },
    {
      id: "mc-pending",
      kind: "monte_carlo",
      name: "Pending simulation",
      status: "RUNNING",
    },
    {
      id: "mc-failed",
      kind: "monte_carlo",
      name: "Failed simulation",
      status: "FAILED",
    },
    {
      id: "wrong-kind",
      kind: "dcf",
      name: "Unrelated valuation",
      status: "SUCCEEDED",
    },
  );
  renderLedger(<ReportsWorkspace deck />);
  await screen.findByRole("option", { name: "quant" });
  await userEvent.selectOptions(screen.getByLabelText("Report type"), "quant");
  expect(screen.getByRole("button", { name: "Generate PPTX" })).toHaveProperty(
    "disabled",
    true,
  );
  await screen.findByRole("option", { name: /Completed simulation/ });
  for (const name of [
    /Pending simulation/,
    /Failed simulation/,
    /Unrelated valuation/,
  ]) {
    expect(screen.queryByRole("option", { name })).toBeNull();
  }
  await userEvent.selectOptions(
    screen.getByLabelText("Report analysis"),
    "mc-complete",
  );
  await userEvent.click(screen.getByRole("button", { name: "Generate PPTX" }));
  await waitFor(() =>
    expect(knkApi.post).toHaveBeenCalledWith(
      "/api/v1/report-jobs",
      expect.objectContaining({
        kind: "quant",
        format: "pptx",
        analysis_run_id: "mc-complete",
      }),
    ),
  );
});

it("disables generation when the selected run no longer qualifies after refresh", async () => {
  sourceRuns.push({
    id: "backtest-run",
    kind: "backtest",
    name: "Saved backtest",
    status: "SUCCEEDED",
  });
  const { client } = renderLedger(<ReportsWorkspace />);
  await screen.findByRole("option", { name: "backtest" });
  await userEvent.selectOptions(
    screen.getByLabelText("Report type"),
    "backtest",
  );
  await screen.findByRole("option", { name: /Saved backtest/ });
  await userEvent.selectOptions(
    screen.getByLabelText("Report analysis"),
    "backtest-run",
  );
  expect(
    screen.getByRole("button", { name: "Generate workbook" }),
  ).toHaveProperty("disabled", false);
  sourceRuns.length = 0;
  await client.refetchQueries({ queryKey: ["report-source-runs"] });
  await waitFor(() =>
    expect(
      screen.getByRole("button", { name: "Generate workbook" }),
    ).toHaveProperty("disabled", true),
  );
  expect(knkApi.post).not.toHaveBeenCalled();
});

it("uses only the source kinds advertised for the selected template", async () => {
  vi.mocked(knkApi.get).mockImplementation(async (path: string) => {
    if (path.endsWith("/templates"))
      return {
        items: [
          { kind: "quant", formats: ["pptx"], analysis_kinds: ["factor"] },
        ],
      };
    if (path === "/api/v1/terminal/runs")
      return {
        items: [
          {
            id: "allowed-factor",
            kind: "factor",
            name: "Allowed source",
            status: "SUCCEEDED",
          },
          {
            id: "excluded-backtest",
            kind: "backtest",
            name: "Excluded source",
            status: "SUCCEEDED",
          },
        ],
      };
    return { items: [] };
  });
  renderLedger(<ReportsWorkspace deck />);
  await screen.findByRole("option", { name: "quant" });
  await userEvent.selectOptions(screen.getByLabelText("Report type"), "quant");
  await screen.findByRole("option", { name: /Allowed source/ });
  expect(screen.queryByRole("option", { name: /Excluded source/ })).toBeNull();
});

it("does not submit a cached source after refreshing the run list fails", async () => {
  sourceRuns.push({
    id: "saved-run",
    kind: "backtest",
    name: "Saved source",
    status: "SUCCEEDED",
  });
  const { client } = renderLedger(<ReportsWorkspace />);
  await screen.findByRole("option", { name: "backtest" });
  await userEvent.selectOptions(
    screen.getByLabelText("Report type"),
    "backtest",
  );
  await userEvent.selectOptions(
    screen.getByLabelText("Report analysis"),
    "saved-run",
  );
  expect(
    screen.getByRole("button", { name: "Generate workbook" }),
  ).toHaveProperty("disabled", false);
  vi.mocked(knkApi.get).mockRejectedValue(
    new Error("Run registry unavailable"),
  );
  await client.refetchQueries({ queryKey: ["report-source-runs"] });
  expect(await screen.findByRole("alert")).toHaveProperty(
    "textContent",
    "Run registry unavailable",
  );
  expect(
    screen.getByRole("button", { name: "Generate workbook" }),
  ).toHaveProperty("disabled", true);
  expect(knkApi.post).not.toHaveBeenCalled();
});

it("fails closed when a template does not declare its source contract", async () => {
  vi.mocked(knkApi.get).mockImplementation(async (path: string) => {
    if (path.endsWith("/templates"))
      return { items: [{ kind: "portfolio", formats: ["xlsx"] }] };
    return { items: [] };
  });
  renderLedger(<ReportsWorkspace />);
  await screen.findByRole("option", { name: "portfolio" });
  expect(
    screen.getByRole("button", { name: "Generate workbook" }),
  ).toHaveProperty("disabled", true);
  expect(knkApi.post).not.toHaveBeenCalled();
});
