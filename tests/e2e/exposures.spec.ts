import { expect, test } from "@playwright/test";
import { mkdirSync } from "node:fs";

test("saved exposure groups and cash freshness are inspectable at five terminal sizes", async ({
  page,
  request,
}) => {
  test.setTimeout(180000);
  mkdirSync("logs/ledger-screenshots", { recursive: true });
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  for (const [width, height] of [
    [1366, 768],
    [1440, 900],
    [1920, 1080],
    [2560, 1440],
    [390, 844],
  ]) {
    await page.setViewportSize({ width, height });
    await page.goto("/overview");
    const trigger = page.getByRole("button", {
      name: "Portfolio accounting",
      exact: true,
    });
    await trigger.click();
    const dialog = page.getByRole("dialog", {
      name: "Portfolio accounting / KNK_MAIN",
    });
    await expect(dialog.getByLabel("Cost-basis method")).toHaveValue("AVERAGE");
    const pending = page.waitForResponse(
      (response) =>
        response.url().includes("/exposures?run_id=") &&
        response.status() === 200,
    );
    await dialog
      .getByRole("button", { name: "Exposures", exact: true })
      .click();
    const payload = await (await pending).json();
    expect(payload.calculation_version).toBe("knk-nav-4.8");
    const controls = dialog.getByRole("group", {
      name: "Accounting view",
      exact: true,
    });
    expect(
      await controls.evaluate((node) => {
        const parent = node.getBoundingClientRect();
        return [...node.querySelectorAll("button")].every((button) => {
          const rect = button.getBoundingClientRect();
          return (
            rect.top >= parent.top &&
            rect.bottom <= parent.bottom + 1 &&
            rect.left >= parent.left &&
            rect.right <= parent.right + 1
          );
        });
      }),
    ).toBe(true);
    await expect(
      dialog.getByRole("table", { name: "Grouped portfolio exposures" }),
    ).toBeVisible();
    await expect(
      dialog.getByRole("rowheader", { name: "SGD", exact: true }),
    ).toBeVisible();
    await expect(
      dialog.getByRole("columnheader", { name: "Net / SGD" }),
    ).toBeVisible();
    await expect(dialog.locator(".ledger-run-details")).toContainText(
      payload.valuation_run_id,
    );
    const box = await dialog.boundingBox();
    expect(box).not.toBeNull();
    expect(box!.x).toBeGreaterThanOrEqual(0);
    expect(box!.y).toBeGreaterThanOrEqual(0);
    expect(box!.x + box!.width).toBeLessThanOrEqual(width);
    expect(box!.y + box!.height).toBeLessThanOrEqual(height);
    expect(
      await dialog.evaluate((node) => node.scrollWidth <= node.clientWidth + 1),
    ).toBe(true);
    expect(
      await dialog
        .locator("thead th")
        .evaluateAll((cells) =>
          cells.every((cell) => cell.scrollWidth <= cell.clientWidth + 1),
        ),
    ).toBe(true);
    await page.screenshot({
      path: `logs/ledger-screenshots/exposure-currency-${width}.png`,
    });
    for (const dimension of ["sector", "country", "asset_class"]) {
      await dialog.getByLabel("Exposure dimension").selectOption(dimension);
      await expect(
        dialog.getByRole("rowheader", {
          name: payload.groups[dimension][0].name,
          exact: true,
        }),
      ).toBeVisible();
    }
    await dialog
      .getByRole("button", { name: "Freshness", exact: true })
      .click();
    await expect(
      dialog.getByText("Stale cash / SGD", { exact: true }),
    ).toBeVisible();
    await expect(
      dialog.getByText("Total stale value / SGD", { exact: true }),
    ).toBeVisible();
    expect(
      await dialog.evaluate((node) => node.scrollWidth <= node.clientWidth + 1),
    ).toBe(true);
    await page.screenshot({
      path: `logs/ledger-screenshots/exposure-freshness-${width}.png`,
    });
    await dialog
      .getByRole("button", { name: "Balance marks", exact: true })
      .click();
    await expect(
      dialog.getByText("No outstanding manual balance adjustments"),
    ).toBeVisible();
    const saved = await request.get(
      `/backend/api/v1/portfolios/KNK_MAIN/exposures?run_id=${encodeURIComponent(payload.valuation_run_id)}`,
    );
    expect(saved.ok()).toBe(true);
    expect(await saved.json()).toEqual(payload);
    const refreshed = page.waitForResponse(
      (response) =>
        response.url().includes("/exposures?run_id=") &&
        response.status() === 200,
    );
    await dialog
      .getByRole("button", { name: "Refresh accounting records" })
      .click();
    expect((await refreshed).ok()).toBe(true);
    await expect(
      dialog.getByText("No outstanding manual balance adjustments"),
    ).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(dialog).toBeHidden();
    await expect(trigger).toBeFocused();
  }
  expect(errors).toEqual([]);
});
