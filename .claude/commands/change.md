---
description: "Use for any modification to an existing bootstrapped app: new features, bug fixes, UI polish, analytics fixes, or adding tests."
type: code-writing
reads:
  - idea/idea.yaml
  - EVENTS.yaml
  - CLAUDE.md
stack_categories: [framework, database, auth, analytics, ui, payment, testing, hosting]
requires_approval: true
references:
  - .claude/patterns/verify.md
  - .claude/patterns/branch.md
branch_prefix: change
modifies_specs: true
---
Make a change to the existing app: $ARGUMENTS

## Step 0: Branch Setup

Follow the branch setup procedure in `.claude/patterns/branch.md`. Use branch prefix `change` and slugify `$ARGUMENTS` for the branch name.

## Step 1: Validate input

- If `$ARGUMENTS` is empty or unclear: stop and ask the user to describe what they want to change
- If `$ARGUMENTS` contains `#<number>` or is just a number: read the GitHub issue via `gh issue view <number>` and use its content as the change description. If `gh issue view` fails (issue not found, permission denied, or network error), tell the user: "Could not read issue #<number>. Describe the change directly, or check `gh auth status` and retry."

## Step 2: Read context

- Read `idea/idea.yaml` — understand the current scope, existing pages, existing features, target user, primary metric
- Read `EVENTS.yaml` — understand existing analytics events (this is the canonical event list)
- Resolve the stack: read idea.yaml `stack`. For each category, read `.claude/stacks/<category>/<value>.md`. If a stack file doesn't exist, use your knowledge of that technology.
- Scan `src/app/` to understand the current page structure and codebase state

## Step 3: Check preconditions

- Verify `package.json` exists. If not, stop and tell the user: "No app found. Run `/bootstrap` first, or if you already have a bootstrap PR open, merge it before running `/change`."
- Verify `EVENTS.yaml` exists. If not, stop and tell the user: "EVENTS.yaml not found. This file defines all analytics events and is required. Restore it from your template repo or re-create it following the format in the EVENTS.yaml section of the template."
- Run `npm run build` to confirm the project compiles before making changes (unless the change IS about fixing the build or is classified as a Fix). If the build fails and the change is not a build fix or Fix-type change: stop and tell the user: "The app has build errors that need to be fixed first. Run `/change fix build errors` to address them. After that PR is merged, re-run your original change. Note: the current branch will be abandoned — this is expected. You can delete it later with `git branch -d` followed by the branch name created in Step 0. Re-running `/change` creates a new branch (the name may have a numeric suffix like `-2` if the old branch still exists)."
- For analytics changes: verify the analytics library file exists (see analytics stack file for expected path). If it doesn't, stop and tell the user: "Analytics library not found. Run `/bootstrap` first."
- If `$ARGUMENTS` mentions payment or the change will add `payment` to the stack: verify `stack.auth` and `stack.database` are present in idea.yaml. If `stack.auth` is missing, stop: "Payment requires authentication. Add `auth: supabase` (or another auth provider) to idea.yaml `stack` first." If `stack.database` is missing, stop: "Payment requires a database. Add `database: supabase` (or another database provider) to idea.yaml `stack` first."
- If `testing` is present in idea.yaml `stack` and the classified type is NOT Test: read the testing stack file's `assumes` list and verify each `category/value` pair against idea.yaml `stack`. If any assumption is unmet, warn: "Your testing setup assumes [unmet dependencies]. Tests may fail. Consider running `/change fix test configuration` or removing `testing` from idea.yaml `stack`."
- If classified as Test type: read the testing stack file's `assumes` list and check each `category/value` against idea.yaml `stack` (per bootstrap's validation approach: the value must match, not just the category). Record the result — this determines the template path reported in the plan.

## Step 4: Classify the change

Determine the type from `$ARGUMENTS`:

| Type      | Signal                                     |
|-----------|---------------------------------------------|
| Feature   | Adds capability that doesn't exist today    |
| Fix       | Repairs broken behavior                     |
| Polish    | Improves UX/copy/visuals of existing stuff  |
| Analytics | Fixes/audits analytics coverage             |
| Test      | Adds or fixes tests                         |

State the classification before proceeding: "I'm treating this as a **[type]** change."

---

## Phase 1: Plan (BEFORE writing any code)

DO NOT write any code, create any files, or run any install commands during this phase.

Present the plan using the format for the classified type:

### Feature plan
```
## What I'll Add

**Feature:** [description from $ARGUMENTS]
**Complexity:** Simple (single layer) | Multi-layer (spans pages + API + DB)

**New pages (if any):**
- [Page Name] (/route) — [purpose]

**Files I'll create or modify:**
- [file] — [what changes]

**New database tables (if any):**
- [table] — stores [what]

**New analytics events (if any):**
- [event_name] — fires when [trigger]

**Questions:**
- [any ambiguities, or "None"]
- [if new library needed: "This feature needs [library]. Should I add it?"]
```

