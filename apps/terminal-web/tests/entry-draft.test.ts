import { describe, expect, it } from "vitest";
import {
  entryMode,
  entryPayload,
  newEntryDraft,
  transactionTypes,
  type EntryDraft,
  type TransactionType,
} from "../components/ledger/entry-draft";

function draft(
  type: TransactionType,
  changes: Partial<EntryDraft> = {},
): EntryDraft {
  return {
    ...newEntryDraft("2026-01-06"),
    transaction_type: type,
    quantity: "2.12345678",
    price: "100",
    amount: "10.12345678",
    ...changes,
  };
}

describe("transaction entry contract", () => {
  it.each(transactionTypes)(
    "builds the supported %s contract without browser financial arithmetic",
    (type) => {
      const data = entryPayload(draft(type));
      expect(data.transaction_type).toBe(type);
      expect(data.trade_date).toBe("2026-01-06");
      expect(data.currency).toBe("USD");
      expect(data).not.toHaveProperty("net_amount");
      expect(data).not.toHaveProperty("base_value");
      for (const key of [
        "quantity",
        "price",
        "amount",
        "commission",
        "fee",
        "tax",
        "contract_multiplier",
      ]) {
        if (key in data) expect(typeof data[key]).toBe("string");
      }
    },
  );

  it.each(["BUY", "SELL", "SHORT", "COVER"] as const)(
    "preserves exact %s price and quantity and leaves derived gross to the server",
    (type) => {
      const data = entryPayload(
        draft(type, {
          amount: "",
          price: "0.00000001",
          quantity: "9999999",
          contract_multiplier: "100",
          symbol: " aapl ",
        }),
      );
      expect(data).toMatchObject({
        symbol: "AAPL",
        quantity: "9999999",
        price: "0.00000001",
        contract_multiplier: "100",
      });
      expect(data).not.toHaveProperty("amount");
      expect(data.metadata).toEqual({});
    },
  );

  it.each(["COMMISSION", "FEE", "TAX"] as const)(
    "does not double-charge a standalone %s expense",
    (type) => {
      const data = entryPayload(
        draft(type, { commission: "9", fee: "8", tax: "7" }),
      );
      expect(data.amount).toBe("10.12345678");
      for (const key of [
        "commission",
        "fee",
        "tax",
        "quantity",
        "price",
        "symbol",
      ])
        expect(data).not.toHaveProperty(key);
    },
  );

  it.each(["TRANSFER_IN", "TRANSFER_OUT"] as const)(
    "distinguishes cash and security %s without stale symbol leakage",
    (type) => {
      const cash = entryPayload(draft(type));
      expect(cash.amount).toBe("10.12345678");
      expect(cash).not.toHaveProperty("symbol");
      expect(cash).not.toHaveProperty("quantity");
      const security = entryPayload(
        draft(type, { transfer_mode: "SECURITY", amount: "" }),
      );
      expect(security).toMatchObject({
        symbol: "AAPL",
        quantity: "2.12345678",
        price: "100",
      });
      expect(security).not.toHaveProperty("amount");
    },
  );

  it.each(["SPLIT", "REVERSE_SPLIT"] as const)(
    "sends only the ratio for a %s action",
    (type) => {
      const data = entryPayload(
        draft(type, { ratio: "0.25", to_amount: "123", child_symbol: "MSFT" }),
      );
      expect(data.metadata).toEqual({ ratio: "0.25" });
      expect(data).not.toHaveProperty("quantity");
      expect(data).not.toHaveProperty("price");
      expect(data).not.toHaveProperty("amount");
      expect(data).not.toHaveProperty("child_symbol");
    },
  );

  it("does not mistake merger consideration per share for a transaction cash total", () => {
    const data = entryPayload(
      draft("MERGER", {
        child_symbol: " msft ",
        exchange_ratio: "2",
        cash_per_share: "3.12",
        cash_cost_allocation: "0.25",
        cost_allocation: "0.9",
      }),
    );
    expect(data.child_symbol).toBe("MSFT");
    expect(data.metadata).toEqual({
      exchange_ratio: "2",
      cash_per_share: "3.12",
      cash_cost_allocation: "0.25",
    });
    expect(data).not.toHaveProperty("quantity");
    expect(data).not.toHaveProperty("amount");
  });

  it("sends child share units and allocated basis for a spinoff", () => {
    const data = entryPayload(
      draft("SPINOFF", {
        child_symbol: "MSFT",
        cost_allocation: "0.15",
        exchange_ratio: "99",
      }),
    );
    expect(data).toMatchObject({
      quantity: "2.12345678",
      child_symbol: "MSFT",
      metadata: { cost_allocation: "0.15" },
    });
    expect(data).not.toHaveProperty("amount");
    expect(data.metadata).not.toHaveProperty("exchange_ratio");
  });

  it("retains both explicit FX legs and never calculates a fictional received amount", () => {
    const data = entryPayload(
      draft("FX_CONVERSION", {
        amount: "100",
        to_currency: "SGD",
        to_amount: "132.12",
        fee: "0.05",
      }),
    );
    expect(data).toMatchObject({
      amount: "100",
      currency: "USD",
      fee: "0.05",
      metadata: { to_currency: "SGD", to_amount: "132.12" },
    });
    expect(data).not.toHaveProperty("symbol");
    expect(data).not.toHaveProperty("fx_rate_to_base");
  });

  it("captures adjustment direction and reason independently of amount", () => {
    expect(
      entryPayload(
        draft("OTHER_ADJUSTMENT", {
          adjustment_direction: "DEBIT",
          adjustment_reason: "Statement rounding",
        }),
      ).metadata,
    ).toEqual({ direction: "DEBIT", reason: "Statement rounding" });
  });

  it("omits missing audit fields and normalizes entered references without inventing identity", () => {
    const empty = entryPayload(draft("DEPOSIT"));
    for (const field of [
      "trade_timestamp",
      "external_reference",
      "broker_execution_id",
      "strategy_id",
      "thesis_id",
      "created_by",
      "account_id",
    ])
      expect(empty).not.toHaveProperty(field);
    const data = entryPayload(
      draft("DEPOSIT", {
        external_reference: "  statement:001  ",
        broker_execution_id: " fill-1 ",
        strategy_id: " research ",
        thesis_id: " idea-1 ",
        account_id: " cash-1 ",
        settle_date: "2026-01-08",
        fx_rate_to_base: "1.31234567",
      }),
    );
    expect(data).toMatchObject({
      external_reference: "statement:001",
      broker_execution_id: "fill-1",
      strategy_id: "research",
      thesis_id: "idea-1",
      account_id: "cash-1",
      settle_date: "2026-01-08",
      fx_rate_to_base: "1.31234567",
    });
  });

  it("converts explicitly entered local time to an aware ISO timestamp", () => {
    const time = "2026-01-06T09:30";
    expect(
      entryPayload(draft("BUY", { trade_time: time })).trade_timestamp,
    ).toBe(new Date(time).toISOString());
    expect(() => entryPayload(draft("BUY", { trade_time: "morning" }))).toThrow(
      "Trade time is invalid",
    );
  });

  it.each(["DIVIDEND", "INTEREST"] as const)(
    "accepts an optional security for %s",
    (type) => {
      expect(entryMode(draft(type)).income).toBe(true);
      expect(entryPayload(draft(type, { symbol: "" }))).not.toHaveProperty(
        "symbol",
      );
      expect(entryPayload(draft(type)).symbol).toBe("AAPL");
    },
  );
});
