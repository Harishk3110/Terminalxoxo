import { expect, test } from "@playwright/test";

test("approved fundamental import reaches FIN with immutable metric lineage", async ({
  page,
  request,
}) => {
  test.setTimeout(120000);
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/data-drop");
  const uploaded = page.waitForResponse(
    (response) =>
      response.url().endsWith("/api/v1/data-drop/files") &&
      response.request().method() === "POST",
  );
  const fields = {
    revenue: 100,
    net_income: 15,
    ebit: 25,
    depreciation: 3,
    capex: 5,
    free_cash_flow: 30,
    cash: 20,
    debt: 12,
    shares: 10,
  };
  await page.getByLabel("Upload data files").setInputFiles({
    name: "NVDA_fictional_fundamentals.csv",
    mimeType: "text/csv",
    buffer: Buffer.from(
      "Symbol,Period,Metric,Value,Frequency,Unit,Scale,Actual Estimate,Report Date\n" +
        Object.entries(fields)
          .map(
            ([metric, value]) =>
              `NVDA,2025,${metric},${value},ANNUAL,USD,1000000,ACTUAL,2026-02-01`,
          )
          .join("\n") +
        "\n",
    ),
  });
  const uploadResponse = await uploaded;
  expect(uploadResponse.ok()).toBe(true);
  const file: { id: string } = await uploadResponse.json();
  await expect(page.getByLabel("data-drop-inbox table")).toContainText(
    "MAPPING_REQUIRED",
  );
  await page.getByRole("tab", { name: "Mapping", exact: true }).click();
  await page
    .getByLabel("Mapping profile")
    .selectOption({ label: "GENERIC_FUNDAMENTALS_LONG / v1" });
  await page.getByRole("button", { name: "Validate mapping" }).click();
  await expect(page.getByLabel("data-drop-inbox table")).toContainText(
    "AWAITING_APPROVAL",
  );
  await page
    .getByLabel("Licence / permitted use")
    .fill("Fictional browser test only; not company filings");
  await page.getByLabel("Approve this validated version").check();
  const imported = page.waitForResponse(
    (response) =>
      response.url().endsWith(`/api/v1/data-drop/files/${file.id}/import`) &&
      response.request().method() === "POST",
  );
  await page.getByRole("button", { name: "Import approved file" }).click();
  const importResponse = await imported;
  expect(importResponse.ok()).toBe(true);
  const receipt: { state: string; dataset_version_id: string } =
    await importResponse.json();
  expect(receipt.state).toBe("IMPORTED");
  expect(receipt.dataset_version_id).toBeTruthy();
  await page.goto("/financials/NVDA");
  await expect(page.getByLabel("financial-Income table")).toContainText(
    "revenue",
  );
  await expect(page.locator(".loading-state, .error-state")).toHaveCount(0);
  await page.reload();
  await expect(page.getByLabel("financial-Income table")).toContainText("100");
  const response = await request.get("/backend/api/v1/equity/NVDA/financials");
  expect(response.ok()).toBe(true);
  const financial: {
    quality: string;
    items: {
      revenue: number;
      cash: number;
      shares: number;
      metric_sources: Record<string, { version_id: string }>;
    }[];
    lineage: { version_id: string; file_id: string }[];
    warnings: string[];
  } = await response.json();
  expect(financial.quality).toBe("FILE IMPORT");
  expect(financial.items).toHaveLength(1);
  expect(financial.items[0].revenue).toBe(100);
  expect(financial.items[0].cash).toBe(20);
  expect(financial.items[0].shares).toBe(10);
  expect(financial.items[0].metric_sources.revenue.version_id).toBe(
    receipt.dataset_version_id,
  );
  expect(
    financial.lineage.every(
      (source) =>
        source.version_id === receipt.dataset_version_id &&
        source.file_id === file.id,
    ),
  ).toBe(true);
  expect(
    financial.warnings.some((warning) =>
      warning.includes("not independently verified"),
    ),
  ).toBe(true);
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
    await page.screenshot({
      path: `logs/portfolio-screenshots/financial-import-${width}.png`,
    });
  }
  expect(errors).toEqual([]);
});
