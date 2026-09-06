"use client";
import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { knkApi } from "@knk/api-client";
import { Check, RefreshCw } from "lucide-react";
import { useTerminal } from "./context";
import { PageTitle, useApi } from "./core-pages";
import { Badge, DataTable, Field, Panel, timestamp } from "./ui";
import type { Row } from "./types";

type Snapshot = Row & {
  id: string;
  fills: Row[];
  positions: Row[];
  cash: Row[];
};
export function BrokerMonitorPage() {
  const { open } = useTerminal();
  const query = useApi<{ state: string; snapshot: Snapshot | null }>(
    "broker-snapshot",
    "/api/v1/broker/snapshot",
  );
  const snapshot = query.data?.snapshot;
  const [fill, setFill] = useState<Row | null>(null);
  const [kind, setKind] = useState("BUY");
  const [fx, setFx] = useState("");
  const [reason, setReason] = useState("");
  const client = useQueryClient();
  const approve = useMutation({
    mutationFn: () =>
      knkApi.post("/api/v1/broker/fills/import", {
        snapshot_id: snapshot?.id,
        execution_id: fill?.execution_id,
        transaction_type: kind,
        fx_rate_to_base: fx,
        rationale: reason,
      }),
    onSuccess: () => {
      setFill(null);
      setReason("");
      client.invalidateQueries({ queryKey: ["terminal-portfolio"] });
      client.invalidateQueries({ queryKey: ["operating-trades"] });
    },
  });
  const reconcile = useMutation({
    mutationFn: () =>
      knkApi.post<{ state: string; items: Row[] }>(
        "/api/v1/operations/reconciliation",
        {},
      ),
  });
  return (
    <>
      <PageTitle code="IBKR" title="Paper Broker Monitor">
        <Badge>{query.data?.state ?? "CHECKING"}</Badge>
        <button
          title="Refresh snapshot"
          aria-label="Refresh snapshot"
          onClick={() => query.refetch()}
        >
          <RefreshCw size={14} />
        </button>
        <button onClick={() => open("/data-drop", "DATADROP")}>
          Agent pairing
        </button>
        <button
          onClick={() => reconcile.mutate()}
          disabled={reconcile.isPending}
        >
          <RefreshCw size={14} /> Reconcile ledger
        </button>
      </PageTitle>
      <div className="page-grid operation-two-column">
        <Panel
          title="Reported paper account"
          source="IBKR PAPER"
          quality={query.data?.state}
          asOf={snapshot?.as_of as string}
          loading={query.isLoading}
          error={query.error}
        >
          <div className="operation-form">
            <div>
              Account: {String(snapshot?.account_mask ?? "NOT CONNECTED")}
            </div>
            <div>
              Reported NAV: {String(snapshot?.nav ?? "--")}{" "}
              {String(snapshot?.currency ?? "")}
            </div>
            <div>
              Snapshot:{" "}
              {snapshot?.as_of ? timestamp(String(snapshot.as_of)) : "--"}
            </div>
            <div className="warning-note">
              READ ONLY / NO ORDER TRANSMISSION
            </div>
            <div className="secondary">
              Current broker balances and internal ledger history are separate.
              Broker-history performance and risk are unavailable.
            </div>
          </div>
          <DataTable
            id="broker-cash"
            rows={snapshot?.cash ?? []}
            columns={[
              { key: "currency", label: "CCY" },
              { key: "amount", label: "Native cash", numeric: true },
            ]}
          />
        </Panel>
        <Panel
          title="Broker positions"
          source="IBKR PAPER"
          quality={query.data?.state}
        >
          <DataTable
            id="broker-positions"
            rows={snapshot?.positions ?? []}
            columns={[
              { key: "symbol", label: "Symbol" },
              { key: "quantity", label: "Quantity", numeric: true },
              { key: "average_cost", label: "Average cost", numeric: true },
              { key: "market_price", label: "Reported price", numeric: true },
              { key: "currency", label: "CCY" },
            ]}
          />
        </Panel>
        <Panel
          title="Recorded executions / ledger approval"
          source="IBKR PAPER"
        >
          <DataTable
            id="broker-fills"
            rows={snapshot?.fills ?? []}
            onSelect={(r) => {
              setFill(r);
              setKind(["BOT", "BUY"].includes(String(r.side)) ? "BUY" : "SELL");
              setFx("");
              approve.reset();
            }}
            columns={[
              { key: "execution_id", label: "Execution ID", size: 180 },
              { key: "symbol", label: "Symbol" },
              { key: "side", label: "Side" },
              { key: "quantity", label: "Qty", numeric: true },
              { key: "price", label: "Price", numeric: true },
              { key: "commission", label: "Commission", numeric: true },
            ]}
          />
        </Panel>
        <Panel
          title="Approve recorded fill to internal ledger"
          source="EXPLICIT APPROVAL"
        >
          {fill ? (
            <div className="operation-form">
              <div>
                {String(fill.execution_id)} / {String(fill.symbol)}
              </div>
              <Field label="Ledger type">
                <select value={kind} onChange={(e) => setKind(e.target.value)}>
                  {(["BOT", "BUY"].includes(String(fill.side))
                    ? ["BUY", "COVER"]
                    : ["SELL", "SHORT"]
                  ).map((k) => (
                    <option key={k}>{k}</option>
                  ))}
                </select>
              </Field>
              <Field label="Recorded trade-date FX to base">
                <input
                  type="number"
                  min="0.00000001"
                  step="any"
                  value={fx}
                  onChange={(e) => setFx(e.target.value)}
                />
              </Field>
              <Field label="Approval rationale">
                <textarea
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                />
              </Field>
              <button
                disabled={
                  approve.isPending ||
                  reason.trim().length < 5 ||
                  Number(fx) <= 0
                }
                onClick={() => approve.mutate()}
              >
                <Check size={14} /> Approve ledger entry
              </button>
              {approve.error && <div role="alert">{approve.error.message}</div>}
            </div>
          ) : (
            <div className="section-pad secondary">
              {approve.isSuccess
                ? "Ledger entry recorded."
                : "No execution selected."}
            </div>
          )}
        </Panel>
        <Panel
          title={"Reconciliation / " + (reconcile.data?.state ?? "NOT RUN")}
          source="INTERNAL VS BROKER"
          error={reconcile.error}
          loading={reconcile.isPending}
        >
          <DataTable
            id="broker-breaks"
            rows={reconcile.data?.items ?? []}
            columns={[
              { key: "type", label: "Break", size: 200 },
              { key: "key", label: "Reference", size: 160 },
              {
                key: "internal",
                label: "Internal",
                format: (v) =>
                  typeof v === "object" ? JSON.stringify(v) : String(v ?? "--"),
              },
              {
                key: "external",
                label: "Broker",
                format: (v) =>
                  typeof v === "object" ? JSON.stringify(v) : String(v ?? "--"),
              },
              { key: "difference", label: "Difference", numeric: true },
            ]}
          />
        </Panel>
      </div>
    </>
  );
}
