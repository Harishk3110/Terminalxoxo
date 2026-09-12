import { expect, test } from "@playwright/test";

const sources = [
  "**/backend/api/v1/operations/trades",
  "**/backend/api/v1/desks/quant",
  "**/backend/api/v1/data-drop/agents",
];
const registryTitles = [
  "Trade monitor / recent ledger events",
  "Quant / jobs and strategy registry",
];
const operationsTitle = "Operations / freshness and exceptions";

test("home keeps delayed registries pending and agent state checking", async ({
  page,
}) => {
  let release = () => {};
  const barrier = new Promise<void>((resolve) => {
    release = resolve;
  });
  const requested = new Set<string>();
  for (const source of sources) {
    await page.route(source, async (route) => {
      requested.add(source);
      await barrier;
      await route.continue();
    });
  }
  try {
    await page.goto("/overview");
    await expect(page.getByLabel("main-holdings table")).toContainText("AAPL");
    await expect.poll(() => requested.size).toBe(3);
    for (const name of registryTitles) {
      const panel = page.getByRole("region", { name, exact: true });
      await expect(panel.getByText("Loading data")).toBeVisible();
      await expect(panel.getByText("No matching records")).toHaveCount(0);
    }
    const operations = page.getByRole("region", { name: operationsTitle });
    await expect(
      operations.getByText("Agent CHECKING", { exact: true }),
    ).toBeVisible();
    await expect(operations.getByText("OFFLINE", { exact: true })).toHaveCount(
      0,
    );
    release();
    await expect(page.locator(".loading-state")).toHaveCount(0);
    for (const id of ["main-trades", "main-strategies"]) {
      await expect(
        page.getByLabel(`${id} table`).locator("tbody tr"),
      ).not.toHaveCount(0);
    }
    await expect(
      operations.getByText("Agent OFFLINE", { exact: true }),
    ).toBeVisible();
    await expect(page.locator(".error-state")).toHaveCount(0);
  } finally {
    release();
    await page.unrouteAll({ behavior: "wait" });
  }
});

test("home distinguishes failed registries and agent status from empty or offline", async ({
  page,
}) => {
  for (const source of sources) {
    await page.route(source, (route) =>
      route.fulfill({
        status: 503,
        contentType: "application/json",
        body: JSON.stringify({ detail: "Dashboard source unavailable" }),
      }),
    );
  }
  await page.goto("/overview");
  await expect(page.getByLabel("main-holdings table")).toContainText("AAPL");
  for (const name of registryTitles) {
    const panel = page.getByRole("region", { name, exact: true });
    await expect(panel.getByRole("alert")).toContainText(
      "Dashboard source unavailable",
    );
    await expect(panel.getByText("No matching records")).toHaveCount(0);
  }
  const operations = page.getByRole("region", { name: operationsTitle });
  await expect(
    operations.getByText("Agent UNAVAILABLE", { exact: true }),
  ).toBeVisible();
  await expect(operations.getByText("OFFLINE", { exact: true })).toHaveCount(0);
  await expect(operations.getByRole("alert")).toContainText(
    "Dashboard source unavailable",
  );
  await page.unrouteAll({ behavior: "wait" });
  for (const name of registryTitles) {
    await page
      .getByRole("region", { name, exact: true })
      .getByRole("button", { name: "Retry", exact: true })
      .click();
  }
  await operations
    .getByRole("button", { name: "Refresh agent status" })
    .click();
  await expect(page.locator(".loading-state")).toHaveCount(0);
  await expect(page.locator(".error-state")).toHaveCount(0);
  await expect(operations.getByRole("alert")).toHaveCount(0);
  await expect(
    operations.getByText("Agent OFFLINE", { exact: true }),
  ).toBeVisible();
  for (const id of ["main-trades", "main-strategies"]) {
    await expect(
      page.getByLabel(`${id} table`).locator("tbody tr"),
    ).not.toHaveCount(0);
  }
});
