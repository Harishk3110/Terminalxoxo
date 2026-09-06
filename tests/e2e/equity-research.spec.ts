import { expect, test } from "@playwright/test";

test("financials, source-pinned DCF, peers and versioned thesis", async ({
  page,
  request,
}) => {
  test.setTimeout(240000);
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/financials/AAPL");
  await expect(page.getByLabel("financial-Income table")).toContainText(
    "revenue",
  );
  await page.getByLabel("Financial frequency").selectOption("TTM");
  await expect(
    page.getByText("No matching statements", { exact: true }),
  ).toBeVisible();
  await page.goto("/dcf/AAPL");
  await page
    .getByRole("button", { name: "Calculate & Save", exact: true })
    .click();
  await expect(page.getByLabel("fcff-forecast table")).toContainText("1", {
    timeout: 30000,
  });
  const runs = await (
    await request.get("/backend/api/v1/terminal/runs?kind=dcf")
  ).json();
  const run = runs.items.find(
    (r: { result: { symbol: string } }) => r.result.symbol === "AAPL",
  );
  expect(run.result.scenarios).toHaveLength(3);
  expect(run.result.input_hash).toHaveLength(64);
  expect(Number(run.result.scenarios[0].fair_value)).toBeGreaterThan(
    Number(run.result.scenarios[2].fair_value),
  );
  for (const width of [1440, 390]) {
    await page.setViewportSize({ width, height: 1000 });
    const hide = page.getByRole("button", {
      name: "Hide inspector",
      exact: true,
    });
    if (await hide.isVisible()) await hide.click();
    await page.getByLabel("FCFF forecast chart").scrollIntoViewIfNeeded();
    await expect(
      page.getByLabel("FCFF forecast chart").locator("canvas"),
    ).toBeVisible();
    const grid = await page
      .locator(".equity-workspace > .page-grid")
      .boundingBox();
    const table = await page
      .getByRole("region", {
        name: "Annual operating forecast / millions",
        exact: true,
      })
      .boundingBox();
    expect(grid!.y + grid!.height).toBeLessThanOrEqual(table!.y);
    expect(
      await page.evaluate(() => document.documentElement.scrollWidth),
    ).toBeLessThanOrEqual(width);
    await page.screenshot({
      path: `logs/portfolio-screenshots/dcf-${width}.png`,
    });
  }
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto("/comparables/AAPL");
  await page.getByLabel("Comparable peers").fill("MSFT,NVDA");
  await page
    .getByRole("button", { name: "Calculate & Save", exact: true })
    .click();
  await expect(page.getByLabel("equity-peer-statistics table")).toContainText(
    "pe",
  );
  await page.goto("/thesis");
  await page.getByLabel("Thesis security").selectOption("AAPL");
  await page
    .getByLabel("Thesis title", { exact: true })
    .fill("AAPL test research");
  await page
    .getByLabel("Thesis one_sentence")
    .fill("Testable margin thesis from pinned statement inputs");
  await page.getByLabel("Thesis linked DCF").selectOption(run.id);
  await page.getByRole("button", { name: "Save version", exact: true }).click();
  await expect(page.locator(".page-toolbar")).toContainText("SAVED v1");
  await page
    .getByLabel("Thesis risks", { exact: true })
    .fill("Margin compression");
  await page.getByRole("button", { name: "Save version", exact: true }).click();
  await expect(page.locator(".page-toolbar")).toContainText("SAVED v2");
  await page.reload();
  await expect(page.locator(".thesis-sidebar").first()).toContainText(
    "AAPL test research",
  );
  await page.setViewportSize({ width: 390, height: 1000 });
  await page.getByLabel("Thesis full_thesis").scrollIntoViewIfNeeded();
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth),
  ).toBeLessThanOrEqual(390);
  await page.screenshot({ path: "logs/portfolio-screenshots/thesis-390.png" });
  expect(errors).toEqual([]);
});

test("security OHLC chart, comparison, aggregates and desk", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/chart/AAPL");
  await expect(
    page.getByLabel("Security price chart").locator("canvas"),
  ).toBeVisible();
  await page.getByLabel("Security chart type").selectOption("AREA");
  await page.getByLabel("Security comparison").selectOption("SPY");
  await page.getByLabel("Security chart interval").selectOption("WEEKLY");
  await expect(page.getByLabel("Security comparison")).toBeDisabled();
  await page.screenshot({ path: "logs/portfolio-screenshots/security-m5.png" });
  await page.goto("/equity");
  await expect(page.getByLabel("equity-universe table")).toContainText("AAPL");
  expect(errors).toEqual([]);
});
