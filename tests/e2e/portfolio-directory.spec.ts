import { expect, test } from "@playwright/test";
import { mkdirSync } from "node:fs";

test("portfolio directory and creation controls fit the approved terminal at five sizes", async ({
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
      name: "Portfolio ledgers",
      exact: true,
    });
    await trigger.click();
    const directory = page.getByRole("dialog", {
      name: "Portfolio ledgers",
      exact: true,
    });
    await expect(
      directory.getByRole("region", { name: "Selected ledger / KNK_MAIN" }),
    ).toBeVisible();
    await expect(
      directory.getByRole("table", { name: "Selected ledger transactions" }),
    ).toBeVisible();
    expect(
      await directory.evaluate(
        (node) => node.scrollWidth <= node.clientWidth + 1,
      ),
    ).toBe(true);
    await page.screenshot({
      path: `logs/ledger-screenshots/portfolio-directory-${width}.png`,
    });
    await directory
      .getByRole("button", { name: "Create portfolio ledger", exact: true })
      .click();
    const form = page.getByRole("dialog", {
      name: "Create portfolio ledger",
      exact: true,
    });
    await expect(
      form.getByLabel("Portfolio code", { exact: true }),
    ).toBeVisible();
    await expect(
      form.getByLabel("Opening contribution", { exact: true }),
    ).toHaveValue("");
    await form
      .getByLabel("Portfolio name")
      .fill("KnK Capital / Internal Research Allocation Ledger");
    await form
      .getByLabel("Opening contribution", { exact: true })
      .fill("1000.12345678");
    await form.getByLabel("Base currency", { exact: true }).selectOption("USD");
    await expect(
      form.getByText("Opening contribution / USD", { exact: true }),
    ).toBeVisible();
    expect(
      await form.evaluate((node) => node.scrollWidth <= node.clientWidth + 1),
    ).toBe(true);
    const bounds = await form.boundingBox();
    expect(bounds).not.toBeNull();
    expect(bounds!.x).toBeGreaterThanOrEqual(0);
    expect(bounds!.y).toBeGreaterThanOrEqual(0);
    expect(bounds!.x + bounds!.width).toBeLessThanOrEqual(width);
    expect(bounds!.y + bounds!.height).toBeLessThanOrEqual(height);
    expect(
      await form
        .locator(".ledger-entry-fields input, .ledger-entry-fields select")
        .evaluateAll((inputs) =>
          inputs.every(
            (input) =>
              input.getBoundingClientRect().width <=
              input.parentElement!.getBoundingClientRect().width + 1,
          ),
        ),
    ).toBe(true);
    await page.screenshot({
      path: `logs/ledger-screenshots/portfolio-create-${width}.png`,
    });
    await page.keyboard.press("Escape");
    await expect(directory).toBeVisible();
    await expect(page.getByRole("dialog")).toHaveCount(1);
    await page.keyboard.press("Escape");
    await expect(directory).toBeHidden();
    await expect(trigger).toBeFocused();
  }
  expect(errors).toEqual([]);
});

