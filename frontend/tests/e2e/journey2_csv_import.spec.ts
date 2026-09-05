/**
 * Journey 2: Login → CSV Import → Mapping Confirmation → Dashboard reflects holdings
 *
 * Covers:
 *  - User login
 *  - POST /portfolios/import/preview (file upload)
 *  - POST /portfolios/import/confirm (with column mapping)
 *  - Dashboard shows at least one ticker from the imported CSV
 */

import { test, expect } from "@playwright/test";
import * as path from "path";
import * as fs from "fs";
import * as os from "os";

const email = `e2e-journey2-${Date.now()}@risklens-test.local`;
const password = "E2eTestPass123!";

/** Minimal valid CSV with US-market holdings */
const CSV_CONTENT = `symbol,quantity,average_price
AAPL,10,175.00
MSFT,5,380.00
GOOGL,3,140.00
`;

test.describe("Journey 2 — CSV Import", () => {
  test.beforeAll(async ({ browser }) => {
    // Register user before the test
    const page = await browser.newPage();
    await page.goto("/register");
    await page.getByLabel(/email/i).fill(email);
    await page.getByLabel(/^password$/i).fill(password);
    const confirmField = page.getByLabel(/confirm password/i);
    if (await confirmField.isVisible()) await confirmField.fill(password);
    await page.getByRole("button", { name: /register|sign up/i }).click();
    await page.waitForURL(/dashboard|onboarding/, { timeout: 15_000 });
    await page.close();
  });

  test("imports a CSV file and dashboard reflects holdings", async ({ page }) => {
    // ── Step 1: Login ─────────────────────────────────────────────────────────
    await page.goto("/login");
    await page.getByLabel(/email/i).fill(email);
    await page.getByLabel(/password/i).fill(password);
    await page.getByRole("button", { name: /log in|sign in/i }).click();
    await page.waitForURL(/dashboard/, { timeout: 15_000 });

    // ── Step 2: Navigate to CSV import ────────────────────────────────────────
    // Look for an import/upload link in sidebar or navigation
    const importLink = page
      .getByRole("link", { name: /import|upload/i })
      .or(page.getByRole("button", { name: /import|upload csv/i }));

    if (await importLink.isVisible({ timeout: 5_000 }).catch(() => false)) {
      await importLink.click();
    } else {
      // Navigate directly to portfolio import page or trigger via dashboard CTA
      await page.goto("/dashboard");
      const onboardImport = page.getByRole("button", { name: /import|upload|csv/i }).first();
      if (await onboardImport.isVisible({ timeout: 5_000 }).catch(() => false)) {
        await onboardImport.click();
      }
    }

    // ── Step 3: Upload the CSV file ───────────────────────────────────────────
    // Write temp CSV file to disk for the file-chooser
    const tmpFile = path.join(os.tmpdir(), `risklens-e2e-${Date.now()}.csv`);
    fs.writeFileSync(tmpFile, CSV_CONTENT);

    const fileInput = page.locator('input[type="file"]');
    await expect(fileInput).toBeVisible({ timeout: 10_000 });
    await fileInput.setInputFiles(tmpFile);

    // ── Step 4: Column mapping / confirmation ─────────────────────────────────
    // After upload, the preview/mapping step should appear
    const confirmBtn = page
      .getByRole("button", { name: /confirm|import|next/i })
      .first();
    await expect(confirmBtn).toBeVisible({ timeout: 15_000 });
    await confirmBtn.click();

    // ── Step 5: Dashboard should now reflect the imported portfolio ───────────
    await page.waitForURL(/dashboard/, { timeout: 20_000 });

    // One of the imported tickers should appear somewhere on the dashboard
    const aaplText = page.getByText(/AAPL|Apple/i).first();
    const msftText = page.getByText(/MSFT|Microsoft/i).first();
    const hasHolding =
      (await aaplText.isVisible({ timeout: 10_000 }).catch(() => false)) ||
      (await msftText.isVisible({ timeout: 5_000 }).catch(() => false));

    expect(hasHolding, "At least one imported ticker should appear on the dashboard").toBe(true);

    // Cleanup
    fs.unlinkSync(tmpFile);
  });
});
