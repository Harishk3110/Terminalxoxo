import { defineConfig, devices } from "@playwright/test";
import { tmpdir } from "node:os";
import path from "node:path";

export default defineConfig({
  testDir: "tests/e2e",
  // OneDrive can hold worker artifacts open and stall Playwright cleanup.
  outputDir: process.env.PLAYWRIGHT_OUTPUT_DIR || path.join(tmpdir(), "knk-terminal-e2e"),
  globalSetup: "./tests/e2e/servers.ts",
  timeout: 30_000,
  workers: 1,
  reporter: [["list"], ["json", {outputFile:"logs/terminal-e2e-results.json"}]],
  expect: { timeout: 15000, toHaveScreenshot: { maxDiffPixelRatio: 0.02 } },
  use: { baseURL: "http://127.0.0.1:3002", trace: "retain-on-failure", screenshot: "only-on-failure" },
  projects: [{ name: "chromium", use: {...devices["Desktop Chrome"]} }],
});
