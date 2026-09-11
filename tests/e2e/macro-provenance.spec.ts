import { expect, test } from "@playwright/test";
import { mkdirSync } from "node:fs";

test("macro chart dates reflect observations instead of ingestion on desktop and mobile", async ({
  page,
  request,
}) => {
  const response = await request.get("/backend/api/v1/macro/dashboard");
  expect(response.status()).toBe(200);
  const data = await response.json();
  const selected = data.items.find(
    (item: { series_id: string }) => item.series_id === "DGS10",
  );
  expect(selected.latest_observation_date).toMatch(/^\d{4}-\d{2}-\d{2}$/);
  const expectedDate = new Date(
    `${selected.latest_observation_date}T00:00:00Z`,
  ).toLocaleDateString("en-SG", {
    timeZone: "Asia/Singapore",
    day: "2-digit",
    month: "short",
    year: "2-digit",
  });
  await page.goto("/macro");
  await expect(page.getByLabel("Economic series", { exact: true })).toHaveValue(
    "DGS10",
  );
  const panel = page.getByRole("region", {
    name: "Economic series / DGS10",
    exact: true,
  });
  await expect(panel.locator("footer time")).toHaveText(expectedDate);
  await expect(panel.locator("footer")).toContainText(selected.quality);
  for (const [width, height] of [
    [1366, 768],
    [390, 844],
  ]) {
    await page.setViewportSize({ width, height });
    const canvas = panel.locator("canvas");
    await canvas.scrollIntoViewIfNeeded();
    await expect(canvas).toBeVisible();
    expect(
      await canvas.evaluate((element: HTMLCanvasElement) => {
        const pixels = element
          .getContext("2d")!
          .getImageData(0, 0, element.width, element.height).data;
        let colored = 0;
        for (let i = 0; i < pixels.length; i += 4) {
          if (pixels[i] > 150 && pixels[i + 1] > 60 && pixels[i + 2] < 90)
            colored++;
        }
        return colored;
      }),
    ).toBeGreaterThan(100);
    expect(
      await page.evaluate(() => document.documentElement.scrollWidth),
    ).toBeLessThanOrEqual(width);
    mkdirSync("logs/macro-screenshots", { recursive: true });
    await page.screenshot({
      path: `logs/macro-screenshots/provenance-${width}.png`,
    });
  }
});
