import { expect, test } from "@playwright/test";

test("unconnected broker reconciliation stays explicit on desktop and mobile", async ({
  page,
}) => {
  test.setTimeout(120000);
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/broker-monitor");
  await expect(
    page.getByRole("heading", { name: "Paper Broker Monitor" }),
  ).toBeVisible();
  for (const width of [1440, 390]) {
    await page.setViewportSize({ width, height: 1000 });
    const response = page.waitForResponse(
      (reply) =>
        reply.url().includes("/api/v1/operations/reconciliation") &&
        reply.request().method() === "POST",
    );
    await page
      .getByRole("button", { name: "Reconcile ledger", exact: true })
      .click();
    const reply = await response;
    expect(reply.status()).toBe(200);
    expect(await reply.json()).toMatchObject({
      state: "BROKER_NOT_CONNECTED",
      source: "INTERNAL LEDGER",
      items: [],
      warnings: [
        "No broker snapshot available; reference values are not broker balances",
      ],
    });
    const state = page.getByText("Reconciliation / BROKER_NOT_CONNECTED", {
      exact: true,
    });
    await state.scrollIntoViewIfNeeded();
    await expect(state).toBeVisible();
    await expect(page.locator(".error-state")).toHaveCount(0);
    expect(
      await page.evaluate(() => document.documentElement.scrollWidth),
    ).toBeLessThanOrEqual(width);
    await page.screenshot({ path: `logs/reconciliation-${width}.png` });
  }
  expect(errors).toEqual([]);
});
