---
description: "Use when starting a new experiment from a filled-in idea.yaml. Run once per project."
type: code-writing
reads:
  - idea/idea.yaml
  - EVENTS.yaml
  - CLAUDE.md
stack_categories: [framework, database, auth, analytics, ui, payment, hosting, testing]
requires_approval: true
references:
  - .claude/patterns/verify.md
  - .claude/patterns/branch.md
branch_prefix: feat
modifies_specs: false
---
Bootstrap the MVP from idea.yaml.

## Step 0: Branch Setup

Follow the branch setup procedure in `.claude/patterns/branch.md`. Use branch prefix `feat` and branch name `feat/bootstrap`.

## Phase 1: Plan (BEFORE writing any code)

DO NOT write any code, create any files, or run any install commands during this phase.

1. **Read context files**
   - Read `idea/idea.yaml` — this is the single source of truth
   - Read `EVENTS.yaml` — these are the canonical analytics events to wire up
   - Read `CLAUDE.md` — these are the rules to follow

2. **Resolve the stack**
   - Read idea.yaml `stack`. For each category present in idea.yaml `stack` (always: framework, analytics, ui, hosting; optional: database, auth, payment, testing), read `.claude/stacks/<category>/<value>.md`.
   - If a stack file doesn't exist for a given value, use your own knowledge of that technology and follow the same structural patterns as existing stack files.
   - These files define packages, library files, env vars, and patterns for each technology.
   - For each stack file read, validate its `assumes` entries: every `category/value` in the file's `assumes` list must match a `category: value` pair in idea.yaml `stack`. If any assumption is unmet, stop and list the incompatibilities (e.g., "analytics/posthog assumes framework/nextjs, but your stack has framework: remix"). The user must either change the mismatched stack value or create a compatible stack file.

3. **Validate idea.yaml**
   - Every one of these fields must be present and non-empty (strings must be non-blank, lists must have at least one item): `name`, `title`, `owner`, `problem`, `solution`, `target_user`, `distribution`, `pages`, `features`, `primary_metric`, `target_value`, `measurement_window`, `stack`
   - If ANY field still contains "TODO" or is missing: stop, list exactly which fields need to be filled in, and do nothing else
   - Verify `pages` includes an entry with `name: landing` (required)
   - Verify `name` is lowercase with hyphens only (no spaces, no uppercase)
   - If `stack.payment` is present, verify `stack.auth` is also present. If not: stop and tell the user: "Payment requires authentication to identify the paying user. Add `auth: supabase` (or another auth provider) to your idea.yaml `stack` section."
   - If `stack.payment` is present, verify `stack.database` is also present. If not: stop and tell the user: "Payment requires a database to record transaction state. Add `database: supabase` (or another database provider) to your idea.yaml `stack` section."

4. **Check preconditions**
   - If `package.json` exists AND the `src/` directory contains application files (check for any `.ts` or `.tsx` files): stop and tell the user: "This project has already been bootstrapped. Use `/change ...` to make changes, or run `make clean` to start over."
   - If `package.json` exists but the `src/` directory does NOT contain application files: warn the user: "A previous bootstrap may have partially completed. I'll continue from the beginning — packages may be reinstalled." Note: the branch name `feat/bootstrap` may already exist from the previous attempt. If so, this run will use `feat/bootstrap-2` — you can delete the old branch later with `git branch -d feat/bootstrap`. Then proceed.

5. **Present the plan** in plain language the user can verify:

   ```
   ## What I'll Build

   **Pages:**
   - Landing Page (/) — [purpose from idea.yaml]
   - [Page Name] (/route) — [purpose from idea.yaml]
   - ...

   **Features:**
   - [feature 1] → built in [file(s)]
   - [feature 2] → built in [file(s)]
   - ...

   **Database Tables (if any):**
   - [table name] — stores [what]
   - ...

   **Analytics Events:**
   - [For each EVENTS.yaml standard_funnel event, show: event_name on Page Name]
   - [For each payment_funnel event if stack.payment present, show: event_name on page/route]

   **Activation mapping:**
   - idea.yaml primary_metric: [metric]
   - activate event action value: "[concrete_action]" (e.g., "created_invoice") — or "N/A — all features are descriptive, activate will be omitted" if no feature involves an interactive user action

   **Tests (if stack.testing present):**
   - Template path: Full templates (all assumes met) | No-Auth Fallback (assumes unmet: [list])
   - Smoke tests for: [list each page name]

   **Questions:**
   - [any ambiguities — or "None"]
   ```

