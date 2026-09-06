import { expect, test } from "@playwright/test";

test("private Pine templates persist and compare actual uploaded signal columns", async ({
  page,
  request,
}) => {
  test.setTimeout(120000);
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/tradingview");
  await page.getByRole("button", { name: "Generate", exact: true }).click();
  await expect(page.locator(".pine-source")).toContainText("//@version=6");
  await expect(
    page.getByRole("button", { name: "Download Pine source" }),
  ).toBeEnabled();
  const rows = ["time,close,KNK_SIGNAL"];
  for (let i = 0; i < 80; i++)
    rows.push(
      `${new Date(Date.UTC(2025, 0, 1 + i)).toISOString()},${100 + i},1`,
    );
  await page
    .getByLabel("TradingView chart export", { exact: true })
    .setInputFiles({
      name: "tradingview.csv",
      mimeType: "text/csv",
      buffer: Buffer.from(rows.join("\n")),
    });
  await expect(
    page.getByLabel("Observed signal comparison", { exact: true }),
  ).toContainText("MATCHED_OBSERVED_BARS");
  const history = await (
    await request.get("/backend/api/v1/terminal/runs?kind=pine_compare")
  ).json();
  expect(history.items[0].result.compared).toBe(31);
  expect(history.items[0].parameters.template_hash).toHaveLength(64);
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
      path: `logs/portfolio-screenshots/pine-${width}.png`,
    });
  }
  expect(errors).toEqual([]);
});
