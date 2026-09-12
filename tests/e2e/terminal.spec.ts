import { expect, test, type Page } from "@playwright/test";
import { mkdirSync } from "node:fs";
import {
  completedRun,
  DEMO_VALUATION_DATE,
  populateVisualAnalysis,
} from "./analytical-fixtures";

async function command(page: Page, text: string, newTab = false) {
  await page
    .getByRole("button", { name: "Search securities and functions" })
    .click();
  await page.getByRole("combobox", { name: "Command", exact: true }).fill(text);
  await page
    .getByRole("combobox", { name: "Command", exact: true })
    .press(newTab ? "Control+Enter" : "Enter");
}

test("command navigation, security context, workspaces and keyboard controls", async ({
  page,
}) => {
  await page.goto("/overview");
  await expect(page.getByTestId("terminal-shell")).toBeVisible();
  await command(page, "AAPL FIN");
  await expect(
    page.getByRole("heading", { name: "AAPL / Financial Analysis" }),
  ).toBeVisible();
  await command(page, "MSFT GP", true);
  await expect(page.getByTestId("security-context")).toContainText("MSFT");
  await expect(
    page.getByRole("tab", { name: "AAPL FIN", exact: true }),
  ).toBeVisible();
  await page.getByRole("tab", { name: "AAPL FIN", exact: true }).click();
  await expect(page.getByTestId("security-context")).toContainText("AAPL");
  await page.getByRole("button", { name: "Manage workspaces" }).click();
  await page.getByLabel("Workspace name").fill("QA Workspace");
  await page.getByRole("button", { name: "Duplicate", exact: true }).click();
  await expect(
    page.getByRole("combobox", { name: "Workspace", exact: true }),
  ).toContainText("QA Workspace");
  await page.reload();
  await expect(
    page.getByRole("tab", { name: "AAPL FIN", exact: true }),
  ).toBeVisible();
  await page.keyboard.press("Control+k");
  await expect(
    page.getByRole("dialog", { name: "Command palette" }),
  ).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(
    page.getByRole("dialog", { name: "Command palette" }),
  ).toBeHidden();
});

test("editable stress inputs produce persisted reconciled results and exports", async ({
  page,
  request,
}) => {
  test.setTimeout(90000);
  await page.goto("/stress-tests");
  await expect(page.getByTestId("terminal-shell")).toBeVisible();
  await page
    .getByLabel("Stress valuation date", { exact: true })
    .fill(DEMO_VALUATION_DATE);
  const firstSubmission = page.waitForResponse(
    (response) =>
      response.url().endsWith("/api/v1/terminal/runs") &&
      response.request().method() === "POST",
  );
  await page.getByRole("button", { name: "Run Scenario", exact: true }).click();
  const firstAccepted = await firstSubmission;
  expect(firstAccepted.status(), await firstAccepted.text()).toBe(202);
  const firstQueued = await firstAccepted.json();
  expect(firstQueued.kind).toBe("stress");
  expect(firstQueued.parameters.equity_shock).toBe(-10);
  await expect
    .poll(
      async () => {
        const response = await request.get(
          `/backend/api/v1/terminal/runs/${firstQueued.id}`,
        );
        expect(response.ok()).toBeTruthy();
        return (await response.json()).status;
      },
      { timeout: 60000 },
    )
    .toBe("SUCCEEDED");
  const before = await (
    await request.get(`/backend/api/v1/terminal/runs/${firstQueued.id}`)
  ).json();
  await expect(page.getByTestId("context-inspector")).toContainText(before.id);
  await expect(page.getByTestId("context-inspector")).toContainText(
    "SUCCEEDED",
  );
  await page.getByLabel("Equity shock", { exact: true }).fill("-20");
  const secondSubmission = page.waitForResponse(
    (response) =>
      response.url().endsWith("/api/v1/terminal/runs") &&
      response.request().method() === "POST",
  );
  await page.getByRole("button", { name: "Run Scenario", exact: true }).click();
  const secondAccepted = await secondSubmission;
  expect(secondAccepted.status(), await secondAccepted.text()).toBe(202);
  const secondQueued = await secondAccepted.json();
  expect(secondQueued.kind).toBe("stress");
  expect(secondQueued.parameters.equity_shock).toBe(-20);
  expect(secondQueued.id).not.toBe(before.id);
  await expect
    .poll(
      async () => {
        const response = await request.get(
          `/backend/api/v1/terminal/runs/${secondQueued.id}`,
        );
        expect(response.ok()).toBeTruthy();
        return (await response.json()).status;
      },
      { timeout: 60000 },
    )
    .toBe("SUCCEEDED");
  const after = await (
    await request.get(`/backend/api/v1/terminal/runs/${secondQueued.id}`)
  ).json();
  await expect(page.getByTestId("context-inspector")).toContainText(after.id);
  await expect(page.getByTestId("context-inspector")).toContainText(
    "SUCCEEDED",
  );
  expect(after.result.loss).not.toBe(before.result.loss);
  expect(after.result.valuation_date).toBe(DEMO_VALUATION_DATE);
  expect(after.result.post_nav).toBeCloseTo(
    after.result.pre_nav + after.result.loss,
    2,
  );
  expect(after.history.map((h: { state: string }) => h.state)).toEqual([
    "QUEUED",
    "RUNNING",
    "SUCCEEDED",
  ]);
  const report = await (
    await request.get(`/backend/api/v1/terminal/runs/${after.id}/export`)
  ).json();
  const file = await request.get(`/backend${report.download_url}`);
  expect(file.ok()).toBeTruthy();
  expect((await file.body()).subarray(0, 2).toString()).toBe("PK");
});

