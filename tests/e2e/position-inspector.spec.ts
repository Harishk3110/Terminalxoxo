import { expect, test } from "@playwright/test";
import { mkdirSync } from "node:fs";
import type { PositionSnapshot } from "../../apps/terminal-web/components/ledger/position-contracts";

test("position inspector retains saved-run provenance and fits all terminal widths", async ({
  page,
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
        response.url().includes("/portfolios/KNK_MAIN/positions/") &&
        response.request().method() === "GET",
    );
    await dialog
      .getByRole("button", { name: "Positions", exact: true })
      .click();
    const response = await pending;
    expect(response.ok()).toBe(true);
    const position: PositionSnapshot = await response.json();
    const run = new URL(response.url()).searchParams.get("run_id");
    expect(run).toBeTruthy();
    expect(run).toBe(position.valuation_run_id);
    await expect(dialog.locator(".ledger-run-details")).toContainText(
      "Run " + run,
    );
    const inspector = dialog.getByRole("region", {
      name: "Position accounting detail",
    });
    await expect(
      inspector.getByText(position.symbol + " / " + position.name, {
        exact: true,
      }),
    ).toBeVisible();
    await expect(
      inspector.getByText("Native market value / " + position.currency, {
        exact: true,
      }),
    ).toBeVisible();
    await expect(
      inspector.getByText("Base market value / " + position.base_currency, {
        exact: true,
      }),
    ).toBeVisible();
    expect(
      await inspector
        .locator(".ledger-position-measures dd")
        .evaluateAll((cells) =>
          cells.every((cell) => cell.scrollWidth <= cell.clientWidth + 1),
        ),
    ).toBe(true);
    const bounds = await dialog.boundingBox();
    expect(bounds).not.toBeNull();
    expect(bounds!.x).toBeGreaterThanOrEqual(0);
    expect(bounds!.y).toBeGreaterThanOrEqual(0);
    expect(bounds!.x + bounds!.width).toBeLessThanOrEqual(width);
    expect(bounds!.y + bounds!.height).toBeLessThanOrEqual(height);
    expect(
      await dialog.evaluate((node) => node.scrollWidth <= node.clientWidth + 1),
    ).toBe(true);
    await page.screenshot({
      path: `logs/ledger-screenshots/position-value-${width}.png`,
    });
    await inspector
      .getByRole("button", { name: "Day P&L", exact: true })
      .click();
    await expect(
      inspector.getByText("Position P&L", { exact: true }),
    ).toBeVisible();
    await expect(
      inspector.getByText("Period methodology", { exact: true }),
    ).toBeVisible();
    await page.screenshot({
      path: `logs/ledger-screenshots/position-daily-${width}.png`,
    });
    await inspector
      .getByRole("button", { name: "Sources", exact: true })
      .click();
    const price = inspector.getByRole("region", { name: "Price provenance" });
    const fx = inspector.getByRole("region", { name: "FX provenance" });
    await expect(
      price.getByText(position.price_provenance.source, { exact: true }),
    ).toBeVisible();
    await expect(
      fx.getByText(position.fx_provenance.source, { exact: true }),
    ).toBeVisible();
    expect(
      await dialog.evaluate((node) => node.scrollWidth <= node.clientWidth + 1),
    ).toBe(true);
    await page.screenshot({
      path: `logs/ledger-screenshots/position-sources-${width}.png`,
    });
    await inspector
      .getByRole("button", { name: "Open lots", exact: true })
      .click();
    const lots = inspector.getByRole("table", {
      name: "Selected position lots",
    });
    await expect(lots.getByRole("row")).toHaveCount(
      1 + position.lots.filter((lot) => Number(lot.quantity) !== 0).length,
    );
    const choices = await inspector
      .getByLabel("Position", { exact: true })
      .locator("option")
      .evaluateAll((options) =>
        options.map((option) => ({
          value: (option as HTMLOptionElement).value,
          label: option.textContent,
        })),
      );
    const next = choices.find(
      (option) => option.value !== position.instrument_id,
    );
    expect(next).toBeDefined();
    const switched = page.waitForResponse((result) =>
      result.url().includes("/positions/" + next!.value + "?"),
    );
    await inspector
      .getByLabel("Position", { exact: true })
      .selectOption(next!.value);
    const nextResponse = await switched;
    expect(nextResponse.ok()).toBe(true);
    expect(new URL(nextResponse.url()).searchParams.get("run_id")).toBe(run);
    const nextPosition: PositionSnapshot = await nextResponse.json();
    await expect(
      inspector.getByText(nextPosition.symbol + " / " + nextPosition.name, {
        exact: true,
      }),
    ).toBeVisible();
    await expect(
      inspector.getByText(position.symbol + " / " + position.name, {
        exact: true,
      }),
    ).toHaveCount(0);
    await page.keyboard.press("Escape");
    await expect(dialog).toBeHidden();
    await expect(trigger).toBeFocused();
  }
  expect(errors).toEqual([]);
});
