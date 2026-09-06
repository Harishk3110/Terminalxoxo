"use client";

import { useQuery } from "@tanstack/react-query";
import { knkApi } from "@knk/api-client";
import { Badge, number } from "../ui";
import { LedgerError, LedgerLoading } from "./dialog";
import { portfolioPath } from "./contracts";

export interface NavStatement {
  state: "AVAILABLE" | "INCOMPLETE";
  items: {
    nav: string | null;
    cash: string | null;
    cash_assets: string | null;
    cash_overdrafts: string | null;
    market_value: string | null;
    long_market_value: string | null;
    short_liabilities: string | null;
    gross_asset_value: string | null;
    accrued_income: string | null;
    receivables: string | null;
    payables: string | null;
    accrued_fees: string | null;
    other_liabilities: string | null;
    liabilities: string | null;
  };
  difference: string | null;
  reconciliation_state: "BALANCED" | "BREAK" | "INCOMPLETE";
  methodology: string;
  warnings: string[];
}

export interface NavStatementSnapshot {
  portfolio: { id: string; base_currency: string; nav: string | null };
  balance_sheet: NavStatement | null;
  state: "AVAILABLE" | "INCOMPLETE" | "LEGACY_SNAPSHOT";
  valuation_run_id: string;
  valuation_date: string;
  calculation_version: string;
  quality: string;
  calculated_at: string;
}

const assetLines = [
  ["cash_assets", "Positive settled cash"],
  ["long_market_value", "Long position assets"],
  ["accrued_income", "Accrued income"],
  ["receivables", "Receivables"],
] as const;
const liabilityLines = [
  ["cash_overdrafts", "Cash overdrafts"],
  ["short_liabilities", "Short position liabilities"],
  ["payables", "Payables"],
  ["accrued_fees", "Accrued fees"],
  ["other_liabilities", "Other liabilities"],
] as const;

function StatementSide({
  label,
  lines,
  items,
  total,
  currency,
}: {
  label: string;
  lines: readonly (readonly [keyof NavStatement["items"], string])[];
  items: NavStatement["items"];
  total: "gross_asset_value" | "liabilities";
  currency: string;
}) {
  return (
    <div className="ledger-table-scroll">
      <table className="ledger-table" aria-label={label + " statement"}>
        <thead>
          <tr>
            <th scope="col">{label}</th>
            <th scope="col">{currency}</th>
          </tr>
        </thead>
        <tbody>
          {lines.map(([key, title]) => (
            <tr key={key}>
              <th scope="row">{title}</th>
              <td>{number(items[key], 8)}</td>
            </tr>
          ))}
        </tbody>
        <tfoot>
          <tr>
            <th scope="row">
              {total === "gross_asset_value"
                ? "Gross assets"
                : "Total liabilities"}
            </th>
            <td>{number(items[total], 8)}</td>
          </tr>
        </tfoot>
      </table>
    </div>
  );
}

export function NavInspector({
  portfolioKey,
  runId,
}: {
  portfolioKey: string;
  runId: string;
}) {
  const query = useQuery({
    queryKey: ["ledger-nav", portfolioKey, runId],
    queryFn: ({ signal }) =>
      knkApi.get<NavStatementSnapshot>(
        portfolioPath(portfolioKey) +
          "/nav?" +
          new URLSearchParams({ run_id: runId }),
        signal,
      ),
  });
  const data = query.data;
  const sheet = data?.balance_sheet;
  return (
    <section aria-label="NAV balance sheet">
      <LedgerError error={query.error} />
      {query.isPending && <LedgerLoading />}
      {data && (
        <>
          <div className="ledger-toolbar">
            <Badge>{data.state}</Badge>
            {sheet && <Badge>{sheet.reconciliation_state}</Badge>}
            <span className="ledger-position-context">
              {data.valuation_date} / {data.portfolio.base_currency}
            </span>
          </div>
          <dl className="ledger-totals ledger-position-measures">
            <div>
              <dt>Closing NAV / {data.portfolio.base_currency}</dt>
              <dd>{number(sheet ? sheet.items.nav : data.portfolio.nav, 8)}</dd>
            </div>
            <div>
              <dt>Gross assets</dt>
              <dd>{number(sheet?.items.gross_asset_value, 8)}</dd>
            </div>
            <div>
              <dt>Total liabilities</dt>
              <dd>{number(sheet?.items.liabilities, 8)}</dd>
            </div>
          </dl>
          {!sheet && (
            <div role="status" className="ledger-error">
              This saved run predates the complete NAV balance sheet
            </div>
          )}
          {sheet && (
            <>
              {sheet.warnings.map((warning) => (
                <div role="status" className="ledger-error" key={warning}>
                  {warning}
                </div>
              ))}
              <div className="ledger-nav-columns">
                <StatementSide
                  label="Assets"
                  lines={assetLines}
                  items={sheet.items}
                  total="gross_asset_value"
                  currency={data.portfolio.base_currency}
                />
                <StatementSide
                  label="Liabilities"
                  lines={liabilityLines}
                  items={sheet.items}
                  total="liabilities"
                  currency={data.portfolio.base_currency}
                />
              </div>
              <dl className="ledger-totals ledger-position-measures">
                <div>
                  <dt>Net settled cash</dt>
                  <dd>{number(sheet.items.cash, 8)}</dd>
                </div>
                <div>
                  <dt>Net position value</dt>
                  <dd>{number(sheet.items.market_value, 8)}</dd>
                </div>
                <div>
                  <dt>Assets less liabilities less NAV</dt>
                  <dd>{number(sheet.difference, 8)}</dd>
                </div>
              </dl>
              <p className="ledger-methodology">{sheet.methodology}</p>
            </>
          )}
        </>
      )}
    </section>
  );
}
