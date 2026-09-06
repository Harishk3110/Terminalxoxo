import { expect, test } from "@playwright/test";
import { mkdirSync } from "node:fs";

test("accounting dialogs fit desktop and mobile, retain focus, and expose cash and lots", async ({
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
    await expect(trigger).toBeVisible();
    await trigger.click();
    const dialog = page.getByRole("dialog", {
      name: "Portfolio accounting / KNK_MAIN",
    });
    await expect(dialog.getByLabel("Cost-basis method")).toHaveValue("AVERAGE");
    await expect(
      dialog.getByRole("button", { name: "Save policy" }),
    ).toBeDisabled();
    const bounds = await dialog.boundingBox();
    expect(bounds).not.toBeNull();
    expect(bounds!.x).toBeGreaterThanOrEqual(0);
    expect(bounds!.y).toBeGreaterThanOrEqual(0);
    expect(bounds!.x + bounds!.width).toBeLessThanOrEqual(width);
    expect(bounds!.y + bounds!.height).toBeLessThanOrEqual(height);
    expect(
      await dialog.evaluate((node) => node.contains(document.activeElement)),
    ).toBe(true);
    await page.screenshot({
      path: `logs/ledger-screenshots/policy-${width}.png`,
    });
    await dialog.getByRole("button", { name: "Cash", exact: true }).click();
    await expect(
      dialog.getByRole("columnheader", { name: "Available", exact: true }),
    ).toBeVisible();
    await expect(
      dialog.getByText("Economic cash / SGD", { exact: true }),
    ).toBeVisible();
    await page.screenshot({
      path: `logs/ledger-screenshots/cash-${width}.png`,
    });
    await dialog.getByRole("button", { name: "Lots", exact: true }).click();
    await expect(
      dialog.getByRole("rowheader", { name: "AAPL", exact: true }),
    ).toBeVisible();
    await expect(dialog.locator(".ledger-run-details")).toContainText(
      "knk-nav-4.6",
    );
    expect(
      await dialog.evaluate((node) => node.scrollWidth <= node.clientWidth + 1),
    ).toBe(true);
    await page.screenshot({
      path: `logs/ledger-screenshots/lots-${width}.png`,
    });
    await dialog.getByRole("button", { name: "Activity", exact: true }).click();
    await expect(
      dialog.getByRole("table", { name: "Accounting component records" }),
    ).toBeVisible();
    await expect(dialog.getByText("BALANCED", { exact: true })).toBeVisible();
    expect(await dialog.locator("thead th").evaluateAll((cells) =>
      cells.every((cell) => cell.scrollWidth <= cell.clientWidth + 1),
    )).toBe(true);
    expect(
      await dialog.evaluate((node) => node.scrollWidth <= node.clientWidth + 1),
    ).toBe(true);
    await page.screenshot({
      path: `logs/ledger-screenshots/activity-${width}.png`,
    });
    await dialog.getByRole("button", { name: "Balances", exact: true }).click();
    await expect(dialog.getByLabel("Signed adjustment amount")).toBeVisible();
    expect(
      await dialog.evaluate((node) => node.scrollWidth <= node.clientWidth + 1),
    ).toBe(true);
    await page.screenshot({
      path: `logs/ledger-screenshots/balances-${width}.png`,
    });
    await page.keyboard.press("Escape");
    await expect(dialog).toBeHidden();
    await expect(trigger).toBeFocused();
    await expect(
      page.getByRole("heading", { name: "Portfolio Command Centre" }),
    ).toBeVisible();
  }
  expect(errors).toEqual([]);
});

test("balance entry, negative-balance rejection and append-only reversal work through the browser", async ({
  page,
  request,
}) => {
  test.setTimeout(90000);
  const base = "/backend/api/v1/portfolios/KNK_MAIN";
  const before = await (await request.get(base + "/summary")).json();
  await page.goto("/overview");
  await page
    .getByRole("button", { name: "Portfolio accounting", exact: true })
    .click();
  const dialog = page.getByRole("dialog", {
    name: "Portfolio accounting / KNK_MAIN",
  });
  await dialog.getByRole("button", { name: "Balances", exact: true }).click();
  await dialog.getByLabel("Balance bucket").selectOption("payables");
  await dialog.getByLabel("Signed adjustment amount").fill("12.34");
  await dialog
    .getByLabel("Adjustment reason")
    .fill("Isolated vendor accrual browser test");
  await dialog
    .getByRole("button", { name: "Record adjustment", exact: true })
    .click();
  await expect(dialog.getByText("Balance adjustment recorded")).toBeVisible();
  const after = await (await request.get(base + "/summary")).json();
  expect(
    Number(before.portfolio.nav) - Number(after.portfolio.nav),
  ).toBeCloseTo(12.34, 2);
  const run = after.valuation_run_id;
  await dialog.getByLabel("Signed adjustment amount").fill("-99");
  await dialog
    .getByLabel("Adjustment reason")
    .fill("Reject excess reversal in test");
  await dialog
    .getByRole("button", { name: "Record adjustment", exact: true })
    .click();
  await expect(dialog.getByRole("alert")).toContainText(
    "payables in SGD negative",
  );
  await expect(dialog.getByLabel("Signed adjustment amount")).toHaveValue(
    "-99",
  );
  await dialog.getByLabel("Signed adjustment amount").fill("-12.34");
  await dialog
    .getByLabel("Adjustment reason")
    .fill("Restore vendor accrual after browser test");
  await dialog
    .getByRole("button", { name: "Record adjustment", exact: true })
    .click();
  await expect(dialog.getByText("Balance adjustment recorded")).toBeVisible();
  await expect(
    dialog
      .getByRole("table", { name: "Balance adjustment history" })
      .getByRole("row"),
  ).toHaveCount(3);
  const restored = await (await request.get(base + "/summary")).json();
  expect(restored.portfolio.nav).toBe(before.portfolio.nav);
  const historical = await (
    await request.get(
      base + "/accounting?" + new URLSearchParams({ run_id: run }),
    )
  ).json();
  expect(Number(historical.totals.payables)).toBe(12.34);
  await dialog.getByRole("button", { name: "Activity", exact: true }).click();
  await dialog.getByLabel("Accounting category").selectOption("LIABILITY");
  await expect(
    dialog
      .getByRole("table", { name: "Accounting component records" })
      .getByRole("row"),
  ).toHaveCount(3);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({
    path: "logs/ledger-screenshots/balance-reversal-mobile.png",
  });
  await page.keyboard.press("Escape");
  await page.reload();
  await page
    .getByRole("button", { name: "Portfolio accounting", exact: true })
    .click();
  await page.getByRole("button", { name: "Balances", exact: true }).click();
  await expect(
    page.getByRole("table", { name: "Balance adjustment history" }),
  ).toContainText("Restore vendor accrual after browser test");
});

