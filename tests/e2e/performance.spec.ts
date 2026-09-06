import { expect, test } from "@playwright/test";

test("authenticated overview and saved performance use the 100K ledger", async ({
  page,
  request,
}) => {
  test.setTimeout(120000);
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/overview");
  await expect(
    page.getByRole("heading", { name: "Portfolio Command Centre" }),
  ).toBeVisible();
  await expect(
    page
      .locator(".operating-ribbon > div")
      .filter({ hasText: "Opening capital" }),
  ).toContainText("100,000");
  const response = await request.get(
    "/backend/api/v1/performance/portfolios/KNK_MAIN/report?end=2026-09-04",
  );
  expect(response.ok()).toBeTruthy();
  const report = await response.json();
  expect(report.source_precision).toBe("DECIMAL");
  expect(report.summary.ytd.state).toBe("PARTIAL_PERIOD");
  await page.goto("/performance");
  await expect(
    page.getByRole("heading", { name: "Performance / Internal Ledger" }),
  ).toBeVisible();
  await expect(page.getByLabel("performance-metrics table")).toContainText(
    "PARTIAL_PERIOD",
  );
  await expect(
    page
      .getByLabel("performance-metrics table")
      .getByRole("row")
      .filter({ has: page.getByText("twr", { exact: true }) }),
  ).toContainText("%");
  await page.getByLabel("Fees", { exact: true }).selectOption("GROSS");
  await page
    .getByRole("button", { name: "Save performance calculation" })
    .click();
  await expect(
    page.getByRole("status").filter({ hasText: "Saved calculation" }),
  ).toBeVisible();
  await page.getByLabel("Frequency", { exact: true }).selectOption("MONTHLY");
  await expect(page.getByLabel("performance-metrics table")).toContainText(
    "INSUFFICIENT_DATA",
  );
  for (const width of [1440, 390]) {
    await page.setViewportSize({ width, height: 900 });
    await expect(page.locator(".loading-state")).toHaveCount(0);
    expect(
      await page.evaluate(() => document.documentElement.scrollWidth),
    ).toBeLessThanOrEqual(width);
    const toolbar = await page.locator(".page-toolbar").boundingBox();
    const controls = await page.locator(".performance-controls").boundingBox();
    expect(toolbar!.y + toolbar!.height).toBeLessThanOrEqual(controls!.y + 1);
    await page.screenshot({
      path: `logs/portfolio-screenshots/performance-${width}.png`,
    });
  }
  expect(errors).toEqual([]);
});
