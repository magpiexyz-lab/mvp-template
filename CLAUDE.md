# CLAUDE.md — Experiment Template Rules (v1.0)

Read `idea/idea.yaml` before every task. It is the single source of truth for what to build.

Rules are in priority order. When two rules conflict, the lower-numbered rule wins.

## Rule 0: Scope Lock
- Only build what is described in `idea/idea.yaml`
- If a feature isn't listed in `features`, don't build it
- If a page isn't listed in `pages`, don't create it
- If you're unsure whether something is in scope, it isn't
- To add a new feature, use the /change skill — it updates idea.yaml first, then implements
- When asked to do something outside a defined skill (/bootstrap, /change, /iterate, /retro, /distribute, /verify), ask the user to clarify before proceeding

## Rule 1: PR-First Workflow
- Never commit directly to `main`
- Every change goes on a feature branch and gets a PR
- Branch naming: `feat/<topic>`, `fix/<topic>`, `chore/<topic>`, `change/<topic>`
- Use `gh pr create` to open PRs
- Fill in the PR template at `.github/PULL_REQUEST_TEMPLATE.md` for every PR

## Rule 2: Analytics Mandatory
- Every page and user action must fire events defined in `EVENTS.yaml` — that file is the **canonical** list of all events; always read it for the full specification
- Use the analytics library for all tracking calls — never call the analytics provider directly. See your analytics stack file (`.claude/stacks/analytics/<value>.md`) for the file path, exports, and import conventions.
- Use typed event wrappers (see analytics stack file) for standard and payment funnel events — this provides compile-time validation. For custom events, use the generic `track()` function. For server-side events (webhooks, API routes), use `trackServerEvent()` from the server analytics library with the event name as a string — typed wrappers are client-side only.
- The analytics library auto-attaches global properties defined in EVENTS.yaml `global_properties` to every event — these distinguish experiments in the shared analytics project.
- Wire each `standard_funnel` event from EVENTS.yaml to its corresponding page. If no page provides a natural trigger for an event (e.g., no signup page), omit that event.
- `payment_funnel` events from EVENTS.yaml are required only when `stack.payment` is present in idea.yaml.
- If you rename the project in idea.yaml (`name` field), update the analytics library constants — see your analytics stack file for which constants to change.

## Rule 3: Use Stack from idea.yaml
- Default stack: Next.js (App Router), Vercel, Supabase, PostHog, shadcn/ui
- For each stack category in idea.yaml, there is a corresponding implementation file at `.claude/stacks/<category>/<value>.md`. Skills read these files to know which packages to install, which library files to create, and which patterns to follow.
- To add support for a new technology (e.g., Firebase), create the corresponding stack file — don't modify skill files.
- Do not add frameworks or libraries not listed in idea.yaml `stack` section
- Exception: small utility packages (clsx, date-fns, zod) are fine
- If a feature requires a library not in `stack`, ask the user before adding it
- Bootstrap installs latest versions of all packages (no version pinning). This is intentional for MVPs — `package-lock.json` locks exact versions for reproducibility

## Rule 4: Keep It Minimal
- Prefer well-known libraries over custom code
- Bootstrap creates page-load smoke tests when `stack.testing` is present. Use `/change` for full funnel tests and `/verify` to run tests and fix failures. No additional tests except for auth and payment flows. Exception: if a feature contains non-trivial business logic (calculations, state machines, multi-step workflows), add unit tests for that logic. This is rare in first MVPs — if you're writing complex algorithms, consider whether you're overbuilding.
- No abstraction layers unless there's concrete duplication (3+ copies)
- Ship the simplest thing that works
- No premature optimization — no caching, no memoization, no lazy loading unless there's a measured problem

## Rule 5: Deploy-Ready
- Every PR must pass `npm run build` with zero errors before committing
- Skills use the verification procedure in `.claude/patterns/verify.md` (3-attempt retry with error tracking)
- No broken imports, no missing env vars in code
- Reference `.env.example` for all environment variables
- Every page must render without runtime errors

## Rule 6: Security Baseline
- Secrets go in environment variables, never in code
- Validate and sanitize all user input with zod or similar
- Add rate limiting to auth and payment API routes. See hosting stack file for deployment-specific constraints (e.g., serverless rate-limiting limitations).
- Use database-level access control (e.g., RLS) for all data access — never trust the client. See database stack file for details.
- Never expose database admin/service keys to the client

## Rule 7: File Conventions
```
src/
  app/              # Pages and API routes (see framework stack file)
    api/            # API route handlers (all mutations go here)
    <page-name>/    # One folder per idea.yaml page
      page.tsx      # Page component
  components/       # Reusable UI components (see UI stack file)
    ui/             # UI library components (auto-generated)
  lib/              # Utilities
    analytics.*     # Analytics tracking (see analytics stack file for filename)
idea/               # idea.yaml lives here
```
> This tree shows the default layout (Next.js). See your framework stack file for the actual file structure and extensions.
- One component per file
- Colocate page-specific components in the page's folder
- API routes: see your framework stack file for the route handler convention

## Rule 8: Communication Style
- Commit messages: imperative mood, ≤72 chars (e.g., "Add signup flow with email verification")
- PR descriptions: bullet points, reference idea.yaml features by name
- Fill in every section of the PR template — don't leave sections empty

## Rule 9: Framework Patterns
Follow the framework patterns defined in your active framework stack file (`.claude/stacks/framework/<value>.md`). That file specifies page conventions, routing patterns, data fetching approach, and restrictions. When no stack file exists for the configured framework, use your knowledge of that technology and follow the same structural patterns.

## Rule 10: Database
Follow the database patterns defined in your active database stack file (`.claude/stacks/database/<value>.md`). That file specifies migration format, schema conventions, access control setup, and typing requirements. When no stack file exists for the configured database, use your knowledge of that technology and follow the same structural patterns. Always follow Rule 6 for security, and keep the schema minimal — only create tables that idea.yaml features require.

## Rule 11: Memory
- After fixing build errors in the verification procedure, save project-specific patterns to auto memory
- Universal patterns that apply to any project with this stack belong in `.claude/stacks/<category>/<value>.md` — not in auto memory
- Auto memory is an accelerator, not a dependency — skills must function correctly with empty auto memory (fresh developer, fresh machine)
