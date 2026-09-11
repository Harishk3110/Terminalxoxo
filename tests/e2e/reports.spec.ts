import { expect, test } from "@playwright/test";

test("owned report job produces downloadable workbook PDF and deck", async ({
  page,
  request,
}) => {
  test.setTimeout(150000);
  await page.goto("/excel-studio");
  await expect(
    page.getByRole("heading", { name: "Excel Studio", exact: true }),
  ).toBeVisible();
  await page.getByLabel("Report valuation date").fill("2026-09-04");
  for (const format of ["xlsx", "pdf", "pptx"]) {
    await page.getByLabel("Report format").selectOption(format);
    const submission = page.waitForResponse(
      (response) =>
        response.url().endsWith("/report-jobs") &&
        response.request().method() === "POST",
    );
    await page
      .getByRole("button", {
        name:
          format === "xlsx"
            ? "Generate workbook"
            : `Generate ${format.toUpperCase()}`,
      })
      .click();
    const response = await submission;
    expect(response.status()).toBe(202);
    const job = await response.json();
    await expect
      .poll(
        async () =>
          (
            await (
              await request.get(`/backend/api/v1/report-jobs/${job.id}`)
            ).json()
          ).status,
        { timeout: 60000 },
      )
      .toBe("SUCCEEDED");
    const result = await (
      await request.get(`/backend/api/v1/report-jobs/${job.id}`)
    ).json();
    const downloaded = await request.get(`/backend${result.download_url}`);
    expect(downloaded.ok()).toBeTruthy();
    expect((await downloaded.body()).length).toBeGreaterThan(1000);
    await expect(
      page.getByRole("link", {
        name: `Download ${format.toUpperCase()}`,
        exact: true,
      }),
    ).toBeVisible();
  }
  await page.reload();
  await expect(
    page.getByRole("link", { name: "Download PPTX", exact: true }),
  ).toBeVisible();
  await expect(page.getByLabel("Report format")).toHaveValue("pptx");
  await expect(page.getByLabel("Report valuation date")).toHaveValue(
    "2026-09-04",
  );
  for (const width of [1440, 390]) {
    await page.setViewportSize({ width, height: 900 });
    if (width === 390)
      await expect(page.getByTestId("context-inspector")).toBeHidden();
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    ).toBeTruthy();
    await page.screenshot({
      path: `logs/reports-${width}.png`,
      fullPage: true,
    });
  }
  await page.goto("/functions/deck");
  await expect(
    page.getByRole("heading", { name: "Deck Builder", exact: true }),
  ).toBeVisible();
});
