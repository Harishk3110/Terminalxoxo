import { expect, test } from "@playwright/test";

test("options demo stays explicit, GEX signs persist and hypothetical payoff has no ledger effect", async ({
  page,
  request,
}) => {
  test.setTimeout(180000);
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  const before = await (
    await request.get("/backend/api/v1/portfolios/KNK_MAIN/summary")
  ).json();
  await page.goto("/options");
  await page
    .getByRole("button", {
      name: "Create synthetic European demo chain",
      exact: true,
    })
    .click();
  await expect(page.getByLabel("Options dataset")).not.toHaveValue("");
  const response = page.waitForResponse(
    (r) =>
      r.url().endsWith("/options/calculate") && r.request().method() === "POST",
  );
  await page
    .getByRole("button", { name: "Calculate & Save", exact: true })
    .click();
  const saved = await (await response).json();
  expect(saved.quality).toBe("DEMO DATA");
  expect(saved.summary.net_gex).toBeLessThan(0);
  expect(saved.coverage.gex_included).toBe(30);
  await expect(page.getByLabel("options-chain table")).toContainText("DEMO.");
  await page.getByRole("tab", { name: "GEX", exact: true }).click();
  for (const width of [1440, 390]) {
    await page.setViewportSize({ width, height: 1000 });
    const hide = page.getByRole("button", {
      name: "Hide inspector",
      exact: true,
    });
    if (await hide.isVisible()) await hide.click();
    const plot = page.getByLabel("GEX by strike");
    await plot.scrollIntoViewIfNeeded();
    const canvas = plot.locator("canvas");
    await expect(canvas).toBeVisible();
    expect(
      await canvas.evaluate((element: HTMLCanvasElement) => {
        const pixels = element
          .getContext("2d")!
          .getImageData(0, 0, element.width, element.height).data;
        let colored = 0;
        for (let i = 0; i < pixels.length; i += 4)
          if (pixels[i] > 150 && pixels[i + 1] > 60 && pixels[i + 2] < 90)
            colored++;
        return colored;
      }),
    ).toBeGreaterThan(100);
    expect(
      await page.evaluate(() => document.documentElement.scrollWidth),
    ).toBeLessThanOrEqual(width);
    await page.screenshot({
      path: `logs/portfolio-screenshots/options-${width}.png`,
    });
  }
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.getByLabel("Dealer sign convention").selectOption("NEUTRAL");
  const changed = page.waitForResponse(
    (r) =>
      r.url().endsWith("/options/calculate") && r.request().method() === "POST",
  );
  await page
    .getByRole("button", { name: "Calculate & Save", exact: true })
    .click();
  expect((await (await changed).json()).summary.net_gex).toBeGreaterThan(0);
  await page.getByRole("tab", { name: "GREEKS", exact: true }).click();
  await expect(page.getByLabel("standard-greeks table")).toContainText(
    "CALCULATED",
  );
  await page.getByRole("tab", { name: "VOLATILITY", exact: true }).click();
  await expect(
    page.getByLabel("Implied volatility surface").locator("canvas"),
  ).toBeVisible();
  await page.getByRole("tab", { name: "PAYOFF", exact: true }).click();
  await page
    .getByRole("button", { name: "Add hypothetical option leg", exact: true })
    .click();
  await page.getByLabel("Leg 1 quantity").fill("-2");
  const payoff = page.waitForResponse(
    (r) =>
      r.url().endsWith("/options/calculate") && r.request().method() === "POST",
  );
  await page
    .getByRole("button", { name: "Calculate & Save", exact: true })
    .click();
  const position = (await (await payoff).json()).positions;
  expect(position.payoff).toHaveLength(101);
  expect(position.totals.gamma).toBeLessThan(0);
  const after = await (
    await request.get("/backend/api/v1/portfolios/KNK_MAIN/summary")
  ).json();
  expect(after.transactions).toEqual(before.transactions);
  expect(after.portfolio.nav).toBe(before.portfolio.nav);
  const runs = await (
    await request.get("/backend/api/v1/terminal/runs?kind=options")
  ).json();
  await page.reload();
  await expect(page.getByLabel("Saved options analysis")).toContainText(
    runs.items[0].id.slice(0, 8),
  );
  expect(errors).toEqual([]);
});