test("manual ledger, upload validation and backtest lifecycle", async ({
  page,
  request,
}) => {
  test.setTimeout(120000);
  await page.goto("/portfolio");
  await page.getByRole("button", { name: "Add manual transaction" }).click();
  await page.getByLabel("Transaction price", { exact: true }).fill("200");
  await page.getByRole("button", { name: "Record transaction" }).click();
  await expect(
    page.getByRole("dialog", { name: "Manual transaction" }),
  ).toBeHidden();
  await page.getByRole("tab", { name: "Transactions", exact: true }).click();
  await expect(page.getByLabel("transactions table")).toContainText("MANUAL");
  await command(page, "DROP");
  const csv =
    "Date,Open,High,Low,Close,Volume\n" +
    Array.from(
      { length: 240 },
      (_, i) =>
        `${new Date(Date.UTC(2024, 0, i + 1)).toISOString().slice(0, 10)},${100 + 0.1 * i + 10 * Math.sin(i / 8)},${101 + 0.1 * i + 10 * Math.sin(i / 8)},${99 + 0.1 * i + 10 * Math.sin(i / 8)},${100 + 0.1 * i + 10 * Math.sin(i / 8)},10000`,
    ).join("\n");
  await page.locator("input[type=file]").setInputFiles({
    name: "QQQ_2024-08-27_prices.csv",
    mimeType: "text/csv",
    buffer: Buffer.from(csv),
  });
  await expect(page.getByLabel("Dataset name")).toBeVisible();
  await page.getByRole("tab", { name: "Mapping", exact: true }).click();
  await page
    .getByLabel("Mapping profile")
    .selectOption({ label: "KOYFIN_PRICE_HISTORY / v1" });
  await page
    .getByRole("button", { name: "Validate mapping", exact: true })
    .click();
  await expect(page.getByLabel("data-drop-inbox table")).toContainText(
    "AWAITING_APPROVAL",
  );
  await page
    .getByLabel("Licence / permitted use")
    .fill("Self-created QA fixture");
  await page.getByLabel("Approve this validated version").check();
  await page
    .getByRole("button", { name: "Import approved file", exact: true })
    .click();
  await expect(page.getByLabel("data-drop-inbox table")).toContainText(
    "IMPORTED",
  );
  await page
    .getByRole("button", { name: "Backtest dataset", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Backtest Lab" }),
  ).toBeVisible();
  await expect(
    page.getByLabel("Backtest security", { exact: true }),
  ).toHaveValue("QQQ");
  await expect(page.getByTestId("context-inspector")).not.toContainText(
    "SUCCEEDED",
  );
  await page
    .getByLabel("Backtest currency", { exact: true })
    .selectOption("USD");
  const submission = page.waitForResponse(
    (response) =>
      response.url().endsWith("/api/v1/terminal/runs") &&
      response.request().method() === "POST",
  );
  await page.getByRole("button", { name: "Run backtest", exact: true }).click();
  const accepted = await submission;
  expect(accepted.status(), await accepted.text()).toBe(202);
  const queued = await accepted.json();
  expect(queued.parameters.symbol).toBe("QQQ");
  expect(queued.parameters.base_currency).toBe("USD");
  expect(queued.parameters.dataset_version_id).toBeTruthy();
  await expect
    .poll(
      async () =>
        (
          await (
            await request.get(`/backend/api/v1/terminal/runs/${queued.id}`)
          ).json()
        ).status,
      { timeout: 60000 },
    )
    .toBe("SUCCEEDED");
  await expect(page.getByTestId("context-inspector")).toContainText(
    "SUCCEEDED",
  );
  const completed = await (
    await request.get(`/backend/api/v1/terminal/runs/${queued.id}`)
  ).json();
  expect(completed.parameters.symbol).toBe("QQQ");
  expect(completed.id).toBe(queued.id);
});

test("table controls, security context menu and resized inspector", async ({
  page,
}) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/portfolio");
  await page.getByRole("tab", { name: "Holdings", exact: true }).click();
  await page.getByLabel("Filter holdings").fill("AAPL");
  await expect(page.getByLabel("holdings table")).toContainText("AAPL");
  await page
    .getByRole("button", { name: "Columns holdings", exact: true })
    .click();
  await page.getByLabel("Pin first column").check();
  await page.getByRole("button", { name: "Save view", exact: true }).click();
  await page
    .getByLabel("holdings table")
    .getByText("AAPL", { exact: true })
    .click({ button: "right" });
  await expect(
    page.getByRole("menu", { name: "AAPL functions" }),
  ).toBeVisible();
  await page
    .getByRole("menuitem", { name: "FIN Financial Statements" })
    .click();
  await expect(
    page.getByRole("heading", { name: "AAPL / Financial Analysis" }),
  ).toBeVisible();
  const handle = page.locator("[data-panel-resize-handle-id]");
  const box = await handle.boundingBox();
  const before = (await page.getByTestId("context-inspector").boundingBox())!
    .width;
  await page.mouse.move(box!.x + 2, box!.y + 100);
  await page.mouse.down();
  await page.mouse.move(box!.x - 60, box!.y + 100);
  await page.mouse.up();
  expect(
    (await page.getByTestId("context-inspector").boundingBox())!.width,
  ).toBeGreaterThan(before + 30);
  await command(page, "EXCEL");
  await page
    .getByRole("button", { name: "Generate workbook", exact: true })
    .click();
  await expect(
    page.getByRole("link", { name: "Download XLSX", exact: true }),
  ).toBeVisible();
});

