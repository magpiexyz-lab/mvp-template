---
assumes: [database/supabase, auth/supabase, analytics/posthog]
packages:
  runtime: []
  dev: ["@playwright/test"]
files:  # conditional: global-setup.ts and global-teardown.ts only when all assumes are met
  - playwright.config.ts
  - e2e/global-setup.ts
  - e2e/global-teardown.ts
  - e2e/helpers.ts
  - e2e/smoke.spec.ts
env:
  server: []
  client: []
ci_placeholders: {}
clean:
  files: [playwright.config.ts]
  dirs: [e2e, test-results, playwright-report, blob-report]
gitignore: [/test-results/, /playwright-report/, /blob-report/, /e2e/.auth.json]
---
# Testing: Playwright
> Used when idea.yaml has `stack.testing: playwright` or when the `/change` skill is invoked for test changes
> Assumes: `database/supabase` and `auth/supabase` (test user lifecycle uses Supabase Admin API), `analytics/posthog` (`blockAnalytics` route pattern targets PostHog)

## Packages
```bash
npm install -D @playwright/test
npx playwright install chromium
```

## Files to Create

### `playwright.config.ts` — Playwright configuration
```ts
import { loadEnvConfig } from "@next/env";
loadEnvConfig(process.cwd());

import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  timeout: 30_000,
  fullyParallel: false,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: "html",
  globalSetup: "./e2e/global-setup.ts",
  globalTeardown: "./e2e/global-teardown.ts",
  use: {
    baseURL: process.env.E2E_BASE_URL || "http://localhost:3000",
    trace: "on-first-retry",
  },
  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] } },
  ],
  webServer: {
    command: "npm run dev",
    url: "http://localhost:3000",
    reuseExistingServer: !process.env.CI,
  },
});
```
- Single project (chromium) — cross-browser is out of scope per Rule 4
- `webServer` starts `npm run dev` automatically and waits for the app
- Serial execution (`fullyParallel: false`, `workers: 1`) since funnel tests depend on order
- 1 retry in CI to handle flakiness, 0 locally for fast feedback

### `e2e/global-setup.ts` — Create test user before all tests
```ts
import { createClient } from "@supabase/supabase-js";
import { writeFileSync } from "fs";
import path from "path";

const AUTH_FILE = path.join(__dirname, ".auth.json");

export default async function globalSetup() {
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const serviceRoleKey = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!supabaseUrl || !serviceRoleKey) {
    throw new Error("Missing NEXT_PUBLIC_SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY");
  }
  const supabase = createClient(supabaseUrl, serviceRoleKey);
  const email = `e2e-${Date.now()}@test.example`;
  const password = "test-password-e2e-123";
  const { data, error } = await supabase.auth.admin.createUser({
    email,
    password,
    email_confirm: true,
  });
  if (error) throw new Error(`Failed to create test user: ${error.message}`);
  writeFileSync(AUTH_FILE, JSON.stringify({ email, password, userId: data.user.id }));
}
```
- Uses `supabase.auth.admin.createUser` with `email_confirm: true` to bypass email verification
- Writes credentials to `e2e/.auth.json` for tests to read
- Email pattern `e2e-{timestamp}@test.example` avoids collisions

### `e2e/global-teardown.ts` — Delete test user after all tests
```ts
import { createClient } from "@supabase/supabase-js";
import { readFileSync, unlinkSync } from "fs";
import path from "path";

const AUTH_FILE = path.join(__dirname, ".auth.json");

export default async function globalTeardown() {
  try {
    const { userId } = JSON.parse(readFileSync(AUTH_FILE, "utf-8"));
    const supabase = createClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL!,
      process.env.SUPABASE_SERVICE_ROLE_KEY!,
    );
    await supabase.auth.admin.deleteUser(userId);
    unlinkSync(AUTH_FILE);
  } catch {
    // Swallow errors — cleanup is best-effort
  }
}
```
- Reads user ID from `.auth.json`, deletes via admin API, removes the file
- Swallows all errors so teardown never fails the test run

### `e2e/helpers.ts` — Shared test utilities
```ts
import { readFileSync } from "fs";
import path from "path";
import type { Page } from "@playwright/test";

const AUTH_FILE = path.join(__dirname, ".auth.json");

export function getTestCredentials() {
  return JSON.parse(readFileSync(AUTH_FILE, "utf-8")) as {
    email: string;
    password: string;
    userId: string;
  };
}

export async function login(page: Page, email: string, password: string) {
  await page.goto("/login");
  await page.getByLabel(/email/i).fill(email);
  await page.getByLabel(/password/i).fill(password);
  await page.getByRole("button", { name: /log in|sign in/i }).click();
  await page.waitForURL((url) => !url.pathname.includes("/login"));
}

export async function blockAnalytics(page: Page) {
  await page.route("**/posthog*/**", (route) => route.abort());
}
```
- `login()` uses generic selectors — the skill adjusts these based on actual app code
- `blockAnalytics()` intercepts PostHog network requests via route interception — no app code changes needed. **Provider adaptation:** if analytics is not PostHog, update the route pattern to match that provider's domain (e.g., `**/api.amplitude.com/**` for Amplitude, `**/api.segment.io/**` for Segment). Check the analytics stack file for the provider's endpoint domain.
- `getTestCredentials()` reads from the `.auth.json` written by global setup

