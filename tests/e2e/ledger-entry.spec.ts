import { expect, test } from "@playwright/test";
import { mkdirSync } from "node:fs";
import { transactionTypes } from "../../apps/terminal-web/components/ledger/entry-draft";

const sizes = [
  [1366, 768],
  [1440, 900],
  [1920, 1080],
  [2560, 1440],
  [390, 844],
];

test("all ledger entry modes fit the existing terminal and restore launch focus", async ({
  page,
}) => {
  test.setTimeout(180000);
  mkdirSync("logs/ledger-screenshots", { recursive: true });
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  for (const [width, height] of sizes) {
    await page.setViewportSize({ width, height });
    await page.goto("/trade-monitor");
    const launch = page.getByRole("button", {
      name: "Record transaction",
      exact: true,
    });
    await launch.click();
    const dialog = page.getByRole("dialog", {
      name: "Record ledger transaction",
    });
    await expect(dialog.getByLabel("Transaction type")).toBeEnabled();
    if (width < 600) {
      expect(
        (await dialog.getByLabel(/Trade time/).boundingBox())!.width,
      ).toBeGreaterThan(300);
    }
    expect(
      await dialog.getByLabel("Transaction type").locator("option").count(),
    ).toBe(19);
    for (const type of transactionTypes) {
      const option = dialog
        .getByLabel("Transaction type")
        .getByRole("option", { name: type, exact: true });
      // A policy-disabled SHORT is intentionally unavailable to this book.
      if (await option.isDisabled()) continue;
      await dialog.getByLabel("Transaction type").selectOption(type);
      expect(
        await dialog.evaluate(
          (element) => element.scrollWidth <= element.clientWidth + 1,
        ),
      ).toBe(true);
      expect(
        await dialog
          .locator(".ledger-entry-fields .field")
          .evaluateAll((fields) =>
            fields.every((field) => field.scrollWidth <= field.clientWidth + 1),
          ),
      ).toBe(true);
      if (type === "REVERSE_SPLIT")
        await expect(
          dialog.getByLabel("New shares per old share"),
        ).toBeAttached();
      if (type === "SPINOFF")
        await expect(dialog.getByLabel("Child shares received")).toBeAttached();
      if (type === "MERGER") {
        await expect(dialog.getByLabel("Cash per parent share")).toBeAttached();
        await expect(dialog.getByLabel("Successor security")).toBeAttached();
      }
      if (type === "FX_CONVERSION") {
        expect(
          await dialog.getByLabel("Currency", { exact: true }).inputValue(),
        ).not.toBe(await dialog.getByLabel("Received currency").inputValue());
      }
      if (type === "BUY" || type === "MERGER") {
        await dialog.getByLabel("Transaction type").scrollIntoViewIfNeeded();
        await page.screenshot({
          path: `logs/ledger-screenshots/entry-${type.toLowerCase()}-${width}.png`,
        });
      }
    }
    const bounds = await dialog.boundingBox();
    expect(bounds).not.toBeNull();
    expect(bounds!.x).toBeGreaterThanOrEqual(0);
    expect(bounds!.y).toBeGreaterThanOrEqual(0);
    expect(bounds!.x + bounds!.width).toBeLessThanOrEqual(width);
    expect(bounds!.y + bounds!.height).toBeLessThanOrEqual(height);
    expect(
      await dialog.evaluate((element) =>
        element.contains(document.activeElement),
      ),
    ).toBe(true);
    await page.keyboard.press("Escape");
    await expect(dialog).toBeHidden();
    await expect(launch).toBeFocused();
  }
  expect(errors).toEqual([]);
});