test("provider states and private session login", async ({ page, context }) => {
  await context.clearCookies();
  await page.goto("/overview");
  await expect(page).toHaveURL(/\/login$/);
  await page
    .getByLabel("Email", { exact: true })
    .fill(process.env.PLAYWRIGHT_TEST_EMAIL!);
  await page
    .getByLabel("Password", { exact: true })
    .fill(process.env.PLAYWRIGHT_TEST_PASSWORD!);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await page.waitForURL("**/overview");
  await page.goto("/settings/security");
  await expect(page.getByText("AUTHENTICATED", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Sign out", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Sign in", exact: true }),
  ).toBeVisible();
  await page
    .getByLabel("Email", { exact: true })
    .fill(process.env.PLAYWRIGHT_TEST_EMAIL!);
  await page
    .getByLabel("Password", { exact: true })
    .fill(process.env.PLAYWRIGHT_TEST_PASSWORD!);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await page.waitForURL("**/overview");
  await command(page, "CONN");
  await expect(
    page.getByRole("heading", { name: "Connections / Data Sources" }),
  ).toBeVisible();
  await expect(
    page.getByText("NOT_CONFIGURED", { exact: true }).first(),
  ).toBeVisible();
  await command(page, "HEALTH");
  await expect(
    page.getByRole("heading", { name: "System Health / Observed State" }),
  ).toBeVisible();
});

