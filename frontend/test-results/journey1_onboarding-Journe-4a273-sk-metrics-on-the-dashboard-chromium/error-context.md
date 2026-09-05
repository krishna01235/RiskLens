# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: journey1_onboarding.spec.ts >> Journey 1 — Register → Onboarding → Dashboard >> registers a new user, creates a demo portfolio, and sees risk metrics on the dashboard
- Location: tests\e2e\journey1_onboarding.spec.ts:17:7

# Error details

```
Error: At least one risk metric should be visible on the dashboard

expect(received).toBe(expected) // Object.is equality

Expected: true
Received: false
```

# Page snapshot

```yaml
- generic [active] [ref=e1]:
  - button "Open Next.js Dev Tools" [ref=e7] [cursor=pointer]:
    - generic [ref=e10]:
      - text: Rendering
      - generic [ref=e11]:
        - generic [ref=e12]: .
        - generic [ref=e13]: .
        - generic [ref=e14]: .
  - alert [ref=e15]
  - generic [ref=e16]:
    - complementary "Primary navigation" [ref=e17]:
      - generic [ref=e18]: RiskLens
      - navigation [ref=e23]:
        - link "Dashboard" [ref=e24] [cursor=pointer]:
          - /url: /dashboard
        - link "Simulate" [ref=e33] [cursor=pointer]:
          - /url: /dashboard/simulate
        - link "Replay" [ref=e40] [cursor=pointer]:
          - /url: /dashboard/replay
      - button "Collapse sidebar" [ref=e47] [cursor=pointer]
    - banner [ref=e50]:
      - paragraph [ref=e51]: PortfolioMy Portfolio
      - generic [ref=e52]:
        - 'generic "Market data: live" [ref=e53]': Live
        - button "Switch to light mode" [ref=e57] [cursor=pointer]
        - button "User menu" [ref=e63] [cursor=pointer]:
          - generic [ref=e64]: E
          - generic [ref=e65]: e2e-journey1-1788615347325@risklens-test.com
    - main [ref=e68]:
      - generic [ref=e70]:
        - generic [ref=e71]:
          - generic [ref=e72]:
            - heading "Risk Dashboard" [level=1] [ref=e73]
            - paragraph [ref=e74]: Waiting for market data…
          - generic [ref=e75]:
            - 'generic "Market regime: Calm at 100.0% confidence" [ref=e76]':
              - generic [ref=e79]: Calm
              - generic [ref=e80]: 100.0%
            - button "AI Analyst" [ref=e81] [cursor=pointer]
        - generic [ref=e86]:
          - img "Loading" [ref=e87]
          - paragraph [ref=e90]: Waiting for market data…
          - paragraph [ref=e91]: Risk metrics compute once live prices arrive.
```

# Test source

```ts
  1  | /**
  2  |  * Journey 1: Register → Onboarding → Demo Portfolio → Dashboard shows risk metrics
  3  |  *
  4  |  * Covers:
  5  |  *  - New user registration (POST /auth/register)
  6  |  *  - Onboarding flow (POST /portfolios/demo)
  7  |  *  - Dashboard renders at least one non-empty metric card
  8  |  */
  9  | 
  10 | import { test, expect } from "@playwright/test";
  11 | 
  12 | // Generate a unique email so this test is idempotent across runs
  13 | const email = `e2e-journey1-${Date.now()}@risklens-test.com`;
  14 | const password = "E2eTestPass123!";
  15 | 
  16 | test.describe("Journey 1 — Register → Onboarding → Dashboard", () => {
  17 |   test("registers a new user, creates a demo portfolio, and sees risk metrics on the dashboard", async ({
  18 |     page,
  19 |   }) => {
  20 |     // ── Step 1: Navigate to register page ────────────────────────────────────
  21 |     await page.goto("/register");
  22 |     await expect(page).toHaveTitle(/risklens/i);
  23 | 
  24 |     // ── Step 2: Fill in registration form ────────────────────────────────────
  25 |     await page.getByLabel(/email/i).fill(email);
  26 |     await page.getByLabel(/^password$/i).fill(password);
  27 | 
  28 |     // Some forms have a confirm password field
  29 |     const confirmField = page.getByLabel(/confirm password/i);
  30 |     if (await confirmField.isVisible()) {
  31 |       await confirmField.fill(password);
  32 |     }
  33 | 
  34 |     await page.getByRole("button", { name: /register|sign up|create account/i }).click();
  35 | 
  36 |     // ── Step 3: Expect redirect to dashboard or onboarding ───────────────────
  37 |     await page.waitForURL(/dashboard|onboarding/, { timeout: 15_000 });
  38 | 
  39 |     // ── Step 4: If onboarding page, click "Demo Portfolio" CTA ───────────────
  40 |     if (page.url().includes("onboarding") || page.url().includes("dashboard")) {
  41 |       // Look for a demo / get started button
  42 |       const demoBtn = page.getByRole("button", {
  43 |         name: /demo|get started|load demo/i,
  44 |       });
  45 |       if (await demoBtn.isVisible({ timeout: 5_000 }).catch(() => false)) {
  46 |         await demoBtn.click();
  47 |         // Wait for dashboard to load with actual data
  48 |         await page.waitForURL(/dashboard/, { timeout: 15_000 });
  49 |       }
  50 |     }
  51 | 
  52 |     // ── Step 5: Dashboard must show at least one metric card ─────────────────
  53 |     // MetricCard renders a numeric value alongside a label — wait for any
  54 |     // element that looks like a risk metric (VaR, volatility, Sharpe ratio, etc.)
  55 |     const metricCard = page
  56 |       .locator('[data-testid="metric-card"], .metric-card, [class*="MetricCard"]')
  57 |       .first();
  58 | 
  59 |     // Fallback: look for text that matches a known metric name
  60 |     const metricText = page.getByText(/var|volatility|sharpe|drawdown/i).first();
  61 | 
  62 |     const hasMetric =
  63 |       (await metricCard.isVisible({ timeout: 10_000 }).catch(() => false)) ||
  64 |       (await metricText.isVisible({ timeout: 5_000 }).catch(() => false));
  65 | 
> 66 |     expect(hasMetric, "At least one risk metric should be visible on the dashboard").toBe(true);
     |                                                                                      ^ Error: At least one risk metric should be visible on the dashboard
  67 | 
  68 |     // ── Step 6: Verify non-empty values — look for a percentage or decimal ───
  69 |     const metricValue = page
  70 |       .locator(
  71 |         '[data-testid="metric-value"], .metric-value, [class*="value"], [class*="Value"]'
  72 |       )
  73 |       .first();
  74 | 
  75 |     // The value should be a number (possibly "—" if data not yet loaded,
  76 |     // but the element itself must be present)
  77 |     await expect(metricValue.or(metricText)).toBeVisible({ timeout: 10_000 });
  78 |   });
  79 | });
  80 | 
```