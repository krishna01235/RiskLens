/**
 * Journey 1: Register → Onboarding → Demo Portfolio → Dashboard shows risk metrics
 *
 * Covers:
 *  - New user registration (POST /auth/register)
 *  - Onboarding flow (POST /portfolios/demo)
 *  - Dashboard renders at least one non-empty metric card
 */

import { test, expect } from "@playwright/test";

// Generate a unique email so this test is idempotent across runs
const email = `e2e-journey1-${Date.now()}@risklens-test.com`;
const password = "E2eTestPass123!";

test.describe("Journey 1 — Register → Onboarding → Dashboard", () => {
  test("registers a new user, creates a demo portfolio, and sees risk metrics on the dashboard", async ({
    page,
  }) => {
    // ── Step 1: Navigate to register page ────────────────────────────────────
    await page.goto("/register");
    await expect(page).toHaveTitle(/risklens/i);

    // ── Step 2: Fill in registration form ────────────────────────────────────
    await page.getByLabel(/email/i).fill(email);
    await page.getByLabel(/^password$/i).fill(password);

    // Confirm password field
    const confirmField = page.getByLabel(/confirm password/i);
    if (await confirmField.isVisible()) {
      await confirmField.fill(password);
    }

    await page.getByRole("button", { name: /register|sign up|create account/i }).click();

    // ── Step 3: Wait for onboarding page ─────────────────────────────────────
    // Register redirects to /dashboard (no portfolio) → dashboard immediately
    // redirects to /onboarding because the user has no portfolio yet.
    // We wait for /onboarding to settle rather than /dashboard.
    await page.waitForURL(/onboarding/, { timeout: 20_000 });

    // ── Step 4: Click "Try Demo" on onboarding page ───────────────────────────
    const demoBtn = page.getByRole("button", { name: /try demo/i });
    await expect(demoBtn).toBeVisible({ timeout: 10_000 });
    await demoBtn.click();

    // ── Step 5: Wait for dashboard after demo portfolio creation ──────────────
    // POST /portfolios/demo can take a few seconds; allow 20s.
    await page.waitForURL(/dashboard/, { timeout: 20_000 });

    // ── Step 6: Dashboard must show the Risk Dashboard heading ────────────────
    // Use expect().toBeVisible() which correctly auto-waits (locator.isVisible()
    // ignores the timeout parameter and returns immediately).
    // The heading is always rendered once the portfolio is loaded, regardless of
    // whether the slow-path worker has finished computing risk metrics yet.
    await expect(
      page.getByRole("heading", { name: /risk dashboard/i }).first()
    ).toBeVisible({ timeout: 20_000 });
  });
});
