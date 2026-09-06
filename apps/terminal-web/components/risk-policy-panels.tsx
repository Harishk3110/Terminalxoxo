"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { knkApi } from "@knk/api-client";
import { Plus, Save, Settings2 } from "lucide-react";
import { LedgerDialog } from "./ledger/dialog";
import { useApi } from "./core-pages";
import {
  Badge,
  DataTable,
  Field,
  IconButton,
  Panel,
  money,
  number,
  pct,
} from "./ui";
import type { Row } from "./types";

interface Monitor {
  limits: Row[];
  timeline: Row[];
  risk: Record<string, number | null>;
  model: {
    state: string;
    reason: string | null;
    settings: Record<string, number>;
  };
  source: string;
  quality: string;
  as_of: string;
}
const limitMetrics = [
  "max_position_weight",
  "top_five_concentration",
  "max_sector_weight",
  "max_country_weight",
  "max_industry_weight",
  "max_currency_weight",
  "gross_exposure",
  "net_exposure",
  "beta",
  "volatility",
  "var_loss_95",
  "cvar_loss_95",
  "drawdown_loss",
  "cash_weight",
  "leverage",
  "stale_exposure",
];
const defaults = {
  minimum_observations: 60,
  ewma_decay: 0.94,
  simulations: 10000,
  seed: 3110,
  rolling_window: 60,
};
const unit = (metric: string) =>
  metric.includes("var_loss")
    ? "SGD loss"
    : ["beta", "leverage"].includes(metric)
      ? "ratio"
      : "NAV fraction";

