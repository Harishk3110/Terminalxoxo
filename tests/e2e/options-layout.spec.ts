import { expect, test } from "@playwright/test";
import { mkdirSync } from "node:fs";

test("negative million-scale gamma labels stay inside the chart canvas", async ({
  page,
}) => {
  await page.addInitScript(() => {
    const originalText = CanvasRenderingContext2D.prototype.fillText;
    const originalClear = CanvasRenderingContext2D.prototype.clearRect;
    CanvasRenderingContext2D.prototype.clearRect = function (
      x,
      y,
      width,
      height,
    ) {
      delete this.canvas.dataset.negativeLabelBounds;
      originalClear.call(this, x, y, width, height);
    };
    CanvasRenderingContext2D.prototype.fillText = function (
      text,
      x,
      y,
      maxWidth,
    ) {
      if (/^[-\u2212]\d/.test(text)) {
        const metrics = this.measureText(text);
        const matrix = this.getTransform();
        const corners = [
          [
            x - metrics.actualBoundingBoxLeft,
            y - metrics.actualBoundingBoxAscent,
          ],
          [
            x + metrics.actualBoundingBoxRight,
            y - metrics.actualBoundingBoxAscent,
          ],
          [
            x - metrics.actualBoundingBoxLeft,
            y + metrics.actualBoundingBoxDescent,
          ],
          [
            x + metrics.actualBoundingBoxRight,
            y + metrics.actualBoundingBoxDescent,
          ],
        ].map(([left, top]) => matrix.transformPoint({ x: left, y: top }));
        const bounds = JSON.parse(
          this.canvas.dataset.negativeLabelBounds || "[]",
        );
        bounds.push({
          text,
          left: Math.min(...corners.map((point) => point.x)),
          right: Math.max(...corners.map((point) => point.x)),
          width: this.canvas.width,
        });
        this.canvas.dataset.negativeLabelBounds = JSON.stringify(bounds);
      }
      if (maxWidth === undefined) originalText.call(this, text, x, y);
      else originalText.call(this, text, x, y, maxWidth);
    };
  });
  await page.goto("/functions/gex");
  await page
    .getByRole("button", {
      name: "Create synthetic European demo chain",
      exact: true,
    })
    .click();
  await expect(page.getByLabel("Options dataset")).not.toHaveValue("");
  const calculation = page.waitForResponse(
    (response) =>
      response.url().endsWith("/options/calculate") &&
      response.request().method() === "POST",
  );
  await page
    .getByRole("button", { name: "Calculate & Save", exact: true })
    .click();
  expect((await calculation).status()).toBe(201);
  await page.getByRole("tab", { name: "GEX", exact: true }).click();
  for (const [width, height] of [
    [1366, 768],
    [1440, 900],
    [1920, 1080],
    [2560, 1440],
    [390, 844],
  ]) {
    await page.setViewportSize({ width, height });
    const metricLabels = page.locator(".kpi > span");
    await expect(metricLabels).toHaveCount(11);
    await expect
      .poll(async () =>
        metricLabels.evaluateAll((labels) =>
          labels
            .filter((label) => label.scrollWidth > label.clientWidth)
            .map((label) => label.textContent),
        ),
      )
      .toEqual([]);
    await metricLabels.last().scrollIntoViewIfNeeded();
    mkdirSync("logs/options-layout", { recursive: true });
    await page.screenshot({ path: `logs/options-layout/metrics-${width}.png` });
    const canvas = page
      .getByLabel("Gamma spot profile", { exact: true })
      .locator("canvas");
    await canvas.scrollIntoViewIfNeeded();
    await expect(canvas).toBeVisible();
    await expect
      .poll(async () => {
        const raw = await canvas.getAttribute("data-negative-label-bounds");
        return raw ? JSON.parse(raw).length : 0;
      })
      .toBeGreaterThan(0);
    const bounds: {
      text: string;
      left: number;
      right: number;
      width: number;
    }[] = JSON.parse(
      (await canvas.getAttribute("data-negative-label-bounds"))!,
    );
    expect(
      bounds.some(
        (label) =>
          Math.abs(
            Number(label.text.replaceAll(",", "").replace("\u2212", "-")),
          ) >= 1_000_000,
      ),
    ).toBe(true);
    for (const label of bounds) {
      expect(label.left, label.text).toBeGreaterThanOrEqual(0);
      expect(label.right, label.text).toBeLessThanOrEqual(label.width);
    }
    expect(
      await page.evaluate(() => document.documentElement.scrollWidth),
    ).toBeLessThanOrEqual(width);
    mkdirSync("logs/options-layout", { recursive: true });
    await page.screenshot({ path: `logs/options-layout/gamma-${width}.png` });
  }
});
