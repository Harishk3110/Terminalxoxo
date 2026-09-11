// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, screen, waitFor, within } from "@testing-library/react";
import { QueryObserver } from "@tanstack/react-query";
import userEvent from "@testing-library/user-event";
import { knkApi } from "@knk/api-client";
import { TransactionEntryDialog } from "../components/ledger/transaction-entry";
import { TransactionDetails } from "../components/ledger/transaction-details";
import {
  transactionTypes,
  type EntryOptions,
} from "../components/ledger/entry-draft";
import { metadata, transaction } from "./fixtures/accounting";
import { renderLedger } from "./ledger-render";

const options: EntryOptions = {
  portfolio: metadata,
  transaction_types: [...transactionTypes],
  currencies: ["SGD", "USD", "EUR"],
  strategies: [
    { id: "strategy-1", name: "Value allocation", state: "RESEARCH" },
  ],
  theses: [
    {
      id: "thesis-1",
      title: "Apple cash flows",
      state: "DRAFT",
      instrument_id: "AAPL",
    },
  ],
};

beforeEach(() => {
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
    if (path.endsWith("/entry-options")) return options as T;
    return {
      instruments: [
        { id: "aapl", symbol: "AAPL", name: "Apple Inc.", currency: "USD" },
      ],
    } as T;
  });
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

async function choose(type: string) {
  const select = screen.getByRole("combobox", { name: "Transaction type" });
  await waitFor(() => expect(select.closest("fieldset")?.disabled).toBe(false));
  await userEvent.selectOptions(select, type);
}

