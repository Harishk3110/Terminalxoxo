"use client";

import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { knkApi } from "@knk/api-client";
import { ChevronLeft, ChevronRight, FileSearch } from "lucide-react";
import { Badge, Field, IconButton, number } from "../ui";
import { portfolioPath } from "./contracts";
import { LedgerError, LedgerLoading } from "./dialog";

const categories = {
  CAPITAL: "Capital flows",
  INCOME: "Income",
  FEE: "Fees and taxes",
  ACCRUAL: "Accruals",
  LIABILITY: "Liabilities",
} as const;
type Category = keyof typeof categories;

export type AccountingRecord = {
  id: string;
  key: string;
  category: Category;
  kind: string;
  effective_date: string;
  settlement_date: string | null;
  currency: string;
  native_amount: string;
  fx_rate: string | null;
  base_amount: string | null;
  capitalized_base: string | null;
  transaction_id: string | null;
  adjustment_id: string | null;
  account_id: string | null;
  instrument_id: string | null;
  provenance: Record<string, unknown>;
};

export type AccountingActivityResult = {
  items: AccountingRecord[];
  state: "AVAILABLE" | "UNAVAILABLE";
  base_currency?: string;
  valuation_run_id: string;
  warnings?: string[];
  totals?: Record<string, string | null>;
  reconciliation?: { state: string; differences: Record<string, string> };
};

const PAGE_SIZE = 25;

export function AccountingActivity({
  portfolioKey,
  runId,
}: {
  portfolioKey: string;
  runId: string;
}) {
  const [category, setCategory] = useState<Category | "ALL">("ALL");
  const [page, setPage] = useState(0);
  const [selected, setSelected] = useState<string | null>(null);
  const records = useQuery({
    queryKey: ["ledger-accounting", portfolioKey, runId],
    queryFn: ({ signal }) =>
      knkApi.get<AccountingActivityResult>(
        portfolioPath(portfolioKey) +
          "/accounting?" +
          new URLSearchParams({ run_id: runId }),
        signal,
      ),
  });
  useEffect(() => {
    setPage(0);
    setSelected(null);
  }, [runId, category]);
  const data = records.data;
  const rows =
    data?.items.filter(
      (row) => category === "ALL" || row.category === category,
    ) ?? [];
  const pages = Math.max(1, Math.ceil(rows.length / PAGE_SIZE));
  const currentPage = Math.min(page, pages - 1);
  const visible = rows.slice(
    currentPage * PAGE_SIZE,
    (currentPage + 1) * PAGE_SIZE,
  );
  const detail = rows.find((row) => row.id === selected);
  return (
    <section className="ledger-accounting-activity" aria-label="Accounting activity">
      <LedgerError error={records.error} />
      {records.isPending && <LedgerLoading />}
      {data?.state === "UNAVAILABLE" && (
        <div role="status">
          {data.warnings?.join(" ") ?? "Accounting records unavailable"}
        </div>
      )}
      {data?.state === "AVAILABLE" && (
        <>
          <dl className="ledger-totals">
            <div>
              <dt>Capital flows / {data.base_currency}</dt>
              <dd>{number(data.totals?.external_flows, 2)}</dd>
            </div>
            <div>
              <dt>Income</dt>
              <dd>{number(data.totals?.income, 2)}</dd>
            </div>
            <div>
              <dt>Expensed fees</dt>
              <dd>{number(data.totals?.expensed_fees, 2)}</dd>
            </div>
            <div>
              <dt>Capitalized charges</dt>
              <dd>{number(data.totals?.capitalized_charges, 2)}</dd>
            </div>
            <div>
              <dt>Taxes</dt>
              <dd>{number(data.totals?.taxes, 2)}</dd>
            </div>
            <div>
              <dt>Subledger</dt>
              <dd>
                <Badge>{data.reconciliation?.state ?? "UNAVAILABLE"}</Badge>
              </dd>
            </div>
          </dl>
          <div className="ledger-toolbar">
            <Field label="Accounting category">
              <select
                aria-label="Accounting category"
                value={category}
                onChange={(event) =>
                  setCategory(event.target.value as Category | "ALL")
                }
              >
                <option value="ALL">All components</option>
                {Object.entries(categories).map(([key, label]) => (
                  <option key={key} value={key}>
                    {label}
                  </option>
                ))}
              </select>
            </Field>
            <span className="ledger-record-count" role="status">
              {rows.length} records
            </span>
            <IconButton
              label="Previous accounting page"
              disabled={currentPage === 0}
              onClick={() => setPage(currentPage - 1)}
            >
              <ChevronLeft size={13} />
            </IconButton>
            <span>
              {currentPage + 1} / {pages}
            </span>
            <IconButton
              label="Next accounting page"
              disabled={currentPage + 1 >= pages}
              onClick={() => setPage(currentPage + 1)}
            >
              <ChevronRight size={13} />
            </IconButton>
          </div>
          <div className="ledger-table-scroll">
            <table
              className="ledger-table"
              aria-label="Accounting component records"
            >
              <thead>
                <tr>
                  <th scope="col">Date</th>
                  <th scope="col">Category</th>
                  <th scope="col">Type</th>
                  <th scope="col">CCY</th>
                  <th scope="col">Native amount</th>
                  <th scope="col">Base amount</th>
                  <th scope="col">Capitalized</th>
                  <th scope="col">Details</th>
                </tr>
              </thead>
              <tbody>
                {visible.map((row) => (
                  <tr key={row.id} aria-selected={row.id === selected}>
                    <th scope="row">{row.effective_date}</th>
                    <td>{categories[row.category]}</td>
                    <td>{row.kind}</td>
                    <td>{row.currency}</td>
                    <td>{number(row.native_amount, 2)}</td>
                    <td>{number(row.base_amount, 2)}</td>
                    <td>{number(row.capitalized_base, 2)}</td>
                    <td>
                      <IconButton
                        label={`Inspect ${row.kind} ${row.effective_date}`}
                        onClick={() => setSelected(row.id)}
                      >
                        <FileSearch size={13} />
                      </IconButton>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {!rows.length && (
            <div className="ledger-loading">No accounting components</div>
          )}
          {detail && (
            <section
              className="ledger-record-detail"
              aria-label="Accounting record details"
            >
              <h3>
                {detail.kind} / {detail.currency}
              </h3>
              <dl className="ledger-totals">
                <div>
                  <dt>Transaction</dt>
                  <dd>{detail.transaction_id ?? "Not applicable"}</dd>
                </div>
                <div>
                  <dt>Adjustment</dt>
                  <dd>{detail.adjustment_id ?? "Not applicable"}</dd>
                </div>
                <div>
                  <dt>Account</dt>
                  <dd>{detail.account_id ?? "Not recorded"}</dd>
                </div>
                <div>
                  <dt>Settlement</dt>
                  <dd>{detail.settlement_date ?? "Not applicable"}</dd>
                </div>
                <div>
                  <dt>FX rate</dt>
                  <dd>{number(detail.fx_rate, 8)}</dd>
                </div>
                <div>
                  <dt>Basis</dt>
                  <dd>{String(detail.provenance.basis ?? "Not recorded")}</dd>
                </div>
                <div>
                  <dt>Source</dt>
                  <dd>{String(detail.provenance.source ?? "Not recorded")}</dd>
                </div>
                <div>
                  <dt>Reason</dt>
                  <dd>{String(detail.provenance.reason ?? "Not recorded")}</dd>
                </div>
              </dl>
            </section>
          )}
        </>
      )}
    </section>
  );
}
