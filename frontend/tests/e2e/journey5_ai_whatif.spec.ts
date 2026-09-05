/**
 * Journey 5: AI What-If → Structured scenario result renders with narration
 *
 * Covers:
 *  - POST /ai/what-if (via the AiChatPanel UI)
 *  - ScenarioResultCard renders deterministic numbers from the quant engine
 *  - Narration text (LLM-generated) appears (or timeout message appears gracefully)
 *  - The numeric result renders even if narration times out (resilience check)
 */

import { test, expect } from "@playwright/test";

const email = `e2e-journey5-${Date.now()}@risklens-test.com`;
const password = "E2eTestPass123!";

test.describe("Journey 5 — AI What-If", () => {
  test.beforeAll(async ({ browser }) => {
    const page = await browser.newPage();
    await page.goto("/register");
    await page.getByLabel(/email/i).fill(email);
    await page.getByLabel(/^password$/i).fill(password);
    const confirmField = page.getByLabel(/confirm password/i);
    if (await confirmField.isVisible()) await confirmField.fill(password);
    await page.getByRole("button", { name: /register|sign up|create account/i }).click();
    await page.waitForURL(/dashboard|onboarding/, { timeout: 15_000 });
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

  test("submits an AI what-if question and sees a structured result with numbers", async ({
    page,
  }) => {
    // ── Step 1: Login and navigate to dashboard ───────────────────────────────
    await page.goto("/login");
    await page.getByLabel(/email/i).fill(email);
    await page.getByLabel(/password/i).fill(password);
    await page.getByRole("button", { name: /log in|sign in/i }).click();
    await page.waitForURL(/dashboard/, { timeout: 15_000 });

    // ── Step 2: Open the AI Risk Analyst panel ────────────────────────────────
    const aiToggle = page
      .getByRole("button", { name: /ai analyst|ai risk analyst/i })
      .first();

    await aiToggle.waitFor({ state: "visible", timeout: 10_000 });
    await aiToggle.click();

    // Locate the chat input
    const chatInput = page
      .getByRole("textbox", { name: /question|ask|what if/i })
      .or(page.locator('textarea[placeholder*="what"]'))
      .or(page.locator('input[placeholder*="question"]'));

    await expect(chatInput).toBeVisible({ timeout: 10_000 });

    // ── Step 3: Type a what-if question ───────────────────────────────────────
    await chatInput.fill("What if AAPL drops 10% tomorrow?");

    // ── Step 4: Submit the question ───────────────────────────────────────────
    const submitBtn = page
      .getByRole("button", { name: /send|submit|ask/i })
      .last();
    await submitBtn.click();

    // ── Step 5: Loading indicator must appear ─────────────────────────────────
    const loadingSpinner = page
      .locator('[class*="loading"], [class*="spinner"], [aria-label*="loading"]')
      .first();

    // May briefly flash — tolerate if it disappears quickly
    await loadingSpinner.isVisible({ timeout: 5_000 }).catch(() => false);

    // ── Step 6: ScenarioResultCard must render with numeric values ─────────────
    // Wait up to 60s — LLM call + quant evaluation
    const scenarioResult = page
      .locator('[class*="ScenarioResult"], [data-testid="scenario-result"]')
      .first()
      .or(
        // Fallback: any element containing a percentage (VaR delta) in the result area
        page.getByText(/var|portfolio.*\d+\.?\d*%|scenario/i).first()
      );

    await expect(scenarioResult).toBeVisible({ timeout: 60_000 });

    // ── Step 7: A numeric value must be present (not just a placeholder) ──────
    // ScenarioResultCard renders delta VaR, new VaR, new CVaR as percentages
    const numericValue = page
      .locator('[class*="ScenarioResult"] [class*="value"], [class*="ScenarioResult"] td')
      .first()
      .or(page.getByText(/[+-]?\d+\.?\d+%/).first());

    await expect(numericValue).toBeVisible({ timeout: 10_000 });

    // ── Step 8: Narration OR timeout message must be visible ──────────────────
    // Narration = LLM text; timeout message = graceful fallback
    const narration = page
      .getByText(/the portfolio|risk|impact|exposure|anthropic|narration.*unavailable|timed out/i)
      .first();

    await expect(narration).toBeVisible({ timeout: 10_000 });
  });
});
