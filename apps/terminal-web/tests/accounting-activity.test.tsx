// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { knkApi } from "@knk/api-client";
import { AccountingActivity } from "../components/ledger/accounting-activity";
import { BalanceEditor } from "../components/ledger/balance-editor";
import { renderLedger } from "./ledger-render";
import { activity, income } from "./fixtures/postings";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe("accounting subledger controls", () => {
  it("pins the query to the selected valuation run and escapes identifiers", async () => {
    const get = vi.spyOn(knkApi, "get").mockResolvedValue(activity);
    renderLedger(
      <AccountingActivity portfolioKey="book/id" runId="run one&two" />,
    );
    await screen.findByRole("table", { name: "Accounting component records" });
    expect(get).toHaveBeenCalledWith(
      "/api/v1/portfolios/book%2Fid/accounting?run_id=run+one%26two",
      expect.any(AbortSignal),
    );
    expect(screen.getByText("BALANCED")).toBeTruthy();
    expect(screen.getByText("Capital flows / SGD")).toBeTruthy();
  });

  it("filters typed categories without changing the all-category totals", async () => {
    vi.spyOn(knkApi, "get").mockResolvedValue(activity);
    renderLedger(<AccountingActivity portfolioKey="book" runId="run-1" />);
    await userEvent.selectOptions(
      await screen.findByLabelText("Accounting category"),
      "FEE",
    );
    const table = screen.getByRole("table", {
      name: "Accounting component records",
    });
    expect(within(table).getByText("TAX")).toBeTruthy();
    expect(within(table).queryByText("DIVIDEND")).toBeNull();
    expect(screen.getByText("1 records")).toBeTruthy();
    expect(screen.getByText("15.60")).toBeTruthy();
  });

  it("opens transaction, settlement and rate provenance for a selected row", async () => {
    vi.spyOn(knkApi, "get").mockResolvedValue(activity);
    renderLedger(<AccountingActivity portfolioKey="book" runId="run-1" />);
    await userEvent.click(
      await screen.findByRole("button", {
        name: "Inspect DIVIDEND 2026-01-06",
      }),
    );
    const details = screen.getByRole("region", {
      name: "Accounting record details",
    });
    expect(within(details).getByText("transaction-1")).toBeTruthy();
    expect(within(details).getByText("account-1")).toBeTruthy();
    expect(within(details).getByText("2026-01-08")).toBeTruthy();
    expect(within(details).getByText("1.30000000")).toBeTruthy();
    expect(within(details).getByText("RECORDED TRANSACTION FX")).toBeTruthy();
    await userEvent.selectOptions(
      screen.getByLabelText("Accounting category"),
      "FEE",
    );
    expect(
      screen.queryByRole("region", { name: "Accounting record details" }),
    ).toBeNull();
  });

  it("paginates records and resets to the first page on a category change", async () => {
    vi.spyOn(knkApi, "get").mockResolvedValue({
      ...activity,
      items: Array.from({ length: 30 }, (_, index) => ({
        ...income,
        id: `income-${index}`,
        key: `income-${index}`,
      })),
    });
    renderLedger(<AccountingActivity portfolioKey="book" runId="run-1" />);
    const table = await screen.findByRole("table", {
      name: "Accounting component records",
    });
    expect(within(table).getAllByRole("row").length).toBe(26);
    await userEvent.click(
      screen.getByRole("button", { name: "Next accounting page" }),
    );
    expect(within(table).getAllByRole("row").length).toBe(6);
    expect(
      (
        screen.getByRole("button", {
          name: "Next accounting page",
        }) as HTMLButtonElement
      ).disabled,
    ).toBe(true);
    await userEvent.selectOptions(
      screen.getByLabelText("Accounting category"),
      "INCOME",
    );
    expect(within(table).getAllByRole("row").length).toBe(26);
    expect(
      (
        screen.getByRole("button", {
          name: "Previous accounting page",
        }) as HTMLButtonElement
      ).disabled,
    ).toBe(true);
  });

  it("shows absent FX as unavailable rather than a zero amount", async () => {
    vi.spyOn(knkApi, "get").mockResolvedValue({
      ...activity,
      items: [
        { ...income, base_amount: null, fx_rate: null, capitalized_base: null },
      ],
    });
    renderLedger(<AccountingActivity portfolioKey="book" runId="run-1" />);
    const table = await screen.findByRole("table", {
      name: "Accounting component records",
    });
    expect(within(table).getAllByText("--").length).toBe(2);
    expect(within(table).queryByText("0.00")).toBeNull();
  });

  it("distinguishes historical unavailability from empty available data", async () => {
    vi.spyOn(knkApi, "get").mockResolvedValue({
      state: "UNAVAILABLE",
      items: [],
      valuation_run_id: "old",
      warnings: ["This run predates accounting snapshots"],
    });
    renderLedger(<AccountingActivity portfolioKey="book" runId="old" />);
    expect(
      await screen.findByText("This run predates accounting snapshots"),
    ).toBeTruthy();
    expect(screen.queryByRole("table")).toBeNull();
    expect(screen.queryByText("No accounting components")).toBeNull();
  });

  it("renders an empty category without inventing component rows", async () => {
    vi.spyOn(knkApi, "get").mockResolvedValue(activity);
    renderLedger(<AccountingActivity portfolioKey="book" runId="run-1" />);
    await userEvent.selectOptions(
      await screen.findByLabelText("Accounting category"),
      "LIABILITY",
    );
    expect(screen.getByText("No accounting components")).toBeTruthy();
    expect(screen.getByText("0 records")).toBeTruthy();
  });

  it("reports a query error without pretending records were loaded", async () => {
    vi.spyOn(knkApi, "get").mockRejectedValue(
      new Error("Run not found in portfolio"),
    );
    renderLedger(<AccountingActivity portfolioKey="book" runId="missing" />);
    expect(await screen.findByRole("alert")).toHaveProperty(
      "textContent",
      "Run not found in portfolio",
    );
    expect(screen.queryByRole("table")).toBeNull();
  });
});

