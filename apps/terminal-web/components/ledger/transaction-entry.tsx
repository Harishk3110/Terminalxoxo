"use client";

import { useEffect, useId, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { knkApi } from "@knk/api-client";
import { Check } from "lucide-react";
import { Badge, Field } from "../ui";
import { LedgerDialog, LedgerError, LedgerLoading } from "./dialog";
import { portfolioPath } from "./contracts";
import {
  entryMode,
  entryPayload,
  newEntryDraft,
  transactionTypes,
  type EntryDraft,
  type EntryOptions,
  type TransactionType,
} from "./entry-draft";

type TextField = Exclude<
  keyof EntryDraft,
  "transaction_type" | "transfer_mode" | "adjustment_direction"
>;
type Security = { id: string; symbol: string; name: string; currency: string };

export function TransactionEntryDialog({
  portfolioKey = "KNK_MAIN",
  onClose,
}: {
  portfolioKey?: string;
  onClose: () => void;
}) {
  const [draft, setDraft] = useState<EntryDraft>(() => newEntryDraft());
  const [symbolQuery, setSymbolQuery] = useState(draft.symbol);
  const client = useQueryClient();
  const securityList = useId();
  const mode = entryMode(draft);
  const options = useQuery({
    queryKey: ["ledger-entry-options", portfolioKey],
    queryFn: ({ signal }) =>
      knkApi.get<EntryOptions>(
        portfolioPath(portfolioKey) + "/entry-options",
        signal,
      ),
  });
  useEffect(() => {
    const timer = window.setTimeout(() => setSymbolQuery(draft.symbol), 180);
    return () => window.clearTimeout(timer);
  }, [draft.symbol]);
  const securities = useQuery({
    queryKey: ["ledger-security-options", symbolQuery],
    queryFn: ({ signal }) =>
      knkApi.get<{ instruments: Security[] }>(
        "/api/v1/search?" + new URLSearchParams({ q: symbolQuery }),
        signal,
      ),
    enabled: mode.security,
  });
  useEffect(() => {
    const security = securities.data?.instruments.find(
      (item) => item.symbol === draft.symbol.trim().toUpperCase(),
    );
    if (security && mode.security)
      setDraft((current) => ({ ...current, currency: security.currency }));
  }, [securities.data, draft.symbol, mode.security]);
  const save = useMutation({
    mutationFn: () =>
      knkApi.post(
        portfolioPath(portfolioKey) + "/transactions",
        entryPayload(draft),
      ),
    onSuccess: async () => {
      for (const queryKey of [
        ["operating-trades"],
        ["terminal-portfolio"],
        ["ledger-summary", portfolioKey],
        ["ledger-accounting", portfolioKey],
        ["ledger-transactions", portfolioKey],
      ]) {
        await client.invalidateQueries({ queryKey });
      }
      onClose();
    },
  });
  const update = (field: TextField, value: string) =>
    setDraft((current) => ({ ...current, [field]: value }));
  const input = (
    field: TextField,
    label: string,
    type: "text" | "number" | "date" | "datetime-local" = "number",
    required = false,
  ) => (
    <Field key={field} label={label}>
      <input
        aria-label={label}
        type={type}
        value={draft[field]}
        step={type === "number" ? "any" : undefined}
        min={type === "number" ? "0" : undefined}
        required={required}
        onChange={(event) => update(field, event.target.value)}
      />
    </Field>
  );
  const allowed = options.data?.transaction_types ?? transactionTypes;
  const shortAllowed =
    options.data?.portfolio.configuration?.allow_short === true;
  const currencies = options.data?.currencies ?? ["SGD", "USD"];
  return (
    <LedgerDialog
      title="Record ledger transaction"
      onClose={onClose}
      closeLabel="Close transaction dialog"
    >
      <div className="ledger-toolbar">
        <Badge>MANUAL RECORD</Badge>
        <span>{options.data?.portfolio.code ?? portfolioKey}</span>
      </div>
      <LedgerError error={options.error} />
      {options.isPending && <LedgerLoading />}
      <form
        onSubmit={(event) => {
          event.preventDefault();
          save.mutate();
        }}
      >
        <fieldset
          className="ledger-entry-fields"
          disabled={save.isPending || !options.data}
        >
          <Field label="Transaction type">
            <select
              aria-label="Transaction type"
              value={draft.transaction_type}
              onChange={(event) =>
                setDraft((current) => {
                  const next = {
                    ...current,
                    transaction_type: event.target.value as TransactionType,
                    amount: "",
                  };
                  if (!entryMode(next).security)
                    next.currency =
                      options.data?.portfolio.base_currency ?? current.currency;
                  if (next.to_currency === next.currency)
                    next.to_currency =
                      currencies.find(
                        (currency) => currency !== next.currency,
                      ) ?? "";
                  return next;
                })
              }
            >
              {transactionTypes
                .filter((type) => allowed.includes(type))
                .map((type) => (
                  <option
                    key={type}
                    disabled={type === "SHORT" && !shortAllowed}
                  >
                    {type}
                  </option>
                ))}
            </select>
          </Field>
          <Field label="Account">
            <select
              aria-label="Account"
              value={draft.account_id}
              onChange={(event) => update("account_id", event.target.value)}
            >
              <option value="">Default account</option>
              {options.data?.portfolio.accounts.map((account) => (
                <option key={account.id} value={account.id}>
                  {account.name}
                </option>
              ))}
            </select>
          </Field>
          {input("trade_date", "Trade date", "date", true)}
          {input("settle_date", "Settlement date", "date")}
          <div className="ledger-entry-time">
            {input(
              "trade_time",
              `Trade time / ${Intl.DateTimeFormat().resolvedOptions().timeZone}`,
              "datetime-local",
            )}
          </div>
          <Field label="Currency">
            <select
              aria-label="Currency"
              value={draft.currency}
              onChange={(event) =>
                setDraft((current) => ({
                  ...current,
                  currency: event.target.value,
                  to_currency:
                    current.to_currency === event.target.value
                      ? (currencies.find(
                          (currency) => currency !== event.target.value,
                        ) ?? "")
                      : current.to_currency,
                }))
              }
            >
              {currencies.map((currency) => (
                <option key={currency}>{currency}</option>
              ))}
            </select>
          </Field>
          {mode.transfer && (
            <div
              className="segmented ledger-entry-wide"
              role="group"
              aria-label="Transfer asset"
            >
              <button
                type="button"
                aria-pressed={draft.transfer_mode === "CASH"}
                onClick={() =>
                  setDraft((current) => ({
                    ...current,
                    transfer_mode: "CASH",
                    amount: "",
                    currency:
                      options.data?.portfolio.base_currency ?? current.currency,
                  }))
                }
              >
                Cash
              </button>
              <button
                type="button"
                aria-pressed={draft.transfer_mode === "SECURITY"}
                onClick={() =>
                  setDraft((current) => ({
                    ...current,
                    transfer_mode: "SECURITY",
                    amount: "",
                  }))
                }
              >
                Security
              </button>
            </div>
          )}
          {mode.security && (
            <Field label={mode.income ? "Security (optional)" : "Security"}>
              <input
                aria-label={mode.income ? "Security (optional)" : "Security"}
                value={draft.symbol}
                list={securityList}
                required={!mode.income}
                autoComplete="off"
                onChange={(event) => update("symbol", event.target.value)}
              />
              <datalist id={securityList}>
                {securities.data?.instruments.map((security) => (
                  <option key={security.id} value={security.symbol}>
                    {security.name} / {security.currency}
                  </option>
                ))}
              </datalist>
            </Field>
          )}
          {mode.priced && (
            <>
              {input("quantity", "Quantity", "number", true)}
              {input("price", "Price", "number", true)}
              {input(
                "contract_multiplier",
                "Contract multiplier",
                "number",
                true,
              )}
              {input("amount", "Gross amount (optional)")}
            </>
          )}
          {mode.cashAmount && input("amount", "Gross amount", "number", true)}
          {draft.transaction_type === "SPINOFF" &&
            input("quantity", "Child shares received", "number", true)}
          {!mode.expense && (
            <>
              {input("commission", "Commission")}
              {input("fee", "Fee")}
              {input("tax", "Tax")}
            </>
          )}
          {input("fx_rate_to_base", "Recorded FX to base")}
          {draft.transaction_type === "FX_CONVERSION" && (
            <>
              <Field label="Received currency">
                <select
                  aria-label="Received currency"
                  value={draft.to_currency}
                  onChange={(event) =>
                    update("to_currency", event.target.value)
                  }
                >
                  {currencies.map((currency) => (
                    <option
                      key={currency}
                      disabled={currency === draft.currency}
                    >
                      {currency}
                    </option>
                  ))}
                </select>
              </Field>
              {input("to_amount", "Received amount", "number", true)}
            </>
          )}
          {["SPLIT", "REVERSE_SPLIT"].includes(draft.transaction_type) &&
            input("ratio", "New shares per old share", "number", true)}
          {["SPINOFF", "MERGER"].includes(draft.transaction_type) &&
            input("child_symbol", "Successor security", "text", true)}
          {draft.transaction_type === "SPINOFF" &&
            input("cost_allocation", "Child cost allocation", "number", true)}
          {draft.transaction_type === "MERGER" && (
            <>
              {input(
                "exchange_ratio",
                "Successor shares per parent share",
                "number",
                true,
              )}
              {input("cash_per_share", "Cash per parent share")}
              {input("cash_cost_allocation", "Cash cost allocation")}
            </>
          )}
          {draft.transaction_type === "OTHER_ADJUSTMENT" && (
            <>
              <Field label="Adjustment direction">
                <select
                  aria-label="Adjustment direction"
                  value={draft.adjustment_direction}
                  onChange={(event) =>
                    setDraft((current) => ({
                      ...current,
                      adjustment_direction: event.target.value as
                        | "CREDIT"
                        | "DEBIT",
                    }))
                  }
                >
                  <option value="CREDIT">Credit</option>
                  <option value="DEBIT">Debit</option>
                </select>
              </Field>
              {input("adjustment_reason", "Adjustment reason", "text", true)}
            </>
          )}
          <div className="ledger-entry-section ledger-entry-wide">
            Audit references
          </div>
          {input("external_reference", "External reference", "text")}
          {input("broker_execution_id", "Broker execution reference", "text")}
          <Field label="Strategy">
            <select
              aria-label="Strategy"
              value={draft.strategy_id}
              onChange={(event) => update("strategy_id", event.target.value)}
            >
              <option value="">Unlinked</option>
              {options.data?.strategies.map((strategy) => (
                <option key={strategy.id} value={strategy.id}>
                  {strategy.name} / {strategy.state}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Thesis">
            <select
              aria-label="Thesis"
              value={draft.thesis_id}
              onChange={(event) => update("thesis_id", event.target.value)}
            >
              <option value="">Unlinked</option>
              {options.data?.theses.map((thesis) => (
                <option key={thesis.id} value={thesis.id}>
                  {thesis.title} / {thesis.state}
                </option>
              ))}
            </select>
          </Field>
          <div className="ledger-entry-wide">
            <Field label="Rationale / notes">
              <textarea
                aria-label="Rationale / notes"
                rows={3}
                maxLength={10000}
                value={draft.notes}
                onChange={(event) => update("notes", event.target.value)}
              />
            </Field>
          </div>
        </fieldset>
        <LedgerError error={save.error} />
        {mode.security && <LedgerError error={securities.error} />}
        <button type="submit" disabled={save.isPending || !options.data}>
          <Check size={13} />
          {save.isPending ? "Recording..." : "Record transaction"}
        </button>
      </form>
    </LedgerDialog>
  );
}
