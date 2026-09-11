import { expect, test } from "@playwright/test";

test("saved alpha, model and Monte Carlo runs render private quant views", async ({
  page,
  request,
}) => {
  test.setTimeout(300000);
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  const queued = await request.post("/backend/api/v1/terminal/runs", {
    data: {
      kind: "backtest",
      name: "Alpha browser fixture",
      parameters: {
        symbol: "SPY",
        source_mode: "DEMO_RESEARCH",
        strategy: "SMA",
        start: "2025-01-01",
      },
    },
  });
  expect(queued.status(), await queued.text()).toBe(202);
  const source = await queued.json();
  await expect
    .poll(
      async () => {
        const run = await (
          await request.get(`/backend/api/v1/terminal/runs/${source.id}`)
        ).json();
        return run.status;
      },
      { timeout: 120000 },
    )
    .toBe("SUCCEEDED");
  await page.goto("/alpha");
  await page.getByLabel("Alpha return source").selectOption(source.id);
  const synced = page.waitForResponse((response) => {
    if (
      !response.url().includes("/api/v1/workspaces/") ||
      response.request().method() !== "POST"
    )
      return false;
    const states =
      response.request().postDataJSON()?.configuration?.tabStates ?? {};
    return Object.values(states).some(
      (state) => !!(state as Record<string, unknown>)["alpha-run"],
    );
  });
  await page
    .getByRole("button", { name: "Calculate Alpha", exact: true })
    .click();
  await expect(page.getByLabel("alpha-coefficients table")).toContainText(
    "market_excess",
    { timeout: 30000 },
  );
  expect((await synced).ok()).toBeTruthy();
  await page.reload();
  await expect(page.getByLabel("alpha-coefficients table")).toContainText(
    "market_excess",
  );
  await expect(page.getByText(/server sync failed/)).toHaveCount(0);
  await page.goto("/model-lab");
  await page.getByLabel("Model source").selectOption("DEMO_RESEARCH");
  await page.getByRole("button", { name: "Train model", exact: true }).click();
  await expect(page.getByLabel("model-partitions table")).toContainText(
    "TEST",
    { timeout: 120000 },
  );
  await expect(page.getByLabel("model-cost-backtests table")).toContainText(
    "VALIDATION",
  );
  const runs = await (
    await request.get("/backend/api/v1/terminal/runs?kind=model")
  ).json();
  expect(runs.items[0].status).toBe("SUCCEEDED");
  expect(runs.items[0].result.inputs.content_hash).toHaveLength(64);
  expect(runs.items[0].result.artifact.content_hash).toHaveLength(64);
  expect(
    (
      await request.get(
        `/backend/api/v1/terminal/runs/${runs.items[0].id}/model-artifact`,
      )
    ).ok(),
  ).toBeTruthy();
  for (const width of [1440, 390]) {
    await page.setViewportSize({ width, height: 1000 });
    const hide = page.getByRole("button", {
      name: "Hide inspector",
      exact: true,
    });
    if (await hide.isVisible()) await hide.click();
    expect(
      await page.evaluate(() => document.documentElement.scrollWidth),
    ).toBeLessThanOrEqual(width);
    const grid = await page.locator(".model-grid").boundingBox();
    const costs = await page
      .getByRole("region", {
        name: "Held-out cost-adjusted trading diagnostics",
        exact: true,
      })
      .boundingBox();
    expect(grid!.y + grid!.height).toBeLessThanOrEqual(costs!.y);
    const chart = await page.getByLabel("Model predictions").boundingBox();
    expect(chart!.height).toBeGreaterThan(150);
    await page
      .locator(".model-grid > section")
      .first()
      .scrollIntoViewIfNeeded();
    await page.screenshot({
      path: `logs/portfolio-screenshots/model-${width}.png`,
    });
  }
  await page.goto("/monte-carlo");
  await page.getByLabel("Monte Carlo return source").selectOption(source.id);
  await page.getByLabel("Monte Carlo paths").fill("200");
  await page.getByLabel("Monte Carlo horizon").fill("30");
  await page
    .getByRole("button", { name: "Run simulation", exact: true })
    .click();
  await expect(page.locator(".page-toolbar")).toContainText("SUCCEEDED", {
    timeout: 30000,
  });
  await page.screenshot({
    path: "logs/portfolio-screenshots/monte-carlo-390.png",
  });
  await page.goto("/factor-lab");
  await page.getByLabel("Factor type").selectOption("VOLATILITY");
  await page.getByLabel("Factor horizon", { exact: true }).selectOption("21");
  await expect(page.getByLabel("factor-values table")).toContainText("IWM");
  expect(errors).toEqual([]);
});

test("multi-security backtest persists costs, FX and next-open fills", async ({
  page,
  request,
}) => {
  test.setTimeout(180000);
  await page.goto("/backtests");
  await page.getByLabel("Backtest source").selectOption("DEMO_RESEARCH");
  await page.getByLabel("Start", { exact: true }).fill("2025-01-01");
  await page.getByLabel("Backtest additional securities").fill("AAPL,MSFT");
  await page.getByLabel("Backtest strategy").selectOption("MOMENTUM");
  const queued = page.waitForResponse(
    (response) =>
      response.url().endsWith("/api/v1/terminal/runs") &&
      response.request().method() === "POST",
  );
  await page.getByRole("button", { name: "Run backtest", exact: true }).click();
  const response = await queued;
  expect(response.status(), await response.text()).toBe(202);
  const submitted = await response.json();
  await expect
    .poll(
      async () =>
        (
          await (
            await request.get(`/backend/api/v1/terminal/runs/${submitted.id}`)
          ).json()
        ).status,
      { timeout: 120000 },
    )
    .toBe("SUCCEEDED");
  await expect(page.locator(".page-toolbar")).toContainText("SUCCEEDED", {
    timeout: 120000,
  });
  const finished = await (
    await request.get(`/backend/api/v1/terminal/runs/${submitted.id}`)
  ).json();
  const result = finished.result;
  expect(Object.keys(result.inputs)).toHaveLength(3);
  expect(result.currency).toBe("SGD");
  expect(result.fills.length).toBeGreaterThan(0);
  expect(result.gross_equity_curve.length).toBe(result.equity_curve.length);
  expect(result.fills[0].date).not.toBe(result.target_weights[0].date);
  await page.screenshot({ path: "logs/portfolio-screenshots/backtest-m4.png" });
});
