import { execFileSync } from "node:child_process";
import { expect, test } from "@playwright/test";

test("confirmed TOTP, recovery login and private security controls", async ({
  page,
  browser,
  request,
}) => {
  test.setTimeout(180000);
  const password = process.env.PLAYWRIGHT_TEST_PASSWORD!;
  const email = process.env.PLAYWRIGHT_TEST_EMAIL!;
  let codes: string[] = [];
  await page.setViewportSize({ width: 1440, height: 900 });
  try {
    await page.goto("/settings/security");
    await page
      .getByRole("button", { name: "Enable authenticator", exact: true })
      .click();
    await page.getByLabel("Current password", { exact: true }).fill(password);
    const start = page.waitForResponse(
      (r) =>
        r.url().endsWith("/auth/totp/enroll") &&
        r.request().method() === "POST",
    );
    await page.getByRole("button", { name: "Create enrollment" }).click();
    expect((await start).ok()).toBeTruthy();
    const secret = await page
      .getByLabel("Authenticator key", { exact: true })
      .inputValue();
    const otp = execFileSync(
      process.env.PLAYWRIGHT_PYTHON || "python",
      [
        "-c",
        "import sys, pyotp; print(pyotp.TOTP(sys.stdin.read().strip()).now())",
      ],
      { input: secret, encoding: "utf8", windowsHide: true },
    ).trim();
    await page.getByLabel("Authenticator code", { exact: true }).fill(otp);
    const confirmed = page.waitForResponse(
      (r) =>
        r.url().endsWith("/auth/totp/confirm") &&
        r.request().method() === "POST",
    );
    await page.getByRole("button", { name: "Confirm authenticator" }).click();
    const response = await confirmed;
    expect(response.ok()).toBeTruthy();
    codes = (await response.json()).recovery_codes;
    expect(codes).toHaveLength(8);
    await page.getByRole("button", { name: "Dismiss recovery codes" }).click();
    await expect(page.getByText("TOTP ENABLED", { exact: true })).toBeVisible();
    for (const size of [
      { width: 1440, height: 900 },
      { width: 390, height: 844 },
    ]) {
      await page.setViewportSize(size);
      if (size.width < 600 && await page.getByRole("button", {name: "Hide inspector"}).isVisible()) {
        await page.getByRole("button", {name: "Hide inspector"}).click();
      }
      await page.screenshot({
        path: `logs/security-${size.width}.png`,
        fullPage: true,
      });
      expect(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth + 1,
        ),
      ).toBeTruthy();
    }
    const other = await browser.newContext({
      baseURL: "http://127.0.0.1:3002",
      storageState: { cookies: [], origins: [] },
    });
    try {
      expect(
        (
          await other.request.post("/backend/api/v1/auth/login", {
            data: { email, password },
          })
        ).status(),
      ).toBe(401);
      const loginPage = await other.newPage();
      await loginPage.goto("/login");
      await loginPage.getByLabel("Email", { exact: true }).fill(email);
      await loginPage.getByLabel("Password", { exact: true }).fill(password);
      await loginPage
        .getByRole("checkbox", { name: "Use recovery code" })
        .check();
      await loginPage
        .getByLabel("Recovery code", { exact: true })
        .fill(codes[0]);
      await loginPage
        .getByRole("button", { name: "Sign in", exact: true })
        .click();
      await expect(loginPage).toHaveURL(/\/overview$/);
      expect(
        (
          await other.request.post("/backend/api/v1/auth/login", {
            data: { email, password, recovery_code: codes[0] },
          })
        ).status(),
      ).toBe(401);
      expect(
        (
          await other.request.post("/backend/api/v1/auth/totp/disable", {
            data: { password, recovery_code: codes[1] },
          })
        ).ok(),
      ).toBeTruthy();
    } finally {
      await other.close();
    }
  } finally {
    // Restore the shared isolated-suite account, never a user database/account.
    let loggedIn = await request.post("/backend/api/v1/auth/login", {
      data: { email, password },
    });
    if (!loggedIn.ok() && codes.length) {
      loggedIn = await request.post("/backend/api/v1/auth/login", {
        data: { email, password, recovery_code: codes[6] },
      });
      if (loggedIn.ok())
        await request.post("/backend/api/v1/auth/totp/disable", {
          data: { password, recovery_code: codes[7] },
        });
    }
    if (loggedIn.ok())
      await request.storageState({ path: "logs/e2e-auth.json" });
  }
});