### Fix plan
```
## Bug Diagnosis

**Bug:** [description from $ARGUMENTS]
**Root cause:** [why this happens]

**Files affected:**
- [file] — [what's wrong]

**Fix approach:** [what you'll change, minimal diff]
**Risk:** [what else could be affected, or "Low — isolated change"]
```

### Polish plan
```
## Planned Changes

1. **[Page/Component]**: [what you'll change] — [why this improves things for target_user]
2. ...
```

### Analytics plan
```
## Audit Report

### Standard Funnel Events
| Event | Expected Location | Status | Issue |
|-------|-------------------|--------|-------|
| [event from EVENTS.yaml] | [page] | ✅/❌/⚠️ | [issue or —] |

### Custom Events
| Event | Expected Location | Status | Issue |
|-------|-------------------|--------|-------|
| (from EVENTS.yaml custom_events) | ... | ... | ... |

### Suggested Custom Events (if any)
- [event_name] — fires when [trigger]
```

### Test plan
```
## Smoke Test Plan

**Funnel Steps:**
| # | Event | Route | Browser Actions | Selectors |
|---|-------|-------|-----------------|-----------|
| 1 | [event] | [route] | [actions] | [selectors from app code] |

**Skipped:** retain_return (requires 24h delay)

**Activation Detail:**
- primary_metric: [from idea.yaml]
- Activation test: [what the test will do]

**Files to Create/Modify:**
- [list of files]

**Template path:** Full templates (all assumes met) | No-Auth Fallback (assumes unmet: [list unmet category/value pairs])
```

### STOP. End your response here. Say:
> Does this plan look right? Reply **approve** to proceed, or tell me what to change.

DO NOT proceed to Phase 2 until the user explicitly replies with approval.
If the user requests changes instead of approving, revise the plan to address their feedback and present it again. Repeat until approved.

---

## Phase 2: Implement (only after the user has approved)

### Step 5: Update specs (type-specific)

- **Feature**: add the new feature to idea.yaml `features` list. Add any new pages to `pages` list. Do NOT remove or modify existing features or pages.
- **Analytics**: if the user approved custom events, add them to `custom_events` in EVENTS.yaml following the `<object>_<action>` naming convention with all properties.
- **Fix / Polish**: do NOT modify idea.yaml or EVENTS.yaml.
- **Test**: do NOT modify EVENTS.yaml. If adding tests for the first time (no `stack.testing` in idea.yaml and no `playwright.config.ts` on disk), add `testing: <value>` to idea.yaml `stack` section. Do not modify other parts of idea.yaml.

### Step 6: Make changes (type-specific)

#### Feature constraints
- If adding `payment` to idea.yaml `stack`: verify both `stack.auth` and `stack.database` are also present. If `stack.auth` is missing, stop and tell the user: "Payment requires authentication to identify the paying user. Add `auth: supabase` (or another auth provider) to idea.yaml `stack` first." If `stack.database` is missing, stop and tell the user: "Payment requires a database to record transaction state. Add `database: supabase` (or another database provider) to your idea.yaml `stack` section."
- If the change requires a stack category whose library files don't exist yet (e.g., `payment: stripe` was just added to idea.yaml but `src/lib/stripe.ts` is missing): install the packages listed in the stack file's "Packages" section, create the library files from its "Files to Create" section, and add its environment variables to `.env.example` — before proceeding to routes and pages. If any install command fails, stop and show the error — the user must fix the environment issue, then retry the failed install command on this branch (do NOT re-run `/change`).
- Wire analytics: every user action in the new feature must fire a tracked event
- Create new pages following the framework stack file's file structure
- Every new page: follow page conventions from the framework stack file, import tracking functions per the analytics stack file, fire appropriate EVENTS.yaml events

> **STOP** — verify analytics before proceeding. Every new page must fire its events from EVENTS.yaml. Every user action in the new feature must have a tracking call. Do not proceed until confirmed. "I'll add analytics later" is not acceptable.

- Create or modify API routes for any new mutations (see framework stack file for route conventions). Every API route: validate input with zod, return proper HTTP status codes. If `stack.database` is present, use the server-side database client for data access.
- If database tables are needed: create a migration following the database stack file (next sequential number, `IF NOT EXISTS`), add TypeScript types, add post-merge instructions to PR body. Note: concurrent branches may create conflicting migration numbers — resolve by renumbering the later-merged migration at merge time.
- **If Multi-layer**: implement in two sub-steps with an intermediate build check:
  - Sub-step 6a — Data and server layer (migrations, types, API routes)
  - Checkpoint: run `npm run build`. Fix errors before proceeding. If still broken after 2 attempts, proceed to Sub-step 6b without retrying — Step 7 (verification) has its own 3-attempt retry budget.
  - Sub-step 6b — Client layer (pages, components, analytics wiring)

#### Fix constraints
- Make the minimal change needed — smaller diffs are easier to review
- Fix only the root cause, no refactoring of surrounding code
- If the fix touches auth or payment code: add or update a test (per CLAUDE.md Rule 4)
- Check that analytics events on modified pages are still intact

