import { expect, test } from "@playwright/test";

test("factor input changes preserve autosave while obsolete reads are in flight", async ({
  page,
}) => {
  test.setTimeout(90000);
  const failures: string[] = [];
  page.on("response", (response) => {
    if (response.url().includes("/backend/") && response.status() >= 500)
      failures.push(`${response.status()} ${response.url()}`);
  });
  const isFactor = (request: { url(): string }) =>
    request.url().includes("/api/v1/factors?");
  const first = page.waitForRequest(isFactor);
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/factor-lab");
  await first;
  const type = page.getByLabel("Factor type");
  const lookback = page.getByLabel("Factor horizon", { exact: true });
  const nextType =
    (await type.inputValue()) === "VOLATILITY" ? "MOMENTUM" : "VOLATILITY";
  const nextLookback = (await lookback.inputValue()) === "21" ? "63" : "21";
  const saved = page.waitForResponse((response) => {
    if (
      !response.url().includes("/api/v1/workspaces/") ||
      response.request().method() !== "POST"
    )
      return false;
    const states: Record<string, Record<string, unknown>> = response
      .request()
      .postDataJSON()?.configuration?.tabStates ?? {};
    return Object.values(states).some(
      (state) =>
        state["factor-name"] === nextType &&
        state["factor-lookback"] === Number(nextLookback),
    );
  });
  const second = page.waitForRequest(isFactor);
  await type.selectOption(nextType);
  await second;
  const third = page.waitForRequest(isFactor);
  await lookback.selectOption(nextLookback);
  await third;
  await expect(page.getByLabel("factor-values table")).toContainText("IWM");
  expect((await saved).ok()).toBeTruthy();
  await expect(page.getByText(/server sync failed/)).toHaveCount(0);
  await page.screenshot({
    path: "logs/portfolio-screenshots/factor-concurrency-1440.png",
  });
  await page.reload();
  await expect(type).toHaveValue(nextType);
  await expect(lookback).toHaveValue(nextLookback);
  await expect(page.getByLabel("factor-values table")).toContainText("IWM");
  await page.setViewportSize({ width: 390, height: 844 });
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth),
  ).toBeLessThanOrEqual(390);
  await page.screenshot({
    path: "logs/portfolio-screenshots/factor-concurrency-390.png",
  });
  expect(failures).toEqual([]);
});
