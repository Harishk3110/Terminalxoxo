import { expect, test } from "@playwright/test";
import { mkdirSync } from "node:fs";

test("NAV statement shows saved assets and liability components at all terminal widths", async ({
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
    const response = page.waitForResponse(
      (res) => res.url().includes("/nav?run_id=") && res.ok(),
    );
    await dialog.getByRole("button", { name: "NAV", exact: true }).click();
    const payload = await (await response).json();
    expect(payload.calculation_version).toBe("knk-nav-4.8");
    expect(Number(payload.balance_sheet.difference)).toBe(0);
    await expect(
      dialog.getByRole("table", { name: "Assets statement" }),
    ).toBeVisible();
    await expect(
      dialog.getByRole("table", { name: "Liabilities statement" }),
    ).toBeVisible();
    await expect(
      dialog.getByRole("rowheader", { name: "Cash overdrafts" }),
    ).toBeVisible();
    await expect(
      dialog.getByRole("rowheader", { name: "Short position liabilities" }),
    ).toBeVisible();
    await expect(dialog.getByText("Closing NAV / SGD")).toBeVisible();
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
    await page.screenshot({
      path: `logs/ledger-screenshots/nav-statement-${width}.png`,
    });
    const saved = await request.get(
      `/backend/api/v1/portfolios/KNK_MAIN/nav?run_id=${encodeURIComponent(payload.valuation_run_id)}`,
    );
    expect(await saved.json()).toEqual(payload);
    const refresh = page.waitForResponse(
      (res) => res.url().includes("/nav?run_id=") && res.ok(),
    );
    await dialog
      .getByRole("button", { name: "Refresh accounting records" })
      .click();
    expect((await refresh).ok()).toBe(true);
    await page.keyboard.press("Escape");
    await expect(dialog).toBeHidden();
    await expect(trigger).toBeFocused();
  }
  expect(errors).toEqual([]);
});
