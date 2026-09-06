import { expect, test } from "@playwright/test";

test("connection controls persist without network claims and fit responsive terminal", async ({
  page,
  request,
}) => {
  test.setTimeout(120000);
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/settings/connections");
  const fred = page.getByRole("article", {
    name: "FRED connection",
    exact: true,
  });
  await expect(fred).toContainText("NOT_CONFIGURED");
  await expect(
    page.getByRole("button", { name: "Test FRED connection", exact: true }),
  ).toBeDisabled();
  const figi = page.getByLabel("Enable OpenFIGI", { exact: true });
  await figi.check();
  await expect(
    page.getByRole("article", { name: "OpenFIGI connection", exact: true }),
  ).toContainText("NOT_TESTED");
  await page
    .getByRole("button", { name: "Revoke OpenFIGI local access" })
    .click();
  await expect(figi).not.toBeChecked();
  await page.reload();
  await expect(
    page.getByRole("article", { name: "OpenFIGI connection", exact: true }),
  ).toContainText("REVOKED");
  for (const width of [1440, 390]) {
    await page.setViewportSize({ width, height: 1000 });
    const hide = page.getByRole("button", {
      name: "Hide inspector",
      exact: true,
    });
    if (await hide.isVisible()) await hide.click();
    await fred.scrollIntoViewIfNeeded();
    expect(
      await page.evaluate(() => document.documentElement.scrollWidth),
    ).toBeLessThanOrEqual(width);
    expect(
      await page
        .locator(".connection-item")
        .evaluateAll((items) =>
          items.every((item) => item.scrollWidth <= item.clientWidth + 1),
        ),
    ).toBe(true);
    await page.screenshot({
      path: `logs/portfolio-screenshots/connections-${width}.png`,
    });
  }
  await page.getByRole("tab", { name: "FILINGS", exact: true }).click();
  await expect(page.getByLabel("sec-filings table")).toBeVisible();
  await page.getByRole("tab", { name: "IDENTIFIERS", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Lookup FIGI", exact: true }),
  ).toBeDisabled();
  const status = await (
    await request.get("/backend/api/v1/connections")
  ).json();
  expect(
    status.items.find((row: { key: string }) => row.key === "openfigi")
      .last_success,
  ).toBeNull();
  expect(errors).toEqual([]);
});
