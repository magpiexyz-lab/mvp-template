---
description: "Use after deploying to verify the experiment works. Runs E2E tests and fixes failures."
type: code-writing
reads:
  - idea/idea.yaml
  - EVENTS.yaml
stack_categories: [testing, framework, analytics]
requires_approval: false
references:
  - .claude/patterns/verify.md
  - .claude/patterns/branch.md
branch_prefix: fix
modifies_specs: false
---
Verify the deployed experiment works by running E2E tests.

## Step 0: Read context

- Read `idea/idea.yaml` — understand pages, features, stack
- Read `EVENTS.yaml` — understand tracked events
- If `stack.testing` is present in idea.yaml, read `.claude/stacks/testing/<value>.md`
- Verify `playwright.config.ts` exists. If not: "No test configuration found. Add
  `testing: playwright` to idea.yaml `stack` and re-run `/bootstrap`, or run
  `/change add E2E smoke tests`."
- Verify `@playwright/test` is in package.json devDependencies. If not: "Playwright
  is not installed. Run `npm install -D @playwright/test && npx playwright install chromium`."

## Step 1: Run tests

- Run `npx playwright test`
- Capture the full output

## Step 2: Report results

- If ALL tests pass: report success with test count and summary. **Done.** No branch, no PR, no further steps.
- If any tests fail: proceed to Step 3

## Step 3: Branch setup

Follow `.claude/patterns/branch.md` with prefix `fix` and name `fix/e2e-failures`.

## Step 4: Fix failures (max 3 attempts)

For each attempt:
1. Read the test output — identify which tests failed and why
2. Read the failing test files and the app code they exercise
3. Fix the issues (may be test code or app code — fix whatever is actually wrong)
4. Re-run `npx playwright test`
5. If all pass: proceed to Step 5
6. If still failing: note what you tried, start next attempt

If all 3 attempts fail: report to the user with attempt history and remaining errors.
Offer options: (1) tell me what to try, (2) save progress as WIP commit on this branch.

## Step 5: Verify build

Follow `.claude/patterns/verify.md` (build & lint with retry).

## Step 6: Commit, push, open PR

- Commit: descriptive message about what was fixed (e.g., "Fix landing page title assertion in E2E smoke test")
- Push and open PR using `.github/PULL_REQUEST_TEMPLATE.md`:
  - **Summary**: what tests were failing and what was fixed
  - **How to Test**: "Run `npm run test:e2e` — all tests should pass"
  - **What Changed**: files modified and why
  - **Why**: tests were failing after deploy; fixes ensure the experiment is verified
  - **Checklist**: standard checks

## Do NOT
- Modify idea.yaml or EVENTS.yaml
- Add new features — only fix what tests expose
- Run tests against production (always use local dev server)
- Skip the build verification step
- Commit to main directly