for (const viewport of [
  { width: 1366, height: 768 },
  { width: 1440, height: 900 },
  { width: 1920, height: 1080 },
  { width: 2560, height: 1440 },
  { width: 390, height: 844 },
]) {
  test(`visual workspace ${viewport.width}x${viewport.height}`, async ({
    page,
    request,
  }) => {
    test.setTimeout(300000);
    await page.setViewportSize(viewport);
    const bootstrap = await (
      await request.get("/backend/api/v1/terminal/bootstrap")
    ).json();
    const stress = await completedRun(request, "stress");
    const backtest = await completedRun(request, "backtest");
    await page.addInitScript(
      ({ workspaceId, stress, backtest }) => {
        localStorage.setItem(
          "knk-terminal-v2",
          JSON.stringify({
            workspaceId,
            configuration: {
              tabs: [
                { id: "home", title: "HOME", route: "/overview" },
                {
                  id: "gp",
                  title: "AAPL GP",
                  route: "/chart/AAPL",
                  security: "AAPL",
                },
                { id: "risk", title: "PORT RISK", route: "/risk" },
                { id: "stress", title: "STRESS", route: "/stress-tests" },
                { id: "backtest", title: "BACKTEST", route: "/backtests" },
              ],
              securities: ["AAPL"],
              rail: true,
              inspector: true,
              sizes: [78, 22],
              tabStates: {
                stress: {
                  "stress-run": stress?.id,
                  scenario: { ...stress.parameters, name: stress.name },
                },
                backtest: {
                  "backtest-run": backtest?.id,
                  "backtest-config": backtest?.parameters,
                },
              },
            },
          }),
        );
      },
      { workspaceId: bootstrap.workspaces[0].id, stress, backtest },
    );
    for (const route of [
      "overview",
      "macro",
      "portfolio",
      "performance",
      "alpha",
      "equity",
      "quant-dashboard",
      "options/AAPL",
      "functions/gex",
      "risk-trade-monitor",
      "risk",
      "stress-tests",
      "hedge",
      "backtests",
      "data-drop",
      "data-catalogue",
      "excel-studio",
      "deck-builder",
      "system-health",
    ]) {
      const errors: string[] = [];
      const recordError = (error: Error) => errors.push(error.message);
      page.on("pageerror", recordError);
      await page.goto(`/${route}`);
      await expect(page.getByTestId("terminal-shell")).toBeVisible();
      await expect(page.locator(".loading-state")).toHaveCount(0);
      await expect(page.locator(".error-state")).toHaveCount(0);
      await populateVisualAnalysis(
        page,
        route,
        backtest.id,
        backtest.parameters.dataset_id,
      );
      await expect(page.locator(".error-state")).toHaveCount(0);
      await expect(page.locator(".page-toolbar h1")).toBeVisible();
      await expect(page.getByTestId("security-context")).toBeVisible();
      await expect(page.locator(".status-bar")).toBeVisible();
      if (route === "overview") {
        for (const id of ["main-holdings", "main-trades", "main-strategies"]) {
          await expect(
            page.getByLabel(`${id} table`).locator("tbody tr"),
          ).not.toHaveCount(0);
        }
        await expect(
          page.locator('.operation-health [aria-busy="true"]'),
        ).toHaveCount(0);
        await expect(page.locator(".operation-notice[role=alert]")).toHaveCount(
          0,
        );
      }
      if (
        [
          "overview",
          "macro",
          "performance",
          "risk",
          "stress-tests",
          "backtests",
        ].includes(route)
      )
        await expect(page.locator(".chart canvas")).not.toHaveCount(0);
      if (route === "hedge") {
        await expect(page.getByLabel("hedge-history table")).toBeVisible();
        await expect(
          page.getByLabel("Hedge target", { exact: true }),
        ).toBeVisible();
      }
      if (route === "risk-trade-monitor") {
        const contained = await page
          .locator(
            ".risk-trade-dashboard-grid > .terminal-panel, .risk-exposure-grid > .terminal-panel, .risk-policy-grid > .terminal-panel",
          )
          .evaluateAll((panels) =>
            panels.map((panel) => {
              const bounds = panel.getBoundingClientRect();
              const parent = panel.parentElement!.getBoundingClientRect();
              return (
                bounds.top >= parent.top - 1 &&
                bounds.bottom <= parent.bottom + 1
              );
            }),
          );
        expect(contained).toHaveLength(6);
        expect(contained.every(Boolean)).toBe(true);
      }
      const bounds = await page.evaluate(() => ({
        width: innerWidth,
        height: innerHeight,
        scrollWidth: document.documentElement.scrollWidth,
        scrollHeight: document.documentElement.scrollHeight,
        header: document
          .querySelector(".global-header")!
          .getBoundingClientRect().height,
      }));
      expect(bounds.scrollWidth).toBeLessThanOrEqual(bounds.width);
      expect(bounds.scrollHeight).toBeLessThanOrEqual(bounds.height);
      expect(bounds.header).toBe(40);
      if (viewport.width === 390)
        await expect(page.getByTestId("context-inspector")).toBeHidden();
      expect(errors).toEqual([]);
      const canvases = await page
        .locator(".chart canvas")
        .evaluateAll((elements) =>
          elements.map((el) => {
            const canvas = el as HTMLCanvasElement;
            const pixels = canvas
              .getContext("2d")!
              .getImageData(0, 0, canvas.width, canvas.height).data;
            const colors = new Set<string>();
            for (let i = 0; i < pixels.length; i += 16)
              colors.add(`${pixels[i]},${pixels[i + 1]},${pixels[i + 2]}`);
            return {
              width: canvas.width,
              height: canvas.height,
              colors: colors.size,
            };
          }),
        );
      for (const canvas of canvases) {
        expect(canvas.width).toBeGreaterThan(30);
        expect(canvas.height).toBeGreaterThan(30);
        expect(canvas.colors).toBeGreaterThan(5);
      }
      mkdirSync("docs/screenshots", { recursive: true });
      await page.screenshot({
        path: `docs/screenshots/${route.replaceAll("/", "-")}-${viewport.width}.png`,
      });
      if (process.env.KNK_COMPARE_SCREENSHOTS === "1")
        await expect(page).toHaveScreenshot(
          `${route.replaceAll("/", "-")}-${viewport.width}.png`,
          {
            animations: "disabled",
            maskColor: "#111111",
            mask: [
              page.locator(".header-clock"),
              page.locator(".valuation-timestamp"),
              page.locator(".quote-meta time"),
              page.locator(".status-bar"),
              page.locator(".inspector-body"),
              page.locator(".panel-footer time"),
              page.locator(".run-history"),
            ],
          },
        );
      page.off("pageerror", recordError);
    }
  });
}

