import { expect, test } from "@playwright/test";

test("risk limits, model settings and manual hedge reviews persist", async ({
  page,
  request,
}) => {
  test.setTimeout(180000);
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  const bootstrap = await (
    await request.get("/backend/api/v1/terminal/bootstrap")
  ).json();
  await page.goto("/overview");
  await expect(page.getByTestId("terminal-shell")).toBeVisible();
  await page.evaluate((workspaceId) => {
    localStorage.setItem(
      "knk-terminal-v2",
      JSON.stringify({
        workspaceId,
        configuration: {
          tabs: Array.from({ length: 20 }, (_, i) => ({
            id: `bookmark-${i}`,
            title: `Chart ${i}`,
            route: `/chart/test-${i}`,
          })),
          securities: ["AAPL"],
          rail: true,
          inspector: false,
        },
      }),
    );
  }, bootstrap.workspaces[0].id);
  await page.goto("/risk-trade-monitor");
  await page.getByRole("button", { name: "Add risk limit" }).click();
  const dialog = page.getByRole("dialog", { name: "Configure risk limit" });
  await dialog.getByLabel("Risk limit metric").selectOption("gross_exposure");
  await dialog.getByLabel("Risk limit threshold").fill("0.01");
  await dialog
    .getByLabel("Risk change reason")
    .fill("Browser verification of limit audit trail");
  await dialog.getByRole("button", { name: "Save configuration" }).click();
  await expect(dialog).toHaveCount(0);
  await expect(page.getByLabel("risk-limits table")).toContainText("BREACH");
  await page.getByRole("button", { name: "Risk model settings" }).click();
  const model = page.getByRole("dialog", { name: "Risk model settings" });
  await model.getByLabel("simulations").fill("2000");
  await model
    .getByLabel("Risk change reason")
    .fill("Reproducible Monte Carlo model verification");
  await model.getByRole("button", { name: "Save configuration" }).click();
  await expect(model).toHaveCount(0);
  const monitor = await request.get(
    "/backend/api/v1/risk/portfolios/KNK_MAIN/monitor",
  );
  expect(monitor.ok()).toBeTruthy();
  expect((await monitor.json()).model.settings.simulations).toBe(2000);
  for (const width of [1440, 390]) {
    await page.setViewportSize({ width, height: 1000 });
    const hide = page.getByRole("button", {
      name: "Hide inspector",
      exact: true,
    });
    if (await hide.isVisible()) await hide.click();
    expect(
      await page.evaluate(() => document.documentElement.scrollWidth),
    ).toBeLessThanOrEqual(width);
    await page.screenshot({
      path: `logs/portfolio-screenshots/risk-${width}.png`,
    });
  }
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto("/hedge");
  await page
    .getByLabel("Hedge valuation date", { exact: true })
    .fill("2026-09-03");
  await page.getByLabel("Hedge target", { exact: true }).fill("0.2");
  await page.getByLabel("Hedge fees").fill("2");
  await page
    .getByRole("button", { name: "Calculate Hedge", exact: true })
    .click();
  await expect(page.getByLabel("hedge-history table")).toContainText(
    "BETA / SPY",
  );
  await page
    .getByLabel("Hedge review reason")
    .fill("Reviewed sizing and recorded source timestamps");
  await page.getByRole("button", { name: "Save Review", exact: true }).click();
  await expect(page.getByLabel("hedge-history table")).toContainText(
    "REVIEWED",
  );
  const runs = await (
    await request.get("/backend/api/v1/terminal/runs?kind=hedge")
  ).json();
  expect(runs.items[0].result.valuation_run_id).toBeTruthy();
  expect(runs.items[0].result.valuation_date).toBe("2026-09-03");
  expect(runs.items[0].result.var_state).toBe("AVAILABLE");
  expect(runs.items[0].result.beta_after).not.toBeNull();
  await page.reload();
  await expect
    .poll(async () =>
      page.evaluate(() => {
        const saved = JSON.parse(localStorage.getItem("knk-terminal-v2")!);
        return saved.configuration.tabs.length;
      }),
    )
    .toBe(20);
  await expect(page.getByLabel("Hedge target", { exact: true })).toHaveValue(
    "0.2",
  );
  await expect(page.getByLabel("Hedge fees")).toHaveValue("2");
  await expect(page.getByLabel("Hedge valuation date")).toHaveValue(
    "2026-09-03",
  );
  await expect(page.getByLabel("hedge-history table")).toContainText(
    "REVIEWED",
  );
  for (const width of [1440, 390]) {
    await page.setViewportSize({ width, height: 1000 });
    const table = page.getByLabel("hedge-history table");
    const controls = page.getByLabel("Hedge review state");
    await controls.scrollIntoViewIfNeeded();
    const tableBox = await table.boundingBox();
    const controlsBox = await controls.boundingBox();
    expect(tableBox!.height).toBeGreaterThan(100);
    expect(tableBox!.y + tableBox!.height).toBeLessThanOrEqual(controlsBox!.y);
    expect(
      await page.evaluate(() => document.documentElement.scrollWidth),
    ).toBeLessThanOrEqual(width);
    await page.screenshot({
      path: `logs/portfolio-screenshots/hedge-${width}.png`,
    });
  }
  expect(errors).toEqual([]);
});
