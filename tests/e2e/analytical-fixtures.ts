import { expect, type APIRequestContext, type Page } from "@playwright/test";

export const DEMO_VALUATION_DATE = "2026-09-03";

export async function populateVisualAnalysis(
  page: Page,
  route: string,
  backtestId: string,
  datasetId: string,
) {
  if (route === "data-drop") {
    const width = page.viewportSize()!.width;
    await page.getByLabel("Upload data files").setInputFiles({
      name: `QQQ_2026-01-06_visual-draft-${width}.csv`,
      mimeType: "text/csv",
      buffer: Buffer.from(
        `Date,Open,High,Low,Close,Volume\n2026-01-05,100,102,99,101,${width}\n2026-01-06,101,103,100,102,${width + 1}\n`,
      ),
    });
    await expect(
      page.getByRole("tab", { name: "Preview", exact: true }),
    ).toBeVisible();
    await expect(page.getByLabel(/^file-preview-.* table$/)).toContainText(
      "2026-01-06",
    );
    await expect(
      page.getByLabel("Approve this validated version"),
    ).not.toBeChecked();
  }
  if (route === "data-catalogue") {
    expect(datasetId).toBeTruthy();
    await page.goto(`/data-catalogue/${datasetId}`);
    await expect(page.getByLabel("dataset-version table")).toContainText("SPY");
    await expect(page.getByLabel("Dataset version")).not.toHaveValue("");
  }
  if (route === "backtests") {
    await expect(
      page.getByLabel("Backtest currency", { exact: true }),
    ).toHaveValue("SGD");
    await expect(
      page.getByLabel("Backtest security", { exact: true }),
    ).toHaveValue("SPY");
    const numbers = page.getByRole("spinbutton", { name: /^Backtest / });
    await expect(numbers).toHaveCount(12);
    for (const input of await numbers.all()) {
      await expect(input).not.toHaveValue("");
    }
  }
  if (route === "alpha") {
    await page.getByLabel("Alpha return source").selectOption(backtestId);
    await page
      .getByRole("button", { name: "Calculate Alpha", exact: true })
      .click();
    await expect(page.getByLabel("alpha-coefficients table")).toContainText(
      "market_excess",
    );
  }
  if (route === "hedge") {
    await page
      .getByLabel("Hedge valuation date", { exact: true })
      .fill(DEMO_VALUATION_DATE);
    await page.getByLabel("Hedge target", { exact: true }).fill("0.2");
    const completed = page.waitForResponse(
      (response) =>
        response.url().endsWith("/hedges") &&
        response.request().method() === "POST",
    );
    await page
      .getByRole("button", { name: "Calculate Hedge", exact: true })
      .click();
    const response = await completed;
    expect(response.ok(), await response.text()).toBeTruthy();
    expect((await response.json()).valuation_date).toBe(DEMO_VALUATION_DATE);
    await expect(page.getByLabel("hedge-history table")).toContainText(
      "BETA / SPY",
    );
  }
  if (route === "options/AAPL" || route === "functions/gex") {
    await page
      .getByRole("button", {
        name: "Create synthetic European demo chain",
        exact: true,
      })
      .click();
    await expect(page.getByLabel("Options dataset")).not.toHaveValue("");
    const completed = page.waitForResponse(
      (response) =>
        response.url().endsWith("/options/calculate") &&
        response.request().method() === "POST",
    );
    await page
      .getByRole("button", { name: "Calculate & Save", exact: true })
      .click();
    const response = await completed;
    expect(response.ok(), await response.text()).toBeTruthy();
    const report = await response.json();
    expect(report.quality).toBe("DEMO DATA");
    expect(report.coverage.gex_included).toBe(30);
    await expect(
      page.getByText("No saved analysis selected", { exact: true }),
    ).toHaveCount(0);
    if (route === "functions/gex") {
      await page.getByRole("tab", { name: "GEX", exact: true }).click();
      await expect(
        page.getByLabel("GEX by strike").locator("canvas"),
      ).toBeVisible();
    }
  }
}

export async function completedRun(
  request: APIRequestContext,
  kind: "stress" | "backtest",
) {
  const response = await request.post("/backend/api/v1/terminal/runs", {
    data: {
      kind,
      name: `Independent visual ${kind}`,
      parameters:
        kind === "stress"
          ? {
              portfolio: "KNK_MAIN",
              valuation_date: DEMO_VALUATION_DATE,
              equity_shock: -10,
              fx_shock: 0,
              rates_bp: 0,
              scope: "All",
            }
          : {
              symbol: "SPY",
              source_mode: "DEMO_RESEARCH",
              start: "2025-01-01",
              end: DEMO_VALUATION_DATE,
              base_currency: "SGD",
              strategy: "SMA",
              fast: 20,
              slow: 50,
            },
    },
  });
  expect(response.ok(), await response.text()).toBeTruthy();
  const queued = await response.json();
  await expect
    .poll(
      async () => {
        const result = await request.get(
          `/backend/api/v1/terminal/runs/${queued.id}`,
        );
        expect(result.ok()).toBeTruthy();
        return (await result.json()).status;
      },
      { timeout: 60000 },
    )
    .toBe("SUCCEEDED");
  const final = await request.get(`/backend/api/v1/terminal/runs/${queued.id}`);
  return final.json();
}
