// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { knkApi } from "@knk/api-client";
import { PortfolioDirectory } from "../components/ledger/portfolio-directory";
import type { PortfolioRecord } from "../components/ledger/portfolio-create";
import { summary, transaction } from "./fixtures/accounting";
import {
  mainLedger,
  researchLedger,
  creationOptions,
} from "./fixtures/portfolios";
import { renderLedger } from "./ledger-render";

let records: PortfolioRecord[];
let trades: (typeof transaction)[];

beforeEach(() => {
  records = [mainLedger, researchLedger];
  trades = [
    {
      ...transaction,
      id: "main-trade",
      portfolio_id: mainLedger.id,
      notes: "Main book record",
    },
    {
      ...transaction,
      id: "research-trade",
      portfolio_id: researchLedger.id,
      currency: "USD",
      notes: "Research book record",
    },
  ];
  Object.defineProperties(HTMLDialogElement.prototype, {
    showModal: {
      configurable: true,
      value: function (this: HTMLDialogElement) {
        this.setAttribute("open", "");
      },
    },
    close: {
      configurable: true,
      value: function (this: HTMLDialogElement) {
        this.removeAttribute("open");
      },
    },
  });
  vi.spyOn(knkApi, "get").mockImplementation(async <T,>(path: string) => {
    if (path === "/api/v1/portfolios") return { items: records } as T;
    if (path.endsWith("/creation-options")) return creationOptions as T;
    if (path.startsWith("/api/v1/search")) return { instruments: [] } as T;
    const record = records.find((row) =>
      path.startsWith("/api/v1/portfolios/" + row.id),
    );
    if (!record) throw new Error("Unexpected portfolio query: " + path);
    if (path.endsWith("/summary"))
      return {
        ...summary,
        portfolio: {
          ...summary.portfolio,
          id: record.id,
          code: record.code,
          base_currency: record.base_currency,
        },
      } as T;
    if (path.endsWith("/entry-options"))
      return {
        portfolio: record,
        transaction_types: ["BUY", "DEPOSIT"],
        currencies: creationOptions.currencies,
        strategies: [],
        theses: [],
      } as T;
    if (path.endsWith("/transactions"))
      return {
        items: trades.filter((row) => row.portfolio_id === record.id),
      } as T;
    if (path.includes("/transactions/"))
      return trades.find((row) => path.endsWith("/" + row.id)) as T;
    return record as T;
  });
});
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

async function selectResearch() {
  await userEvent.click(
    await screen.findByRole("button", { name: "Select ledger RESEARCH" }),
  );
  return screen.findByRole("region", { name: "Selected ledger / RESEARCH" });
}