test("manual entry preserves audit context and replay cash details across a reload", async ({
  page,
  request,
}) => {
  test.setTimeout(120000);
  const base = "/backend/api/v1/portfolios/KNK_MAIN";
  const day = new Date().toISOString().slice(0, 10);
  const recordedAt = new Date(Date.now() - 60000);
  const localTime = new Date(
    recordedAt.getTime() - recordedAt.getTimezoneOffset() * 60000,
  )
    .toISOString()
    .slice(0, 16);
  const reference = `test-statement:${Date.now()}:row-7`;
  const brokerReference = "paper-reference-only-no-broker-confirmation";
  await page.goto("/trade-monitor");
  await page
    .getByRole("button", { name: "Record transaction", exact: true })
    .click();
  const entry = page.getByRole("dialog", { name: "Record ledger transaction" });
  await expect(entry.getByLabel("Transaction type")).toBeEnabled();
  await entry.getByLabel("Transaction type").selectOption("TAX");
  await entry.getByLabel("Trade date", { exact: true }).fill(day);
  await entry.getByLabel(/Trade time/).fill(localTime);
  await entry.getByLabel("Gross amount", { exact: true }).fill("1.23");
  await entry.getByLabel("External reference", { exact: true }).fill(reference);
  await entry
    .getByLabel("Broker execution reference", { exact: true })
    .fill(brokerReference);
  await entry
    .getByLabel("Rationale / notes")
    .fill("Isolated audited tax entry browser test");
  const response = page.waitForResponse(
    (result) =>
      result.url().endsWith("/api/v1/portfolios/KNK_MAIN/transactions") &&
      result.request().method() === "POST",
  );
  await entry
    .getByRole("button", { name: "Record transaction", exact: true })
    .click();
  const saved = await response;
  expect(saved.status()).toBe(201);
  const created = await saved.json();
  expect(created.external_reference).toBe(reference);
  expect(created.broker_execution_id).toBe(brokerReference);
  expect(new Date(created.trade_timestamp).toISOString()).toBe(
    new Date(localTime).toISOString(),
  );
  expect(created.trade_timestamp_state).toBe("RECORDED");
  expect(created.reconciliation_state).toBe("INTERNAL_ONLY");
  expect(Number(created.net_amount)).toBe(-1.23);
  await expect(entry).toBeHidden();
  await page.getByLabel("Filter trade-monitor").fill("TAX");
  const row = page
    .getByLabel("trade-monitor table")
    .getByRole("row")
    .filter({ hasText: day })
    .filter({ hasText: "MANUAL" });
  await expect(row).toHaveCount(1);
  await row.click();
  await page.getByRole("button", { name: "Correct ledger record" }).click();
  let details = page.getByRole("dialog", { name: "Transaction / TAX" });
  await details.getByRole("button", { name: "Details", exact: true }).click();
  await expect(details.getByText(reference, { exact: true })).toBeVisible();
  await expect(
    details.getByRole("table", { name: "Transaction cash legs" }),
  ).toContainText("-1.23000000");
  for (const [width, height] of sizes) {
    await page.setViewportSize({ width, height });
    expect(
      await details.evaluate(
        (element) => element.scrollWidth <= element.clientWidth + 1,
      ),
    ).toBe(true);
    expect(
      await details
        .locator(".ledger-audit-fields dd")
        .evaluateAll((cells) =>
          cells.every((cell) => cell.scrollWidth <= cell.clientWidth + 1),
        ),
    ).toBe(true);
    await page.screenshot({
      path: `logs/ledger-screenshots/transaction-details-${width}.png`,
    });
  }
  await page.keyboard.press("Escape");
  await page.reload();
  await page.getByLabel("Filter trade-monitor").fill("TAX");
  await row.click();
  await page.getByRole("button", { name: "Correct ledger record" }).click();
  details = page.getByRole("dialog", { name: "Transaction / TAX" });
  await details.getByRole("button", { name: "Details", exact: true }).click();
  await expect(
    details.getByText(brokerReference, { exact: true }),
  ).toBeVisible();
  const reloaded = await (
    await request.get(base + "/transactions/" + created.id)
  ).json();
  expect(reloaded.external_reference).toBe(reference);
  expect(reloaded.cash_effect_state).toBe("REPLAYED");
  expect(reloaded.net_cash_by_currency).toHaveLength(1);
  expect(reloaded.net_cash_by_currency[0].currency).toBe("SGD");
  expect(Number(reloaded.net_cash_by_currency[0].amount)).toBe(-1.23);
});
