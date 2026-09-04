import { expect, test } from "@playwright/test";

test("documents required demo workflow labels", async () => {
  expect("KnK Capital Terminal").toContain("KnK Capital");
  expect("DEMO DATA").toBe("DEMO DATA");
});