#### Polish constraints
- No new features, pages, routes, or libraries
- Copywriting principles: headline = outcome for target_user (not what the product does), CTA = action verb + outcome
- Keep it to one screen: headline, subheadline, CTA. Remove anything that doesn't serve conversion
- Count steps between CTA click and first value moment — remove or defer unnecessary fields
- Every required field: inline validation errors. Every async button: loading state. API errors: user-friendly messages.
- Consistent spacing, component usage, text hierarchy, mobile layout
- Preserve all existing analytics events

#### Analytics constraints
- Fix gaps per the audit: add missing tracking calls with all required properties, add missing properties to incomplete calls
- Do NOT change event names — they must match EVENTS.yaml exactly
- Do NOT remove existing correct analytics calls
- Only add custom events the user explicitly approved

#### Test constraints
- Do NOT modify application code — tests observe the app, they don't change it
- Install packages per the testing stack file, create config and helpers per the testing stack file templates
- Test funnel happy path only — skip error states, edge cases, and `retain_return`
- Read actual page source code for selectors — never guess
- Call `blockAnalytics(page)` in `beforeEach` to prevent analytics pollution. The default `blockAnalytics` route pattern targets PostHog — if the analytics provider is different, adapt the route pattern using the endpoint domain from the analytics stack file.
- For payment tests: use Stripe test card `4242424242424242`
- Before applying testing stack file templates: read the testing stack file's `assumes` list. For each `category/value` entry, verify that idea.yaml `stack` has a matching `category: value` pair (e.g., `analytics/posthog` requires `stack.analytics: posthog`, not just that `analytics` is present). If ALL assumed dependencies match → use the full templates (global-setup/teardown, login helper, auth-based tests). If ANY assumed dependency is unmet → use the testing stack file's "No-Auth Fallback" section instead (no global-setup/teardown, no login helper, tests run as anonymous visitors). Document the chosen path in the PR body.
- Update `.gitignore` and CI workflow per the testing stack file. Add env vars to `.env.example` based on the chosen template path (full or no-auth fallback), not solely from the frontmatter.
- If `stack.payment` is present, uncomment payment-related env vars in the testing CI template when generating the CI job.

### Step 7: Verify
- Follow the verification procedure in `.claude/patterns/verify.md` (build & lint with retry)
- Type-specific checks:
  - **Feature**: trace the user flow — can a user discover, use, and complete the feature? Verify all new analytics events fire.
  - **Fix**: trace the bug report's user flow through code to confirm it's fixed.
  - **Polish**: open each changed file and confirm analytics imports and event calls are intact.
  - **Analytics**: re-trace each standard funnel event through the code to confirm it now fires correctly.
  - **Test**: run `npx playwright test --list` to verify test discovery works. If test discovery fails, treat it as a build error — fix the test files and re-run. If still failing after the verify.md retry budget, report to the user with the error output.
  - **Feature (spec compliance)**: Re-read `idea/idea.yaml`. For each page in `pages`, confirm `src/app/<page-name>/page.tsx` exists. For each feature in `features`, confirm the implementation addresses it. For each event in `EVENTS.yaml`, confirm tracking calls are intact. If anything is missing, fix it before proceeding.

### Step 8: Commit, push, open PR
- You are already on a feature branch (created in Step 0). Do not create another branch.
- Commit message: imperative mood describing the change (e.g., "Add invoice email reminders", "Fix email validation on signup form", "Polish landing copy and error states")
- Push and open PR using `.github/PULL_REQUEST_TEMPLATE.md` format:
  - **Summary**: plain-English description of the change
  - **How to Test**: steps to verify the change works after merging
  - **What Changed**: list every file created/modified and what changed
  - **Why**: how this change serves the target user and primary metric. If from a GitHub issue, include `Closes #<number>`.
  - **Checklist — Scope**: check all boxes. For features: confirm idea.yaml was updated.
  - **Checklist — Analytics**: list all new/modified events and which pages fire them. For fixes/polish: confirm no events were removed or broken.
  - **Checklist — Build**: confirm build passes, no hardcoded secrets
- Fill in **every** section of the PR template. Empty sections are not acceptable. If a section does not apply, write "N/A" with a one-line reason.
- If `git push` or `gh pr create` fails: show the error and tell the user to check their GitHub authentication (`gh auth status`) and remote configuration (`git remote -v`), then retry.

## Do NOT
- Add more than what `$ARGUMENTS` describes — one change per PR
- Modify existing features unless the change requires integration (e.g., adding a nav link)
- Remove or break existing analytics events (unless the change is specifically about fixing analytics)
- Add libraries not in idea.yaml `stack` without user approval
- Skip updating idea.yaml when adding new features — the source of truth must always reflect the current app
- Change analytics event names — they must match EVENTS.yaml
- Add custom analytics events without user approval
- Add error-state tests — funnel happy path only (Rule 4)
- Mock services in tests — the whole point is testing real integrations
- Skip the build verification step
- Commit to main directly
