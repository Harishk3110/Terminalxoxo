import { expect, test } from "@playwright/test";
import { randomUUID } from "node:crypto";

test("recorded trade review and financial evidence survive reload at desktop and mobile sizes", async ({
  page,
  request,
}) => {
  test.setTimeout(120000);
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  const reference = "fictional-trade-review-" + randomUUID();
  const fillPrice = "217.37";
  const recorded = await request.post(
    "/backend/api/v1/operations/transactions",
    {
      data: {
        transaction_type: "BUY",
        trade_date: "2026-09-04",
        symbol: "AAPL",
        quantity: "1",
        price: fillPrice,
        currency: "USD",
        external_reference: reference,
        notes: reference,
      },
    },
  );
  expect(recorded.status()).toBe(200);
  const transaction: { id: string; trade_event_id: string } =
    await recorded.json();
  await page.goto("/trade-monitor");
  await expect(
    page.getByRole("heading", { name: "Trade Monitor", exact: true }),
  ).toBeVisible();
  await page.getByLabel("Filter trade-monitor").fill(fillPrice);
  const row = page.getByLabel("trade-monitor table").locator("tbody tr");
  await expect(row).toHaveCount(1);
  await row.getByText("AAPL", { exact: true }).click();
  await page.getByLabel("Review state").selectOption("FLAGGED");
  await page
    .getByLabel("Review note")
    .fill("Fictional fill evidence checked against the ledger.");
  const reviewed = page.waitForResponse(
    (response) =>
      response.url().endsWith(`/trades/${transaction.trade_event_id}/review`) &&
      response.request().method() === "POST",
  );
  await page
    .getByRole("button", { name: "Record review", exact: true })
    .click();
  const review = await reviewed;
  expect(review.status()).toBe(200);
  expect(await review.json()).toMatchObject({
    id: transaction.trade_event_id,
    state: "FLAGGED",
  });
  for (const width of [1440, 390]) {
    await page.setViewportSize({ width, height: 1000 });
    await page.reload();
    await page.getByLabel("Filter trade-monitor").fill(fillPrice);
    await expect(row).toHaveCount(1);
    await expect(row).toContainText("FLAGGED");
    await row.getByText("AAPL", { exact: true }).click();
    await expect(page.locator(".error-state")).toHaveCount(0);
    await expect(page.locator(".loading-state")).toHaveCount(0);
    expect(
      await page.evaluate(() => document.documentElement.scrollWidth),
    ).toBeLessThanOrEqual(width);
    await page.screenshot({ path: `logs/trade-monitor-reviewed-${width}.png` });
  }
  const response = await request.get("/backend/api/v1/operations/trades");
  expect(response.status()).toBe(200);
  const result: {
    items: {
      id: string;
      transaction_id: string;
      review_state: string;
      symbol: string;
      price: string;
      external_reference: string;
      weight_after: number | string | null;
    }[];
  } = await response.json();
  const evidence = result.items.find(
    (item) => item.id === transaction.trade_event_id,
  );
  expect(evidence).toMatchObject({
    transaction_id: transaction.id,
    review_state: "FLAGGED",
    symbol: "AAPL",
    external_reference: reference,
  });
  expect(evidence?.weight_after).not.toBeNull();
  expect(Number(evidence?.price)).toBe(Number(fillPrice));
  expect(Number.isFinite(Number(evidence?.weight_after))).toBe(true);
  expect(errors).toEqual([]);
});
