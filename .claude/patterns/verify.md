# Verification Procedure

Run this procedure after making code changes and before committing.

## Build & Lint Loop (max 3 attempts)

You have a budget of **3 attempts** to get a clean build and lint. Track each failed
attempt so you can reference previous errors and avoid repeating them.

For each attempt:

1. Run `npm run build`
2. If build fails: note the errors (mentally log: "Attempt N — build: [error summary]").
   Fix the errors, then start the next attempt.
3. If build passes: run `npm run lint` (skip if no lint script exists).
   Warnings are OK; errors are not.
4. If lint fails: note the errors (mentally log: "Attempt N — lint: [error summary]").
   Fix the errors, then start the next attempt.
5. If both pass: verification is complete. Proceed to the next step.

**If all 3 attempts fail**, stop and report to the user:

> **Build verification failed after 3 attempts.** Here's what I tried:
>
> - Attempt 1: [what failed and what I changed]
> - Attempt 2: [what failed and what I changed]
> - Attempt 3: [what still fails]
>
> The remaining errors are: [paste current errors]
>
> **Your options:**
> 1. Tell me what to try and I'll fix it
> 2. Save current progress first: `git add -A && git commit -m "WIP: build not passing yet"` — then decide next steps
> 3. Save progress with option 2 first (if desired), then switch to main (`git checkout main`), run `make clean`, and `/bootstrap` to start fresh (**warning:** `make clean` deletes all generated code — anything not committed will be permanently lost)
> 4. Switch to this branch later (`git checkout <branch>`) and describe the remaining build errors directly — do not re-run `/bootstrap` or `/change`, as those create new branches. Instead, just tell Claude what errors remain and it will fix them on this branch.

Do NOT commit code that fails build or lint. Do NOT skip this procedure.

## Save Notable Patterns (if you fixed any errors above)

After a successful verification where you fixed build or lint errors:

1. For each error you fixed, decide: is this **universal** or **project-specific**?
   - **Universal** (applies to any project with this stack): add the pattern to the relevant
     `.claude/stacks/<category>/<value>.md` file instead
   - **Project-specific** (unique to this codebase): save a brief entry to your auto memory
     with the error, cause, and fix
2. Skip if: the error was a simple typo or something unlikely to recur
