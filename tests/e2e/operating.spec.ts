import { expect, test } from "@playwright/test";
import { mkdirSync } from "node:fs";

test("portfolio operating desks render across desktop and mobile", async ({
  page,
  request,
}) => {
  test.setTimeout(180000);
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  mkdirSync("logs/portfolio-screenshots", { recursive: true });
  for (const [width, height] of [
    [1366, 768],
    [1440, 900],
    [1920, 1080],
    [2560, 1440],
    [390, 844],
  ]) {
    await page.setViewportSize({ width, height });
    await page.goto("/overview");
    await expect(
      page.getByRole("heading", { name: "Portfolio Command Centre" }),
    ).toBeVisible();
    await expect(page.getByLabel("main-holdings table")).toContainText("AAPL");
    await expect(page.locator(".loading-state")).toHaveCount(0);
    for (const id of ["main-trades", "main-strategies"]) {
      await expect(
        page.getByLabel(`${id} table`).locator("tbody tr"),
      ).not.toHaveCount(0);
    }
    await expect(
      page.locator('.operation-health [aria-busy="true"]'),
    ).toHaveCount(0);
    await expect(
      page.locator(".error-state, .operation-notice[role=alert]"),
    ).toHaveCount(0);
    await expect(page.locator(".chart canvas").first()).toBeVisible();
    expect(
      await page.evaluate(() => document.documentElement.scrollWidth),
    ).toBeLessThanOrEqual(width);
    expect(
      await page
        .locator(".operating-ribbon strong")
        .evaluateAll((nodes) =>
          nodes.every((n) => n.scrollWidth <= n.clientWidth + 1),
        ),
    ).toBe(true);
    const colors = await page
      .locator(".chart canvas")
      .first()
      .evaluate((node) => {
        const canvas = node as HTMLCanvasElement;
        const pixels = canvas
          .getContext("2d")!
          .getImageData(0, 0, canvas.width, canvas.height).data;
        const colors = new Set<string>();
        for (let i = 0; i < pixels.length; i += 16)
          colors.add([pixels[i], pixels[i + 1], pixels[i + 2]].join(","));
        return colors.size;
      });
    expect(colors).toBeGreaterThan(5);
    await page.screenshot({
      path: "logs/portfolio-screenshots/overview-" + width + ".png",
    });
  }
  await page.setViewportSize({ width: 1440, height: 900 });
  for (const [route, heading] of [
    ["/data-drop", "External Data Drop"],
    ["/trade-monitor", "Trade Monitor"],
    ["/risk-trade-monitor", "Risk & Trade Monitor"],
    ["/equity", "Equity Research Desk"],
    ["/quant-dashboard", "Quant Research Monitor"],
    ["/edge-lab", "Candidate Edge Lab"],
    ["/broker-monitor", "Paper Broker Monitor"],
  ]) {
    await page.goto(route);
    await expect(
      page.getByRole("heading", { name: heading, exact: true }),
    ).toBeVisible();
    await expect(page.locator(".loading-state")).toHaveCount(0);
    await expect(page.locator(".error-state")).toHaveCount(0);
    await page.screenshot({
      path: "logs/portfolio-screenshots" + route + ".png",
    });
  }
  expect(errors).toEqual([]);
  // Select a genuinely short source in the isolated test database. The unpinned
  // universe also contains valid older history and need not be insufficient.
  const quotesResponse = await request.get("/backend/api/v1/quotes");
  expect(quotesResponse.ok()).toBe(true);
  const quotes: { items: { symbol: string; asset_class: string }[] } =
    await quotesResponse.json();
  const previous: { path: string; rule: Record<string, unknown> }[] = [];
  try {
    for (const quote of quotes.items.filter((item) =>
      ["Equity", "ETF"].includes(item.asset_class),
    )) {
      const path =
        "/backend/api/v1/operations/sources/" +
        encodeURIComponent(quote.symbol);
      const response = await request.get(path);
      expect(response.ok()).toBe(true);
      const { rule } = await response.json();
      previous.push({ path, rule });
      const saved = await request.post(path, {
        data: {
          ...rule,
          preferred_source: "KnK Demo / coherent daily series",
          reason: "Isolated browser short-history fixture",
        },
      });
      expect(saved.ok()).toBe(true);
    }
    expect(previous.length).toBeGreaterThan(1);
    await page.goto("/factor-lab");
    const factorResponse = page.waitForResponse((response) =>
      response.url().includes("/api/v1/factors?lookback=252&"),
    );
    await page.getByLabel("Factor horizon").selectOption("252");
    const response = await factorResponse;
    expect(response.ok()).toBe(true);
    expect(await response.json()).toMatchObject({
      lookback: 252,
      quality: "INSUFFICIENT DATA",
      items: [],
    });
    await expect(
      page.getByText("Requested factor lookback exceeds available history"),
    ).toBeVisible();
  } finally {
    for (const { path, rule } of previous) {
      const restored = await request.post(path, { data: rule });
      expect(restored.ok()).toBe(true);
    }
  }
  expect(errors).toEqual([]);
});

