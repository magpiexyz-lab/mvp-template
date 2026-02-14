# Scoped Review Prompt

Use this file for targeted, bounded LLM reviews of the experiment template. Pick **one dimension** per review session. Paste the relevant section (plus the shared Instructions at the bottom) into a new Claude conversation.

> **Why scoped?** After 9 rounds of unbounded semantic audits, findings never converged — each round invented new issues. Automated validators (`scripts/validate-semantics.py`) now cover TODO resolution, import completeness, error actionability, Makefile guards, and fixture validation. This prompt focuses on what automated checks *can't* catch.

---

## Dimension A: Cross-File Consistency

You are reviewing an experiment template for **cross-file consistency**. The template has skill files (`.claude/commands/*.md`), stack files (`.claude/stacks/**/*.md`), `CLAUDE.md` (rules), `EVENTS.yaml` (analytics events), and `idea/idea.example.yaml` (example configuration).

Automated validators already check:
- Frontmatter cross-references (validate-frontmatter.py)
- TODO resolution coverage across files (validate-semantics.py, Check 1)
- Import completeness in code templates (validate-semantics.py, Check 2)
- CI placeholder ↔ stack file consistency (validate-frontmatter.py, Check 9-10)

**Your focus**: Find contradictions or inconsistencies **between** files that no regex or structural check can catch. Examples:
- A skill file says "do X" but a stack file's code template does Y
- A rule in CLAUDE.md conflicts with how a skill actually operates
- A stack file assumes a convention that another stack file violates
- A prose instruction references a function/file/path that doesn't match reality

Read all files in `.claude/commands/`, `.claude/stacks/`, `CLAUDE.md`, `EVENTS.yaml`, and `idea/idea.example.yaml`. Then report findings per the Instructions below.

---

## Dimension B: Edge Case Robustness

You are reviewing an experiment template for **edge case robustness**. The template must work for diverse `idea.yaml` configurations — from single-page landing pages to full-stack apps with auth+payments.

Automated validators already check:
- Fixture validation for 4 edge case configurations (validate-semantics.py, Check 5)
- Makefile target guards for pre-bootstrap state (validate-semantics.py, Check 4)
- Error message actionability (validate-semantics.py, Check 3)

**Your focus**: Find configurations where skills or stack files would produce broken output. Examples:
- A skill assumes auth exists but the idea.yaml has no `stack.auth`
- A code template hard-codes a path that changes based on stack choices
- A conditional branch in a skill handles 2 of 3 possible states
- An edge case not covered by the 4 test fixtures in `tests/fixtures/`

Read all skill files, stack files, test fixtures, and `CLAUDE.md`. Mentally simulate running `/bootstrap` and `/change` with each fixture's configuration. Report findings per the Instructions below.

---

## Dimension C: User Journey Completeness

You are reviewing an experiment template for **user journey completeness**. When a user (template operator) encounters an error or unexpected state, they should always have a clear path forward.

Automated validators already check:
- Error messages contain actionable fix hints (validate-semantics.py, Check 3)
- Skill files reference verify.md for build error recovery (validate-frontmatter.py, Check 5)

**Your focus**: Find dead-end states where a user gets stuck with no clear next step. Examples:
- A skill exits early but doesn't tell the user what to do next
- A build failure produces an error not covered by `failure-patterns.md`
- A workflow step assumes a previous step succeeded but doesn't verify
- A Makefile target fails silently or with an unhelpful error
- The user follows instructions but ends up in an undocumented state

Read all skill files, `Makefile`, `.claude/patterns/verify.md`, `.claude/failure-patterns.md`, and stack files. Trace the user journey from `make validate` → `make bootstrap` → `make change` → `make iterate` → `make retro`. Report findings per the Instructions below.

---

## Instructions (append to any dimension above)

**Rules for this review:**

1. **Maximum 5 findings.** If you find more than 5 issues, keep only the 5 most impactful. Quality over quantity.

2. **No overlap with automated validators.** Do not report anything that `validate-frontmatter.py` or `validate-semantics.py` already checks. If you're unsure, read those scripts first.

3. **Each finding must include:**
   - **File(s)**: Which files are involved
   - **Issue**: What's wrong (be specific — quote the conflicting text)
   - **Impact**: What breaks or confuses the user
   - **Fix**: A concrete, implementable fix (not "consider improving")
   - **Proposed automated check**: Describe a regex, structural, or cross-reference check that could catch this category of issue automatically in the future

4. **Graduation rule**: If you've seen a finding category in a previous review (check `scripts/validate-semantics.py` for existing checks), it should already be automated. Don't re-report it — instead, check whether the existing automated check covers your specific case. If not, propose extending the check.

5. **Format findings as:**
   ```
   ### Finding N: <title>
   - **File(s)**: ...
   - **Issue**: ...
   - **Impact**: ...
   - **Fix**: ...
   - **Proposed check**: ...
   ```

6. **If you find 0 issues**, that's a valid outcome. Say "No findings for this dimension" and explain what you checked.