test("accounting policy mutation is persisted and preserves economic NAV", async ({
  page,
  request,
}) => {
  test.setTimeout(90000);
  const base = "/backend/api/v1/portfolios/KNK_MAIN";
  const before = await (await request.get(base + "/summary")).json();
  const original = before.portfolio.accounting_policy;
  let changed = false;
  try {
    await page.goto("/overview");
    await page
      .getByRole("button", { name: "Portfolio accounting", exact: true })
      .click();
    const dialog = page.getByRole("dialog", {
      name: "Portfolio accounting / KNK_MAIN",
    });
    await dialog.getByLabel("Cost-basis method").selectOption("FIFO");
    await dialog.getByLabel("Capitalize transaction commissions").check();
    await dialog
      .getByLabel("Policy change reason")
      .fill("Isolated test accounting policy");
    await dialog.getByRole("button", { name: "Save policy" }).click();
    await expect(dialog.getByRole("status")).toHaveText(
      "Accounting policy saved",
    );
    changed = true;
    const after = await (await request.get(base + "/summary")).json();
    expect(after.portfolio.accounting_policy.method).toBe("FIFO");
    expect(after.portfolio.accounting_policy.capitalize_commissions).toBe(true);
    expect(after.portfolio.nav).toBe(before.portfolio.nav);
    expect(after.reconciliation.state).toBe("BALANCED");
    expect(after.valuation_run_id).not.toBe(before.valuation_run_id);
    await page.reload();
    await page
      .getByRole("button", { name: "Portfolio accounting", exact: true })
      .click();
    await expect(page.getByLabel("Cost-basis method")).toHaveValue("FIFO");
  } finally {
    if (changed) {
      const restore = await request.put(base + "/accounting-policy", {
        data: { ...original, reason: "Restore isolated test policy" },
      });
      expect(restore.ok()).toBe(true);
    }
  }
});

test("trade correction posts an audited version and history survives reload", async ({
  page,
  request,
}) => {
  test.setTimeout(90000);
  const base = "/backend/api/v1/portfolios/KNK_MAIN";
  const day = new Date().toISOString().slice(0, 10);
  const response = await request.post(base + "/transactions", {
    data: {
      transaction_type: "FEE",
      trade_date: day,
      currency: "SGD",
      amount: "1.25",
      notes: "Isolated correction workflow",
    },
  });
  expect(response.ok()).toBe(true);
  const transaction = await response.json();
  await page.goto("/trade-monitor");
  await page.getByLabel("Filter trade-monitor").fill("FEE");
  const row = page
    .getByLabel("trade-monitor table")
    .getByRole("row")
    .filter({ hasText: day })
    .filter({ hasText: "MANUAL" });
  await expect(row).toHaveCount(1);
  await row.click();
  await page.getByRole("button", { name: "Correct ledger record" }).click();
  const dialog = page.getByRole("dialog", { name: "Transaction / FEE" });
  await dialog.getByLabel("Gross amount").fill("1.75");
  await dialog
    .getByLabel("Correction reason")
    .fill("Correct test statement fee");
  await dialog.getByRole("button", { name: "Record correction" }).click();
  await expect(dialog.getByRole("status")).toHaveText("Revision 2 recorded");
  await expect(dialog.locator(".ledger-revision-list")).toContainText(
    "Correct test statement fee",
  );
  const persisted = await (
    await request.get(base + "/transactions/" + transaction.id)
  ).json();
  expect(persisted.audit_version).toBe(2);
  expect(Number(persisted.gross_amount)).toBe(1.75);
  expect(Number(persisted.revisions[0].before.entry.amount)).toBe(1.25);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({
    path: "logs/ledger-screenshots/correction-history-mobile.png",
  });
  await page.keyboard.press("Escape");
  await page.reload();
  await page.getByLabel("Filter trade-monitor").fill("FEE");
  await page
    .getByLabel("trade-monitor table")
    .getByRole("row")
    .filter({ hasText: day })
    .filter({ hasText: "MANUAL" })
    .click();
  await page.getByRole("button", { name: "Correct ledger record" }).click();
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "History", exact: true })
    .click();
  await expect(page.locator(".ledger-revision-list")).toContainText(
    "Correct test statement fee",
  );
});