6. **STOP.** End your response here. Say:
   > Does this plan look right? Reply **approve** to proceed, or tell me what to change.

   DO NOT proceed to Phase 2 until the user explicitly replies with approval.
   If the user requests changes instead of approving, revise the plan to address their feedback and present it again. Repeat until approved.

7. **Save the approved plan.** Write the plan you presented above to `.claude/current-plan.md`. This file persists the plan across context compression and serves as the reference for checkpoint verification.

## Phase 2: Implement (only after the user has approved)

### Step 1: Project initialization
- Create `package.json` with `name` from idea.yaml and project setup from the framework stack file (.nvmrc, scripts, engines, tsconfig, config)
- Install packages from all stack files whose categories are present in idea.yaml `stack`
- Install dev dependencies from the framework and UI stack files
- Run the UI setup commands from the UI stack file
- After UI setup, verify the UI stack file's post-setup checks pass (PostCSS config, globals.css, scripts intact). If any post-setup check fails: stop and tell the user which check failed and how to fix it (e.g., "PostCSS config was overwritten by shadcn init — restore it from the framework stack file template"). Do not proceed to Step 2 until all post-setup checks pass.
- If any install command fails: stop, show the error, and ask the user to fix the environment issue. After fixing, tell Claude: "Continue the bootstrap on this branch from the install step." Claude will re-run the failed install and any subsequent install commands, then continue with Step 2. Do NOT re-run `/bootstrap` (that would create a duplicate branch). If you close this conversation: either (1) commit partial files on this branch (`git add -A && git commit -m "WIP: partial install"`), then tell Claude "Continue the bootstrap on this branch from the install step"; or (2) switch to main (`git checkout main`), run `make clean`, and start `/bootstrap` fresh.

### Step 2: Core library files
- Create the library files specified in each stack file's "Files to Create" section:
  - Analytics library (from the analytics stack file)
  - If `stack.database` is present: database clients (from the database stack file)
- If `stack.auth` is present, create auth files from the auth stack file using the correct conditional path:
  - If `stack.database` matches the auth provider (e.g., both `supabase`): auth shares the database client files — only create auth-specific pages (signup, login)
  - If `stack.database` is absent or a different provider: create standalone auth library files from the "Standalone Client" section (e.g., `supabase-auth.ts` instead of `supabase.ts`)
