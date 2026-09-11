import { expect, test } from "@playwright/test";
import { mkdirSync } from "node:fs";

test("missing observed service times remain explicit on desktop and mobile", async ({
  page,
}) => {
  await page.goto("/system-health");
  const table = page.getByLabel("service-health table", { exact: true });
  const worker = table.getByRole("row").filter({
    has: page.getByRole("cell", { name: "Data worker", exact: true }),
  });
  await expect(worker).toBeVisible();
  await expect(worker.getByRole("cell").nth(3)).toHaveText("Not observed");
  await expect(table).not.toContainText("Invalid Date");
  for (const [width, height] of [
    [1366, 768],
    [390, 844],
  ]) {
    await page.setViewportSize({ width, height });
    await worker.scrollIntoViewIfNeeded();
    expect(
      await page.evaluate(() => document.documentElement.scrollWidth),
    ).toBeLessThanOrEqual(width);
    mkdirSync("logs/health-screenshots", { recursive: true });
    await page.screenshot({
      path: `logs/health-screenshots/observed-${width}.png`,
    });
  }
});
