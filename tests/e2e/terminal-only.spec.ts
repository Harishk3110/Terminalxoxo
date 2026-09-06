import { expect, test } from "@playwright/test";

test.use({ storageState: { cookies: [], origins: [] } });

test("private root requires sign-in and contains no portfolio payload", async ({ page, request }) => {
  const root = await request.get("/", { maxRedirects: 0 });
  expect(root.status()).toBe(307);
  expect(root.headers().location).toBe("/overview");
  const overview = await request.get("/overview", { maxRedirects: 0 });
  expect(overview.status()).toBe(307);
  expect(overview.headers().location).toBe("/login");
  expect(await overview.text()).not.toContain("KNK_MAIN");
  await page.goto("/overview");
  await expect(page).toHaveURL(/\/login$/);
  await expect(page.getByRole("heading", { name: "KNK CAPITAL TERMINAL", exact: true })).toBeVisible();
  await expect(page.getByLabel("Email", { exact: true })).toBeVisible();
  await expect(page.getByTestId("context-inspector")).toHaveCount(0);
  expect(await page.locator('meta[name="robots"]').getAttribute("content")).toContain("noindex");
  const anonymous = await request.get("/backend/api/v1/operations/portfolio");
  expect(anonymous.status()).toBe(401);
});

test("retired public pages do not resolve and indexing is disabled", async ({ request }) => {
  for (const path of ["/principles", "/products", "/methodology", "/about", "/contact", "/disclosures"]) {
    const response = await request.get(path);
    expect(response.status()).toBe(404);
  }
  const robots = await request.get("/robots.txt");
  expect(await robots.text()).toContain("Disallow: /");
  expect((await request.get("/login")).headers()["x-robots-tag"]).toContain("noindex");
});
