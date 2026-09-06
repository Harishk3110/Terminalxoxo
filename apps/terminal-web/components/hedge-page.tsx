"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { knkApi } from "@knk/api-client";
import { Check, Download, Play } from "lucide-react";
import { PageTitle, useApi } from "./core-pages";
import { useTabState, useTerminal } from "./context";
import {
  Badge,
  DataTable,
  Field,
  IconButton,
  Kpis,
  Panel,
  exportCsv,
  money,
  number,
  pct,
} from "./ui";
import type { Row, Run } from "./types";

interface HedgeResult extends Row {
  id: string;
  source: string;
  as_of: string;
  quality: string;
  warnings: string[];
  review_state: string;
}

export function HedgeWorkspace() {
  const { bootstrap } = useTerminal();
  const [mode, setMode] = useTabState("hedge-mode", "BETA");
  const [instrumentType, setInstrumentType] = useTabState("hedge-type", "ETF");
  const [symbol, setSymbol] = useTabState("hedge-symbol-v2", "SPY");
  const [target, setTarget] = useTabState("hedge-target-v2", "0.8");
  const [sector, setSector] = useTabState("hedge-sector", "Technology");
  const [currency, setCurrency] = useTabState("hedge-currency", "USD");
  const [fees, setFees] = useTabState("hedge-fees", "0");
  const [slippage, setSlippage] = useTabState("hedge-slippage", "0");
  const [price, setPrice] = useTabState("hedge-futures-price", "");
  const [beta, setBeta] = useTabState("hedge-futures-beta", "");
  const [multiplier, setMultiplier] = useTabState("hedge-multiplier", "");
  const [result, setResult] = useTabState<HedgeResult | null>(
    "hedge-result-v2",
    null,
  );
  const [reviewState, setReviewState] = useState("REVIEWED");
  const [reason, setReason] = useState("");
  const recent = useApi<{ items: Run[] }>(
    "hedge-runs",
    "/api/v1/terminal/runs?kind=hedge",
  );
  const calculate = useMutation({
    mutationFn: () =>
      knkApi.post<HedgeResult>("/api/v1/risk/portfolios/KNK_MAIN/hedges", {
        mode,
        symbol,
        target: Number(target),
        sector,
        currency,
        instrument_type: mode === "CURRENCY" ? "FX_CONVERSION" : instrumentType,
        fee_bps: Number(fees),
        slippage_bps: Number(slippage),
        ...(instrumentType === "FUTURE_ESTIMATE" && mode !== "CURRENCY"
          ? {
              assumed_price: Number(price),
              assumed_beta: Number(beta),
              contract_multiplier: Number(multiplier),
            }
          : {}),
      }),
    onSuccess: (value) => {
      setResult(value);
      recent.refetch();
    },
  });
  const review = useMutation({
    mutationFn: () =>
      knkApi.post<HedgeResult>(
        `/api/v1/risk/portfolios/KNK_MAIN/hedges/${result?.id}/review`,
        { state: reviewState, reason },
      ),
    onSuccess: (value) => {
      setResult(value);
      setReason("");
      recent.refetch();
    },
  });
  const comparison = [
    { metric: "Beta", before: result?.beta_before, after: result?.beta_after },
    {
      metric: "Gross / NAV",
      before: result?.gross_before,
      after: result?.gross_after,
    },
    {
      metric: "Net / NAV",
      before: result?.net_before,
      after: result?.net_after,
    },
    {
      metric: "Historical 1d VaR 95% (SGD)",
      before: result?.var_before,
      after: result?.var_after,
    },
    {
      metric: "NAV after assumed costs (SGD)",
      before: result?.pre_nav,
      after: result?.post_cost_nav,
    },
  ];
  return (
    <>
      <PageTitle code="HEDGE" title="Internal Hedge Analysis">
        <Badge>{result?.quality ?? "ASSUMPTIONS"}</Badge>
        <Badge>{result?.review_state ?? "DRAFT"}</Badge>
      </PageTitle>
      <Kpis
        source={result?.source}
        asOf={result?.as_of}
        items={[
          { label: "Current beta", value: number(result?.beta_before) },
          { label: "Post-hedge beta", value: number(result?.beta_after) },
          { label: "Signed notional", value: money(result?.signed_notional) },
          { label: "Rounded quantity", value: number(result?.units) },
          {
            label: "Residual notional",
            value: money(result?.residual_notional),
          },
          { label: "Post-hedge gross", value: pct(result?.gross_after) },
        ]}
      />
      <div className="page-grid hedge-grid">
        <Panel
          title="Hedge assumptions"
          source="KNK_MAIN / internal ledger"
          quality="ASSUMPTIONS"
        >
          <div className="compact-form">
            <Field label="Target mode">
              <select
                aria-label="Hedge target mode"
                value={mode}
                onChange={(e) => setMode(e.target.value)}
              >
                {["BETA", "NET", "SECTOR", "CURRENCY"].map((v) => (
                  <option key={v}>{v}</option>
                ))}
              </select>
            </Field>
            <Field
              label={
                mode === "BETA" ? "Target beta" : "Target weight (fraction)"
              }
            >
              <input
                aria-label="Hedge target"
                type="number"
                min="-3"
                max="3"
                step=".05"
                value={target}
                onChange={(e) => setTarget(e.target.value)}
              />
            </Field>
            {mode !== "CURRENCY" && (
              <>
                <Field label="Instrument type">
                  <select
                    aria-label="Hedge instrument type"
                    value={instrumentType}
                    onChange={(e) => setInstrumentType(e.target.value)}
                  >
                    <option value="ETF">ETF</option>
                    <option value="FUTURE_ESTIMATE">
                      Index futures estimate
                    </option>
                  </select>
                </Field>
                <Field label="Instrument">
                  {instrumentType === "ETF" ? (
                    <select
                      aria-label="Hedge instrument"
                      value={symbol}
                      onChange={(e) => setSymbol(e.target.value)}
                    >
                      {bootstrap.quotes
                        .filter((q) => q.asset_class === "ETF")
                        .map((q) => (
                          <option key={q.id}>{q.symbol}</option>
                        ))}
                    </select>
                  ) : (
                    <input
                      aria-label="Futures symbol"
                      value={symbol}
                      onChange={(e) => setSymbol(e.target.value.toUpperCase())}
                    />
                  )}
                </Field>
              </>
            )}
            {mode === "SECTOR" && (
              <Field label="Sector">
                <input
                  aria-label="Hedge sector"
                  value={sector}
                  onChange={(e) => setSector(e.target.value)}
                />
              </Field>
            )}
            {(mode === "CURRENCY" || instrumentType === "FUTURE_ESTIMATE") && (
              <Field label="Native currency">
                <input
                  aria-label="Hedge currency"
                  value={currency}
                  maxLength={3}
                  onChange={(e) => setCurrency(e.target.value.toUpperCase())}
                />
              </Field>
            )}
            {mode !== "CURRENCY" && instrumentType === "FUTURE_ESTIMATE" && (
              <>
                <Field label="Assumed futures price">
                  <input
                    aria-label="Assumed futures price"
                    type="number"
                    min=".01"
                    step=".25"
                    value={price}
                    onChange={(e) => setPrice(e.target.value)}
                  />
                </Field>
                <Field label="Assumed futures beta">
                  <input
                    aria-label="Assumed futures beta"
                    type="number"
                    min="-5"
                    max="5"
                    step=".01"
                    value={beta}
                    onChange={(e) => setBeta(e.target.value)}
                  />
                </Field>
                <Field label="Contract multiplier">
                  <input
                    aria-label="Contract multiplier"
                    type="number"
                    min=".01"
                    step=".01"
                    value={multiplier}
                    onChange={(e) => setMultiplier(e.target.value)}
                  />
                </Field>
              </>
            )}
            <Field label="Fees (bp)">
              <input
                aria-label="Hedge fees"
                type="number"
                min="0"
                max="100"
                value={fees}
                onChange={(e) => setFees(e.target.value)}
              />
            </Field>
            <Field label="Slippage (bp)">
              <input
                aria-label="Hedge slippage"
                type="number"
                min="0"
                max="500"
                value={slippage}
                onChange={(e) => setSlippage(e.target.value)}
              />
            </Field>
          </div>
          <div className="form-actions">
            <button
              className="primary-button"
              disabled={
                calculate.isPending ||
                !target ||
                !fees ||
                !slippage ||
                (instrumentType === "FUTURE_ESTIMATE" &&
                  mode !== "CURRENCY" &&
                  (!price || !beta || !multiplier))
              }
              onClick={() => calculate.mutate()}
            >
              <Play size={13} />
              {calculate.isPending ? "Calculating..." : "Calculate Hedge"}
            </button>
          </div>
          {calculate.error && (
            <p className="error-state" role="alert">
              {calculate.error.message}
            </p>
          )}
          <p className="warning-note section-pad">
            MANUAL REVIEW REQUIRED - NO ORDER WILL BE SUBMITTED
          </p>
        </Panel>
        <Panel
          title="Before / after"
          source={result?.source}
          asOf={result?.as_of}
          quality={result?.quality}
          rows={comparison}
        >
          <DataTable
            id="hedge-comparison"
            rows={comparison}
            columns={[
              { key: "metric", label: "Metric", size: 220 },
              { key: "before", label: "Before", numeric: true },
              { key: "after", label: "After", numeric: true },
            ]}
          />
          {result && (
            <div className="section-pad">
              <p>
                Incremental equity stress: {money(result.equity_stress_impact)}
              </p>
              <p>
                Incremental currency stress:{" "}
                {money(result.currency_stress_impact)}
              </p>
              <p>
                Fees: {money(result.estimated_fees)} / Slippage:{" "}
                {money(result.estimated_slippage)}
              </p>
              <p>VaR model: {String(result.var_state)}</p>
            </div>
          )}
        </Panel>
        <Panel
          className="wide-panel"
          title="Saved analyses / review"
          source="Internal analytical records"
          quality="MANUAL REVIEW"
        >
          <DataTable
            id="hedge-history"
            rows={
              recent.data?.items.map((run) => ({
                id: run.id,
                name: run.name,
                created_at: run.created_at,
                review: run.result?.review_state,
                units: run.result?.units,
                notional: run.result?.signed_notional,
              })) ?? []
            }
            columns={[
              { key: "name", label: "Analysis", size: 200 },
              { key: "units", label: "Units", numeric: true },
              { key: "notional", label: "Signed notional", numeric: true },
              { key: "review", label: "Review", size: 160 },
              { key: "created_at", label: "Created", size: 200 },
            ]}
            onSelect={(row) => {
              const run = recent.data?.items.find((item) => item.id === row.id);
              if (run?.result) {
                setResult({
                  ...run.result,
                  id: run.id,
                  review_state: String(run.result.review_state ?? "DRAFT"),
                });
                setMode(String(run.parameters.mode));
                setInstrumentType(String(run.parameters.instrument_type));
                setSymbol(String(run.parameters.symbol));
                setTarget(String(run.parameters.target));
                setFees(String(run.parameters.fee_bps));
                setSlippage(String(run.parameters.slippage_bps));
                setSector(String(run.parameters.sector));
                setCurrency(String(run.parameters.currency));
                setPrice(String(run.parameters.assumed_price ?? ""));
                setBeta(String(run.parameters.assumed_beta ?? ""));
                setMultiplier(String(run.parameters.contract_multiplier ?? ""));
              }
            }}
          />
          {result && (
            <>
              <div className="form-actions">
                <select
                  aria-label="Hedge review state"
                  value={reviewState}
                  onChange={(e) => setReviewState(e.target.value)}
                >
                  {["DRAFT", "REVIEWED", "ACCEPTED MANUALLY", "REJECTED"].map(
                    (v) => (
                      <option key={v}>{v}</option>
                    ),
                  )}
                </select>
                <input
                  aria-label="Hedge review reason"
                  placeholder="Review reason"
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                />
                <button
                  disabled={reason.trim().length < 10 || review.isPending}
                  onClick={() => review.mutate()}
                >
                  <Check size={13} />
                  Save Review
                </button>
                <IconButton
                  label="Export hedge analysis"
                  onClick={() => exportCsv("hedge-analysis", [result])}
                >
                  <Download size={13} />
                </IconButton>
              </div>
              <p className="source-note">
                Run {result.id} / Valuation {String(result.valuation_run_id)}
              </p>
              {result.warnings.map((warning) => (
                <p className="warning-note section-pad" key={warning}>
                  {warning}
                </p>
              ))}
            </>
          )}
          {review.error && (
            <p role="alert" className="error-state">
              {review.error.message}
            </p>
          )}
        </Panel>
      </div>
    </>
  );
}
