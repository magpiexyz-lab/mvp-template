# Check Inventory

Scannable reference listing all automated checks by name, grouped by validator.
51 active checks consolidated into 47 inventory rows.

Last updated: 2026-02-17

## Validation philosophy

Automated checks enforce invariants that prevent **silent failures** in generated
code: structural correctness, cross-file synchronization, behavioral contracts,
and reference integrity. Checks that regex-match natural-language prose for specific
phrasing are out of scope — phrasing quality in prose consumed by an LLM reader is
better enforced by the scoped LLM review (`scripts/scoped-review-prompt.md`).

## validate-frontmatter.py

| Name | Description |
|------|-------------|
| Require stack frontmatter keys | Every stack file must have all required keys (assumes, packages, files, env, ci_placeholders, clean, gitignore) |
| Resolve assumes entries to existing stack files | Every `assumes` entry must point to an existing `.claude/stacks/<path>.md` |
| Require skill frontmatter keys | Every skill file must have all required keys (type, reads, stack_categories, requires_approval, references, branch_prefix, modifies_specs) |
| Verify referenced file paths exist | Every `references` path in skill frontmatter must exist on disk |
| Require verify.md in code-writing skill references | Code-writing skills must include verify.md in their `references` list |
| Require branch.md in code-writing skill references | Code-writing skills must include branch.md in their `references` list |
| Match CLAUDE.md Rule 0 skill list to filenames | The parenthetical skill list in Rule 0 must match actual skill filenames |
| Verify ci_placeholders keys in ci.yml | Union of all `ci_placeholders` keys must appear in `.github/workflows/ci.yml` |
| Verify ci_placeholders values in gitleaks allowlist | All `ci_placeholders` values must be matched by a `.gitleaks.toml` allowlist pattern |
| Verify skill branch_prefix values in CLAUDE.md Rule 1 | Every skill `branch_prefix` value must appear as an allowed prefix in CLAUDE.md Rule 1 branch naming convention |

## validate-semantics.py

| Name | Description |
|------|-------------|
| Verify import completeness in TSX templates | JSX components used in code blocks have matching imports |
| Verify Makefile target guards | npm/node targets guard on package.json existence |
| Validate fixture structure | Test fixtures have required keys, valid idea.name, correct assertions |
| Verify frontmatter-content sync | Code block headers match `files` frontmatter; Makefile clean lines match `clean` frontmatter |
| Verify conditional dependency guards | References to optional stack categories have conditional guards within 150 chars |
| Verify required fields consistency | Required idea.yaml fields match between Makefile and validate-semantics.py |
| Verify fixture stack coverage | Every stack file is covered by at least one fixture; mandatory categories present in all fixtures |
| Verify tool and prereq validity | Tool names referenced in skill prose are in the known tools list |
| Verify env loading outside Next.js runtime | Non-`src/` templates using `process.env` load env config |
| Validate warning differentiation | Makefile validate target differentiates clean pass from pass with warnings |
| Verify hardcoded provider names match assumes | Code blocks using provider-specific identifiers must have matching `assumes` declaration |
| Verify prose file references in reads frontmatter | Spec files (CLAUDE.md, EVENTS.yaml) referenced in skill prose must appear in `reads` frontmatter |
| Verify fixture coverage for stack file branching | Conditional stack paths (`when stack.X is NOT Y`) must have fixture coverage for the alternate branch |
| Verify stack fallback when assumes not met | Stack files with optional-category `assumes` must have a fallback section for absent dependencies |
| Verify Makefile deploy hosting guard | Deploy target using provider-specific commands must check `stack.hosting` |
| Verify change skill validates payment-auth dependency | change.md must validate that `stack.auth` is present when adding `payment` to idea.yaml stack |
| Verify stack file env vars in prose match frontmatter declarations | Environment Variables prose sections mentioning env var names must have those vars declared in frontmatter `env.server` or `env.client` |
| Verify change skill validates payment requires database | change.md Feature constraints must validate that `payment` in the stack requires `database` to also be present |
| Verify fixture coverage for testing with partial assumptions | Testing fixtures must not only cover all-met and none-met assumes scenarios — at least one partial-met fixture (e.g., auth present, database absent) is required |
| Verify Makefile help text doesn't hard-code optional env var names | Makefile target help comments (`## ...` text) must not contain specific environment variable names that are conditional on stack configuration |
| Verify stack file packages in prose match frontmatter declarations | Packages prose sections with `npm install` commands must have those packages declared in frontmatter `packages.runtime` or `packages.dev` |
| Verify bootstrap validates payment requires database | bootstrap.md Validate idea.yaml section must validate that `stack.payment` requires `stack.database` to also be present |
| Verify testing CI template includes payment env vars | If ci.yml e2e job contains Stripe env vars, the testing stack CI Job Template must also reference them |
| Verify testing no-auth fallback includes CI job template | Testing stack No-Auth Fallback section must contain a YAML code block with an `e2e:` job definition |
| Verify change skill Test type permits adding testing to idea.yaml | change.md Test type constraints must address adding `testing` to idea.yaml stack section |
| Verify testing env frontmatter excludes assumes-dependent vars | Testing stack env frontmatter with optional assumes and a fallback must not unconditionally declare provider-specific env vars |
| Verify auth page templates contain post-auth redirects | Auth stack signup/login code blocks must contain `router.push` or `redirect` after auth success — a bare TODO comment fails |
| Verify change skill assumes validation matches bootstrap assumes validation | change.md assumes validation must include value-matching language, not just category-existence checks |
| Verify change skill validates payment dependencies before plan phase | At least one payment dependency stop message must appear before the plan phase marker in change.md |
| Verify analytics stack files include Dashboard Navigation section | Every `.claude/stacks/analytics/*.md` file must contain a `## Dashboard Navigation` heading (case-insensitive) |
| Verify change skill revalidates testing assumes for all change types | change.md Step 3 must contain testing assumes validation that is NOT gated by the Test-type classification |

