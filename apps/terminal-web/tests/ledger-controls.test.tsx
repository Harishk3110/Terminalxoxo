// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { knkApi } from "@knk/api-client";
import { useState } from "react";
import { AccountingDialog } from "../components/ledger/accounting-dialog";
import { TransactionCorrectionDialog } from "../components/ledger/transaction-correction";
import { metadata, summary, transaction } from "./fixtures/accounting";
import { positionSnapshot } from "./fixtures/position";
import { renderLedger } from "./ledger-render";

beforeEach(() => {
  // jsdom lacks native dialog methods; browser tests cover focus and Escape.
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
    if (path.endsWith("/summary")) return summary as T;
    if (path.includes("/positions/")) return positionSnapshot as T;
    if (path.includes("/transactions/")) return transaction as T;
    return metadata as T;
  });
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe("accounting controls", () => {
  it("opens position detail from the saved accounting run", async () => {
    renderLedger(<AccountingDialog portfolioKey="book" onClose={() => {}} />);
    await screen.findByLabelText("Cost-basis method");
    await userEvent.click(screen.getByRole("button", { name: "Positions" }));
    await screen.findByText("AAA / Test security");
    expect(knkApi.get).toHaveBeenCalledWith("/api/v1/portfolios/book/positions/AAA?run_id=run-1", expect.any(AbortSignal));
    expect(screen.getByText("Base market value / SGD")).toBeTruthy();
  });
  it("returns focus to the launch control after the dialog unmounts", async () => {
    function Launcher() {
      const [open, setOpen] = useState(false);
      return (
        <>
          <button onClick={() => setOpen(true)}>Open accounting</button>
          {open && (
            <AccountingDialog
              portfolioKey="book"
              onClose={() => setOpen(false)}
            />
          )}
        </>
      );
    }
    renderLedger(<Launcher />);
    const trigger = screen.getByRole("button", { name: "Open accounting" });
    await userEvent.click(trigger);
    await userEvent.click(await screen.findByLabelText("Cost-basis method"));
    expect(document.activeElement).not.toBe(trigger);
    await userEvent.click(
      screen.getByRole("button", { name: "Close accounting dialog" }),
    );
    expect(document.activeElement).toBe(trigger);
  });
  it("loads the saved policy and requires a changed policy plus reason", async () => {
    renderLedger(<AccountingDialog portfolioKey="book" onClose={() => {}} />);
    const method = (await screen.findByLabelText(
      "Cost-basis method",
    )) as HTMLSelectElement;
    expect(method.value).toBe("AVERAGE");
    const save = screen.getByRole("button", {
      name: "Save policy",
    }) as HTMLButtonElement;
    expect(save.disabled).toBe(true);
    await userEvent.selectOptions(method, "FIFO");
    expect(save.disabled).toBe(true);
    await userEvent.type(
      screen.getByLabelText("Policy change reason"),
      "Adopt FIFO matching",
    );
    expect(save.disabled).toBe(false);
  });
  it("submits explicit boolean switches and invalidates portfolio results", async () => {
    const put = vi.spyOn(knkApi, "put").mockResolvedValue(metadata);
    const { client } = renderLedger(
      <AccountingDialog portfolioKey="book" onClose={() => {}} />,
    );
    const invalidate = vi.spyOn(client, "invalidateQueries");
    await userEvent.selectOptions(
      await screen.findByLabelText("Cost-basis method"),
      "FIFO",
    );
    await userEvent.click(
      screen.getByLabelText("Capitalize transaction commissions"),
    );
    await userEvent.type(
      screen.getByLabelText("Policy change reason"),
      "Reconcile accounting treatment",
    );
    await userEvent.click(screen.getByRole("button", { name: "Save policy" }));
    await waitFor(() =>
      expect(put).toHaveBeenCalledWith(
        "/api/v1/portfolios/book/accounting-policy",
        {
          method: "FIFO",
          capitalize_commissions: true,
          capitalize_fees: false,
          reason: "Reconcile accounting treatment",
        },
      ),
    );
    await waitFor(() =>
      expect(invalidate).toHaveBeenCalledWith({
        queryKey: ["terminal-portfolio"],
      }),
    );
  });
  it("shows settlement cash and lot provenance in separate views", async () => {
    renderLedger(<AccountingDialog portfolioKey="book" onClose={() => {}} />);
    await screen.findByLabelText("Cost-basis method");
    await userEvent.click(screen.getByRole("button", { name: "Cash" }));
    expect(screen.getByRole("columnheader", { name: "Payable" })).toBeTruthy();
    expect(screen.getByText("IDENTITY")).toBeTruthy();
    expect(screen.getByText("Economic cash / SGD")).toBeTruthy();
    await userEvent.click(screen.getByRole("button", { name: "Lots" }));
    expect(screen.getByText("buy-1")).toBeTruthy();
    expect(screen.getByText("AAA")).toBeTruthy();
    expect(screen.getByText("Run run-1")).toBeTruthy();
  });
  it("reports API failure without reporting a successful policy save", async () => {
    vi.spyOn(knkApi, "put").mockRejectedValue(
      new Error("Accounting policy is unchanged"),
    );
    renderLedger(<AccountingDialog portfolioKey="book" onClose={() => {}} />);
    await userEvent.selectOptions(
      await screen.findByLabelText("Cost-basis method"),
      "FIFO",
    );
    await userEvent.type(
      screen.getByLabelText("Policy change reason"),
      "New policy request",
    );
    await userEvent.click(screen.getByRole("button", { name: "Save policy" }));
    expect((await screen.findByRole("alert")).textContent).toContain(
      "Accounting policy is unchanged",
    );
    expect(screen.queryByText("Accounting policy saved")).toBeNull();
  });
  it("closes with its named icon control", async () => {
    const close = vi.fn();
    renderLedger(<AccountingDialog portfolioKey="book" onClose={close} />);
    await userEvent.click(
      screen.getByRole("button", { name: "Close accounting dialog" }),
    );
    expect(close).toHaveBeenCalledOnce();
  });
});

