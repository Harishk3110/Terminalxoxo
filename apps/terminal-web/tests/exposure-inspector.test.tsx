// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { knkApi } from "@knk/api-client";
import { QueryClientProvider } from "@tanstack/react-query";
import { ExposureInspector } from "../components/ledger/exposure-inspector";
import { exposureSnapshot } from "./fixtures/exposures";
import { renderLedger } from "./ledger-render";

beforeEach(() => {
  vi.spyOn(knkApi, "get").mockResolvedValue(exposureSnapshot);
});
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

function renderExposure(portfolioKey = "book", runId = "run-1") {
  return renderLedger(
    <ExposureInspector portfolioKey={portfolioKey} runId={runId} />,
  );
}

describe("saved exposure inspector", () => {
  it("pins an encoded portfolio and run and displays exact signed server values", async () => {
    renderExposure("desk/a", "run+1");
    const table = await screen.findByRole("table", {
      name: "Grouped portfolio exposures",
    });
    expect(knkApi.get).toHaveBeenCalledWith(
      "/api/v1/portfolios/desk%2Fa/exposures?run_id=run%2B1",
      expect.any(AbortSignal),
    );
    const row = within(table).getByRole("rowheader", {
      name: "USD",
    }).parentElement!;
    expect(
      within(row)
        .getAllByRole("cell")
        .map((cell) => cell.textContent),
    ).toEqual([
      "675.23456789",
      "+67.52%",
      "1,000.23456789",
      "-200.00000000",
      "-100.00000000",
      "-25.00000000",
      "1,425.23456789",
      "+142.52%",
      "675.23456789",
      "0",
      "3",
      "AVAILABLE",
    ]);
    expect(screen.getByText("NAV / SGD").nextElementSibling?.textContent).toBe(
      "1,000.00000000",
    );
  });

  it("changes all classification dimensions without repricing or fetching a different run", async () => {
    renderExposure();
    await screen.findByRole("rowheader", { name: "USD" });
    for (const [dimension, label] of [
      ["sector", "Technology"],
      ["country", "United States"],
      ["asset_class", "Equity"],
    ]) {
      await userEvent.selectOptions(
        screen.getByLabelText("Exposure dimension"),
        dimension,
      );
      expect(screen.getByRole("rowheader", { name: label })).toBeTruthy();
      expect(screen.queryByRole("rowheader", { name: "USD" })).toBeNull();
    }
    expect(knkApi.get).toHaveBeenCalledTimes(1);
  });

  it("shows absolute stale cash and liabilities and does not cap the NAV ratio at 100 percent", async () => {
    renderExposure();
    await userEvent.click(
      await screen.findByRole("button", { name: "Freshness" }),
    );
    expect(
      screen.getByText("Stale cash / SGD").nextElementSibling?.textContent,
    ).toBe("100.00000000");
    expect(
      screen.getByText("Stale balances / SGD").nextElementSibling?.textContent,
    ).toBe("25.00000000");
    expect(
      screen.getByText("Stale value / absolute NAV").nextElementSibling
        ?.textContent,
    ).toBe("+132.52%");
    expect(
      screen.getByText("Cash FX coverage").nextElementSibling?.textContent,
    ).toBe("50.00%");
    expect(
      screen.getByText("Position mark coverage").nextElementSibling
        ?.textContent,
    ).toBe("100.00%");
    expect(
      screen.getByText("Stale components").nextElementSibling?.textContent,
    ).toBe("3");
    expect(
      screen.getByText("Absolute stale components divided by absolute NAV"),
    ).toBeTruthy();
  });

  it("retains unknown totals, counts and weights instead of using legacy rounded zeros", async () => {
    vi.mocked(knkApi.get).mockResolvedValue({
      ...exposureSnapshot,
      state: "INCOMPLETE",
      nav: null,
      groups: {
        currency: [
          {
            ...exposureSnapshot.groups.currency![0],
            state: "INCOMPLETE",
            value: "0",
            net_value: null,
            gross_value: null,
            weight: null,
            gross_weight: null,
            long_value: null,
            short_value: null,
            known_value: "-125",
            missing_count: 1,
          },
        ],
      },
    });
    renderExposure();
    const table = await screen.findByRole("table", {
      name: "Grouped portfolio exposures",
    });
    const cells = within(table).getAllByRole("row")[1].querySelectorAll("td");
    expect(cells[0].textContent).toBe("--");
    expect(cells[1].textContent).toBe("--");
    expect(cells[6].textContent).toBe("--");
    expect(cells[8].textContent).toBe("-125.00000000");
    expect(cells[9].textContent).toBe("1");
    expect(screen.getByText("NAV / SGD").nextElementSibling?.textContent).toBe(
      "--",
    );
    expect(screen.getByRole("status").textContent).toContain(
      "Incomplete marks",
    );
  });

  it("keeps legacy components unrecorded while displaying the saved aggregate", async () => {
    vi.mocked(knkApi.get).mockResolvedValue({
      ...exposureSnapshot,
      state: "LEGACY_SNAPSHOT",
      methodology: null,
      warnings: ["This historical run predates complete exposure components"],
      balances: [],
      groups: { currency: [{ name: "USD", value: "52", weight: "0.05" }] },
      freshness: {
        stale_market_value: "0",
        stale_nav_pct: 0,
        price_coverage_pct: 100,
      },
    });
    renderExposure();
    const table = await screen.findByRole("table", {
      name: "Grouped portfolio exposures",
    });
    expect(within(table).getByText("52.00000000")).toBeTruthy();
    expect(within(table).getAllByText("--").length).toBeGreaterThanOrEqual(8);
    expect(within(table).getByText("NOT RECORDED")).toBeTruthy();
    await userEvent.click(
      screen.getByRole("button", { name: "Balance marks" }),
    );
    expect(
      screen.getByText("Balance exposure components not recorded"),
    ).toBeTruthy();
    await userEvent.click(screen.getByRole("button", { name: "Freshness" }));
    expect(
      screen.getByText("Stale cash / SGD").nextElementSibling?.textContent,
    ).toBe("--");
    expect(
      screen.getByText("Cash FX coverage").nextElementSibling?.textContent,
    ).toBe("--");
  });

  it("shows net outstanding native balance and signed base liability with stale FX provenance", async () => {
    renderExposure();
    await userEvent.click(
      await screen.findByRole("button", { name: "Balance marks" }),
    );
    const table = screen.getByRole("table", {
      name: "Outstanding balance marks",
    });
    expect(
      within(table).getByRole("rowheader", { name: "accrued fees" }),
    ).toBeTruthy();
    expect(within(table).getByText("20.00000000")).toBeTruthy();
    expect(within(table).getByText("-25.00000000")).toBeTruthy();
    expect(within(table).getByText("1.25000000")).toBeTruthy();
    expect(within(table).getByText("FX_FILE")).toBeTruthy();
    expect(within(table).getByText("STALE")).toBeTruthy();
  });

  it("marks an unconverted balance unavailable without replacing it with zero", async () => {
    vi.mocked(knkApi.get).mockResolvedValue({
      ...exposureSnapshot,
      balances: [
        {
          ...exposureSnapshot.balances[0],
          base_value: null,
          fx_rate: null,
          fx_provenance: {
            source: "UNAVAILABLE",
            data_state: "UNAVAILABLE",
            stale: false,
            as_of: null,
          },
        },
      ],
    });
    renderExposure();
    await userEvent.click(
      await screen.findByRole("button", { name: "Balance marks" }),
    );
    const table = screen.getByRole("table", {
      name: "Outstanding balance marks",
    });
    expect(within(table).getAllByText("--").length).toBe(2);
    expect(within(table).getAllByText("UNAVAILABLE").length).toBe(2);
  });

  it("uses honest empty states for absent groups, balances and freshness", async () => {
    vi.mocked(knkApi.get).mockResolvedValue({
      ...exposureSnapshot,
      groups: {},
      balances: [],
      freshness: null,
    });
    renderExposure();
    await screen.findByText("No currency groups in this valuation");
    await userEvent.selectOptions(
      screen.getByLabelText("Exposure dimension"),
      "sector",
    );
    expect(screen.getByText("No sector groups in this valuation")).toBeTruthy();
    await userEvent.click(
      screen.getByRole("button", { name: "Balance marks" }),
    );
    expect(
      screen.getByText("No outstanding manual balance adjustments"),
    ).toBeTruthy();
    await userEvent.click(screen.getByRole("button", { name: "Freshness" }));
    expect(
      screen.getByText("Freshness measurements not recorded"),
    ).toBeTruthy();
    expect(screen.queryByRole("table")).toBeNull();
  });

  it("does not retain exposure from another book when the scope changes", async () => {
    const rendered = renderExposure();
    await screen.findByRole("rowheader", { name: "USD" });
    vi.mocked(knkApi.get).mockResolvedValue({
      ...exposureSnapshot,
      portfolio_id: "second",
      groups: {},
    });
    rendered.rerender(
      <QueryClientProvider client={rendered.client}>
        <ExposureInspector portfolioKey="second" runId="run-2" />
      </QueryClientProvider>,
    );
    await screen.findByText("No currency groups in this valuation");
    expect(screen.queryByRole("rowheader", { name: "USD" })).toBeNull();
    expect(knkApi.get).toHaveBeenLastCalledWith(
      "/api/v1/portfolios/second/exposures?run_id=run-2",
      expect.any(AbortSignal),
    );
  });

  it("shows loading then the server failure without a fabricated table", async () => {
    let fail!: (reason: Error) => void;
    vi.mocked(knkApi.get).mockReturnValue(
      new Promise((_resolve, reject) => {
        fail = reject;
      }),
    );
    renderExposure();
    expect(screen.getByText("Loading ledger...")).toBeTruthy();
    fail(new Error("Valuation run not found in portfolio"));
    expect((await screen.findByRole("alert")).textContent).toContain(
      "Valuation run not found in portfolio",
    );
    expect(screen.queryByRole("table")).toBeNull();
  });
});