## consistency-check.sh

9 active checks consolidated into 5 rows. Three checks removed (scripts #8, #11, #12).

| Name | Description | Scripts |
|------|-------------|---------|
| Forbid event name enumerations in rules and skills | CLAUDE.md and skill files must not enumerate event names inline | #1, #2 |
| Forbid hardcoded analytics paths and constants in reference files | Skills, CLAUDE.md, and PR template must not hardcode analytics import paths or constant names | #3, #6, #9 |
| Forbid framework-specific terms in rules and skills | CLAUDE.md and skill files must not use framework-specific directives or terms | #4, #5 |
| Forbid hardcoded framework paths in change skill | change.md must not hardcode API or types paths | #7 |
| Require verify.md references in code-writing skill content | Code-writing skill content (not just frontmatter) must reference verify.md | #10 |

## Cross-validator overlaps

Two checks appear in both `validate-frontmatter.py` and `consistency-check.sh`:

- **verify.md references**: frontmatter validator checks the `references` list (structural); consistency checker greps the file content (belt-and-suspenders)
- **branch.md references**: frontmatter validator checks the `references` list for code-writing skills; consistency checker verifies via frontmatter type detection

These overlaps are intentional — they catch different failure modes (metadata vs. content) and provide redundancy.

## Pending

| Name | Dimension | Target validator | Status |
|------|-----------|-----------------|--------|
| *(none)* | | | |

## Rejected

| Name | Reason | Date |
|------|--------|------|
| Verify TODO resolution coverage | Prose-phrasing check: regex-matches natural language for specific wording | 2026-02-15 |
| Verify error message actionability | Prose-phrasing check: regex-matches natural language for specific wording | 2026-02-15 |
| Verify branch context in recovery messages | Prose-phrasing check: regex-matches natural language for specific wording | 2026-02-15 |
| Verify destructive recovery save-first guidance | Prose-phrasing check: regex-matches natural language for specific wording | 2026-02-15 |
| Verify sequential numbering in enumerated lists | Cosmetic formatting check: no silent failure risk | 2026-02-15 |
| Verify skill stack_categories documents exclusions | Prose-phrasing check: regex-matches natural language for specific wording | 2026-02-15 |
| Verify abandon-branch cleanup guidance | Prose-phrasing check: regex-matches natural language for specific wording | 2026-02-15 |
| Verify multi-turn resumption guidance | Prose-phrasing check: regex-matches natural language for specific wording | 2026-02-15 |
| Verify analytics stack files document test-blocking endpoint pattern | Prose-phrasing check: regex-matches natural language for specific wording | 2026-02-15 |
| Verify bootstrap documents conditional file-creation for interdependent stacks | Prose-phrasing check: regex-matches natural language for specific wording | 2026-02-15 |
| Verify testing template selection documents assumes-check branching | Prose-phrasing check: regex-matches natural language for specific wording | 2026-02-15 |
| Verify bootstrap lists placeholder-constant replacements for stack templates | Prose-phrasing check: regex-matches natural language for specific wording | 2026-02-15 |
| Verify migration numbering documents concurrent-branch behavior | Prose-phrasing check: regex-matches natural language for specific wording | 2026-02-15 |
| Verify analysis-only skills check for spec file existence | Prose-phrasing check: regex-matches natural language for specific wording | 2026-02-15 |
| Verify install-failure recovery specifies retry scope | Prose-phrasing check: regex-matches natural language for specific wording | 2026-02-15 |
| Verify bootstrap validates stack assumes dependencies | Prose-phrasing check: regex-matches natural language for specific wording | 2026-02-15 |
| Verify Makefile deploy error names the command to replace | Prose-phrasing check: regex-matches natural language for specific wording | 2026-02-15 |
| Verify bootstrap rejects excluded stack categories | Prose-phrasing check: regex-matches natural language for specific wording | 2026-02-15 |
| Verify stack file prose flags silent TODOs distinctly from build-failing TODOs | Prose-phrasing check: regex-matches natural language for specific wording | 2026-02-15 |