describe("manual transaction entry", () => {
  it("closes using its transaction-specific accessible control", async () => {
    const close = vi.fn();
    renderLedger(
      <TransactionEntryDialog portfolioKey="book" onClose={close} />,
    );
    await userEvent.click(
      screen.getByRole("button", { name: "Close transaction dialog" }),
    );
    expect(close).toHaveBeenCalledOnce();
  });
  it("loads actual portfolio accounts and research links and offers all nineteen ledger types", async () => {
    renderLedger(
      <TransactionEntryDialog portfolioKey="book" onClose={() => {}} />,
    );
    await choose("BUY");
    expect(
      screen.getByRole("option", { name: "Internal ledger" }),
    ).toBeTruthy();
    expect(
      screen.getByRole("option", { name: "Value allocation / RESEARCH" }),
    ).toBeTruthy();
    expect(
      screen.getByRole("option", { name: "Apple cash flows / DRAFT" }),
    ).toBeTruthy();
    expect(
      within(screen.getByLabelText("Transaction type")).getAllByRole("option"),
    ).toHaveLength(19);
    expect(screen.getByText("MANUAL RECORD")).toBeTruthy();
    expect(knkApi.get).toHaveBeenCalledWith(
      "/api/v1/portfolios/book/entry-options",
      expect.any(AbortSignal),
    );
  });

  it("posts the exact recorded trade and audit references and refreshes dependent views", async () => {
    const post = vi.spyOn(knkApi, "post").mockResolvedValue(transaction);
    const close = vi.fn();
    const { client } = renderLedger(
      <TransactionEntryDialog portfolioKey="book" onClose={close} />,
    );
    const invalidate = vi.spyOn(client, "invalidateQueries");
    await choose("BUY");
    await userEvent.clear(screen.getByLabelText("Quantity"));
    await userEvent.type(screen.getByLabelText("Quantity"), "1.12345678");
    await userEvent.type(
      screen.getByLabelText("Price", { exact: true }),
      "100",
    );
    await userEvent.selectOptions(screen.getByLabelText("Account"), "account");
    await userEvent.type(
      screen.getByLabelText("External reference"),
      "statement:7",
    );
    await userEvent.type(
      screen.getByLabelText("Broker execution reference"),
      "paper:42",
    );
    await userEvent.selectOptions(
      screen.getByLabelText("Strategy"),
      "strategy-1",
    );
    await userEvent.selectOptions(screen.getByLabelText("Thesis"), "thesis-1");
    await userEvent.click(
      screen.getByRole("button", { name: "Record transaction" }),
    );
    await waitFor(() =>
      expect(post).toHaveBeenCalledWith(
        "/api/v1/portfolios/book/transactions",
        expect.objectContaining({
          transaction_type: "BUY",
          symbol: "AAPL",
          currency: "USD",
          quantity: "1.12345678",
          price: "100",
          account_id: "account",
          external_reference: "statement:7",
          broker_execution_id: "paper:42",
          strategy_id: "strategy-1",
          thesis_id: "thesis-1",
          metadata: {},
        }),
      ),
    );
    expect(vi.mocked(post).mock.calls[0][1]).not.toHaveProperty("amount");
    await waitFor(() => expect(close).toHaveBeenCalledOnce());
    expect(invalidate).toHaveBeenCalledWith({
      queryKey: ["terminal-portfolio"],
    });
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ["operating-trades"] });
    expect(invalidate).toHaveBeenCalledWith({
      queryKey: ["ledger-accounting", "book"],
    });
  });

  it.each([
    ["operating-trades"],
    ["terminal-portfolio"],
    ["ledger-summary", "book"],
    ["ledger-accounting", "book"],
    ["ledger-transactions", "book"],
  ])(
    "replaces the pending initial %s read after a successful entry",
    async (...queryKey) => {
      const post = vi.spyOn(knkApi, "post").mockResolvedValue(transaction);
      const close = vi.fn();
      const { client } = renderLedger(
        <TransactionEntryDialog portfolioKey="book" onClose={close} />,
      );
      let finishOldRead: (value: string[]) => void = () => {};
      let oldSignal: AbortSignal | undefined;
      const oldRead = new Promise<string[]>((resolve) => {
        finishOldRead = resolve;
      });
      const read = vi.fn(({ signal }: { signal: AbortSignal }) => {
        if (!oldSignal) {
          oldSignal = signal;
          return oldRead;
        }
        return Promise.resolve([transaction.id]);
      });
      const observer = new QueryObserver(client, { queryKey, queryFn: read });
      const unsubscribe = observer.subscribe(() => {});
      try {
        await waitFor(() => expect(read).toHaveBeenCalledOnce());
        await choose("TAX");
        await userEvent.type(
          screen.getByLabelText("Gross amount", { exact: true }),
          "1.23",
        );
        await userEvent.click(
          screen.getByRole("button", { name: "Record transaction" }),
        );
        await waitFor(() => expect(post).toHaveBeenCalledOnce());
        await waitFor(() => expect(close).toHaveBeenCalledOnce());
        expect(read).toHaveBeenCalledTimes(2);
        expect(oldSignal?.aborted).toBe(true);
        expect(observer.getCurrentResult().data).toEqual([transaction.id]);
        await act(async () => {
          finishOldRead([]);
          await oldRead;
        });
        expect(observer.getCurrentResult().data).toEqual([transaction.id]);
      } finally {
        finishOldRead([]);
        unsubscribe();
        client.clear();
      }
    },
  );

  it("defaults cash to the book currency and never offers an identical FX pair", async () => {
    renderLedger(
      <TransactionEntryDialog portfolioKey="book" onClose={() => {}} />,
    );
    await choose("FX_CONVERSION");
    expect((screen.getByLabelText("Currency") as HTMLSelectElement).value).toBe(
      "SGD",
    );
    expect(
      (screen.getByLabelText("Received currency") as HTMLSelectElement).value,
    ).toBe("USD");
    await userEvent.selectOptions(screen.getByLabelText("Currency"), "USD");
    expect(
      (screen.getByLabelText("Received currency") as HTMLSelectElement).value,
    ).toBe("SGD");
    expect(
      (
        within(screen.getByLabelText("Received currency")).getByRole("option", {
          name: "USD",
        }) as HTMLOptionElement
      ).disabled,
    ).toBe(true);
    expect(screen.queryByLabelText("Security")).toBeNull();
  });

  it("switches cash and security transfers without submitting hidden trade fields", async () => {
    const post = vi.spyOn(knkApi, "post").mockResolvedValue({ id: "transfer" });
    renderLedger(
      <TransactionEntryDialog portfolioKey="book" onClose={() => {}} />,
    );
    await choose("TRANSFER_IN");
    expect(screen.queryByLabelText("Quantity")).toBeNull();
    await userEvent.click(screen.getByRole("button", { name: "Security" }));
    expect(screen.getByLabelText("Quantity")).toBeTruthy();
    await userEvent.click(screen.getByRole("button", { name: "Cash" }));
    await userEvent.type(
      screen.getByLabelText("Gross amount", { exact: true }),
      "25",
    );
    await userEvent.click(
      screen.getByRole("button", { name: "Record transaction" }),
    );
    await waitFor(() => expect(post).toHaveBeenCalledOnce());
    expect(vi.mocked(post).mock.calls[0][1]).toMatchObject({
      currency: "SGD",
      amount: "25",
    });
    expect(vi.mocked(post).mock.calls[0][1]).not.toHaveProperty("symbol");
  });

  it("exposes the correct reverse-split, spinoff and merger inputs", async () => {
    renderLedger(
      <TransactionEntryDialog portfolioKey="book" onClose={() => {}} />,
    );
    await choose("REVERSE_SPLIT");
    expect(screen.getByLabelText("New shares per old share")).toBeTruthy();
    expect(screen.queryByLabelText("Price")).toBeNull();
    await choose("SPINOFF");
    expect(screen.getByLabelText("Child shares received")).toBeTruthy();
    expect(screen.getByLabelText("Child cost allocation")).toBeTruthy();
    await choose("MERGER");
    expect(
      screen.getByLabelText("Successor shares per parent share"),
    ).toBeTruthy();
    expect(screen.getByLabelText("Cash per parent share")).toBeTruthy();
    expect(screen.queryByLabelText("Child shares received")).toBeNull();
  });

  it("requires an adjustment reason and hides separate charges for standalone fees", async () => {
    renderLedger(
      <TransactionEntryDialog portfolioKey="book" onClose={() => {}} />,
    );
    await choose("OTHER_ADJUSTMENT");
    expect(
      (screen.getByLabelText("Adjustment reason") as HTMLInputElement).required,
    ).toBe(true);
    expect(screen.getByLabelText("Adjustment direction")).toBeTruthy();
    await choose("FEE");
    expect(screen.queryByLabelText("Adjustment reason")).toBeNull();
    expect(screen.queryByLabelText("Commission")).toBeNull();
    expect(screen.queryByLabelText("Fee", { exact: true })).toBeNull();
    expect(screen.getByLabelText("Gross amount")).toBeTruthy();
  });

  it("disables SHORT when portfolio policy disallows it", async () => {
    vi.mocked(knkApi.get).mockImplementation(async <T,>(path: string) => {
      return (
        path.endsWith("/entry-options")
          ? {
              ...options,
              portfolio: { ...metadata, configuration: { allow_short: false } },
            }
          : { instruments: [] }
      ) as T;
    });
    renderLedger(
      <TransactionEntryDialog portfolioKey="book" onClose={() => {}} />,
    );
    await waitFor(() =>
      expect(
        (screen.getByRole("option", { name: "SHORT" }) as HTMLOptionElement)
          .disabled,
      ).toBe(true),
    );
  });

  it("retains the entered values and surfaces server rejection without closing", async () => {
    vi.spyOn(knkApi, "post").mockRejectedValue(
      new Error("Trade timestamp is inconsistent with the supplied trade date"),
    );
    const close = vi.fn();
    renderLedger(
      <TransactionEntryDialog portfolioKey="book" onClose={close} />,
    );
    await choose("DEPOSIT");
    await userEvent.type(screen.getByLabelText("Gross amount"), "42.12");
    await userEvent.click(
      screen.getByRole("button", { name: "Record transaction" }),
    );
    expect((await screen.findByRole("alert")).textContent).toContain(
      "inconsistent",
    );
    expect(
      (screen.getByLabelText("Gross amount") as HTMLInputElement).value,
    ).toBe("42.12");
    expect(close).not.toHaveBeenCalled();
  });

  it("does not permit a write when portfolio options fail to load", async () => {
    vi.mocked(knkApi.get).mockRejectedValue(new Error("Portfolio not found"));
    renderLedger(
      <TransactionEntryDialog portfolioKey="missing" onClose={() => {}} />,
    );
    await screen.findAllByRole("alert");
    expect(
      (
        screen.getByRole("button", {
          name: "Record transaction",
        }) as HTMLButtonElement
      ).disabled,
    ).toBe(true);
    expect(
      screen.getByLabelText("Quantity").closest("fieldset")?.disabled,
    ).toBe(true);
  });
});

