"use client";
import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { knkApi } from "@knk/api-client";
import {
  BookOpen,
  Crosshair,
  Layers,
  PieChart,
  RefreshCw,
  Save,
  Scale,
  Settings2,
  Wallet,
} from "lucide-react";
import { Badge, Field, IconButton, money, number, timestamp } from "../ui";
import { LedgerDialog, LedgerError, LedgerLoading } from "./dialog";
import { AccountingActivity } from "./accounting-activity";
import { BalanceEditor } from "./balance-editor";
import { PositionInspector } from "./position-inspector";
import { ExposureInspector } from "./exposure-inspector";
import {
  portfolioPath,
  type AccountingPolicy,
  type LedgerSummary,
  type PortfolioMetadata,
} from "./contracts";

type View =
  | "policy"
  | "cash"
  | "lots"
  | "activity"
  | "balances"
  | "positions"
  | "exposures";

export function AccountingDialog({
  portfolioKey = "KNK_MAIN",
  onClose,
}: {
  portfolioKey?: string;
  onClose: () => void;
}) {
  const [view, setView] = useState<View>("policy");
  const [policy, setPolicy] = useState<AccountingPolicy | null>(null);
  const [reason, setReason] = useState("");
  const client = useQueryClient();
  const metadata = useQuery({
    queryKey: ["ledger-metadata", portfolioKey],
    queryFn: ({ signal }) =>
      knkApi.get<PortfolioMetadata>(portfolioPath(portfolioKey), signal),
  });
  const summary = useQuery({
    queryKey: ["ledger-summary", portfolioKey],
    queryFn: ({ signal }) =>
      knkApi.get<LedgerSummary>(
        portfolioPath(portfolioKey) + "/summary",
        signal,
      ),
  });
  useEffect(() => {
    if (metadata.data) setPolicy(metadata.data.accounting_policy);
  }, [metadata.data]);
  const save = useMutation({
    mutationFn: () =>
      knkApi.put<PortfolioMetadata>(
        portfolioPath(portfolioKey) + "/accounting-policy",
        { ...policy, reason },
      ),
    onSuccess: async () => {
      setReason("");
      await client.invalidateQueries({
        queryKey: ["ledger-metadata", portfolioKey],
      });
      await client.invalidateQueries({
        queryKey: ["ledger-summary", portfolioKey],
      });
      await client.invalidateQueries({ queryKey: ["terminal-portfolio"] });
    },
  });
  const unchanged =
    policy &&
    metadata.data &&
    policy.method === metadata.data.accounting_policy.method &&
    policy.capitalize_commissions ===
      metadata.data.accounting_policy.capitalize_commissions &&
    policy.capitalize_fees === metadata.data.accounting_policy.capitalize_fees;
  const symbols = new Map(
    summary.data?.positions.map((position) => [
      position.instrument_id,
      position.symbol,
    ]),
  );
  return (
    <LedgerDialog
      title={`Portfolio accounting / ${metadata.data?.code ?? portfolioKey}`}
      onClose={onClose}
    >
      <div className="ledger-toolbar">
        <div className="segmented" role="group" aria-label="Accounting view">
          <button
            aria-pressed={view === "policy"}
            onClick={() => setView("policy")}
          >
            <Settings2 size={13} /> Policy
          </button>
          <button
            aria-pressed={view === "cash"}
            onClick={() => setView("cash")}
          >
            <Wallet size={13} /> Cash
          </button>
          <button
            aria-pressed={view === "positions"}
            onClick={() => setView("positions")}
          >
            <Crosshair size={13} /> Positions
          </button>
          <button
            aria-pressed={view === "lots"}
            onClick={() => setView("lots")}
          >
            <Layers size={13} /> Lots
          </button>
          <button
            aria-pressed={view === "exposures"}
            onClick={() => setView("exposures")}
          >
            <PieChart size={13} /> Exposures
          </button>
          <button
            aria-pressed={view === "activity"}
            onClick={() => setView("activity")}
          >
            <BookOpen size={13} /> Activity
          </button>
          <button
            aria-pressed={view === "balances"}
            onClick={() => setView("balances")}
          >
            <Scale size={13} /> Balances
          </button>
        </div>
        <IconButton
          label="Refresh accounting records"
          onClick={() => {
            metadata.refetch();
            summary.refetch();
            client.invalidateQueries({
              queryKey: ["ledger-accounting", portfolioKey],
            });
            client.invalidateQueries({
              queryKey: ["ledger-balances", portfolioKey],
            });
            client.invalidateQueries({
              queryKey: ["ledger-exposures", portfolioKey],
            });
            client.invalidateQueries({
              queryKey: ["ledger-position", portfolioKey],
            });
          }}
        >
          <RefreshCw size={13} />
        </IconButton>
        {summary.data && <Badge>{summary.data.quality}</Badge>}
      </div>
      <LedgerError error={metadata.error ?? summary.error} />
      {view === "policy" &&
        (!policy ? (
          !metadata.error && <LedgerLoading />
        ) : (
          <form
            className="ledger-policy-form"
            onSubmit={(event) => {
              event.preventDefault();
              save.mutate();
            }}
          >
            <Field label="Cost-basis method">
              <select
                aria-label="Cost-basis method"
                value={policy.method}
                onChange={(event) =>
                  setPolicy({
                    ...policy,
                    method: event.target.value as AccountingPolicy["method"],
                  })
                }
                disabled={save.isPending}
              >
                <option value="AVERAGE">Weighted average</option>
                <option value="FIFO">FIFO</option>
              </select>
            </Field>
            <label className="ledger-checkbox">
              <input
                type="checkbox"
                checked={policy.capitalize_commissions}
                onChange={(event) =>
                  setPolicy({
                    ...policy,
                    capitalize_commissions: event.target.checked,
                  })
                }
                disabled={save.isPending}
              />{" "}
              Capitalize transaction commissions
            </label>
            <label className="ledger-checkbox">
              <input
                type="checkbox"
                checked={policy.capitalize_fees}
                onChange={(event) =>
                  setPolicy({
                    ...policy,
                    capitalize_fees: event.target.checked,
                  })
                }
                disabled={save.isPending}
              />{" "}
              Capitalize transaction fees
            </label>
            <Field label="Policy change reason">
              <textarea
                aria-label="Policy change reason"
                required
                minLength={5}
                maxLength={2000}
                rows={3}
                value={reason}
                onChange={(event) => setReason(event.target.value)}
                disabled={save.isPending}
              />
            </Field>
            <LedgerError error={save.error} />
            {save.isSuccess && (
              <div role="status" className="positive">
                Accounting policy saved
              </div>
            )}
            <button
              type="submit"
              disabled={
                Boolean(unchanged) || reason.trim().length < 5 || save.isPending
              }
            >
              <Save size={13} /> {save.isPending ? "Saving..." : "Save policy"}
            </button>
          </form>
        ))}
      {view === "cash" &&
        (!summary.data ? (
          !summary.error && <LedgerLoading />
        ) : (
          <>
            <dl className="ledger-totals">
              <div>
                <dt>Economic cash / {summary.data.portfolio.base_currency}</dt>
                <dd>{money(summary.data.portfolio.cash)}</dd>
              </div>
              <div>
                <dt>Settled cash</dt>
                <dd>{money(summary.data.portfolio.settled_cash)}</dd>
              </div>
              <div>
                <dt>Available cash</dt>
                <dd>{money(summary.data.portfolio.available_cash)}</dd>
              </div>
            </dl>
            <div className="ledger-table-scroll">
              <table className="ledger-table">
                <thead>
                  <tr>
                    <th scope="col">CCY</th>
                    <th scope="col">Economic</th>
                    <th scope="col">Settled</th>
                    <th scope="col">Receivable</th>
                    <th scope="col">Payable</th>
                    <th scope="col">Available</th>
                    <th scope="col">FX</th>
                    <th scope="col">Source</th>
                  </tr>
                </thead>
                <tbody>
                  {summary.data.cash.map((cash) => (
                    <tr key={cash.currency}>
                      <th scope="row">{cash.currency}</th>
                      <td>{number(cash.amount, 2)}</td>
                      <td>{number(cash.settled, 2)}</td>
                      <td>{number(cash.receivable, 2)}</td>
                      <td>{number(cash.payable, 2)}</td>
                      <td>{number(cash.available, 2)}</td>
                      <td>{number(cash.fx_rate, 6)}</td>
                      <td>{cash.source}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        ))}
      {view === "lots" &&
        (!summary.data ? (
          !summary.error && <LedgerLoading />
        ) : (
          <div className="ledger-table-scroll">
            <table className="ledger-table">
              <thead>
                <tr>
                  <th scope="col">Security</th>
                  <th scope="col">Acquired</th>
                  <th scope="col">Side</th>
                  <th scope="col">Quantity</th>
                  <th scope="col">Native basis</th>
                  <th scope="col">Base basis</th>
                  <th scope="col">Opening transaction</th>
                </tr>
              </thead>
              <tbody>
                {summary.data.lots.map((lot) => (
                  <tr key={lot.id}>
                    <th scope="row">
                      {symbols.get(lot.instrument_id) ?? lot.instrument_id}
                    </th>
                    <td>{lot.opened}</td>
                    <td>{lot.direction}</td>
                    <td>{number(lot.quantity, 8)}</td>
                    <td>{number(lot.native_basis, 2)}</td>
                    <td>{number(lot.base_basis, 2)}</td>
                    <td className="ledger-identifier">{lot.entry_id}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {!summary.data.lots.length && (
              <div className="ledger-loading">No position lots</div>
            )}
          </div>
        ))}
      {view === "activity" && summary.data && (
        <AccountingActivity
          portfolioKey={portfolioKey}
          runId={summary.data.valuation_run_id}
        />
      )}
      {view === "balances" && <BalanceEditor portfolioKey={portfolioKey} />}
      {view === "exposures" && summary.data && (
        <ExposureInspector
          portfolioKey={portfolioKey}
          runId={summary.data.valuation_run_id}
        />
      )}
      {view === "positions" && summary.data && (
        <PositionInspector
          portfolioKey={portfolioKey}
          runId={summary.data.valuation_run_id}
          positions={summary.data.positions}
        />
      )}
      {summary.data && (
        <footer className="ledger-run-details">
          <span>Run {summary.data.valuation_run_id}</span>
          <span>{summary.data.calculation_version}</span>
          <span>{timestamp(summary.data.calculated_at)}</span>
        </footer>
      )}
    </LedgerDialog>
  );
}
