# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: journey2_csv_import.spec.ts >> Journey 2 — CSV Import >> imports a CSV file and dashboard reflects holdings
- Location: tests\e2e\journey2_csv_import.spec.ts:40:7

# Error details

```
TimeoutError: page.waitForURL: Timeout 20000ms exceeded.
=========================== logs ===========================
waiting for navigation until "load"
============================================================
```

# Page snapshot

```yaml
- generic [ref=e1]:
  - generic [active]:
    - menu "Next.js Dev Tools Items" [ref=e2]:
      - generic [ref=e3]:
        - menuitem "Route Static" [ref=e4] [cursor=pointer]:
          - generic [ref=e5]: Route
          - generic [ref=e6]: Static
        - generic "Turbopack is enabled." [ref=e7]:
          - generic [ref=e8]: Bundler
          - generic [ref=e9]: Turbopack
        - menuitem "Route Info" [ref=e10]
      - menuitem "Preferences" [ref=e16]
    - button "Close Next.js Dev Tools" [expanded] [ref=e26] [cursor=pointer]
  - alert [ref=e30]: Let's build your portfolio
  - generic [ref=e32]:
    - generic [ref=e33]:
      - heading "Let's build your portfolio" [level=1] [ref=e34]
      - paragraph [ref=e35]: How would you like to add your holdings?
      - generic [ref=e36]:
        - button "India (NSE)" [disabled] [ref=e37]
        - button "US (NYSE/NASDAQ)" [disabled] [ref=e41]
    - generic [ref=e45]:
      - button "Back to options" [ref=e46] [cursor=pointer]
      - generic [ref=e50]:
        - heading "Confirm Column Mapping" [level=3] [ref=e51]
        - paragraph [ref=e52]: We've automatically detected the columns from your CSV. Please verify that the required fields are mapped correctly before importing.
        - table [ref=e54]:
          - rowgroup [ref=e55]:
            - row [ref=e56]:
              - columnheader "CSV Header" [ref=e57]
              - columnheader "Maps To" [ref=e58]
              - columnheader "Preview Data (First row)" [ref=e59]
          - rowgroup [ref=e60]:
            - row [ref=e61]:
              - cell "symbol" [ref=e62]
              - cell "Symbol / Ticker *" [ref=e66]:
                - combobox [ref=e67]:
                  - option "-- Ignore this column --"
                  - option "Symbol / Ticker *" [selected]
                  - option "Quantity / Shares *" [disabled]
                  - option "Average Price *" [disabled]
                  - option "Currency (Optional)"
              - cell "AAPL" [ref=e68]
            - row [ref=e69]:
              - cell "quantity" [ref=e70]
              - cell "Quantity / Shares *" [ref=e74]:
                - combobox [ref=e75]:
                  - option "-- Ignore this column --"
                  - option "Symbol / Ticker *" [disabled]
                  - option "Quantity / Shares *" [selected]
                  - option "Average Price *" [disabled]
                  - option "Currency (Optional)"
              - cell "10" [ref=e76]
            - row [ref=e77]:
              - cell "average_price" [ref=e78]
              - cell "Average Price *" [ref=e82]:
                - combobox [ref=e83]:
                  - option "-- Ignore this column --"
                  - option "Symbol / Ticker *" [disabled]
                  - option "Quantity / Shares *" [disabled]
                  - option "Average Price *" [selected]
                  - option "Currency (Optional)"
              - cell "175.00" [ref=e84]
        - generic [ref=e85]:
          - generic [ref=e86]: Ready to import. Portfolio currency will be INR.
          - button "Confirm & Import" [ref=e90] [cursor=pointer]
```

# Test source

