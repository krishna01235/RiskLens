# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: journey3_simulation.spec.ts >> Journey 3 — Monte Carlo Simulation >> runs a simulation, watches progress reach 100%, and sees EVT results
- Location: tests\e2e\journey3_simulation.spec.ts:40:7

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator: locator('[role="progressbar"], [class*="progress"], [class*="Progress"]').first()
Expected: visible
Timeout: 15000ms
Error: element(s) not found

Call log:
  - Expect "toBeVisible" locator('[role="progressbar"], [class*="progress"], [class*="Progress"]').first() with timeout 15000ms
  - waiting for locator('[role="progressbar"], [class*="progress"], [class*="Progress"]').first()

```

```yaml
- alert: Monte Carlo Simulation
- complementary "Primary navigation":
  - text: RiskLens
  - navigation:
    - link "Dashboard":
      - /url: /dashboard
    - link "Simulate":
      - /url: /dashboard/simulate
    - link "Replay":
      - /url: /dashboard/replay
  - button "Collapse sidebar"
- banner:
  - paragraph: PortfolioMy Portfolio
  - text: Live
  - button "Switch to light mode"
  - button "User menu": E e2e-journey3-1788615383636@risklens-test.com
- main:
  - heading "Monte Carlo Simulation" [level=1]
  - paragraph: Vectorised GBM with Cholesky-correlated shocks, GARCH volatility, and antithetic variates.
  - paragraph: Queuing simulation...
  - text: 0%
  - paragraph: Job is queued — it will start momentarily.
```

# Test source

```ts
  1   | /**
  2   |  * Journey 3: Monte Carlo Simulation → Progress bar → Results with EVT row
  3   |  *
  4   |  * Covers:
  5   |  *  - POST /simulations (via UI form)
  6   |  *  - Live progress bar reaching 100%
  7   |  *  - SimulationResults renders (prob_profit, prob_loss, percentiles)
  8   |  *  - EVTComparisonRow is present in results
  9   |  */
  10  | 
  11  | import { test, expect } from "@playwright/test";
  12  | 
  13  | const email = `e2e-journey3-${Date.now()}@risklens-test.com`;
  14  | const password = "E2eTestPass123!";
  15  | 
  16  | test.describe("Journey 3 — Monte Carlo Simulation", () => {
  17  |   test.beforeAll(async ({ browser }) => {
  18  |     const page = await browser.newPage();
  19  |     // Register and create demo portfolio
  20  |     await page.goto("/register");
  21  |     await page.getByLabel(/email/i).fill(email);
  22  |     await page.getByLabel(/^password$/i).fill(password);
  23  |     const confirmField = page.getByLabel(/confirm password/i);
  24  |     if (await confirmField.isVisible()) await confirmField.fill(password);
  25  |     await page.getByRole("button", { name: /register|sign up|create account/i }).click();
  26  |     await page.waitForURL(/dashboard|onboarding/, { timeout: 15_000 });
  27  | 
  28  |     // Create demo portfolio if on onboarding
  29  |     const demoBtn = page.getByRole("button", { name: /demo|get started/i }).first();
  30  |     try {
  31  |       await demoBtn.waitFor({ state: "visible", timeout: 10_000 });
  32  |       await demoBtn.click();
  33  |       await page.waitForURL(/dashboard/, { timeout: 15_000 });
  34  |     } catch (e) {
  35  |       // ignore
  36  |     }
  37  |     await page.close();
  38  |   });
  39  | 
  40  |   test("runs a simulation, watches progress reach 100%, and sees EVT results", async ({
  41  |     page,
  42  |   }) => {
  43  |     // ── Step 1: Login ─────────────────────────────────────────────────────────
  44  |     await page.goto("/login");
  45  |     await page.getByLabel(/email/i).fill(email);
  46  |     await page.getByLabel(/password/i).fill(password);
  47  |     await page.getByRole("button", { name: /log in|sign in/i }).click();
  48  |     await page.waitForURL(/dashboard/, { timeout: 15_000 });
  49  | 
  50  |     // ── Step 2: Navigate to Simulate page ────────────────────────────────────
  51  |     const simulateLink = page
  52  |       .getByRole("link", { name: /simulat/i })
  53  |       .or(page.getByRole("button", { name: /simulat/i }));
  54  | 
  55  |     if (await simulateLink.isVisible({ timeout: 5_000 }).catch(() => false)) {
  56  |       await simulateLink.click();
  57  |     } else {
  58  |       await page.goto("/dashboard/simulate");
  59  |     }
  60  | 
  61  |     // ── Step 3: Fill simulation form ─────────────────────────────────────────
  62  |     // Select 10K paths (smallest, fastest) if a selector is present
  63  |     const pathsSelect = page.locator("select").first();
  64  |     if (await pathsSelect.isVisible({ timeout: 3_000 }).catch(() => false)) {
  65  |       await pathsSelect.selectOption({ label: "10,000" }).catch(async () => {
  66  |         // Fallback: try '10000' without comma formatting
  67  |         await pathsSelect.selectOption({ label: "10000" }).catch(() => {
  68  |           // Leave default if neither option text matches — simulation will still run
  69  |         });
  70  |       });
  71  |     }
  72  | 
  73  |     // Submit the form
  74  |     const runBtn = page
  75  |       .getByRole("button", { name: /run|simulate|start/i })
  76  |       .first();
  77  |     await expect(runBtn).toBeEnabled({ timeout: 10_000 });
  78  |     await runBtn.click();
  79  | 
  80  |     // ── Step 4: Progress bar must appear ─────────────────────────────────────
  81  |     const progressBar = page
  82  |       .locator('[role="progressbar"], [class*="progress"], [class*="Progress"]')
  83  |       .first();
  84  | 
> 85  |     await expect(progressBar).toBeVisible({ timeout: 15_000 });
      |                               ^ Error: expect(locator).toBeVisible() failed
  86  | 
  87  |     // ── Step 5: Wait for results (progress disappears or results appear) ──────
  88  |     // Give generous timeout — simulation may take 10–30s on dev machine
  89  |     const resultsContainer = page
  90  |       .locator(
  91  |         '[data-testid="simulation-results"], [class*="SimulationResult"], [class*="result"]'
  92  |       )
  93  |       .first();
  94  | 
  95  |     const probLabel = page.getByText(/prob.*profit|probability.*profit/i).first();
  96  | 
  97  |     await expect(
  98  |       resultsContainer.or(probLabel)
  99  |     ).toBeVisible({ timeout: 60_000 });
  100 | 
  101 |     // ── Step 6: EVT row must be present ──────────────────────────────────────
  102 |     // EVTComparisonRow renders text like "EVT VaR" or "Tail Risk"
  103 |     const evtLabel = page.getByText(/evt|tail risk|pareto|gpd/i).first();
  104 |     await expect(evtLabel).toBeVisible({ timeout: 10_000 });
  105 |   });
  106 | });
  107 | 
```