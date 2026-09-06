"use client";

import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { knkApi } from "@knk/api-client";
import { Check } from "lucide-react";
import { Badge, Field } from "../ui";
import { LedgerDialog, LedgerError, LedgerLoading } from "./dialog";
import type { AccountingPolicy, PortfolioMetadata } from "./contracts";

export interface PortfolioRecord extends PortfolioMetadata {
  reference_capital: string;
  is_demo: boolean;
  is_default: boolean;
}

export interface PortfolioCreationOptions {
  currencies: string[];
  methods: AccountingPolicy["method"][];
  max_opening_date: string;
  date_boundary: string;
  maximum_capital: string;
  capital_decimal_places: number;
  benchmarks: { symbol: string; name: string; currency: string }[];
}

export interface PortfolioDraft extends AccountingPolicy {
  code: string;
  name: string;
  base_currency: string;
  reference_capital: string;
  opening_date: string;
  benchmark: string;
  allow_short: boolean;
}

export function newPortfolioDraft(
  options: PortfolioCreationOptions,
): PortfolioDraft {
  return {
    code: "",
    name: "",
    base_currency: options.currencies.includes("SGD")
      ? "SGD"
      : (options.currencies[0] ?? ""),
    reference_capital: "",
    opening_date: options.max_opening_date,
    benchmark: options.benchmarks.some((row) => row.symbol === "SPY")
      ? "SPY"
      : (options.benchmarks[0]?.symbol ?? ""),
    allow_short: false,
    method: "AVERAGE",
    capitalize_commissions: true,
    capitalize_fees: false,
  };
}

export function portfolioCreatePayload(draft: PortfolioDraft): PortfolioDraft {
  return {
    ...draft,
    code: draft.code.trim().toUpperCase(),
    name: draft.name.trim(),
    reference_capital: draft.reference_capital.trim(),
  };
}

function PortfolioCreateForm({
  options,
  onCreated,
  onBusy,
}: {
  options: PortfolioCreationOptions;
  onCreated: (record: PortfolioRecord) => void;
  onBusy: (busy: boolean) => void;
}) {
  const [draft, setDraft] = useState(() => newPortfolioDraft(options));
  const save = useMutation({
    mutationFn: (payload: PortfolioDraft) =>
      knkApi.post<PortfolioRecord>("/api/v1/portfolios", payload),
    onMutate: () => onBusy(true),
    onSuccess: (record) => onCreated(record),
    onSettled: () => onBusy(false),
  });
  const update = <K extends keyof PortfolioDraft>(
    key: K,
    value: PortfolioDraft[K],
  ) => setDraft((current) => ({ ...current, [key]: value }));
  return (
    <form
      onSubmit={(event) => {
        event.preventDefault();
        save.mutate(portfolioCreatePayload(draft));
      }}
    >
      <fieldset className="ledger-entry-fields" disabled={save.isPending}>
        <Field label="Portfolio code">
          <input
            aria-label="Portfolio code"
            value={draft.code}
            required
            minLength={2}
            maxLength={40}
            pattern="[A-Z][A-Z0-9_]+"
            onChange={(event) =>
              update("code", event.target.value.toUpperCase())
            }
          />
        </Field>
        <Field label="Portfolio name">
          <input
            aria-label="Portfolio name"
            value={draft.name}
            required
            minLength={2}
            maxLength={200}
            onChange={(event) => update("name", event.target.value)}
          />
        </Field>
        <Field label="Base currency">
          <select
            aria-label="Base currency"
            value={draft.base_currency}
            onChange={(event) => update("base_currency", event.target.value)}
          >
            {options.currencies.map((currency) => (
              <option key={currency}>{currency}</option>
            ))}
          </select>
        </Field>
        <Field label={"Opening contribution / " + draft.base_currency}>
          <input
            aria-label="Opening contribution"
            type="number"
            inputMode="decimal"
            required
            min={"0." + "0".repeat(options.capital_decimal_places - 1) + "1"}
            step="any"
            max={options.maximum_capital}
            value={draft.reference_capital}
            onChange={(event) =>
              update("reference_capital", event.target.value)
            }
          />
        </Field>
        <Field label={"Opening date / " + options.date_boundary}>
          <input
            aria-label="Opening date"
            type="date"
            required
            value={draft.opening_date}
            max={options.max_opening_date}
            onChange={(event) => update("opening_date", event.target.value)}
          />
        </Field>
        <Field label="Benchmark security">
          <select
            aria-label="Benchmark security"
            required
            value={draft.benchmark}
            onChange={(event) => update("benchmark", event.target.value)}
          >
            {options.benchmarks.map((row) => (
              <option key={row.symbol} value={row.symbol}>
                {row.symbol} / {row.name}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Opening cost-basis method">
          <select
            aria-label="Opening cost-basis method"
            value={draft.method}
            onChange={(event) =>
              update("method", event.target.value as AccountingPolicy["method"])
            }
          >
            {options.methods.map((method) => (
              <option key={method} value={method}>
                {method === "AVERAGE" ? "Weighted average" : method}
              </option>
            ))}
          </select>
        </Field>
        <div className="ledger-entry-wide ledger-create-switches">
          <label className="ledger-checkbox">
            <input
              type="checkbox"
              checked={draft.allow_short}
              onChange={(event) => update("allow_short", event.target.checked)}
            />
            Allow short positions
          </label>
          <label className="ledger-checkbox">
            <input
              type="checkbox"
              checked={draft.capitalize_commissions}
              onChange={(event) =>
                update("capitalize_commissions", event.target.checked)
              }
            />
            Capitalize opening-policy commissions
          </label>
          <label className="ledger-checkbox">
            <input
              type="checkbox"
              checked={draft.capitalize_fees}
              onChange={(event) =>
                update("capitalize_fees", event.target.checked)
              }
            />
            Capitalize opening-policy fees
          </label>
        </div>
      </fieldset>
      <LedgerError error={save.error} />
      <button
        type="submit"
        disabled={
          save.isPending ||
          !draft.name.trim() ||
          !draft.code ||
          !draft.reference_capital ||
          !draft.benchmark
        }
      >
        <Check size={13} />{" "}
        {save.isPending ? "Creating ledger..." : "Create internal ledger"}
      </button>
    </form>
  );
}

export function PortfolioCreateDialog({
  onClose,
  onCreated,
}: {
  onClose: () => void;
  onCreated: (record: PortfolioRecord) => void;
}) {
  const [busy, setBusy] = useState(false);
  const options = useQuery({
    queryKey: ["ledger-creation-options"],
    queryFn: ({ signal }) =>
      knkApi.get<PortfolioCreationOptions>(
        "/api/v1/portfolios/creation-options",
        signal,
      ),
  });
  return (
    <LedgerDialog
      title="Create portfolio ledger"
      onClose={onClose}
      closeLabel="Cancel portfolio creation"
      closeDisabled={busy}
    >
      <div className="ledger-toolbar">
        <Badge>INTERNAL LEDGER</Badge>
        <Badge>MANUAL RECORDS</Badge>
      </div>
      <LedgerError error={options.error} />
      {options.isPending && <LedgerLoading />}
      {options.data && (
        <PortfolioCreateForm
          options={options.data}
          onCreated={onCreated}
          onBusy={setBusy}
        />
      )}
    </LedgerDialog>
  );
}