test("new ledger capital, transactions and corrections persist without changing KNK_MAIN", async ({
  page,
  request,
}) => {
  test.setTimeout(120000);
  const main = await (
    await request.get("/backend/api/v1/portfolios/KNK_MAIN/summary")
  ).json();
  const code = "BROWSER_RESEARCH";
  await page.goto("/overview");
  await page
    .getByRole("button", { name: "Portfolio ledgers", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Create portfolio ledger", exact: true })
    .click();
  const form = page.getByRole("dialog", {
    name: "Create portfolio ledger",
    exact: true,
  });
  await form.getByLabel("Portfolio code", { exact: true }).fill(code);
  await form.getByLabel("Portfolio name").fill("Browser research allocation");
  await form
    .getByLabel("Opening contribution", { exact: true })
    .fill("1000.12345678");
  await form.getByLabel("Base currency", { exact: true }).selectOption("USD");
  await form.getByLabel("Opening cost-basis method").selectOption("FIFO");
  const posted = page.waitForResponse(
    (response) =>
      response.url().endsWith("/api/v1/portfolios") &&
      response.request().method() === "POST",
  );
  await form
    .getByRole("button", { name: "Create internal ledger", exact: true })
    .click();
  const response = await posted;
  expect(response.status()).toBe(201);
  const created = await response.json();
  expect(created.code).toBe(code);
  expect(created.reference_capital).toBe("1000.12345678");
  expect(created.is_default).toBe(false);
  expect(created.accounts[0].provider).toBeNull();
  const base = "/backend/api/v1/portfolios/" + created.id;
  const directory = page.getByRole("dialog", {
    name: "Portfolio ledgers",
    exact: true,
  });
  const selected = directory.getByRole("region", {
    name: "Selected ledger / " + code,
  });
  await expect(selected).toBeVisible();
  await expect(
    selected
      .getByRole("table", { name: "Selected ledger transactions" })
      .getByRole("row"),
  ).toHaveCount(2);
  await selected
    .getByRole("button", { name: "Record selected transaction", exact: true })
    .click();
  const entry = page.getByRole("dialog", {
    name: "Record ledger transaction",
    exact: true,
  });
  await entry.getByLabel("Transaction type").selectOption("DEPOSIT");
  await expect(entry.getByLabel("Currency", { exact: true })).toHaveValue(
    "USD",
  );
  await entry.getByLabel("Gross amount", { exact: true }).fill("25.87654322");
  await entry
    .getByRole("button", { name: "Record transaction", exact: true })
    .click();
  await expect(directory).toBeVisible();
  const transactions = await (await request.get(base + "/transactions")).json();
  expect(transactions.items).toHaveLength(2);
  const deposit = transactions.items.find(
    (item: { notes: string }) =>
      item.notes !== "Explicit opening capital contribution",
  );
  expect(deposit.portfolio_id).toBe(created.id);
  await expect(
    selected
      .getByRole("table", { name: "Selected ledger transactions" })
      .getByRole("row"),
  ).toHaveCount(3);
  await selected
    .getByRole("button", {
      name: "Inspect transaction " + deposit.id,
      exact: true,
    })
    .click();
  const correction = page.getByRole("dialog", {
    name: "Transaction / DEPOSIT",
    exact: true,
  });
  await expect(
    correction.getByText("Portfolio " + code, { exact: true }),
  ).toBeVisible();
  await correction
    .getByLabel("Gross amount", { exact: true })
    .fill("26.87654322");
  await correction
    .getByLabel("Correction reason")
    .fill("Correct selected research contribution");
  await correction
    .getByRole("button", { name: "Record correction", exact: true })
    .click();
  await expect(correction.getByRole("status")).toHaveText(
    "Revision 2 recorded",
  );
  await page.keyboard.press("Escape");
  await expect(
    selected
      .getByText("NAV / USD", { exact: true })
      .locator("..")
      .locator("dd"),
  ).toHaveText("1,027.00");
  await selected
    .getByRole("button", { name: "Open selected accounting", exact: true })
    .click();
  const accounting = page.getByRole("dialog", {
    name: "Portfolio accounting / " + code,
    exact: true,
  });
  await expect(accounting.getByLabel("Cost-basis method")).toHaveValue("FIFO");
  await accounting.getByRole("button", { name: "Cash", exact: true }).click();
  await expect(
    accounting.getByText("Economic cash / USD", { exact: true }),
  ).toBeVisible();
  await page.keyboard.press("Escape");
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({
    path: "logs/ledger-screenshots/portfolio-created-390.png",
  });
  await page.keyboard.press("Escape");
  await page.reload();
  await page
    .getByRole("button", { name: "Portfolio ledgers", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Select ledger " + code, exact: true })
    .click();
  await expect(
    selected
      .getByRole("table", { name: "Selected ledger transactions" })
      .getByRole("row"),
  ).toHaveCount(3);
  const saved = await (
    await request.get(base + "/transactions/" + deposit.id)
  ).json();
  expect(saved.audit_version).toBe(2);
  expect(saved.gross_amount).toBe("26.87654322");
  const unchanged = await (
    await request.get("/backend/api/v1/portfolios/KNK_MAIN/summary")
  ).json();
  expect(unchanged.portfolio.nav).toBe(main.portfolio.nav);
  expect(unchanged.transactions).toEqual(main.transactions);
});