- If both `stack.auth` and `stack.payment` are present, create auth library files and pages first — payment templates reference `user.id` which requires auth.
- If `stack.payment` is present, create the payment library files from the payment stack file's "Files to Create" section. Note: the payment stack file's checkout route template intentionally references `user.id` which is undefined until auth is integrated — this will cause a build error at Checkpoint B that you must fix by adding the auth check (see the auth stack file's "Server-Side Auth Check" section). The webhook route template also contains a `// TODO: Update user's payment status in database` — unlike the auth check, this TODO compiles silently, so you must resolve it using the database schema planned in Phase 1.
- Replace placeholder constants: In BOTH analytics library files (`src/lib/analytics.ts` and `src/lib/analytics-server.ts`), replace `PROJECT_NAME = "TODO"` with the `name` from idea.yaml and `PROJECT_OWNER = "TODO"` with the `owner` from idea.yaml. These constants auto-attach to every event — if left as TODO, experiment filtering will fail.
- Generate `src/lib/events.ts` with typed track wrapper functions from EVENTS.yaml. For each event, create a function like `trackVisitLanding(props: { referrer?: string; utm_source?: string })` that calls `track("visit_landing", props)`. Only generate wrappers for standard_funnel events and (if stack.payment is present) payment_funnel events. Pages should import from `events.ts` instead of calling `track()` directly with string event names.

### Checkpoint A — verify library layer
- Re-read `.claude/current-plan.md` to confirm implementation aligns with the approved plan.
- Run `npm run build` to verify all library files compile correctly
- If the build fails: fix the errors in the library files before proceeding. These files are imported by every page — errors here cascade into everything downstream. After fixing, re-run `npm run build` to confirm.
- If the build still fails after 2 fix attempts, proceed to the next step without retrying further at this checkpoint — Step 8 (final verification in `.claude/patterns/verify.md`) has its own 3-attempt retry budget that will catch any remaining issues.

### Step 3: App shell
- Follow the framework stack file's file structure and page conventions
- **Root layout**: metadata from idea.yaml `title`, import globals.css. Also implement `retain_return` tracking following the framework stack file's `retain_return` section and EVENTS.yaml
- **404 page**: simple not-found page with link back to `/`
- **Error boundary**: user-friendly message and retry button

### Step 4: Pages from idea.yaml
For each entry in idea.yaml `pages`:
- If `name` is `landing` → create the root page
- Otherwise → create a page at the appropriate route
- Every page file must:
  - Follow page conventions from the framework stack file
  - Import tracking functions per the analytics stack file conventions
  - Fire the appropriate EVENTS.yaml event(s) on the correct trigger
  - If a standard_funnel event from EVENTS.yaml has no matching page in idea.yaml (e.g., no signup page for signup_start/signup_complete), omit that event — do not create a page just to fire it
- **Landing page specifically**: headline from idea.yaml `title`, subheadline from `solution` (first sentence), CTA button linking to the next logical page (signup if it exists in idea.yaml pages, otherwise the first non-landing page; if landing is the only page, build the idea.yaml features as sections on the landing page below the hero and use a CTA that scrolls to the first feature section via anchor link (e.g., `href="#get-started"`) — do not link to a nonexistent route or add functionality beyond what is listed in `features`; if any feature is interactive (the user can take an action like submitting a form or creating a record), fire `activate` when they complete that action — if all features are descriptive with no user action, omit the `activate` event and note the omission in the PR body), fire the landing page event from EVENTS.yaml on mount with its specified properties
- **Auth pages (if listed)**: signup/login forms using auth provider UI (see auth stack file). Fire the corresponding EVENTS.yaml events at their specified triggers. Update the post-auth redirect in signup and login pages to navigate to the first non-auth, non-landing page from idea.yaml (e.g., `/dashboard`). If no such page exists, keep the redirect to `/`.
- **All other pages**: functional layout with heading, description matching the page's `purpose` from idea.yaml, and a clear next-action CTA. Not blank placeholders — each page should feel like a real (if minimal) screen

> **STOP** — verify analytics before proceeding. Every page must fire its EVENTS.yaml event(s). Every user action listed in EVENTS.yaml must have a tracking call. Do not move to Checkpoint B until each event is wired. "I'll add analytics later" is not acceptable.

### Checkpoint B — verify pages layer
- Re-read `.claude/current-plan.md` to confirm implementation aligns with the approved plan.
- Run `npm run build` to verify all pages compile and their imports from the library files resolve correctly
- If the build fails: fix the errors in the page files (or in the library files they import from) before proceeding. After fixing, re-run `npm run build` to confirm.
- If the build still fails after 2 fix attempts, proceed to the next step without retrying further at this checkpoint — Step 8 (final verification in `.claude/patterns/verify.md`) has its own 3-attempt retry budget that will catch any remaining issues.

### Step 5: API routes
- Create the API routes directory per the framework stack file
- If idea.yaml features imply mutations (creating records, payments, etc.), create corresponding API route handlers. If `stack.payment` is present: for payment routes, use the templates from the payment stack file's "API Routes" section — these include auth-integration checks and webhook signature verification patterns that must not be omitted.
- For the webhook handler's `// TODO: Update user's payment status in database` comment: resolve it using the database schema you planned in Phase 1. If no payments/subscriptions table was planned, add one to the migration in Step 6 and return here to wire the webhook update after the table exists.
- Every API route: validate input with zod, return proper HTTP status codes. If `stack.database` is present, use the server-side database client for data access.
- Follow the hosting stack file for rate limiting guidance in auth and payment API route handlers. Mention any limitations in the PR body so the user knows to address them before production

### Step 6: Database schema (if needed)
If `stack.database` is present and idea.yaml features require persistent data:
- Follow the schema management approach from the database stack file
- Create the initial migration with all tables needed for idea.yaml features. Migration numbering is based on the current branch state — concurrent branches may create conflicting numbers, which should be resolved by renumbering at merge time.
- If `stack.payment` is present and a payments/subscriptions table was created: return to the webhook handler (`src/app/api/webhooks/stripe/route.ts`) and resolve the `// TODO: Update user's payment status in database` using the new table before proceeding to Step 7.
- Also create `src/lib/types.ts` with TypeScript types matching the table schemas
- Include post-merge database setup instructions in the PR body (see database stack file's "PR Instructions" section)

If no features require database tables, skip this step.

### Step 7: Environment config
- Generate `.env.example` by combining all environment variables from active stack files (framework, database, analytics, and any others that define env vars)

### Step 7b: Test scaffolding (if stack.testing is present)

If `stack.testing` is present in idea.yaml:
- Read the testing stack file at `.claude/stacks/testing/<value>.md`
- Check assumes: for each `category/value` in the testing stack file's `assumes` list, verify
  it matches idea.yaml `stack`. If all match → use full templates. If any unmet → use No-Auth
  Fallback templates.
- Install packages: `npm install -D @playwright/test && npx playwright install chromium`
- Create files per the chosen template path:
  - `playwright.config.ts` (full or no-auth)
  - `e2e/helpers.ts` (full or no-auth)
  - If full-auth path: `e2e/global-setup.ts` and `e2e/global-teardown.ts`
- Generate `e2e/smoke.spec.ts` with one page-load test per idea.yaml page:
  ```ts
  test("[page name] loads", async ({ page }) => {
    await page.goto("/[route]");
    await expect(page).toHaveTitle(/.+/);
  });
  ```
  These are page-load smoke tests only — not full funnel tests with selectors.
- Add `.gitignore` entries per testing stack file
- Add `test:e2e` and `test:e2e:ui` scripts to `package.json`
- If the existing CI e2e job in `.github/workflows/ci.yml` does not match the chosen
  template path (full-auth vs. no-auth fallback), replace the `e2e:` job with the
  testing stack file's correct CI Job Template for that path.
- Add env vars from testing stack file to `.env.example` (based on chosen template path)
- NOTE: Tests are NOT run during bootstrap — only created

If `stack.testing` is NOT present in idea.yaml: skip this step entirely.

### Step 8: Verify before shipping
- Follow the verification procedure in `.claude/patterns/verify.md` (build & lint with retry)

### Step 8b: Spec compliance check

Re-read `.claude/current-plan.md` and `idea/idea.yaml` now. Verify each of these before proceeding to the PR:
- For each page in `pages`: confirm `src/app/<page-name>/page.tsx` exists (or root page for `landing`)
- For each feature in `features`: confirm the implementation addresses it
- For each standard_funnel event in `EVENTS.yaml`: confirm a tracking call exists in the appropriate page
- If `stack.payment` is present: confirm the webhook handler does not contain `// TODO: Update user's payment status` (this compiles silently — verify it was resolved in Step 5/6)
- If anything is missing, implement it now. Do not proceed with gaps.

### Step 9: Commit, push, open PR
- You are already on a feature branch (created in Step 0). Do not create another branch.
- Stage all new files and commit: "Bootstrap MVP scaffold from idea.yaml"
- Push and open PR using the `.github/PULL_REQUEST_TEMPLATE.md` format:
  - **Summary**: plain-English explanation — "Full MVP scaffold generated from idea.yaml" with key highlights
  - **How to Test**: "After merging: 1) [If database migrations were created: run the migration SQL — see post-merge instructions below.] Copy .env.example to .env.local and fill in keys, 2) Add the same env vars to Vercel (Project → Settings → Environment Variables), 3) Run `npm run dev` and visit each page locally, 4) Run `make deploy` to deploy to production, 5) Run `/verify` in Claude Code to run E2E tests against the deployed app"
  - **What Changed**: list every file created and its purpose
  - **Why**: reference the idea.yaml problem/solution
  - **Checklist — Scope**: check all boxes (only built what's in idea.yaml)
  - **Checklist — Analytics**: list every event wired and which page fires it
  - **Checklist — Build**: confirm build passes, no hardcoded secrets, .env.example created
- Add a prominent note at the top of the PR body with post-merge instructions: database setup (from database stack file), environment variable setup (from .env.example)
- Fill in **every** section of the PR template. Empty sections are not acceptable. If a section does not apply, write "N/A" with a one-line reason.
- If `git push` or `gh pr create` fails: show the error and tell the user to check their GitHub authentication (`gh auth status`) and remote configuration (`git remote -v`), then retry the push and PR creation.
- Delete `.claude/current-plan.md` — the plan is now captured in the PR description.

## Do NOT
- Add pages not listed in idea.yaml `pages`
- Add features not listed in idea.yaml `features`
- Add libraries not in idea.yaml `stack` (small utilities like clsx are fine)
- Add full funnel tests — bootstrap creates page-load smoke tests only when stack.testing is present; use /change for funnel tests with real selectors
- Violate the restrictions listed in the framework stack file
- Add placeholder "lorem ipsum" text — use real copy derived from idea.yaml
- Skip the build verification step
- Commit to main directly