describe("portfolio directory scoping", () => {
  it("opens on KNK_MAIN with actual metadata, accounts and base-currency units", async () => {
    renderLedger(<PortfolioDirectory onClose={() => {}} />);
    const selected = await screen.findByRole("region", {
      name: "Selected ledger / KNK_MAIN",
    });
    expect(
      within(selected).getByText("Reference capital / SGD").nextElementSibling
        ?.textContent,
    ).toBe("70,000.00000000");
    expect(within(selected).getByText("DEMO LEDGER")).toBeTruthy();
    expect(within(selected).getByText("DEFAULT")).toBeTruthy();
    expect(
      within(selected).getByText(
        "Internal ledger / INTERNAL / No broker provider",
      ),
    ).toBeTruthy();
    await screen.findByRole("button", {
      name: "Inspect transaction main-trade",
    });
    expect(
      screen.queryByRole("button", {
        name: "Inspect transaction research-trade",
      }),
    ).toBeNull();
    expect(knkApi.get).toHaveBeenCalledWith(
      "/api/v1/portfolios/main-book/summary",
      expect.any(AbortSignal),
    );
  });

  it("switches metadata and transaction reads together without changing a global default", async () => {
    const post = vi.spyOn(knkApi, "post");
    const put = vi.spyOn(knkApi, "put");
    renderLedger(<PortfolioDirectory onClose={() => {}} />);
    const selected = await selectResearch();
    expect(
      within(selected).getByText("Reference capital / USD").nextElementSibling
        ?.textContent,
    ).toBe("1,000.12345678");
    expect(
      screen.queryByRole("region", { name: "Selected ledger / KNK_MAIN" }),
    ).toBeNull();
    await screen.findByRole("button", {
      name: "Inspect transaction research-trade",
    });
    expect(
      screen.queryByRole("button", { name: "Inspect transaction main-trade" }),
    ).toBeNull();
    expect(knkApi.get).toHaveBeenCalledWith(
      "/api/v1/portfolios/research-book/transactions",
      expect.any(AbortSignal),
    );
    expect(post).not.toHaveBeenCalled();
    expect(put).not.toHaveBeenCalled();
  });

  it("opens accounting for the selected ID and returns to that same ledger", async () => {
    renderLedger(<PortfolioDirectory onClose={() => {}} />);
    await selectResearch();
    await userEvent.click(
      screen.getByRole("button", { name: "Open selected accounting" }),
    );
    await screen.findByRole("dialog", {
      name: "Portfolio accounting / RESEARCH",
    });
    expect(screen.getAllByRole("dialog")).toHaveLength(1);
    expect(knkApi.get).toHaveBeenCalledWith(
      "/api/v1/portfolios/research-book",
      expect.any(AbortSignal),
    );
    await userEvent.click(
      screen.getByRole("button", { name: "Close accounting dialog" }),
    );
    await screen.findByRole("region", { name: "Selected ledger / RESEARCH" });
    expect(
      screen
        .getByRole("button", { name: "Select ledger RESEARCH" })
        .getAttribute("aria-pressed"),
    ).toBe("true");
  });

  it("opens manual entry with the selected account options and returns without changing the selection", async () => {
    renderLedger(<PortfolioDirectory onClose={() => {}} />);
    await selectResearch();
    await userEvent.click(
      screen.getByRole("button", { name: "Record selected transaction" }),
    );
    await screen.findByRole("dialog", { name: "Record ledger transaction" });
    await waitFor(() =>
      expect(knkApi.get).toHaveBeenCalledWith(
        "/api/v1/portfolios/research-book/entry-options",
        expect.any(AbortSignal),
      ),
    );
    expect(screen.getAllByRole("dialog")).toHaveLength(1);
    await userEvent.click(
      screen.getByRole("button", { name: "Close transaction dialog" }),
    );
    await screen.findByRole("region", { name: "Selected ledger / RESEARCH" });
  });

  it("opens corrections using both the selected portfolio and the chosen immutable transaction ID", async () => {
    renderLedger(<PortfolioDirectory onClose={() => {}} />);
    await selectResearch();
    await userEvent.click(
      await screen.findByRole("button", {
        name: "Inspect transaction research-trade",
      }),
    );
    await screen.findByLabelText("Price");
    expect(screen.getByText("Portfolio RESEARCH")).toBeTruthy();
    expect(knkApi.get).toHaveBeenCalledWith(
      "/api/v1/portfolios/research-book/transactions/research-trade",
      expect.any(AbortSignal),
    );
    expect(
      screen.queryByRole("dialog", { name: "Portfolio ledgers" }),
    ).toBeNull();
  });

  it("filters the directory without silently selecting another ledger", async () => {
    renderLedger(<PortfolioDirectory onClose={() => {}} />);
    await selectResearch();
    await userEvent.type(
      screen.getByLabelText("Filter portfolios"),
      "KNK_MAIN",
    );
    const table = screen.getByRole("table", { name: "Portfolio directory" });
    expect(within(table).getAllByRole("row")).toHaveLength(2);
    expect(
      within(table).queryByRole("button", { name: "Select ledger RESEARCH" }),
    ).toBeNull();
    expect(
      screen.getByRole("region", { name: "Selected ledger / RESEARCH" }),
    ).toBeTruthy();
    await userEvent.clear(screen.getByLabelText("Filter portfolios"));
    await userEvent.type(
      screen.getByLabelText("Filter portfolios"),
      "no match",
    );
    expect(screen.getByText("No matching portfolio ledgers")).toBeTruthy();
  });

  it("paginates selected transactions and resets paging on a text filter", async () => {
    trades = Array.from({ length: 27 }, (_, index) => ({
      ...transaction,
      portfolio_id: researchLedger.id,
      id: "research-" + index,
      notes: index === 0 ? "Opening allocation" : "Subsequent trade",
    }));
    renderLedger(<PortfolioDirectory onClose={() => {}} />);
    await selectResearch();
    const table = await screen.findByRole("table", {
      name: "Selected ledger transactions",
    });
    expect(within(table).getAllByRole("row")).toHaveLength(26);
    await userEvent.click(
      screen.getByRole("button", { name: "Next transaction page" }),
    );
    expect(within(table).getAllByRole("row")).toHaveLength(3);
    expect(screen.getByText("Page 2 / 2")).toBeTruthy();
    await userEvent.type(
      screen.getByLabelText("Filter ledger transactions"),
      "Opening allocation",
    );
    expect(within(table).getAllByRole("row")).toHaveLength(2);
    expect(screen.getByText("Page 1 / 1")).toBeTruthy();
    expect(
      screen.getByRole("button", { name: "Inspect transaction research-0" }),
    ).toBeTruthy();
  });

  it("selects the returned created ledger and retains it through a directory refetch", async () => {
    records = [mainLedger];
    const post = vi.spyOn(knkApi, "post").mockImplementation(async <T,>() => {
      records = [...records, researchLedger];
      return researchLedger as T;
    });
    const { client } = renderLedger(<PortfolioDirectory onClose={() => {}} />);
    const invalidate = vi.spyOn(client, "invalidateQueries");
    await userEvent.click(
      screen.getByRole("button", { name: "Create portfolio ledger" }),
    );
    await userEvent.type(
      await screen.findByLabelText("Portfolio code"),
      "research",
    );
    await userEvent.type(
      screen.getByLabelText("Portfolio name"),
      "Research allocation",
    );
    await userEvent.type(
      screen.getByLabelText("Opening contribution"),
      "1000.12345678",
    );
    await userEvent.selectOptions(
      screen.getByLabelText("Base currency"),
      "USD",
    );
    await userEvent.click(
      screen.getByRole("button", { name: "Create internal ledger" }),
    );
    await screen.findByRole("region", { name: "Selected ledger / RESEARCH" });
    expect(post).toHaveBeenCalledTimes(1);
    expect(screen.getByText("Ledger RESEARCH created")).toBeTruthy();
    expect(
      client
        .getQueryData<{ items: PortfolioRecord[] }>(["ledger-portfolios"])
        ?.items.map((row) => row.id),
    ).toEqual(["main-book", "research-book"]);
    expect(invalidate).toHaveBeenCalledWith({
      queryKey: ["ledger-portfolios"],
    });
    expect(screen.getAllByRole("dialog")).toHaveLength(1);
  });

  it("returns from cancelled creation without posting or losing the selected portfolio", async () => {
    const post = vi.spyOn(knkApi, "post");
    renderLedger(<PortfolioDirectory onClose={() => {}} />);
    await selectResearch();
    await userEvent.click(
      screen.getByRole("button", { name: "Create portfolio ledger" }),
    );
    await screen.findByLabelText("Portfolio code");
    await userEvent.click(
      screen.getByRole("button", { name: "Cancel portfolio creation" }),
    );
    await screen.findByRole("region", { name: "Selected ledger / RESEARCH" });
    expect(post).not.toHaveBeenCalled();
  });

  it("does not show another portfolio as a default when the main book is absent", async () => {
    records = [researchLedger];
    renderLedger(<PortfolioDirectory onClose={() => {}} />);
    await screen.findByRole("button", { name: "Select ledger RESEARCH" });
    expect(
      screen.queryByRole("button", { name: "Record selected transaction" }),
    ).toBeNull();
    expect(vi.mocked(knkApi.get).mock.calls.map(([path]) => path)).toEqual([
      "/api/v1/portfolios",
    ]);
  });
});