describe("balance adjustment controls", () => {
  it("requires a signed amount and meaningful reason before recording", async () => {
    vi.spyOn(knkApi, "get").mockResolvedValue({ items: [] });
    renderLedger(<BalanceEditor portfolioKey="book" />);
    await screen.findByText("No balance adjustments");
    const submit = screen.getByRole("button", {
      name: "Record adjustment",
    }) as HTMLButtonElement;
    expect(submit.disabled).toBe(true);
    await userEvent.type(
      screen.getByLabelText("Signed adjustment amount"),
      "-25",
    );
    await userEvent.type(screen.getByLabelText("Adjustment reason"), "    ");
    expect(submit.disabled).toBe(true);
    await userEvent.clear(screen.getByLabelText("Adjustment reason"));
    await userEvent.type(
      screen.getByLabelText("Adjustment reason"),
      "Reverse settled accrual",
    );
    expect(submit.disabled).toBe(false);
  });

  it("sends exact input strings and refreshes the affected portfolio queries", async () => {
    vi.spyOn(knkApi, "get").mockResolvedValue({ items: [] });
    const post = vi
      .spyOn(knkApi, "post")
      .mockResolvedValue({ id: "adjustment" });
    const { client } = renderLedger(<BalanceEditor portfolioKey="book" />);
    const invalidate = vi.spyOn(client, "invalidateQueries");
    await userEvent.selectOptions(
      screen.getByLabelText("Balance bucket"),
      "payables",
    );
    await userEvent.selectOptions(
      screen.getByLabelText("Balance currency"),
      "USD",
    );
    await userEvent.type(
      screen.getByLabelText("Signed adjustment amount"),
      "12.12345678",
    );
    await userEvent.type(
      screen.getByLabelText("Adjustment reason"),
      "Accrue vendor invoice",
    );
    await userEvent.click(
      screen.getByRole("button", { name: "Record adjustment" }),
    );
    await waitFor(() =>
      expect(post).toHaveBeenCalledWith("/api/v1/portfolios/book/balances", {
        effective_date: new Date().toISOString().slice(0, 10),
        bucket: "payables",
        currency: "USD",
        amount: "12.12345678",
        reason: "Accrue vendor invoice",
      }),
    );
    await waitFor(() =>
      expect(invalidate).toHaveBeenCalledWith({
        queryKey: ["terminal-portfolio"],
      }),
    );
    expect(invalidate).toHaveBeenCalledWith({
      queryKey: ["ledger-accounting", "book"],
    });
    expect(screen.getByLabelText("Signed adjustment amount")).toHaveProperty(
      "value",
      "",
    );
    expect(screen.getByText("Balance adjustment recorded")).toBeTruthy();
  });

  it("preserves failed input and displays the server validation reason", async () => {
    vi.spyOn(knkApi, "get").mockResolvedValue({ items: [] });
    vi.spyOn(knkApi, "post").mockRejectedValue(
      new Error("Adjustment makes payables negative"),
    );
    renderLedger(<BalanceEditor portfolioKey="book" />);
    await userEvent.type(
      screen.getByLabelText("Signed adjustment amount"),
      "-100",
    );
    await userEvent.type(
      screen.getByLabelText("Adjustment reason"),
      "Reverse old payable",
    );
    await userEvent.click(
      screen.getByRole("button", { name: "Record adjustment" }),
    );
    expect(await screen.findByRole("alert")).toHaveProperty(
      "textContent",
      "Adjustment makes payables negative",
    );
    expect(screen.getByLabelText("Signed adjustment amount")).toHaveProperty(
      "value",
      "-100",
    );
    expect(screen.queryByText("Balance adjustment recorded")).toBeNull();
  });

  it("shows append-only adjustments with their original reason", async () => {
    vi.spyOn(knkApi, "get").mockResolvedValue({
      items: [
        {
          id: "balance",
          effective_date: "2026-01-06",
          bucket: "accrued_fees",
          currency: "SGD",
          amount: "-10",
          reason: "Reverse paid fee",
        },
      ],
    });
    renderLedger(<BalanceEditor portfolioKey="book" />);
    const table = await screen.findByRole("table", {
      name: "Balance adjustment history",
    });
    expect(within(table).getByText("-10.00")).toBeTruthy();
    expect(within(table).getByText("Accrued fees")).toBeTruthy();
    expect(within(table).getByText("Reverse paid fee")).toBeTruthy();
  });
});