### `e2e/smoke.spec.ts` — Funnel smoke tests (generated by /change skill — test type)
```ts
import { test, expect } from "@playwright/test";
import { getTestCredentials, login, blockAnalytics } from "./helpers";

test.describe.serial("Funnel smoke test", () => {
  test.beforeEach(async ({ page }) => {
    await blockAnalytics(page);
  });

  test("visit landing page", async ({ page }) => {
    await page.goto("/");
    await expect(page).toHaveTitle(/.+/);
  });

  // Additional tests generated by /change skill based on EVENTS.yaml funnel
});
```
- Uses `test.describe.serial` so funnel steps run in order
- `blockAnalytics` in `beforeEach` prevents analytics calls during tests
- The /change skill reads EVENTS.yaml and the actual page code to generate one test per funnel step with real selectors and assertions

## Environment Variables
```
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key  # Required for test user lifecycle (server-only, never NEXT_PUBLIC_)
E2E_BASE_URL=http://localhost:3000               # Optional, defaults to localhost:3000
```

**When using the No-Auth Fallback:** the auth-specific service role key is not needed. Only the base URL (optional, defaults to localhost:3000) applies.

## .gitignore Additions
```
# Playwright (update if you change stack.testing)
/test-results/
/playwright-report/
/blob-report/
/e2e/.auth.json
```

## package.json Scripts
```json
{
  "test:e2e": "playwright test",
  "test:e2e:ui": "playwright test --ui"
}
```

## CI Job Template
Add this job to `.github/workflows/ci.yml` after the `build` job:
```yaml
  e2e:
    needs: build
    if: hashFiles('playwright.config.ts') != ''
    runs-on: ubuntu-latest
    timeout-minutes: 10
    env:
      NEXT_PUBLIC_SUPABASE_URL: ${{ secrets.E2E_SUPABASE_URL }}
      NEXT_PUBLIC_SUPABASE_ANON_KEY: ${{ secrets.E2E_SUPABASE_ANON_KEY }}
      SUPABASE_SERVICE_ROLE_KEY: ${{ secrets.E2E_SUPABASE_SERVICE_ROLE_KEY }}
      NEXT_PUBLIC_POSTHOG_KEY: phc_placeholder
      NEXT_PUBLIC_POSTHOG_HOST: https://us.i.posthog.com
      # Payment stack (if stack.payment is present in idea.yaml):
      # STRIPE_SECRET_KEY: ${{ secrets.E2E_STRIPE_SECRET_KEY }}
      # NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY: ${{ secrets.E2E_STRIPE_PUBLISHABLE_KEY }}
      # STRIPE_WEBHOOK_SECRET: ${{ secrets.E2E_STRIPE_WEBHOOK_SECRET }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version-file: '.nvmrc'
          cache: npm
      - name: Check for test secrets
        id: check-secrets
        run: |
          if [ -z "$SUPABASE_SERVICE_ROLE_KEY" ]; then
            echo "skip=true" >> "$GITHUB_OUTPUT"
            echo "E2E secrets not configured — skipping"
          else
            echo "skip=false" >> "$GITHUB_OUTPUT"
          fi
      - name: Install dependencies
        if: steps.check-secrets.outputs.skip != 'true'
        run: npm ci
      - name: Install Playwright browsers
        if: steps.check-secrets.outputs.skip != 'true'
        run: npx playwright install chromium --with-deps
      - name: Run E2E tests
        if: steps.check-secrets.outputs.skip != 'true'
        run: npx playwright test
      - uses: actions/upload-artifact@v4
        if: steps.check-secrets.outputs.skip != 'true' && !cancelled()
        with:
          name: playwright-report
          path: playwright-report/
          retention-days: 7
```

## No-Auth Fallback

When `assumes` dependencies are not met (e.g., no `auth/supabase` or `database/supabase`), use these simplified templates instead of the full versions above. Tests run as anonymous visitors with no login flow.

### `playwright.config.ts` — Simplified (no global setup/teardown)
```ts
import { loadEnvConfig } from "@next/env";
loadEnvConfig(process.cwd());

import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  timeout: 30_000,
  fullyParallel: false,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: "html",
  use: {
    baseURL: process.env.E2E_BASE_URL || "http://localhost:3000",
    trace: "on-first-retry",
  },
  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] } },
  ],
  webServer: {
    command: "npm run dev",
    url: "http://localhost:3000",
    reuseExistingServer: !process.env.CI,
  },
});
```
- No `globalSetup`/`globalTeardown` — no test user lifecycle needed
- Everything else is identical to the full config

