import { expect, test } from "@playwright/test";
import { mkdirSync } from "node:fs";

for (const width of [1440, 390]) {
  test(`risk unavailable panels stay explicit and contained at ${width}px`, async ({
    page,
  }) => {
    await page.setViewportSize({ width, height: 900 });
    const errors: string[] = [];
    page.on("pageerror", (error) => errors.push(error.message));
    await page.route("**/backend/api/v1/terminal/portfolio", async (route) => {
      const response = await route.fetch();
      expect(response.ok()).toBeTruthy();
      const snapshot = await response.json();
      await route.fulfill({
        response,
        json: {
          ...snapshot,
          source: "Browser test fixture / unavailable return history",
          quality: "INSUFFICIENT DATA",
          positions: snapshot.positions.map(
            (position: Record<string, unknown>) => ({
              ...position,
              risk_contribution: null,
              beta: null,
            }),
          ),
          correlation: {
            symbols: snapshot.correlation.symbols,
            values: snapshot.correlation.values.map((row: unknown[]) =>
              row.map(() => null),
            ),
          },
        },
      });
    });
    await page.goto("/risk");
    await expect(page.getByTestId("terminal-shell")).toBeVisible();
    for (const name of [
      "Position variance contribution",
      "Daily return correlation",
    ]) {
      const panel = page.getByRole("region", { name });
      const empty = panel.locator(".empty-state");
      await expect(
        empty.getByText("INSUFFICIENT DATA", { exact: true }),
      ).toBeVisible();
      await expect(panel.locator("canvas")).toHaveCount(0);
      const bounds = await empty.boundingBox();
      const parent = await panel.boundingBox();
      expect(bounds).not.toBeNull();
      expect(parent).not.toBeNull();
      expect(bounds!.x).toBeGreaterThanOrEqual(parent!.x);
      expect(bounds!.x + bounds!.width).toBeLessThanOrEqual(
        parent!.x + parent!.width + 1,
      );
      expect(bounds!.y + bounds!.height).toBeLessThanOrEqual(
        parent!.y + parent!.height + 1,
      );
    }
    expect(
      await page.evaluate(() => document.documentElement.scrollWidth),
    ).toBeLessThanOrEqual(width);
    expect(errors).toEqual([]);
    mkdirSync("docs/screenshots", { recursive: true });
    await page.screenshot({
      path: `docs/screenshots/risk-unavailable-${width}.png`,
      fullPage: true,
    });
  });
}
