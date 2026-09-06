"use client";
import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { knkApi } from "@knk/api-client";
import { Ban, History, Info, Pencil, RefreshCw, Save } from "lucide-react";
import { Badge, Field, IconButton, timestamp } from "../ui";
import { LedgerDialog, LedgerError, LedgerLoading } from "./dialog";
import { TransactionDetails } from "./transaction-details";
import {
  portfolioPath,
  type LedgerTransaction,
  type RevisionResult,
} from "./contracts";
import {
  amendmentFields,
  changedFields,
  revisionFieldChanges,
  securityMovement,
  transactionDraft,
  type TransactionDraft,
} from "./transaction-draft";

type View = "amend" | "history" | "void" | "details";

export function TransactionCorrectionDialog({
  transactionId,
  portfolioKey = "KNK_MAIN",
  portfolioLabel,
  onClose,
}: {
  transactionId: string;
  portfolioKey?: string;
  portfolioLabel?: string;
  onClose: () => void;
}) {
  const [view, setView] = useState<View>("amend");
  const [draft, setDraft] = useState<TransactionDraft | null>(null);
  const [reason, setReason] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const client = useQueryClient();
  const path = `${portfolioPath(portfolioKey)}/transactions/${encodeURIComponent(transactionId)}`;
  const queryKey = ["ledger-transaction", portfolioKey, transactionId];
  const query = useQuery({
    queryKey,
    queryFn: ({ signal }) => knkApi.get<LedgerTransaction>(path, signal),
  });
  useEffect(() => {
    if (query.data) setDraft(transactionDraft(query.data));
  }, [query.data]);
  const mutation = useMutation({
    mutationFn: (action: "amend" | "void") => {
      if (!query.data || !draft) throw new Error("Transaction is unavailable");
      const request = { expected_version: query.data.audit_version, reason };
      return action === "amend"
        ? knkApi.put<RevisionResult>(path, {
            ...request,
            changes: changedFields(query.data, draft),
          })
        : knkApi.delete<RevisionResult>(path, request);
    },
    onSuccess: async () => {
      setReason("");
      setConfirmed(false);
      setView("history");
      await client.invalidateQueries({ queryKey });
      await client.invalidateQueries({ queryKey: ["terminal-portfolio"] });
      await client.invalidateQueries({ queryKey: ["operating-trades"] });
      await client.invalidateQueries({
        queryKey: ["ledger-transactions", portfolioKey],
      });
      await client.invalidateQueries({
        queryKey: ["ledger-summary", portfolioKey],
      });
    },
  });
  const transaction = query.data;
  const active = transaction?.ledger_state === "ACTIVE";
  const changes = transaction && draft ? changedFields(transaction, draft) : {};
  return (
    <LedgerDialog
      title={`Transaction / ${transaction?.symbol ?? transaction?.type ?? transactionId}`}
      onClose={onClose}
      closeLabel="Close transaction dialog"
    >
      <div className="ledger-toolbar">
        <div className="segmented" role="group" aria-label="Transaction action">
          <button
            aria-pressed={view === "amend"}
            onClick={() => setView("amend")}
          >
            <Pencil size={13} /> Correct
          </button>
          <button
            aria-pressed={view === "details"}
            onClick={() => setView("details")}
          >
            <Info size={13} /> Details
          </button>
          <button
            aria-pressed={view === "history"}
            onClick={() => setView("history")}
          >
            <History size={13} /> History
          </button>
          <button
            aria-pressed={view === "void"}
            onClick={() => setView("void")}
          >
            <Ban size={13} /> Void
          </button>
        </div>
        <IconButton
          label="Reload transaction version"
          onClick={() => query.refetch()}
        >
          <RefreshCw size={13} />
        </IconButton>
        {transaction && (
          <>
            <span className="secondary mono" title={transaction.portfolio_id}>
              Portfolio {portfolioLabel ?? portfolioKey}
            </span>
            <Badge>{transaction.ledger_state}</Badge>
            <span className="secondary mono">
              Version {transaction.audit_version}
            </span>
          </>
        )}
      </div>
      <LedgerError error={query.error ?? mutation.error} />
      {!transaction || !draft ? (
        <LedgerLoading />
      ) : (
        <>
          <dl className="ledger-totals">
            <div>
              <dt>Transaction</dt>
              <dd className="ledger-identifier">{transaction.id}</dd>
            </div>
            <div>
              <dt>Type</dt>
              <dd>{transaction.type}</dd>
            </div>
            <div>
              <dt>Currency</dt>
              <dd>{transaction.currency}</dd>
            </div>
          </dl>
          {view === "details" && (
            <TransactionDetails transaction={transaction} />
          )}
          {view === "amend" && (
            <form
              onSubmit={(event) => {
                event.preventDefault();
                mutation.mutate("amend");
              }}
            >
              <fieldset
                disabled={!active || mutation.isPending}
                className="ledger-amendment-grid"
              >
                {amendmentFields.map(([key, label, type]) => (
                  <Field key={key} label={label}>
                    <input
                      aria-label={label}
                      type={type === "date" ? "date" : "text"}
                      inputMode={type === "decimal" ? "decimal" : undefined}
                      value={draft[key]}
                      required
                      onChange={(event) =>
                        setDraft({ ...draft, [key]: event.target.value })
                      }
                    />
                  </Field>
                ))}
                {!securityMovement(transaction) && (
                  <Field label="Gross amount">
                    <input
                      aria-label="Gross amount"
                      inputMode="decimal"
                      value={draft.amount}
                      required
                      onChange={(event) =>
                        setDraft({ ...draft, amount: event.target.value })
                      }
                    />
                  </Field>
                )}
                <div className="ledger-amendment-wide">
                  <Field label="Transaction notes">
                    <textarea
                      aria-label="Transaction notes"
                      rows={2}
                      maxLength={10000}
                      value={draft.notes}
                      onChange={(event) =>
                        setDraft({ ...draft, notes: event.target.value })
                      }
                    />
                  </Field>
                </div>
                <div className="ledger-amendment-wide">
                  <Field label="Correction reason">
                    <textarea
                      aria-label="Correction reason"
                      rows={2}
                      minLength={5}
                      maxLength={2000}
                      required
                      value={reason}
                      onChange={(event) => setReason(event.target.value)}
                    />
                  </Field>
                </div>
                <button
                  type="submit"
                  disabled={
                    !Object.keys(changes).length || reason.trim().length < 5
                  }
                >
                  <Save size={13} />{" "}
                  {mutation.isPending ? "Saving..." : "Record correction"}
                </button>
              </fieldset>
            </form>
          )}
          {view === "void" && (
            <form
              className="ledger-policy-form"
              onSubmit={(event) => {
                event.preventDefault();
                mutation.mutate("void");
              }}
            >
              <Field label="Void reason">
                <textarea
                  aria-label="Void reason"
                  rows={3}
                  minLength={5}
                  maxLength={2000}
                  required
                  value={reason}
                  onChange={(event) => setReason(event.target.value)}
                  disabled={!active || mutation.isPending}
                />
              </Field>
              <label className="ledger-checkbox">
                <input
                  type="checkbox"
                  checked={confirmed}
                  onChange={(event) => setConfirmed(event.target.checked)}
                  disabled={!active || mutation.isPending}
                />{" "}
                Confirm void of this ledger transaction
              </label>
              <button
                type="submit"
                disabled={
                  !active ||
                  !confirmed ||
                  reason.trim().length < 5 ||
                  mutation.isPending
                }
              >
                <Ban size={13} />{" "}
                {mutation.isPending ? "Recording..." : "Record void"}
              </button>
            </form>
          )}
          {view === "history" && (
            <div className="ledger-revision-list">
              {!transaction.revisions.length && (
                <div className="ledger-loading">No corrections recorded</div>
              )}
              {transaction.revisions.map((revision) => (
                <section key={revision.id} className="ledger-revision-row">
                  <h3>
                    Version {revision.version} / {revision.action} /{" "}
                    {timestamp(revision.created_at)}
                  </h3>
                  <p>{revision.reason}</p>
                  {revision.action === "AMEND" && (
                    <div className="ledger-table-scroll">
                      <table className="ledger-table">
                        <thead>
                          <tr>
                            <th>Field</th>
                            <th>Before</th>
                            <th>After</th>
                          </tr>
                        </thead>
                        <tbody>
                          {revisionFieldChanges(
                            {
                              ...revision.before.entry,
                              notes: revision.before.notes,
                            },
                            {
                              ...revision.after.entry,
                              notes: revision.after.notes,
                            },
                          ).map((change) => (
                            <tr key={change.field}>
                              <th>{change.field.replaceAll("_", " ")}</th>
                              <td>{change.before}</td>
                              <td>{change.after}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </section>
              ))}
            </div>
          )}
          {mutation.isSuccess && (
            <div role="status" className="positive">
              Revision {mutation.data.audit_version} recorded
            </div>
          )}
        </>
      )}
    </LedgerDialog>
  );
}
