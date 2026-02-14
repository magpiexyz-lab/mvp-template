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
> 3. Run `make clean` then `make bootstrap` to start fresh (**warning:** this deletes all code — use option 2 first if you want to preserve anything)
> 4. Switch to this branch later (`git checkout <branch>`) and run `claude` to resume

Do NOT commit code that fails build or lint. Do NOT skip this procedure.

## Log Failure Patterns (if you fixed any errors above)

After a successful verification where you fixed build or lint errors, log what you learned:

1. Read `.claude/failure-patterns.md` (if it doesn't exist, create it with this content:)
   ```
   # Failure Patterns
   <!-- Lessons learned from build/lint failures in this project. -->
   <!-- Max 30 entries. When full, remove the oldest entry (top) before adding. -->
   <!-- Only project-specific patterns. Universal patterns go in stack files. -->

   ## Patterns

   (none yet)
   ```
2. For each error you fixed, decide: is this project-specific or universal?
   - **Universal** (applies to any project with this stack): add the pattern to the relevant
     `.claude/stacks/<category>/<value>.md` file instead
   - **Project-specific** (unique to this codebase): add an entry to `.claude/failure-patterns.md`
3. Entry format — append to the `## Patterns` section:
   ```
   - **Error:** `<error message or symptom>`
     **Cause:** <why it happened in one sentence>
     **Fix:** <what you did to fix it in one sentence>
     **Category:** <short-kebab-case-tag>
   ```
4. Before adding: check if an entry with the same Category exists. If so, update it instead.
5. If the file has 30+ entries, remove the oldest entry (first in list) before adding.
6. Skip logging if: the error was a simple typo or something unlikely to recur.
