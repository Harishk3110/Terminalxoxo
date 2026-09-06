"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { knkApi } from "@knk/api-client";
import { Save } from "lucide-react";
import { Field, number } from "../ui";
import { portfolioPath } from "./contracts";
import { LedgerError, LedgerLoading } from "./dialog";

const buckets = {
  accrued_income: "Accrued income",
  receivables: "Receivables",
  payables: "Payables",
  accrued_fees: "Accrued fees",
  other_liabilities: "Other liabilities",
} as const;
type Bucket = keyof typeof buckets;
export type BalanceRecord = {
  id: string;
  effective_date: string;
  bucket: Bucket;
  currency: string;
  amount: string;
  reason: string;
  created_at: string;
};

export function BalanceEditor({ portfolioKey }: { portfolioKey: string }) {
  const client = useQueryClient();
  const [bucket, setBucket] = useState<Bucket>("accrued_income");
  const [currency, setCurrency] = useState("SGD");
  const [effectiveDate, setEffectiveDate] = useState(
    new Date().toISOString().slice(0, 10),
  );
  const [amount, setAmount] = useState("");
  const [reason, setReason] = useState("");
  const path = portfolioPath(portfolioKey) + "/balances";
  const records = useQuery({
    queryKey: ["ledger-balances", portfolioKey],
    queryFn: ({ signal }) =>
      knkApi.get<{ items: BalanceRecord[] }>(path, signal),
  });
  const save = useMutation({
    mutationFn: () =>
      knkApi.post<BalanceRecord>(path, {
        bucket,
        currency,
        effective_date: effectiveDate,
        amount,
        reason,
      }),
    onSuccess: async () => {
      setAmount("");
      setReason("");
      await client.invalidateQueries({
        queryKey: ["ledger-balances", portfolioKey],
      });
      await client.invalidateQueries({
        queryKey: ["ledger-summary", portfolioKey],
      });
      await client.invalidateQueries({
        queryKey: ["ledger-accounting", portfolioKey],
      });
      await client.invalidateQueries({ queryKey: ["terminal-portfolio"] });
    },
  });
  return (
    <section aria-label="Portfolio balance adjustments">
      <form
        className="ledger-adjustment-form"
        onSubmit={(event) => {
          event.preventDefault();
          save.mutate();
        }}
      >
        <Field label="Balance bucket">
          <select
            aria-label="Balance bucket"
            value={bucket}
            disabled={save.isPending}
            onChange={(event) => setBucket(event.target.value as Bucket)}
          >
            {Object.entries(buckets).map(([key, label]) => (
              <option key={key} value={key}>
                {label}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Balance currency">
          <select
            aria-label="Balance currency"
            value={currency}
            disabled={save.isPending}
            onChange={(event) => setCurrency(event.target.value)}
          >
            {[
              "SGD",
              "USD",
              "EUR",
              "GBP",
              "JPY",
              "HKD",
              "AUD",
              "CAD",
              "CHF",
              "CNH",
              "CNY",
              "NZD",
            ].map((code) => (
              <option key={code}>{code}</option>
            ))}
          </select>
        </Field>
        <Field label="Effective date">
          <input
            aria-label="Effective date"
            type="date"
            value={effectiveDate}
            required
            max={new Date().toISOString().slice(0, 10)}
            disabled={save.isPending}
            onChange={(event) => setEffectiveDate(event.target.value)}
          />
        </Field>
        <Field label="Signed adjustment amount">
          <input
            aria-label="Signed adjustment amount"
            type="number"
            step="0.00000001"
            value={amount}
            required
            disabled={save.isPending}
            onChange={(event) => setAmount(event.target.value)}
          />
        </Field>
        <Field label="Adjustment reason">
          <textarea
            aria-label="Adjustment reason"
            rows={2}
            value={reason}
            required
            minLength={5}
            maxLength={1000}
            disabled={save.isPending}
            onChange={(event) => setReason(event.target.value)}
          />
        </Field>
        <div className="ledger-adjustment-actions">
          <LedgerError error={save.error} />
          {save.isSuccess && (
            <span className="positive" role="status">
              Balance adjustment recorded
            </span>
          )}
          <button
            type="submit"
            disabled={
              !amount ||
              !effectiveDate ||
              reason.trim().length < 5 ||
              save.isPending
            }
          >
            <Save size={13} />{" "}
            {save.isPending ? "Recording..." : "Record adjustment"}
          </button>
        </div>
      </form>
      <LedgerError error={records.error} />
      {records.isPending && <LedgerLoading />}
      {records.data && (
        <div className="ledger-table-scroll">
          <table
            className="ledger-table"
            aria-label="Balance adjustment history"
          >
            <thead>
              <tr>
                <th scope="col">Effective</th>
                <th scope="col">Bucket</th>
                <th scope="col">CCY</th>
                <th scope="col">Adjustment</th>
                <th scope="col">Reason</th>
              </tr>
            </thead>
            <tbody>
              {records.data.items.map((row) => (
                <tr key={row.id}>
                  <th scope="row">{row.effective_date}</th>
                  <td>{buckets[row.bucket]}</td>
                  <td>{row.currency}</td>
                  <td>{number(row.amount, 2)}</td>
                  <td title={row.reason}>{row.reason}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {records.data?.items.length === 0 && (
        <div className="ledger-loading">No balance adjustments</div>
      )}
    </section>
  );
}
