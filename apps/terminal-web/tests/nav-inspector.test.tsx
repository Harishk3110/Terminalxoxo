// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, screen, within } from "@testing-library/react";
import { knkApi } from "@knk/api-client";
import { NavInspector } from "../components/ledger/nav-inspector";
import { navSnapshot } from "./fixtures/nav";
import { renderLedger } from "./ledger-render";

beforeEach(() => {
  vi.spyOn(knkApi, "get").mockResolvedValue(navSnapshot);
});
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

function renderNav() {
  return renderLedger(<NavInspector portfolioKey="desk/book" runId="run+1" />);
}

describe("saved NAV statement", () => {
  it("pins its read to an encoded portfolio and run and preserves the unrounded NAV", async () => {
    renderNav();
    await screen.findByRole("table", { name: "Assets statement" });
    expect(knkApi.get).toHaveBeenCalledWith(
      "/api/v1/portfolios/desk%2Fbook/nav?run_id=run%2B1",
      expect.any(AbortSignal),
    );
    expect(
      screen.getByText("Closing NAV / SGD").nextElementSibling?.textContent,
    ).toBe("9,947.65432109");
    expect(
      screen.getByText("Assets less liabilities less NAV").nextElementSibling
        ?.textContent,
    ).toBe("0.00000000");
    expect(
      screen.getByText("Net position value").nextElementSibling?.textContent,
    ).toBe("-240.00000000");
  });

  it("presents short liabilities separately from cash, fees and payables", async () => {
    renderNav();
    const table = await screen.findByRole("table", {
      name: "Liabilities statement",
    });
    const short = within(table).getByRole("rowheader", {
      name: "Short position liabilities",
    });
    expect(short.nextElementSibling?.textContent).toBe("240.00000000");
    expect(
      within(table).getByRole("rowheader", { name: "Accrued fees" })
        .nextElementSibling?.textContent,
    ).toBe("12.34567891");
    expect(
      within(table).getByRole("rowheader", { name: "Total liabilities" })
        .nextElementSibling?.textContent,
    ).toBe("252.34567891");
    const assets = screen.getByRole("table", { name: "Assets statement" });
    expect(
      within(assets).getByRole("rowheader", { name: "Positive settled cash" })
        .nextElementSibling?.textContent,
    ).toBe("10,200.00000000");
    expect(
      within(assets).queryByRole("rowheader", {
        name: "Short position liabilities",
      }),
    ).toBeNull();
  });

  it("does not round high-precision API strings through JavaScript numbers before rendering", async () => {
    vi.mocked(knkApi.get).mockResolvedValue({
      ...navSnapshot,
      portfolio: { ...navSnapshot.portfolio, base_currency: "USD" },
      balance_sheet: {
        ...navSnapshot.balance_sheet,
        items: {
          ...navSnapshot.balance_sheet!.items,
          nav: "9007199254740993.12345678",
        },
      },
    });
    renderNav();
    expect(
      (await screen.findByText("Closing NAV / USD")).nextElementSibling
        ?.textContent,
    ).toBe("9,007,199,254,740,993.12345678");
    expect(screen.queryByText("Closing NAV / SGD")).toBeNull();
  });

  it("shows unknown amounts and the selected missing-mark reason instead of a zero liability", async () => {
    vi.mocked(knkApi.get).mockResolvedValue({
      ...navSnapshot,
      state: "INCOMPLETE",
      portfolio: { ...navSnapshot.portfolio, nav: null },
      balance_sheet: {
        ...navSnapshot.balance_sheet,
        state: "INCOMPLETE",
        reconciliation_state: "INCOMPLETE",
        difference: null,
        warnings: ["AAA: missing price"],
        items: Object.fromEntries(
          Object.keys(navSnapshot.balance_sheet!.items).map((key) => [
            key,
            null,
          ]),
        ),
      },
    });
    renderNav();
    expect(
      (await screen.findByText("AAA: missing price")).getAttribute("role"),
    ).toBe("status");
    expect(
      screen.getByText("Closing NAV / SGD").nextElementSibling?.textContent,
    ).toBe("--");
    const table = screen.getByRole("table", { name: "Liabilities statement" });
    expect(
      within(table).getByRole("rowheader", {
        name: "Short position liabilities",
      }).nextElementSibling?.textContent,
    ).toBe("--");
    expect(within(table).queryByText("0.00000000")).toBeNull();
  });

  it("retains a legacy saved NAV without reconstructing missing statement components", async () => {
    vi.mocked(knkApi.get).mockResolvedValue({
      ...navSnapshot,
      state: "LEGACY_SNAPSHOT",
      balance_sheet: null,
    });
    renderNav();
    await screen.findByText(
      "This saved run predates the complete NAV balance sheet",
    );
    expect(
      screen.getByText("Closing NAV / SGD").nextElementSibling?.textContent,
    ).toBe("9,947.65000000");
    expect(
      screen.getByText("Gross assets").nextElementSibling?.textContent,
    ).toBe("--");
    expect(
      screen.getByText("Total liabilities").nextElementSibling?.textContent,
    ).toBe("--");
    expect(screen.queryByRole("table")).toBeNull();
  });

  it("preserves a supplied reconciliation break rather than forcing a balanced label", async () => {
    vi.mocked(knkApi.get).mockResolvedValue({
      ...navSnapshot,
      balance_sheet: {
        ...navSnapshot.balance_sheet,
        difference: "-0.00000002",
        reconciliation_state: "BREAK",
      },
    });
    renderNav();
    expect(
      (await screen.findByText("Assets less liabilities less NAV"))
        .nextElementSibling?.textContent,
    ).toBe("-0.00000002");
    expect(screen.getByText("BREAK")).toBeTruthy();
  });

  it("shows read failure without a fabricated statement", async () => {
    vi.mocked(knkApi.get).mockRejectedValue(
      new Error("Valuation run not found in portfolio"),
    );
    renderNav();
    expect(screen.getByText("Loading ledger...")).toBeTruthy();
    expect((await screen.findByRole("alert")).textContent).toContain(
      "Valuation run not found in portfolio",
    );
    expect(screen.queryByRole("table")).toBeNull();
  });
});
