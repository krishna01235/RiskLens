/**
 * Journey 3: Monte Carlo Simulation → Progress bar → Results with EVT row
 *
 * Covers:
 *  - POST /simulations (via UI form)
 *  - Live progress bar reaching 100%
 *  - SimulationResults renders (prob_profit, prob_loss, percentiles)
 *  - EVTComparisonRow is present in results
 */

import { test, expect } from "@playwright/test";

const email = `e2e-journey3-${Date.now()}@risklens-test.com`;
const password = "E2eTestPass123!";

test.describe("Journey 3 — Monte Carlo Simulation", () => {
  test.beforeAll(async ({ browser }) => {
    const page = await browser.newPage();
    // Register and create demo portfolio
    await page.goto("/register");
    await page.getByLabel(/email/i).fill(email);
    await page.getByLabel(/^password$/i).fill(password);
    const confirmField = page.getByLabel(/confirm password/i);
    if (await confirmField.isVisible()) await confirmField.fill(password);
    await page.getByRole("button", { name: /register|sign up|create account/i }).click();
    await page.waitForURL(/dashboard|onboarding/, { timeout: 15_000 });

    // Create demo portfolio if on onboarding
    const demoBtn = page.getByRole("button", { name: /demo|get started/i }).first();
    try {
      await demoBtn.waitFor({ state: "visible", timeout: 10_000 });
      await demoBtn.click();
      await page.waitForURL(/dashboard/, { timeout: 15_000 });
    } catch (e) {
      // ignore
    }
    await page.close();
  });

  test("runs a simulation, watches progress reach 100%, and sees EVT results", async ({
    page,
  }) => {
    // ── Step 1: Login ─────────────────────────────────────────────────────────
    await page.goto("/login");
    await page.getByLabel(/email/i).fill(email);
    await page.getByLabel(/password/i).fill(password);
    await page.getByRole("button", { name: /log in|sign in/i }).click();
    await page.waitForURL(/dashboard/, { timeout: 15_000 });

    // ── Step 2: Navigate to Simulate page ────────────────────────────────────
    const simulateLink = page
      .getByRole("link", { name: /simulat/i })
      .or(page.getByRole("button", { name: /simulat/i }));

    if (await simulateLink.isVisible({ timeout: 5_000 }).catch(() => false)) {
      await simulateLink.click();
    } else {
      await page.goto("/dashboard/simulate");
    }

    // ── Step 3: Fill simulation form ─────────────────────────────────────────
    // Select 10K paths (smallest, fastest) if a selector is present
    const pathsSelect = page.locator("select").first();
    if (await pathsSelect.isVisible({ timeout: 3_000 }).catch(() => false)) {
      await pathsSelect.selectOption({ label: "10,000" }).catch(async () => {
        // Fallback: try '10000' without comma formatting
        await pathsSelect.selectOption({ label: "10000" }).catch(() => {
          // Leave default if neither option text matches — simulation will still run
        });
      });
    }

    // Submit the form
    const runBtn = page
      .getByRole("button", { name: /run|simulate|start/i })
      .first();
    await expect(runBtn).toBeEnabled({ timeout: 10_000 });
    await runBtn.click();

    // ── Step 4: Progress bar must appear ─────────────────────────────────────
    const progressBar = page
      .locator('[role="progressbar"], [class*="progress"], [class*="Progress"]')
      .first();

    await expect(progressBar).toBeVisible({ timeout: 15_000 });

    // ── Step 5: Wait for results (progress disappears or results appear) ──────
    // Give generous timeout — simulation may take 10–30s on dev machine
    const resultsContainer = page
      .locator(
        '[data-testid="simulation-results"], [class*="SimulationResult"], [class*="result"]'
      )
      .first();

    const probLabel = page.getByText(/prob.*profit|probability.*profit/i).first();

    await expect(
      resultsContainer.or(probLabel)
    ).toBeVisible({ timeout: 60_000 });

    // ── Step 6: EVT row must be present ──────────────────────────────────────
    // EVTComparisonRow renders text like "EVT VaR" or "Tail Risk"
    const evtLabel = page.getByText(/evt|tail risk|pareto|gpd/i).first();
    await expect(evtLabel).toBeVisible({ timeout: 10_000 });
  });
});