describe("transaction cash and audit details", () => {
  it("shows the original reference and read-only broker provenance without displaying the deduplication hash as identity", () => {
    renderLedger(<TransactionDetails transaction={transaction} />);
    expect(screen.getByText("statement-001")).toBeTruthy();
    expect(screen.getByText("paper-reference")).toBeTruthy();
    expect(screen.getByText("INTERNAL_ONLY")).toBeTruthy();
    expect(screen.queryByText("deduplication-key")).toBeNull();
    expect(
      screen.getByText(
        "PROVENANCE_ONLY; same-day replay retains ledger record order",
      ),
    ).toBeTruthy();
    expect(
      screen.getByRole("table", { name: "Transaction cash legs" }).textContent,
    ).toContain("-1,002.00000000");
  });

  it("preserves both currencies in an FX event and displays the server's aggregate", () => {
    renderLedger(
      <TransactionDetails
        transaction={{
          ...transaction,
          currency: "USD",
          net_amount: "-101",
          net_base_value: "-131.3",
          net_cash_base: "-1.3",
          net_cash_by_currency: [
            { currency: "USD", amount: "-101", base_amount: "-131.3" },
            { currency: "SGD", amount: "130", base_amount: "130" },
          ],
        }}
      />,
    );
    const table = screen.getByRole("table", { name: "Transaction cash legs" });
    expect(within(table).getByRole("rowheader", { name: "USD" })).toBeTruthy();
    expect(within(table).getByRole("rowheader", { name: "SGD" })).toBeTruthy();
    expect(
      screen.getByText("Total cash effect in base").nextElementSibling
        ?.textContent,
    ).toBe("-1.30000000");
  });

  it("does not turn unrecorded timestamps or void cash into invented zero values", () => {
    renderLedger(
      <TransactionDetails
        transaction={{
          ...transaction,
          ledger_state: "VOID",
          trade_timestamp: null,
          trade_timestamp_state: "NOT_RECORDED",
          net_amount: null,
          net_base_value: null,
          net_cash_base: null,
          net_cash_by_currency: [],
          cash_effect_state: "NOT_REPLAYED",
          context_warnings: ["Legacy timestamp is unvalidated"],
        }}
      />,
    );
    expect(screen.getByText("No replayed cash legs")).toBeTruthy();
    expect(screen.getByText("NOT_REPLAYED")).toBeTruthy();
    expect(
      screen.getByText("Net amount / SGD").nextElementSibling?.textContent,
    ).toBe("--");
    expect(
      screen.getByText("Trade timestamp / SGT").nextElementSibling?.textContent,
    ).toBe("Not observed");
    expect(screen.getByRole("status").textContent).toBe(
      "Legacy timestamp is unvalidated",
    );
  });
});
