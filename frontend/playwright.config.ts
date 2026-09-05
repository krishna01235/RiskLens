import { defineConfig, devices } from "@playwright/test";

/**
 * Playwright configuration for RiskLens E2E tests.
 *
 * Tests target the local dev server at http://localhost:3000.
 * The backend must be running separately (uvicorn or Docker Compose).
 *
 * Run: npm run test:e2e
 * UI mode: npm run test:e2e -- --ui
 */

export default defineConfig({
  testDir: "./tests/e2e",
  /* Fail fast — show all failures per file, not per test */
  fullyParallel: false,
  /* Never retry in CI (we want fast, deterministic feedback) */
  retries: process.env.CI ? 1 : 0,
  /* One worker; E2E tests share a backend and can conflict */
  workers: 1,
  reporter: [["html", { outputFolder: "playwright-report", open: "never" }]],
  /* Global test timeout — simulation jobs can take 60s+ on dev machines */
  timeout: 120_000,

  use: {
    baseURL: "http://localhost:3000",
    /* Capture screenshot on failure for debugging */
    screenshot: "only-on-failure",
    /* Record video on first retry */
    video: "on-first-retry",
    /* Generous timeout — pages may load slowly on first cold start */
    actionTimeout: 15_000,
    navigationTimeout: 30_000,
  },

  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],

  /*
   * Auto-start the Next.js dev server before tests.
   * The backend (uvicorn + Redis + Postgres) must be started manually
   * via `docker compose up` or equivalent before running E2E tests.
   */
  webServer: {
    command: "npm run dev",
    url: "http://localhost:3000",
    reuseExistingServer: !process.env.CI,
    stdout: "pipe",
    stderr: "pipe",
    timeout: 60_000,
  },
});
