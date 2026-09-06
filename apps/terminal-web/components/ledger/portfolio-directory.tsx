"use client";

import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { knkApi } from "@knk/api-client";
import {
  ArrowLeft,
  ArrowRight,
  BookOpen,
  Plus,
  RefreshCw,
  Settings2,
} from "lucide-react";
import { Badge, Field, IconButton, number } from "../ui";
import { LedgerDialog, LedgerError, LedgerLoading } from "./dialog";
import { AccountingDialog } from "./accounting-dialog";
import { TransactionEntryDialog } from "./transaction-entry";
import { TransactionCorrectionDialog } from "./transaction-correction";
import {
  PortfolioCreateDialog,
  type PortfolioRecord,
} from "./portfolio-create";
import {
  portfolioPath,
  type LedgerSummary,
  type LedgerTransaction,
} from "./contracts";

type View = "directory" | "create" | "accounting" | "entry" | "transaction";

function PortfolioTransactions({
  portfolioKey,
  onSelect,
}: {
  portfolioKey: string;
  onSelect: (id: string) => void;
}) {
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(0);
  const query = useQuery({
    queryKey: ["ledger-transactions", portfolioKey],
    queryFn: ({ signal }) =>
      knkApi.get<{ items: LedgerTransaction[] }>(
        portfolioPath(portfolioKey) + "/transactions",
        signal,
      ),
  });
  const filtered = (query.data?.items ?? [])
    .filter((item) =>
      [
        item.type,
        item.symbol,
        item.trade_date,
        item.source,
        item.notes,
        item.ledger_state,
        item.external_reference,
      ].some((value) =>
        value?.toLowerCase().includes(search.trim().toLowerCase()),
      ),
    )
    .slice()
    .reverse();
  const lastPage = Math.max(0, Math.ceil(filtered.length / 25) - 1);
  const current = Math.min(page, lastPage);
  return (
    <section
      aria-label="Selected portfolio transactions"
      className="ledger-record-detail"
    >
      <div className="ledger-toolbar">
        <Field label="Filter ledger transactions">
          <input
            aria-label="Filter ledger transactions"
            type="search"
            value={search}
            onChange={(event) => {
              setSearch(event.target.value);
              setPage(0);
            }}
          />
        </Field>
        <IconButton
          label="Refresh selected transactions"
          onClick={() => query.refetch()}
        >
          <RefreshCw size={13} />
        </IconButton>
        <span className="secondary">{filtered.length} records</span>
      </div>
      <LedgerError error={query.error} />
      {query.isPending && <LedgerLoading />}
      {query.data && (
        <>
          <div className="ledger-table-scroll">
            <table
              className="ledger-table"
              aria-label="Selected ledger transactions"
            >
              <thead>
                <tr>
                  <th scope="col">Trade date</th>
                  <th scope="col">Event</th>
                  <th scope="col">Security</th>
                  <th scope="col">CCY</th>
                  <th scope="col">Net cash</th>
                  <th scope="col">Source</th>
                  <th scope="col">State</th>
                  <th scope="col">Record</th>
                </tr>
              </thead>
              <tbody>
                {filtered
                  .slice(current * 25, (current + 1) * 25)
                  .map((item) => (
                    <tr key={item.id}>
                      <th scope="row">{item.trade_date}</th>
                      <td>{item.type}</td>
                      <td>{item.symbol ?? "--"}</td>
                      <td>{item.currency}</td>
                      <td>{number(item.net_amount, 8)}</td>
                      <td>{item.source}</td>
                      <td>{item.ledger_state}</td>
                      <td>
                        <IconButton
                          label={"Inspect transaction " + item.id}
                          onClick={() => onSelect(item.id)}
                        >
                          <BookOpen size={13} />
                        </IconButton>
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
          {!filtered.length && (
            <div className="ledger-loading">
              No matching ledger transactions
            </div>
          )}
          <div className="ledger-toolbar ledger-pagination">
            <IconButton
              label="Previous transaction page"
              disabled={current === 0}
              onClick={() => setPage(current - 1)}
            >
              <ArrowLeft size={13} />
            </IconButton>
            <span>
              Page {current + 1} / {lastPage + 1}
            </span>
            <IconButton
              label="Next transaction page"
              disabled={current === lastPage}
              onClick={() => setPage(current + 1)}
            >
              <ArrowRight size={13} />
            </IconButton>
          </div>
        </>
      )}
    </section>
  );
}

function SelectedPortfolio({
  record,
  onView,
  onTransaction,
}: {
  record: PortfolioRecord;
  onView: (view: View) => void;
  onTransaction: (id: string) => void;
}) {
  const summary = useQuery({
    queryKey: ["ledger-summary", record.id],
    queryFn: ({ signal }) =>
      knkApi.get<LedgerSummary>(portfolioPath(record.id) + "/summary", signal),
  });
  return (
    <section
      aria-label={"Selected ledger / " + record.code}
      className="ledger-record-detail"
    >
      <div className="ledger-toolbar">
        <h3>
          {record.code} / {record.name}
        </h3>
        <Badge>{record.is_demo ? "DEMO LEDGER" : "INTERNAL LEDGER"}</Badge>
        {record.is_default && <Badge>DEFAULT</Badge>}
        {summary.data && <Badge>{summary.data.quality}</Badge>}
      </div>
      <dl className="ledger-totals ledger-audit-fields">
        <div>
          <dt>Reference capital / {record.base_currency}</dt>
          <dd>{number(record.reference_capital, 8)}</dd>
        </div>
        <div>
          <dt>NAV / {record.base_currency}</dt>
          <dd>{number(summary.data?.portfolio.nav, 2)}</dd>
        </div>
        <div>
          <dt>Economic cash / {record.base_currency}</dt>
          <dd>{number(summary.data?.portfolio.cash, 2)}</dd>
        </div>
        <div>
          <dt>Benchmark</dt>
          <dd>{String(record.configuration.benchmark ?? "Not recorded")}</dd>
        </div>
        <div>
          <dt>Cost-basis method</dt>
          <dd>{record.accounting_policy.method}</dd>
        </div>
        <div>
          <dt>Short positions</dt>
          <dd>
            {record.configuration.allow_short === true
              ? "Allowed"
              : "Not allowed"}
          </dd>
        </div>
      </dl>
      <LedgerError error={summary.error} />
      {summary.isPending && <LedgerLoading />}
      <div className="ledger-toolbar">
        <button onClick={() => onView("accounting")}>
          <Settings2 size={13} />
          Open selected accounting
        </button>
        <button onClick={() => onView("entry")}>
          <Plus size={13} />
          Record selected transaction
        </button>
        <IconButton
          label="Refresh selected valuation"
          onClick={() => summary.refetch()}
        >
          <RefreshCw size={13} />
        </IconButton>
      </div>
      <dl className="ledger-methodology">
        <dt>Ledger accounts</dt>
        {record.accounts.map((account) => (
          <dd key={account.id}>
            {account.name} / {account.type} /{" "}
            {account.provider ?? "No broker provider"}
          </dd>
        ))}
      </dl>
      <PortfolioTransactions
        key={record.id}
        portfolioKey={record.id}
        onSelect={onTransaction}
      />
    </section>
  );
}

export function PortfolioDirectory({ onClose }: { onClose: () => void }) {
  const [selected, setSelected] = useState("KNK_MAIN");
  const [view, setView] = useState<View>("directory");
  const [transactionId, setTransactionId] = useState("");
  const [search, setSearch] = useState("");
  const [created, setCreated] = useState("");
  const client = useQueryClient();
  const directory = useQuery({
    queryKey: ["ledger-portfolios"],
    queryFn: ({ signal }) =>
      knkApi.get<{ items: PortfolioRecord[] }>("/api/v1/portfolios", signal),
  });
  const records = directory.data?.items ?? [];
  const record = records.find(
    (item) => item.id === selected || item.code === selected,
  );
  const filtered = records.filter((item) =>
    [item.code, item.name, item.base_currency].some((value) =>
      value.toLowerCase().includes(search.trim().toLowerCase()),
    ),
  );
  const back = () => setView("directory");
  if (view === "create")
    return (
      <PortfolioCreateDialog
        onClose={back}
        onCreated={(item) => {
          client.setQueryData<{ items: PortfolioRecord[] }>(
            ["ledger-portfolios"],
            (previous) => ({
              items: [
                ...(previous?.items.filter((row) => row.id !== item.id) ?? []),
                item,
              ].sort((a, b) => a.code.localeCompare(b.code)),
            }),
          );
          setSelected(item.id);
          setCreated(item.code);
          setSearch("");
          back();
          client.invalidateQueries({ queryKey: ["ledger-portfolios"] });
        }}
      />
    );
  if (record && view === "accounting")
    return <AccountingDialog portfolioKey={record.id} onClose={back} />;
  if (record && view === "entry")
    return <TransactionEntryDialog portfolioKey={record.id} onClose={back} />;
  if (record && view === "transaction")
    return (
      <TransactionCorrectionDialog
        portfolioKey={record.id}
        transactionId={transactionId}
        portfolioLabel={record.code}
        onClose={back}
      />
    );
  return (
    <LedgerDialog
      title="Portfolio ledgers"
      onClose={onClose}
      closeLabel="Close portfolio directory"
    >
      <div className="ledger-toolbar">
        <Field label="Filter portfolios">
          <input
            aria-label="Filter portfolios"
            type="search"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
        </Field>
        <IconButton
          label="Create portfolio ledger"
          onClick={() => setView("create")}
        >
          <Plus size={13} />
        </IconButton>
        <IconButton
          label="Refresh portfolio directory"
          onClick={() => directory.refetch()}
        >
          <RefreshCw size={13} />
        </IconButton>
        <span className="secondary">{filtered.length} ledgers</span>
      </div>
      {created && (
        <div role="status" className="positive">
          Ledger {created} created
        </div>
      )}
      <LedgerError error={directory.error} />
      {directory.isPending && <LedgerLoading />}
      {directory.data && (
        <div className="ledger-table-scroll ledger-directory-table">
          <table className="ledger-table" aria-label="Portfolio directory">
            <thead>
              <tr>
                <th scope="col">Code</th>
                <th scope="col">Name</th>
                <th scope="col">Base</th>
                <th scope="col">Reference capital</th>
                <th scope="col">Mode</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((item) => (
                <tr key={item.id} aria-selected={record?.id === item.id}>
                  <th scope="row">
                    <button
                      aria-label={"Select ledger " + item.code}
                      aria-pressed={record?.id === item.id}
                      onClick={() => {
                        setSelected(item.id);
                        setCreated("");
                      }}
                    >
                      {item.code}
                    </button>
                  </th>
                  <td>{item.name}</td>
                  <td>{item.base_currency}</td>
                  <td>{number(item.reference_capital, 8)}</td>
                  <td>{item.is_demo ? "DEMO" : "INTERNAL"}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {!filtered.length && (
            <div className="ledger-loading">No matching portfolio ledgers</div>
          )}
        </div>
      )}
      {record && (
        <SelectedPortfolio
          key={record.id}
          record={record}
          onView={setView}
          onTransaction={(id) => {
            setTransactionId(id);
            setView("transaction");
          }}
        />
      )}
    </LedgerDialog>
  );
}
