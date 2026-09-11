import { expect, test } from "@playwright/test";
import { mkdirSync } from "node:fs";
import { completedRun } from "./analytical-fixtures";

test("equity coverage, theses and universe retain usable rows at every viewport", async ({
  page,
}) => {
  for (const [width, height] of [
    [1366, 768],
    [1440, 900],
    [1920, 1080],
    [2560, 1440],
    [390, 844],
  ]) {
    await page.setViewportSize({ width, height });
    await page.goto("/equity");
    const tables = ["equity-coverage", "equity-theses", "equity-universe"];
    const panels = [];
    for (const id of tables) {
      const table = page.getByLabel(`${id} table`, { exact: true });
      await expect(table).toBeVisible();
      const panel = table.locator(
        "xpath=ancestor::*[contains(@class, 'terminal-panel')][1]",
      );
      const bounds = await panel.boundingBox();
      expect(bounds).not.toBeNull();
      expect(bounds!.height, `${id} at ${width}px`).toBeGreaterThanOrEqual(180);
      panels.push(bounds!);
    }
    if (width > 900) {
      expect(Math.abs(panels[0].y - panels[1].y)).toBeLessThanOrEqual(1);
      expect(panels[2].y).toBeGreaterThanOrEqual(
        Math.max(
          panels[0].y + panels[0].height,
          panels[1].y + panels[1].height,
        ),
      );
    } else {
      expect(panels[1].y).toBeGreaterThanOrEqual(
        panels[0].y + panels[0].height,
      );
      expect(panels[2].y).toBeGreaterThanOrEqual(
        panels[1].y + panels[1].height,
      );
    }
    expect(
      await page.evaluate(() => document.documentElement.scrollWidth),
    ).toBeLessThanOrEqual(width);
    mkdirSync("logs/research-screenshots", { recursive: true });
    await page.screenshot({
      path: `logs/research-screenshots/equity-${width}.png`,
    });
  }
});

test("alpha inference retains nonzero small coefficients and standard errors", async ({
  page,
  request,
}) => {
  test.setTimeout(120000);
  const run = await completedRun(request, "backtest");
  await page.goto("/alpha");
  await page.getByLabel("Alpha return source").selectOption(run.id);
  const completed = page.waitForResponse(
    (response) =>
      response.url().endsWith("/alpha/calculate") &&
      response.request().method() === "POST",
  );
  await page
    .getByRole("button", { name: "Calculate Alpha", exact: true })
    .click();
  const response = await completed;
  expect(response.ok(), await response.text()).toBeTruthy();
  const report = await response.json();
  const alpha = report.results.NET.coefficients.find(
    (row: { factor: string }) => row.factor === "alpha",
  );
  expect(Math.abs(alpha.coefficient)).toBeGreaterThan(0);
  expect(Math.abs(alpha.coefficient)).toBeLessThan(0.005);
  const row = page
    .getByLabel("alpha-coefficients table", { exact: true })
    .getByRole("row")
    .filter({ has: page.getByRole("cell", { name: "alpha", exact: true }) });
  await expect(row).toBeVisible();
  for (const [column, expected] of [
    [1, alpha.coefficient],
    [2, alpha.standard_error],
  ]) {
    const rendered = Number(
      await row.getByRole("cell").nth(column).textContent(),
    );
    expect(rendered).not.toBe(0);
    expect(Math.abs((rendered - expected) / expected)).toBeLessThanOrEqual(
      0.00001,
    );
  }
  for (const [width, height] of [
    [1366, 768],
    [390, 844],
  ]) {
    await page.setViewportSize({ width, height });
    await row.scrollIntoViewIfNeeded();
    await expect(row).toBeVisible();
    expect(
      await page.evaluate(() => document.documentElement.scrollWidth),
    ).toBeLessThanOrEqual(width);
    mkdirSync("logs/research-screenshots", { recursive: true });
    await page.screenshot({
      path: `logs/research-screenshots/alpha-${width}.png`,
    });
  }
});

test("stress chart stays above its source footer without an inner vertical scrollbar", async ({
  page,
  request,
}) => {
  await completedRun(request, "stress");
  await page.setViewportSize({ width: 1366, height: 768 });
  await page.goto("/stress-tests");
  await page.getByRole("button", { name: /Independent visual stress/ }).click();
  const chart = page.getByLabel("Stress position contribution chart", {
    exact: true,
  });
  await expect(chart.locator("canvas")).toBeVisible();
  for (const [width, height] of [
    [1366, 768],
    [390, 844],
  ]) {
    await page.setViewportSize({ width, height });
    await chart.scrollIntoViewIfNeeded();
    await expect
      .poll(async () =>
        chart.evaluate((element) => {
          const canvas = element
            .querySelector("canvas")!
            .getBoundingClientRect();
          const content = element.closest(".panel-content")!;
          const bounds = content.getBoundingClientRect();
          return (
            canvas.top >= bounds.top &&
            canvas.bottom <= bounds.bottom &&
            content.scrollHeight <= content.clientHeight
          );
        }),
      )
      .toBe(true);
    mkdirSync("logs/research-screenshots", { recursive: true });
    await page.screenshot({
      path: `logs/research-screenshots/stress-${width}.png`,
    });
  }
});
