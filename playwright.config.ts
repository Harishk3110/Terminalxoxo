import { defineConfig, devices } from "@playwright/test";

const runId = process.env.PLAYWRIGHT_RUN_ID ?? String(Date.now());

export default defineConfig({
  testDir: "tests/e2e",
  outputDir: `test-results/${runId}`,
  timeout: 30_000,
  use: {
    trace: "retain-on-failure"
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] }
    }
  ]
});
