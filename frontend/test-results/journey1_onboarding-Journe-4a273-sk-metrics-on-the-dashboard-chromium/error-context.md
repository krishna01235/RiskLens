# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: journey1_onboarding.spec.ts >> Journey 1 — Register → Onboarding → Dashboard >> registers a new user, creates a demo portfolio, and sees risk metrics on the dashboard
- Location: tests\e2e\journey1_onboarding.spec.ts:17:7

# Error details

```
Error: Dashboard should show content (metrics or pending state)

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
          - generic [ref=e65]: e2e-journey1-1788618208995@risklens-test.com
    - main [ref=e68]:
      - generic [ref=e70]:
        - generic [ref=e71]:
          - generic [ref=e72]:
            - heading "Risk Dashboard" [level=1] [ref=e73]
            - paragraph [ref=e74]: Waiting for market data…
          - button "AI Analyst" [ref=e76] [cursor=pointer]
        - generic [ref=e81]:
          - img "Loading" [ref=e82]
          - paragraph [ref=e85]: Waiting for market data…
          - paragraph [ref=e86]: Risk metrics compute once live prices arrive.
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
  52 |     // ── Step 5 & 6: Dashboard must show content ────────────────────────────────
  53 |     // New portfolios may take up to 60s for the slow-path worker to compute.
  54 |     // Strategy: first check fast conditions (spinner/pending text), then
  55 |     // wait up to 60s for actual metric values to appear.
  56 | 
  57 |     // Fast checks: pending spinner text that is always present on a new portfolio
  58 |     const waitingText = page.getByText(/waiting for market data/i).first();
  59 |     const pendingText = page.getByText(/risk metrics compute/i).first();
  60 |     const metricText = page.getByText(/var|volatility|sharpe|drawdown/i).first();
  61 |     const metricCard = page
  62 |       .locator('[data-testid="metric-card"], .metric-card, [class*="MetricCard"]')
  63 |       .first();
  64 | 
  65 |     // Check fast options first (5s each), then fall back to 60s metric wait
  66 |     const hasFastContent =
  67 |       (await waitingText.isVisible({ timeout: 5_000 }).catch(() => false)) ||
  68 |       (await pendingText.isVisible({ timeout: 2_000 }).catch(() => false)) ||
  69 |       (await metricText.isVisible({ timeout: 2_000 }).catch(() => false));
  70 | 
  71 |     const hasContent = hasFastContent ||
  72 |       (await metricCard.isVisible({ timeout: 60_000 }).catch(() => false)) ||
  73 |       (await metricText.isVisible({ timeout: 5_000 }).catch(() => false));
  74 | 
> 75 |     expect(hasContent, "Dashboard should show content (metrics or pending state)").toBe(true);
     |                                                                                    ^ Error: Dashboard should show content (metrics or pending state)
  76 |   });
  77 | });
  78 | 
```