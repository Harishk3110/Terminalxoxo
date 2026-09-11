import { expect, test } from "@playwright/test";
import { setTimeout } from "node:timers/promises";

test("production HTTP connections survive the former six-second idle boundary", async ({
  request,
}) => {
  test.setTimeout(20000);
  const before = await request.get("/login");
  expect(before.status()).toBe(200);
  expect(before.headers()["keep-alive"]).toMatch(/\btimeout=70\b/);
  await before.body();
  await setTimeout(6000);
  const after = await request.get("/login");
  expect(after.status()).toBe(200);
  expect(after.headers()["keep-alive"]).toMatch(/\btimeout=70\b/);
  expect(await after.text()).toContain("KnK");
});