export function RiskPolicyPanels() {
  const path = "/api/v1/risk/portfolios/KNK_MAIN";
  const query = useApi<Monitor>("risk-monitor", `${path}/monitor`);
  const cache = useQueryClient();
  const data = query.data;
  const [editor, setEditor] = useState<"limit" | "model" | null>(null);
  const [identifier, setIdentifier] = useState<string | null>(null);
  const [metric, setMetric] = useState("gross_exposure");
  const [threshold, setThreshold] = useState("1.2");
  const [direction, setDirection] = useState("MAX");
  const [enabled, setEnabled] = useState(true);
  const [reason, setReason] = useState("");
  const [settings, setSettings] = useState<Record<string, number>>(defaults);
  const [method, setMethod] = useState("historical");
  const [view, setView] = useState("limits");
  const edit = (row?: Row) => {
    setIdentifier(row ? String(row.id) : null);
    setMetric(String(row?.metric ?? "gross_exposure"));
    setThreshold(String(row?.threshold ?? "1.2"));
    setDirection(String(row?.direction ?? "MAX"));
    setEnabled(row?.enabled !== false);
    setReason("");
    setEditor("limit");
  };
  const save = useMutation({
    mutationFn: () =>
      knkApi.post(
        editor === "model"
          ? `${path}/settings`
          : `${path}/limits${identifier ? "/" + identifier : ""}`,
        editor === "model"
          ? { ...settings, reason }
          : { metric, threshold, direction, enabled, reason },
      ),
    onSuccess: async () => {
      setEditor(null);
      await cache.invalidateQueries();
    },
  });
  const prefix = method === "historical" ? "" : method + "_";
  return (
    <>
      <div className="page-grid risk-policy-grid">
        <Panel
          title="Internal ledger / limit monitor"
          source={data?.source}
          quality={data?.quality}
          asOf={data?.as_of}
          loading={query.isLoading}
          error={query.error}
          actions={
            <>
              <div className="segmented">
                {["limits", "timeline"].map((value) => (
                  <button
                    key={value}
                    aria-pressed={view === value}
                    onClick={() => setView(value)}
                  >
                    {value}
                  </button>
                ))}
              </div>
              <IconButton
                label="Add risk limit"
                onClick={() => {
                  save.reset();
                  edit();
                }}
              >
                <Plus size={13} />
              </IconButton>
            </>
          }
        >
          {view === "limits" ? (
            <DataTable
              id="risk-limits"
              rows={
                data?.limits.map((row) => ({
                  ...row,
                  unit: unit(String(row.metric)),
                })) ?? []
              }
              onSelect={(row) => {
                save.reset();
                edit(row);
              }}
              columns={[
                { key: "metric", label: "Limit", size: 155 },
                { key: "value", label: "Current", numeric: true, size: 80 },
                {
                  key: "threshold",
                  label: "Threshold",
                  numeric: true,
                  size: 90,
                },
                { key: "direction", label: "Rule", size: 55 },
                { key: "unit", label: "Unit", size: 100 },
                { key: "state", label: "State", size: 125 },
                { key: "first_breach", label: "First breach", size: 190 },
                { key: "last_checked", label: "Last checked", size: 190 },
              ]}
            />
          ) : (
            <DataTable
              id="risk-timeline"
              rows={data?.timeline ?? []}
              columns={[
                { key: "timestamp", label: "Checked", size: 190 },
                { key: "action", label: "Event", size: 220 },
                { key: "before", label: "Before", size: 125 },
                { key: "after", label: "After", size: 125 },
              ]}
            />
          )}
        </Panel>
        <Panel
          title="Current-weight security risk"
          source={data?.source}
          quality={data?.quality}
          asOf={data?.as_of}
          actions={
            <IconButton
              label="Risk model settings"
              onClick={() => {
                save.reset();
                setSettings(data?.model?.settings ?? defaults);
                setReason("");
                setEditor("model");
              }}
            >
              <Settings2 size={13} />
            </IconButton>
          }
        >
          <div className="operation-form">
            <div className="segmented">
              {["historical", "parametric", "monte_carlo"].map((value) => (
                <button
                  key={value}
                  aria-pressed={method === value}
                  onClick={() => setMethod(value)}
                >
                  {value.replaceAll("_", " ")}
                </button>
              ))}
            </div>
            <Badge>{data?.model?.state ?? "UNAVAILABLE"}</Badge>
            <dl className="operating-facts">
              {[
                ["VaR 95% / 1D", money(data?.risk[prefix + "var_95"])],
                ["VaR 99% / 1D", money(data?.risk[prefix + "var_99"])],
                ["Historical CVaR 95%", money(data?.risk.cvar_95)],
                ["Volatility", pct(data?.risk.volatility)],
                ["EWMA volatility", pct(data?.risk.ewma_volatility)],
                ["HHI / NAV weights", number(data?.risk.hhi)],
                ["Observations", number(data?.risk.observations, 0)],
              ].map(([label, value]) => (
                <div key={label}>
                  <dt>{label}</dt>
                  <dd>{value}</dd>
                </div>
              ))}
            </dl>
            {data?.model?.reason && (
              <div className="warning">{data.model.reason}</div>
            )}
          </div>
        </Panel>
      </div>
      {editor && (
        <LedgerDialog
          title={
            editor === "model" ? "Risk model settings" : "Configure risk limit"
          }
          closeLabel="Close risk editor"
          closeDisabled={save.isPending}
          onClose={() => setEditor(null)}
        >
          <form
            className="operation-form"
            onSubmit={(event) => {
              event.preventDefault();
              save.mutate();
            }}
          >
            {editor === "limit" ? (
              <>
                <Field label="Metric">
                  <select
                    aria-label="Risk limit metric"
                    value={metric}
                    onChange={(event) => setMetric(event.target.value)}
                  >
                    {limitMetrics.map((value) => (
                      <option key={value}>{value}</option>
                    ))}
                  </select>
                </Field>
                <Field label={`Threshold (${unit(metric)})`}>
                  <input
                    aria-label="Risk limit threshold"
                    type="number"
                    step="any"
                    required
                    value={threshold}
                    onChange={(event) => setThreshold(event.target.value)}
                  />
                </Field>
                <Field label="Direction">
                  <select
                    aria-label="Risk limit direction"
                    value={direction}
                    onChange={(event) => setDirection(event.target.value)}
                  >
                    <option>MAX</option>
                    <option>MIN</option>
                  </select>
                </Field>
                <label className="checkbox">
                  <input
                    type="checkbox"
                    checked={enabled}
                    onChange={(event) => setEnabled(event.target.checked)}
                  />
                  Enabled
                </label>
              </>
            ) : (
              Object.entries(settings).map(([key, value]) => (
                <Field key={key} label={key.replaceAll("_", " ")}>
                  <input
                    aria-label={key.replaceAll("_", " ")}
                    type="number"
                    step={key === "ewma_decay" ? ".01" : "1"}
                    value={value}
                    onChange={(event) =>
                      setSettings((current) => ({
                        ...current,
                        [key]: Number(event.target.value),
                      }))
                    }
                  />
                </Field>
              ))
            )}
            <Field label="Change reason">
              <textarea
                aria-label="Risk change reason"
                required
                minLength={10}
                maxLength={2000}
                value={reason}
                onChange={(event) => setReason(event.target.value)}
                rows={3}
              />
            </Field>
            {save.error && (
              <div role="alert" className="negative">
                {String(save.error)}
              </div>
            )}
            <button
              type="submit"
              disabled={reason.trim().length < 10 || save.isPending}
            >
              <Save size={13} />
              Save configuration
            </button>
          </form>
        </LedgerDialog>
      )}
    </>
  );
}
