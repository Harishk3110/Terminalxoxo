// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { knkApi } from "@knk/api-client";
import { PositionInspector } from "../components/ledger/position-inspector";
import { positionSnapshot } from "./fixtures/position";
import { renderLedger } from "./ledger-render";

const positions = [
  { instrument_id: "AAA", symbol: "AAA" },
  { instrument_id: "BBB", symbol: "BBB" },
];

beforeEach(() => {
  vi.spyOn(knkApi, "get").mockResolvedValue(positionSnapshot);
});
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

function renderPosition() {
  return renderLedger(
    <PositionInspector
      portfolioKey="book"
      runId="run-1"
      positions={positions}
    />,
  );
}

describe("position accounting inspector", () => {
  it("pins its read to the accounting dialog's saved valuation instead of silently repricing", async () => {
    renderPosition();
    await screen.findByText("AAA / Test security");
    expect(knkApi.get).toHaveBeenCalledWith(
      "/api/v1/portfolios/book/positions/AAA?run_id=run-1",
      expect.any(AbortSignal),
    );
    expect(
      screen.getByText("Native market value / USD").nextElementSibling
        ?.textContent,
    ).toBe("1,200.00000000");
    expect(
      screen.getByText("Base market value / SGD").nextElementSibling
        ?.textContent,
    ).toBe("1,680.00000000");
    expect(
      screen.getByText("Price component / SGD").nextElementSibling?.textContent,
    ).toBe("280.00000000");
    expect(
      screen.getByText("FX component / SGD").nextElementSibling?.textContent,
    ).toBe("100.00000000");
    expect(
      screen.getByText("Beta contribution").nextElementSibling?.textContent,
    ).toBe("0.184800");
    expect(
      screen.getByText("Sector NAV weight").nextElementSibling?.textContent,
    ).toBe("+30.00%");
  });

  it("changes security while preserving the selected immutable run", async () => {
    vi.mocked(knkApi.get).mockImplementation(
      async <T,>(path: string) =>
        ({
          ...positionSnapshot,
          instrument_id: path.includes("/BBB?") ? "BBB" : "AAA",
          symbol: path.includes("/BBB?") ? "BBB" : "AAA",
        }) as T,
    );
    renderPosition();
    await screen.findByText("AAA / Test security");
    await userEvent.selectOptions(screen.getByLabelText("Position"), "BBB");
    await screen.findByText("BBB / Test security");
    expect(knkApi.get).toHaveBeenLastCalledWith(
      "/api/v1/portfolios/book/positions/BBB?run_id=run-1",
      expect.any(AbortSignal),
    );
    expect(screen.queryByText("AAA / Test security")).toBeNull();
  });

  it("shows server-calculated daily cash, transfers and P&L without recalculating them", async () => {
    renderPosition();
    await screen.findByText("AAA / Test security");
    await userEvent.click(screen.getByRole("button", { name: "Day P&L" }));
    expect(
      screen.getByText("Opening marked value").nextElementSibling?.textContent,
    ).toBe("1,600.00000000");
    expect(
      screen.getByText("Recorded economic cash").nextElementSibling
        ?.textContent,
    ).toBe("-5.00000000");
    expect(
      screen.getByText("Internal corporate transfer").nextElementSibling
        ?.textContent,
    ).toBe("0.00000000");
    expect(
      screen.getByText("Position P&L").nextElementSibling?.textContent,
    ).toBe("75.00000000");
    expect(
      screen.getByText("Closing less opening plus cash less capital transfers"),
    ).toBeTruthy();
  });

  it("keeps unavailable values unknown even when a legacy fallback field contains zero", async () => {
    vi.mocked(knkApi.get).mockResolvedValue({
      ...positionSnapshot,
      nav_weight: null,
      weight: 0,
      market_value_base_exact: null,
      market_value: "0",
      valuation_state: "UNAVAILABLE",
      valuation_warnings: ["Position FX is unavailable"],
    });
    renderPosition();
    await screen.findByText("AAA / Test security");
    expect(screen.getByText("NAV weight").nextElementSibling?.textContent).toBe(
      "--",
    );
    expect(
      screen.getByText("Base market value / SGD").nextElementSibling
        ?.textContent,
    ).toBe("--");
    expect(
      screen.getByText("Native market value / USD").nextElementSibling
        ?.textContent,
    ).toBe("1,200.00000000");
    expect(screen.getByRole("status").textContent).toBe(
      "Position FX is unavailable",
    );
  });

  it("separates price and FX provenance, inverse rates and stale/conflict flags", async () => {
    vi.mocked(knkApi.get).mockResolvedValue({
      ...positionSnapshot,
      price_provenance: {
        ...positionSnapshot.price_provenance,
        stale: true,
        conflict: true,
      },
    });
    renderPosition();
    await screen.findByText("AAA / Test security");
    await userEvent.click(screen.getByRole("button", { name: "Sources" }));
    const price = screen.getByRole("region", { name: "Price provenance" });
    expect(within(price).getByText("source-file-1")).toBeTruthy();
    expect(within(price).getByText("version-1")).toBeTruthy();
    expect(within(price).getByText("price-1")).toBeTruthy();
    expect(
      within(price).getByText("Material same-date source conflict"),
    ).toBeTruthy();
    expect(within(price).getByText("Selected mark is stale")).toBeTruthy();
    const fx = screen.getByRole("region", { name: "FX provenance" });
    expect(within(fx).getByText("TEST FX")).toBeTruthy();
    expect(within(fx).getByText("INVERSE FX")).toBeTruthy();
    expect(within(fx).queryByText("source-file-1")).toBeNull();
  });

  it("shows only open lots with their recorded opening transaction", async () => {
    vi.mocked(knkApi.get).mockResolvedValue({
      ...positionSnapshot,
      lots: [
        ...positionSnapshot.lots,
        {
          ...positionSnapshot.lots[0],
          id: "closed",
          quantity: "0",
          entry_id: "closed-buy",
        },
      ],
    });
    renderPosition();
    await screen.findByText("AAA / Test security");
    await userEvent.click(screen.getByRole("button", { name: "Open lots" }));
    const table = screen.getByRole("table", { name: "Selected position lots" });
    expect(within(table).getAllByRole("row")).toHaveLength(2);
    expect(within(table).getByText("buy-1")).toBeTruthy();
    expect(within(table).queryByText("closed-buy")).toBeNull();
  });

  it("does not invent a daily breakdown for a legacy valuation", async () => {
    vi.mocked(knkApi.get).mockResolvedValue({
      ...positionSnapshot,
      measurement_state: "LEGACY_SNAPSHOT",
      daily_pnl_details: undefined,
      market_value_native: undefined,
      unrealised_decomposition_method: undefined,
    });
    renderPosition();
    await screen.findByText("AAA / Test security");
    expect(screen.getByRole("status").textContent).toContain(
      "were not recorded",
    );
    expect(
      screen.getByText("Native market value / USD").nextElementSibling
        ?.textContent,
    ).toBe("--");
    await userEvent.click(screen.getByRole("button", { name: "Day P&L" }));
    expect(
      screen.getByText(
        "Daily component breakdown not recorded in this valuation",
      ),
    ).toBeTruthy();
    expect(screen.queryByText("Position P&L")).toBeNull();
  });

  it("reports an unavailable saved run without retaining the previous position's values", async () => {
    vi.mocked(knkApi.get).mockRejectedValue(
      new Error("Valuation run not found in portfolio"),
    );
    renderPosition();
    expect((await screen.findByRole("alert")).textContent).toBe(
      "Valuation run not found in portfolio",
    );
    expect(screen.queryByText("AAA / Test security")).toBeNull();
    expect(screen.queryByText("Native market value / USD")).toBeNull();
  });

  it("does not fetch an arbitrary security when the saved portfolio has no open positions", async () => {
    renderLedger(
      <PositionInspector
        portfolioKey="book"
        runId="empty-run"
        positions={[]}
      />,
    );
    expect(
      screen.getByText("No open positions in this valuation"),
    ).toBeTruthy();
    await waitFor(() => expect(knkApi.get).not.toHaveBeenCalled());
  });
});
