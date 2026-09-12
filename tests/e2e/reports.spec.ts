import { expect, test } from "@playwright/test";
import { completedRun } from "./analytical-fixtures";

test("completed Monte Carlo analysis produces an owned quant deck", async ({
  page,
  request,
}) => {
  test.setTimeout(150000);
  const backtest = await completedRun(request, "backtest");
  const simulation = await request.post("/backend/api/v1/terminal/runs", {
    data: {
      kind: "monte_carlo",
      name: "Deck source simulation",
      parameters: {
        backtest_run_id: backtest.id,
        settings: { paths: 100, horizon: 5, seed: 3110 },
      },
    },
  });
  expect(simulation.status(), await simulation.text()).toBe(202);
  const run = await simulation.json();
  await expect
    .poll(
      async () => {
        const response = await request.get(
          `/backend/api/v1/terminal/runs/${run.id}`,
        );
        expect(response.ok()).toBe(true);
        return (await response.json()).status;
      },
      { timeout: 60000 },
    )
    .toBe("SUCCEEDED");
  await page.goto("/deck-builder");
  await page.getByLabel("Report type").selectOption("quant");
  await expect(
    page
      .getByLabel("Report analysis")
      .getByRole("option", { name: /Deck source simulation/ }),
  ).toHaveCount(1);
  await page.getByLabel("Report analysis").selectOption(run.id);
  const submission = page.waitForResponse(
    (response) =>
      response.url().endsWith("/report-jobs") &&
      response.request().method() === "POST",
  );
  await page
    .getByRole("button", { name: "Generate PPTX", exact: true })
    .click();
  const submitted = await submission;
  expect(submitted.status(), await submitted.text()).toBe(202);
  const job = await submitted.json();
  await expect
    .poll(
      async () => {
        const response = await request.get(
          `/backend/api/v1/report-jobs/${job.id}`,
        );
        expect(response.ok()).toBe(true);
        return (await response.json()).status;
      },
      { timeout: 60000 },
    )
    .toBe("SUCCEEDED");
  await expect(
    page.getByRole("link", { name: "Download PPTX", exact: true }),
  ).toBeVisible();
  const sourceResponse = await request.get(
    `/backend/api/v1/report-jobs/${job.id}/source`,
  );
  expect(sourceResponse.ok()).toBe(true);
  const source = await sourceResponse.json();
  expect(source.references.analysis_run_id).toBe(run.id);
  expect(source.payload.inputs.backtest_run_id).toBe(backtest.id);
  expect(source.payload.settings.seed).toBe(3110);
  const download = await request.get(
    `/backend/api/v1/report-jobs/${job.id}/download`,
  );
  expect(download.ok()).toBe(true);
  expect((await download.body()).subarray(0, 2).toString()).toBe("PK");
});

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