test("mobile monitoring stays within viewport", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/overview");
  await expect(page.getByTestId("terminal-shell")).toBeVisible();
  await expect(page.locator(".loading-state")).toHaveCount(0);
  await expect(page.getByTestId("context-inspector")).toBeHidden();
  await expect(page.locator(".page-toolbar h1")).toBeVisible();
  await expect(page.locator(".chart canvas").first()).toBeVisible();
  const mainBounds = await page.locator("#main-workspace").boundingBox();
  expect(mainBounds!.width).toBeGreaterThan(300);
  expect(mainBounds!.height).toBeGreaterThan(500);
  expect(
    await page
      .locator(".kpi > *")
      .evaluateAll((elements) =>
        elements.every(
          (element) => element.scrollWidth <= element.clientWidth + 1,
        ),
      ),
  ).toBe(true);
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth),
  ).toBeLessThanOrEqual(390);
  mkdirSync("docs/screenshots", { recursive: true });
  await page.screenshot({ path: "docs/screenshots/mobile-overview.png" });
  if (process.env.KNK_COMPARE_SCREENSHOTS === "1")
    await expect(page).toHaveScreenshot("mobile-overview.png", {
      maskColor: "#111111",
      mask: [
        page.locator(".header-clock"),
        page.locator(".valuation-timestamp"),
        page.locator(".status-bar"),
        page.locator(".panel-footer time"),
      ],
    });
});
