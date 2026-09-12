// @vitest-environment jsdom
import { cleanup, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { knkApi } from "@knk/api-client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { renderLedger } from "./ledger-render";

vi.mock("../components/context", async (original) => ({
  ...(await original<object>()),
  useTerminal: () => ({ open: vi.fn(), selectSecurity: vi.fn() }),
}));
vi.mock("../components/ui", async (original) => ({
  ...(await original<object>()),
  LineChart: () => <div role="img" aria-label="NAV chart" />,
}));

import { PortfolioHomePage } from "../components/operating-pages";

const portfolioPath = "/api/v1/terminal/portfolio";
const tradePath = "/api/v1/operations/trades";
const quantPath = "/api/v1/desks/quant";
const agentPath = "/api/v1/data-drop/agents";
const tradesTitle = "Trade monitor / recent ledger events";
const quantTitle = "Quant / jobs and strategy registry";
const operationsTitle = "Operations / freshness and exceptions";
const portfolioTitles = [
  "KnK Capital / NAV and benchmark",
  "Risk / limits",
  "Positions / ledger-derived",
  "P&L / inception attribution",
  operationsTitle,
];
const handlers = new Map<string, () => Promise<unknown>>();
const portfolio = {
  portfolio: { nav: "100000", opening_capital: "100000" },
  source: "Test ledger",
  quality: "DEMO DATA",
  as_of: "2026-09-04T20:00:00Z",
  calculated_at: "2026-09-04T20:01:00Z",
  positions: [],
  attribution: [],
  curve: [],
  performance: {},
  risk: {},
  breaches: [],
  reconciliation: { state: "RECONCILED" },
  freshness: { price_coverage_pct: 0, stale_nav_pct: 0 },
  broker_state: "NOT CONNECTED",
  warnings: [],
};

function panel(title: string) {
  return within(screen.getByRole("region", { name: title }));
}
function agentValue() {
  return panel(operationsTitle)
    .getByText("Agent", { exact: true })
    .querySelector("strong")?.textContent;
}

beforeEach(() => {
  handlers.clear();
  handlers.set(portfolioPath, async () => portfolio);
  handlers.set(tradePath, async () => ({ items: [] }));
  handlers.set(quantPath, async () => ({ strategies: [], runs: [] }));
  handlers.set(agentPath, async () => ({ items: [] }));
  vi.spyOn(knkApi, "get").mockImplementation(async <T,>(path: string) => {
    const handler = handlers.get(path);
    if (!handler) throw new Error(`Unexpected request: ${path}`);
    return (await handler()) as T;
  });
});
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

it.each([
  [tradePath, tradesTitle],
  [quantPath, quantTitle],
])(
  "keeps %s pending instead of displaying an empty registry",
  (path, title) => {
    handlers.set(path, () => new Promise(() => {}));
    renderLedger(<PortfolioHomePage />);
    expect(panel(title).getByText("Loading data")).toBeTruthy();
    expect(panel(title).queryByText("No matching records")).toBeNull();
  },
);

it.each([
  [tradePath, tradesTitle],
  [quantPath, quantTitle],
])("shows a failed %s request and supports retry", async (path, title) => {
  handlers.set(path, async () => {
    throw new Error("Registry unavailable");
  });
  const user = userEvent.setup();
  renderLedger(<PortfolioHomePage />);
  expect((await panel(title).findByRole("alert")).textContent).toContain(
    "Registry unavailable",
  );
  expect(panel(title).queryByText("No matching records")).toBeNull();
  handlers.set(path, async () => ({ items: [], strategies: [], runs: [] }));
  await user.click(panel(title).getByRole("button", { name: "Retry" }));
  await panel(title).findByText("No matching records");
  expect(panel(title).queryByRole("alert")).toBeNull();
});

it("keeps every portfolio panel pending without inventing a zero breach count", () => {
  handlers.set(portfolioPath, () => new Promise(() => {}));
  renderLedger(<PortfolioHomePage />);
  for (const title of portfolioTitles) {
    expect(panel(title).getByText("Loading data")).toBeTruthy();
    expect(panel(title).queryByText("No matching records")).toBeNull();
  }
  expect(panel("Risk / limits").queryByText("0")).toBeNull();
});

it("marks every portfolio panel unavailable after a failed request", async () => {
  handlers.set(portfolioPath, async () => {
    throw new Error("Ledger unavailable");
  });
  renderLedger(<PortfolioHomePage />);
  for (const title of portfolioTitles) {
    expect((await panel(title).findByRole("alert")).textContent).toContain(
      "Ledger unavailable",
    );
    expect(panel(title).queryByText("No matching records")).toBeNull();
  }
  expect(screen.queryByText("LOADING", { exact: true })).toBeNull();
  expect(screen.getByText("UNAVAILABLE", { exact: true })).toBeTruthy();
});

it("keeps agent state checking while the request is pending", async () => {
  handlers.set(agentPath, () => new Promise(() => {}));
  renderLedger(<PortfolioHomePage />);
  await waitFor(() => expect(agentValue()).toBe("CHECKING"));
  expect(panel(operationsTitle).queryByText("OFFLINE")).toBeNull();
  expect(panel(operationsTitle).getByText("Price coverage")).toBeTruthy();
});

it("reports an unavailable agent status and retries the status request", async () => {
  handlers.set(agentPath, async () => {
    throw new Error("Agent status unavailable");
  });
  const user = userEvent.setup();
  renderLedger(<PortfolioHomePage />);
  await waitFor(() => expect(agentValue()).toBe("UNAVAILABLE"));
  expect(panel(operationsTitle).getByRole("alert").textContent).toContain(
    "Agent status unavailable",
  );
  handlers.set(agentPath, async () => ({ items: [{ state: "ONLINE" }] }));
  await user.click(
    panel(operationsTitle).getByRole("button", {
      name: "Refresh agent status",
    }),
  );
  await waitFor(() => expect(agentValue()).toBe("ONLINE"));
  expect(panel(operationsTitle).queryByRole("alert")).toBeNull();
});

it.each(["ONLINE", "OFFLINE"])(
  "does not present cached %s as current after a status refresh fails",
  async (state) => {
    handlers.set(agentPath, async () => ({ items: [{ state }] }));
    const { client } = renderLedger(<PortfolioHomePage />);
    await waitFor(() => expect(agentValue()).toBe(state));
    handlers.set(agentPath, async () => {
      throw new Error("Status refresh failed");
    });
    await client.refetchQueries({ queryKey: ["operating-agents", agentPath] });
    await waitFor(() => expect(agentValue()).toBe("UNAVAILABLE"));
  },
);

it("preserves actual empty lists, no-agent offline state and genuine zero breaches", async () => {
  renderLedger(<PortfolioHomePage />);
  await waitFor(() => expect(agentValue()).toBe("OFFLINE"));
  for (const title of [tradesTitle, quantTitle])
    expect(panel(title).getByText("No matching records")).toBeTruthy();
  const breaches = panel("Risk / limits").getByText("Limit breaches");
  expect(breaches.nextElementSibling?.textContent).toBe("0");
  expect(screen.queryByRole("alert")).toBeNull();
});