test("approved file changes source and survives reload; ledger review persists", async ({
  page,
  request,
}) => {
  test.setTimeout(120000);
  await page.goto("/data-drop");
  await page.getByLabel("Upload data files").setInputFiles({
    name: "AAPL_2026-09-04_prices.csv",
    mimeType: "text/csv",
    buffer: Buffer.from(
      "Date,Open,High,Low,Close,Volume\n2026-09-04,216,220,215,218,1000\n",
    ),
  });
  await expect(page.getByLabel("data-drop-inbox table")).toContainText(
    "MAPPING_REQUIRED",
  );
  await page.getByRole("tab", { name: "Mapping", exact: true }).click();
  await page
    .getByLabel("Mapping profile")
    .selectOption({ label: "KOYFIN_PRICE_HISTORY / v1" });
  await page.getByRole("button", { name: "Validate mapping" }).click();
  await expect(page.getByLabel("data-drop-inbox table")).toContainText(
    "AWAITING_APPROVAL",
  );
  await page
    .getByLabel("Licence / permitted use")
    .fill("Private QA fixture / not Koyfin licensed data");
  await page.getByLabel("Approve this validated version").check();
  await page.getByRole("button", { name: "Import approved file" }).click();
  await expect(page.getByLabel("data-drop-inbox table")).toContainText(
    "IMPORTED",
  );
  await page.reload();
  await expect(page.getByLabel("data-drop-inbox table")).toContainText(
    "IMPORTED",
  );
  const portfolio = await (
    await request.get("/backend/api/v1/operations/portfolio")
  ).json();
  const apple = portfolio.positions.find(
    (p: { symbol: string }) => p.symbol === "AAPL",
  );
  expect(Number(apple.market_price)).toBe(218);
  expect(apple.source).toBe("KOYFIN FILE");
  await page.goto("/trade-monitor");
  await page
    .getByRole("button", { name: "Record transaction", exact: true })
    .click();
  const dialog = page.getByRole("dialog", {
    name: "Record ledger transaction",
  });
  await dialog.getByLabel("Price", { exact: true }).fill("218");
  await dialog.getByLabel("Rationale / notes").fill("QA manual ledger review");
  await dialog
    .getByRole("button", { name: "Record transaction", exact: true })
    .click();
  await expect(dialog).toBeHidden();
  await expect(page.getByLabel("trade-monitor table")).toContainText("MANUAL");
  await page.getByLabel("Filter trade-monitor").fill("MANUAL");
  await page
    .getByLabel("trade-monitor table")
    .getByText("MANUAL", { exact: true })
    .first()
    .click();
  await page
    .getByLabel("Review note")
    .fill("Reconciled recorded fill and cash.");
  await page
    .getByRole("button", { name: "Record review", exact: true })
    .click();
  await expect(page.getByLabel("trade-monitor table")).toContainText(
    "REVIEWED",
  );
  const report = await request.get("/backend/api/v1/operations/export");
  expect(report.ok()).toBeTruthy();
  expect((await report.body()).subarray(0, 2).toString()).toBe("PK");
});
