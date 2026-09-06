import { describe, expect, it } from "vitest";
import {
  changedFields,
  revisionFieldChanges,
  securityMovement,
  transactionDraft,
} from "../components/ledger/transaction-draft";
import { portfolioPath } from "../components/ledger/contracts";
import { transaction } from "./fixtures/accounting";

describe("ledger correction drafts", () => {
  it("preserves server decimal strings without floating point conversion", () => {
    const draft = transactionDraft({
      ...transaction,
      quantity: "0.123456789123456789",
      price: "123456789.123456789",
    });
    expect(draft.quantity).toBe("0.123456789123456789");
    expect(draft.price).toBe("123456789.123456789");
    expect(draft.amount).toBe("1000.00000000");
  });
  it("does not submit untouched fields", () => {
    expect(changedFields(transaction, transactionDraft(transaction))).toEqual(
      {},
    );
  });
  it("posts only changed quantity without calculating replacement gross in React", () => {
    const draft = { ...transactionDraft(transaction), quantity: "8" };
    expect(changedFields(transaction, draft)).toEqual({ quantity: "8" });
    expect(draft.amount).toBe(transaction.gross_amount);
  });
  it("retains explicit zero and empty note changes", () => {
    const original = { ...transaction, notes: "Original note" };
    const draft = { ...transactionDraft(original), fee: "0", notes: "" };
    expect(changedFields(original, draft)).toEqual({ fee: "0", notes: "" });
  });
  it("defaults absent settlement to trade date, matching the service contract", () => {
    expect(
      transactionDraft({ ...transaction, settle_date: null }).settle_date,
    ).toBe(transaction.trade_date);
  });
  it.each(["BUY", "SELL", "SHORT", "COVER", "TRANSFER_IN", "TRANSFER_OUT"])(
    "recognizes %s with a security",
    (type) => {
      expect(securityMovement({ ...transaction, type })).toBe(true);
    },
  );
  it("does not classify cash transfers or corporate actions as priced trades", () => {
    expect(
      securityMovement({ ...transaction, type: "TRANSFER_IN", symbol: null }),
    ).toBe(false);
    expect(securityMovement({ ...transaction, type: "SPINOFF" })).toBe(false);
    expect(securityMovement({ ...transaction, type: "DIVIDEND" })).toBe(false);
  });
  it("limits outgoing fields to the typed correction contract", () => {
    const draft = {
      ...transactionDraft(transaction),
      currency: "USD",
      id: "other",
      quantity: "8",
    };
    expect(changedFields(transaction, draft)).toEqual({ quantity: "8" });
  });
  it("shows changed history values without omitting zero or cleared notes", () => {
    expect(
      revisionFieldChanges(
        { fee: "1", notes: "Original", quantity: "10" },
        { fee: "0", notes: null, quantity: "10" },
      ),
    ).toEqual([
      { field: "fee", before: "1", after: "0" },
      { field: "notes", before: "Original", after: "--" },
    ]);
  });
  it("escapes portfolio identifiers as a single resource path segment", () => {
    expect(portfolioPath("book/another?x=y")).toBe(
      "/api/v1/portfolios/book%2Fanother%3Fx%3Dy",
    );
  });
});