### `e2e/helpers.ts` — Simplified (blockAnalytics only)
```ts
import type { Page } from "@playwright/test";

export async function blockAnalytics(page: Page) {
  await page.route("**/posthog*/**", (route) => route.abort());
}
```
- No `getTestCredentials()` or `login()` — tests run as anonymous visitors
- `blockAnalytics()` still prevents analytics pollution. **Provider adaptation:** if analytics is not PostHog, update the route pattern to match that provider's domain (e.g., `**/api.amplitude.com/**` for Amplitude, `**/api.segment.io/**` for Segment). Check the analytics stack file for the provider's endpoint domain.

### `e2e/smoke.spec.ts` — Simplified (anonymous visitor)
```ts
import { test, expect } from "@playwright/test";
import { blockAnalytics } from "./helpers";

test.describe.serial("Funnel smoke test", () => {
  test.beforeEach(async ({ page }) => {
    await blockAnalytics(page);
  });

  test("visit landing page", async ({ page }) => {
    await page.goto("/");
    await expect(page).toHaveTitle(/.+/);
  });

  // Additional tests generated by /change skill based on EVENTS.yaml funnel
});
```
- No `getTestCredentials` or `login` imports — tests as anonymous visitor
- The /change skill adds tests for the app's specific funnel steps

### No-Auth CI Job Template
When using the No-Auth Fallback path, use this CI template instead of the full-auth version above. It omits the `SUPABASE_SERVICE_ROLE_KEY` check and Supabase env vars, running tests unconditionally when `playwright.config.ts` exists.
```yaml
  e2e:
    needs: build
    if: hashFiles('playwright.config.ts') != ''
    runs-on: ubuntu-latest
    timeout-minutes: 10
    env:
      NEXT_PUBLIC_POSTHOG_KEY: phc_placeholder
      NEXT_PUBLIC_POSTHOG_HOST: https://us.i.posthog.com
      # Analytics env vars above are PostHog-specific — adapt if stack.analytics is different
      # Database stack (if stack.database is supabase):
      # NEXT_PUBLIC_SUPABASE_URL: https://placeholder.supabase.co
      # NEXT_PUBLIC_SUPABASE_ANON_KEY: placeholder-anon-key
      # Payment stack (if stack.payment is present in idea.yaml):
      # STRIPE_SECRET_KEY: ${{ secrets.E2E_STRIPE_SECRET_KEY }}
      # NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY: ${{ secrets.E2E_STRIPE_PUBLISHABLE_KEY }}
      # STRIPE_WEBHOOK_SECRET: ${{ secrets.E2E_STRIPE_WEBHOOK_SECRET }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version-file: '.nvmrc'
          cache: npm
      - name: Install dependencies
        run: npm ci
      - name: Install Playwright browsers
        run: npx playwright install chromium --with-deps
      - name: Run E2E tests
        run: npx playwright test
      - uses: actions/upload-artifact@v4
        if: ${{ !cancelled() }}
        with:
          name: playwright-report
          path: playwright-report/
          retention-days: 7
```

## Patterns
- **Serial tests for funnel**: use `test.describe.serial` — funnel steps depend on each other (signup before activation, activation before payment)
- **Block analytics**: always call `blockAnalytics(page)` in `beforeEach` — tests should not pollute analytics data
- **Test user email pattern**: `e2e-{timestamp}@test.example` — unique per run, clearly identifiable for cleanup
- **Admin API for user lifecycle**: create via `supabase.auth.admin.createUser`, delete via `supabase.auth.admin.deleteUser` — never use the signup form for test user creation
- **Stripe test card**: when `stack.payment` is present, use card number `4242424242424242`, any future expiry, any CVC
- **Funnel happy path only**: test the success path through each funnel step — skip error states, edge cases, and `retain_return` (24h delay makes it untestable)
- **Real selectors from app code**: the /change skill reads actual page components to determine selectors — never guess

## Security
- `SUPABASE_SERVICE_ROLE_KEY` is server-only — never prefix with `NEXT_PUBLIC_`
- `e2e/.auth.json` is gitignored — contains test credentials that should not be committed
- Test users are created and deleted per run — no persistent test accounts

## PR Instructions
- Add `SUPABASE_SERVICE_ROLE_KEY` to `.env.local` (get from Supabase Dashboard → Settings → API → `service_role` key)
- Run `npm run test:e2e` locally to verify tests pass
- For CI: add these secrets to GitHub repo settings (Settings → Secrets and variables → Actions):
  - `E2E_SUPABASE_URL` — your Supabase project URL
  - `E2E_SUPABASE_ANON_KEY` — your Supabase anon key
  - `E2E_SUPABASE_SERVICE_ROLE_KEY` — your Supabase service role key
- If `stack.payment` is present: also add Stripe CI secrets (`E2E_STRIPE_SECRET_KEY`, `E2E_STRIPE_PUBLISHABLE_KEY`, `E2E_STRIPE_WEBHOOK_SECRET`)
- CI E2E job runs only when `playwright.config.ts` exists and secrets are configured — zero friction for repos without E2E

**When using the No-Auth Fallback path:** CI secrets are not required — tests run unconditionally. Just run `npm run test:e2e` locally to verify.