```ts
  1   | /**
  2   |  * Journey 2: Login → CSV Import → Mapping Confirmation → Dashboard reflects holdings
  3   |  *
  4   |  * Covers:
  5   |  *  - User login
  6   |  *  - POST /portfolios/import/preview (file upload)
  7   |  *  - POST /portfolios/import/confirm (with column mapping)
  8   |  *  - Dashboard shows at least one ticker from the imported CSV
  9   |  */
  10  | 
  11  | import { test, expect } from "@playwright/test";
  12  | import * as path from "path";
  13  | import * as fs from "fs";
  14  | import * as os from "os";
  15  | 
  16  | const email = `e2e-journey2-${Date.now()}@risklens-test.com`;
  17  | const password = "E2eTestPass123!";
  18  | 
  19  | /** Minimal valid CSV with US-market holdings */
  20  | const CSV_CONTENT = `symbol,quantity,average_price
  21  | AAPL,10,175.00
  22  | MSFT,5,380.00
  23  | GOOGL,3,140.00
  24  | `;
  25  | 
  26  | test.describe("Journey 2 — CSV Import", () => {
  27  |   test.beforeAll(async ({ browser }) => {
  28  |     // Register user before the test
  29  |     const page = await browser.newPage();
  30  |     await page.goto("/register");
  31  |     await page.getByLabel(/email/i).fill(email);
  32  |     await page.getByLabel(/^password$/i).fill(password);
  33  |     const confirmField = page.getByLabel(/confirm password/i);
  34  |     if (await confirmField.isVisible()) await confirmField.fill(password);
  35  |     await page.getByRole("button", { name: /register|sign up|create account/i }).click();
  36  |     await page.waitForURL(/dashboard|onboarding/, { timeout: 15_000 });
  37  |     await page.close();
  38  |   });
  39  | 
  40  |   test("imports a CSV file and dashboard reflects holdings", async ({ page }) => {
  41  |     // ── Step 1: Login ─────────────────────────────────────────────────────────
  42  |     await page.goto("/login");
  43  |     await page.getByLabel(/email/i).fill(email);
  44  |     await page.getByLabel(/password/i).fill(password);
  45  |     await page.getByRole("button", { name: /log in|sign in/i }).click();
  46  |     await page.waitForURL(/dashboard/, { timeout: 15_000 });
  47  | 
  48  |     // ── Step 2: Navigate to CSV import ────────────────────────────────────────
  49  |     const importLink = page
  50  |       .getByRole("link", { name: /import|upload/i })
  51  |       .or(page.getByRole("button", { name: /import|upload csv/i }))
  52  |       .first();
  53  | 
  54  |     try {
  55  |       await importLink.waitFor({ state: "visible", timeout: 10_000 });
  56  |       await importLink.click();
  57  |     } catch {
  58  |       // Navigate directly to portfolio import page or trigger via dashboard CTA
  59  |       await page.goto("/dashboard");
  60  |       const onboardImport = page.getByRole("button", { name: /import|upload|csv/i }).first();
  61  |       try {
  62  |         await onboardImport.waitFor({ state: "visible", timeout: 10_000 });
  63  |         await onboardImport.click();
  64  |       } catch (e) {}
  65  |     }
  66  | 
  67  |     // ── Step 3: Upload the CSV file ───────────────────────────────────────────
  68  |     // Write temp CSV file to disk for the file-chooser
  69  |     const tmpFile = path.join(os.tmpdir(), `risklens-e2e-${Date.now()}.csv`);
  70  |     fs.writeFileSync(tmpFile, CSV_CONTENT);
  71  | 
  72  |     const fileInput = page.locator('input[type="file"]');
  73  |     await expect(fileInput).toBeAttached({ timeout: 10_000 });
  74  |     await fileInput.setInputFiles(tmpFile);
  75  | 
  76  |     // ── Step 4: Column mapping / confirmation ─────────────────────────────────
  77  |     // After upload, the preview/mapping step should appear
  78  |     const confirmBtn = page
  79  |       .getByRole("button", { name: /confirm|import|next/i })
  80  |       .first();
  81  |     await expect(confirmBtn).toBeVisible({ timeout: 15_000 });
  82  |     await confirmBtn.click();
  83  | 
  84  |     // ── Step 5: Dashboard should now reflect the imported portfolio ───────────
> 85  |     await page.waitForURL(/dashboard/, { timeout: 20_000 });
      |                ^ TimeoutError: page.waitForURL: Timeout 20000ms exceeded.
  86  | 
  87  |     // One of the imported tickers should appear somewhere on the dashboard
  88  |     const aaplText = page.getByText(/AAPL|Apple/i).first();
  89  |     const msftText = page.getByText(/MSFT|Microsoft/i).first();
  90  |     const hasHolding =
  91  |       (await aaplText.isVisible({ timeout: 10_000 }).catch(() => false)) ||
  92  |       (await msftText.isVisible({ timeout: 5_000 }).catch(() => false));
  93  | 
  94  |     expect(hasHolding, "At least one imported ticker should appear on the dashboard").toBe(true);
  95  | 
  96  |     // Cleanup
  97  |     fs.unlinkSync(tmpFile);
  98  |   });
  99  | });
  100 | 
```