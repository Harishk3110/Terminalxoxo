import { execFileSync, spawn, type ChildProcess } from "node:child_process";
import http from "node:http";
import https from "node:https";
import path from "node:path";
import { expect, test } from "@playwright/test";

const root = path.resolve(__dirname, "../..");
const started: ChildProcess[] = [];

test.describe.configure({ timeout: 180_000 });
test.setTimeout(180_000);

async function reachable(url: string) {
  return new Promise<boolean>((resolve) => {
    const parsed = new URL(url);
    const client = parsed.protocol === "https:" ? https : http;
    const request = client.get(parsed, (response) => {
      response.resume();
      resolve(Boolean(response.statusCode && response.statusCode >= 200 && response.statusCode < 400));
    });
    request.setTimeout(3_000, () => {
      request.destroy();
      resolve(false);
    });
    request.on("error", () => resolve(false));
  });
}

async function waitFor(url: string, timeoutMs = 150_000) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    if (await reachable(url)) return;
    await new Promise((resolve) => setTimeout(resolve, 1_500));
  }
  throw new Error(`Timed out waiting for ${url}`);
}

function startApi() {
  const python = process.platform === "win32" ? "python" : "python3";
  const dbPath = path.join(root, "knk_terminal_e2e.db").replaceAll("\\", "/");
  const child = spawn(python, ["-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"], {
    cwd: path.join(root, "services/api"),
    env: { ...process.env, DATABASE_URL: `sqlite:///${dbPath}` },
    stdio: "ignore"
  });
  started.push(child);
}

function startTerminal() {
  const command = process.platform === "win32" ? "cmd.exe" : "corepack";
  const args =
    process.platform === "win32"
      ? ["/d", "/s", "/c", "corepack pnpm --filter @knk/terminal-web start --hostname 127.0.0.1 --port 3001"]
      : ["pnpm", "--filter", "@knk/terminal-web", "start", "--hostname", "127.0.0.1", "--port", "3001"];
  const child = spawn(command, args, {
    cwd: root,
    env: { ...process.env, NEXT_PUBLIC_API_BASE_URL: "http://127.0.0.1:8000" },
    stdio: "ignore"
  });
  started.push(child);
}

function stopProcess(child: ChildProcess) {
  if (!child.pid) return;
  if (process.platform === "win32") {
    try {
      execFileSync("taskkill", ["/pid", String(child.pid), "/t", "/f"], { stdio: "ignore" });
    } catch {
      // Process already exited.
    }
    return;
  }
  child.kill("SIGTERM");
}

test.beforeAll(async () => {
  test.setTimeout(180_000);
  startTerminal();
  startApi();
  await Promise.all([waitFor("http://127.0.0.1:8000/health/ready"), waitFor("http://127.0.0.1:3001/overview")]);
});

test.afterAll(() => {
  for (const child of started.reverse()) {
    stopProcess(child);
  }
});

test("terminal renders database-backed core journey", async ({ page, request }) => {
  const healthResponse = await request.get("http://127.0.0.1:8000/api/v1/system/health");
  expect(healthResponse.ok()).toBeTruthy();
  const health = await healthResponse.json();
  expect(health.counts.instruments).toBeGreaterThanOrEqual(20);
  expect(health.counts.macro_series).toBeGreaterThanOrEqual(17);

  await page.goto("http://127.0.0.1:3001/overview");
  await expect(page.getByText("Reference NAV")).toBeVisible();
  await expect(page.getByText("Database-backed")).toBeVisible();

  await page.getByRole("link", { name: "Macro" }).click();
  await expect(page.getByText("Macro Dashboard")).toBeVisible();
  await expect(page.getByText("FEDFUNDS")).toBeVisible();

  await page.getByRole("link", { name: "Connections" }).click();
  await expect(page.getByRole("heading", { name: "Connections", exact: true })).toBeVisible();
  await expect(page.getByText("FRED")).toBeVisible();
  await expect(page.getByText(/NOT_CONFIGURED|FAILED/).first()).toBeVisible();
});