describe("transaction correction controls", () => {
  it("preserves exact quantities and submits the loaded optimistic version", async () => {
    const put = vi.spyOn(knkApi, "put").mockResolvedValue({
      transaction_id: "buy-1",
      revision_id: "rev-1",
      audit_version: 2,
      ledger_state: "ACTIVE",
    });
    renderLedger(
      <TransactionCorrectionDialog
        transactionId="buy-1"
        portfolioKey="book"
        onClose={() => {}}
      />,
    );
    const quantity = (await screen.findByLabelText(
      "Quantity",
    )) as HTMLInputElement;
    expect(quantity.value).toBe("10.00000000");
    await userEvent.clear(quantity);
    await userEvent.type(quantity, "8.12345678");
    await userEvent.type(
      screen.getByLabelText("Correction reason"),
      "Correct source allocation",
    );
    await userEvent.click(
      screen.getByRole("button", { name: "Record correction" }),
    );
    await waitFor(() =>
      expect(put).toHaveBeenCalledWith(
        "/api/v1/portfolios/book/transactions/buy-1",
        {
          expected_version: 1,
          reason: "Correct source allocation",
          changes: { quantity: "8.12345678" },
        },
      ),
    );
    expect(screen.queryByLabelText("Gross amount")).toBeNull();
  });
  it("requires confirmation and reason before voiding", async () => {
    const remove = vi.spyOn(knkApi, "delete").mockResolvedValue({
      transaction_id: "buy-1",
      revision_id: "rev-1",
      audit_version: 2,
      ledger_state: "VOID",
    });
    renderLedger(
      <TransactionCorrectionDialog
        transactionId="buy-1"
        portfolioKey="book"
        onClose={() => {}}
      />,
    );
    await screen.findByLabelText("Quantity");
    await userEvent.click(screen.getByRole("button", { name: "Void" }));
    const save = screen.getByRole("button", {
      name: "Record void",
    }) as HTMLButtonElement;
    expect(save.disabled).toBe(true);
    await userEvent.type(
      screen.getByLabelText("Void reason"),
      "Duplicate ledger record",
    );
    expect(save.disabled).toBe(true);
    await userEvent.click(
      screen.getByLabelText("Confirm void of this ledger transaction"),
    );
    await userEvent.click(save);
    await waitFor(() =>
      expect(remove).toHaveBeenCalledWith(
        "/api/v1/portfolios/book/transactions/buy-1",
        { expected_version: 1, reason: "Duplicate ledger record" },
      ),
    );
  });
  it("keeps the draft visible when the server rejects a stale version", async () => {
    vi.spyOn(knkApi, "put").mockRejectedValue(
      new Error("Transaction changed; reload its current audit version"),
    );
    renderLedger(
      <TransactionCorrectionDialog
        transactionId="buy-1"
        portfolioKey="book"
        onClose={() => {}}
      />,
    );
    const quantity = (await screen.findByLabelText(
      "Quantity",
    )) as HTMLInputElement;
    await userEvent.clear(quantity);
    await userEvent.type(quantity, "9");
    await userEvent.type(
      screen.getByLabelText("Correction reason"),
      "Correct allocation",
    );
    await userEvent.click(
      screen.getByRole("button", { name: "Record correction" }),
    );
    expect((await screen.findByRole("alert")).textContent).toContain(
      "reload its current audit version",
    );
    expect(quantity.value).toBe("9");
    expect(screen.queryByText("Revision 2 recorded")).toBeNull();
  });
  it("disables correction fields for a voided record", async () => {
    vi.mocked(knkApi.get).mockResolvedValue({
      ...transaction,
      ledger_state: "VOID",
      audit_version: 2,
    });
    renderLedger(
      <TransactionCorrectionDialog
        transactionId="buy-1"
        portfolioKey="book"
        onClose={() => {}}
      />,
    );
    const quantity = await screen.findByLabelText("Quantity");
    expect(quantity.closest("fieldset")?.disabled).toBe(true);
    await userEvent.click(screen.getByRole("button", { name: "Void" }));
    expect(
      (screen.getByRole("button", { name: "Record void" }) as HTMLButtonElement)
        .disabled,
    ).toBe(true);
  });
});
