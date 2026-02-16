#!/usr/bin/env python3
"""Validate semantic correctness across stack files, skill files, and fixtures.

Checks:
  1. Import Completeness in TSX Templates — JSX components have matching imports
  2. Makefile Target Guards — npm/node targets guard on package.json
  3. Fixture Validation — test fixture files are structurally correct
  4. Frontmatter ↔ Content Sync — code block headers match frontmatter files
  5. Conditional Dependency References — optional stack references have guards
  6. Required Fields Consistency — Makefile and validator agree on required fields
  7. Fixture Stack Coverage — every stack file has at least one fixture
  8. Tool & Prereq Validity — referenced tools exist
  9. Env Loading Outside Next.js Runtime — non-src templates load env config
  10. Validate Warning Differentiation — success message varies with warnings
  11. Hardcoded Provider Names Match Assumes — code blocks match assumes
  12. Prose File References in Reads Frontmatter — referenced files in reads
  13. Fixture Branching Coverage — conditional stack paths have fixtures
  14. Stack Fallback When Assumes Not Met — fallback section for missing deps
  15. Makefile Deploy Hosting Guard — deploy target checks hosting stack
  16. Change Payment-Auth Dependency — change skill validates payment requires auth
  17. Stack File Env Vars Prose-Frontmatter Sync — env vars in prose match frontmatter
  18. Change Payment-Database Dependency — change skill validates payment requires database
  19. Fixture Coverage for Testing Partial Assumes — testing fixtures cover partial-met assumes
  20. Makefile Help Text No Conditional Env Var Names — help comments don't hardcode optional env vars
  21. Stack File Packages Prose-Frontmatter Sync — packages in prose match frontmatter
  22. Bootstrap Payment-Database Dependency — bootstrap validates payment requires database
  23. Testing CI Template Payment Env Vars — testing CI template includes payment env vars when ci.yml does
  24. Testing No-Auth Fallback CI Template — testing stack no-auth fallback includes CI job template
  25. Change Test Type Testing Stack Addition — change skill Test type permits adding testing to idea.yaml stack
  26. Testing Env Frontmatter Assumes Dependency — testing stack env frontmatter excludes assumes-dependent vars
  27. Auth Template Post-Auth Redirects — auth page templates contain router.push/redirect after auth success
  28. Change Assumes Validation Matches Bootstrap — change skill value-matches assumes, not just category-exists
  29. Change Payment Validation Before Plan Phase — payment dependency checks appear before plan phase
  30. Analytics Dashboard Navigation Section — analytics stack files include Dashboard Navigation
  31. Change Testing Assumes Revalidation — change skill revalidates testing assumes for all change types
"""

import glob
import os
import re
import sys

import yaml

ERRORS: list[str] = []


def error(msg: str) -> None:
    ERRORS.append(msg)
    print(f"FAIL: {msg}", file=sys.stderr)


def parse_frontmatter(filepath: str) -> dict | None:
    """Extract YAML frontmatter from a markdown file."""
    with open(filepath) as f:
        content = f.read()
    m = re.match(r"^---\n(.*?\n)---", content, re.DOTALL)
    if not m:
        return None
    return yaml.safe_load(m.group(1))


def extract_code_blocks(content: str, lang_filter: set[str] | None = None) -> list[dict]:
    """Extract fenced code blocks from markdown content.

    Returns list of dicts with keys: lang, code, start_line.
    If lang_filter is provided, only blocks with matching language tags are returned.
    """
    blocks = []
    pattern = re.compile(r"^```(\w+)?\s*\n(.*?)^```", re.MULTILINE | re.DOTALL)
    for m in pattern.finditer(content):
        lang = m.group(1) or ""
        if lang_filter and lang not in lang_filter:
            continue
        start_line = content[: m.start()].count("\n") + 1
        blocks.append({"lang": lang, "code": m.group(2), "start_line": start_line})
    return blocks


def extract_prose(content: str) -> str:
    """Extract text outside of fenced code blocks."""
    return re.sub(r"```\w*\s*\n.*?```", "", content, flags=re.MULTILINE | re.DOTALL)


# ---------------------------------------------------------------------------
# Collect files
# ---------------------------------------------------------------------------

stack_files = sorted(
    f
    for f in glob.glob(".claude/stacks/**/*.md", recursive=True)
    if "TEMPLATE" not in f
)
skill_files = sorted(glob.glob(".claude/commands/*.md"))

# Pre-read all file contents
stack_contents: dict[str, str] = {}
for sf in stack_files:
    with open(sf) as f:
        stack_contents[sf] = f.read()

skill_contents: dict[str, str] = {}
for sf in skill_files:
    with open(sf) as f:
        skill_contents[sf] = f.read()

# Required fields for idea.yaml — used by Check 3 (fixtures) and Check 6 (consistency)
REQUIRED_IDEA_FIELDS = [
    "name",
    "title",
    "owner",
    "problem",
    "solution",
    "target_user",
    "distribution",
    "pages",
    "features",
    "primary_metric",
    "target_value",
    "measurement_window",
    "stack",
]

# ---------------------------------------------------------------------------
# Check 1: Import Completeness in TSX Templates
# ---------------------------------------------------------------------------

# Components that don't need explicit imports
BUILTIN_COMPONENTS = {
    "Fragment",
    "Suspense",
    "StrictMode",
}

# HTML-like elements that happen to be capitalized (shouldn't match, but just in case)
HTML_ELEMENTS = set()

for sf, content in stack_contents.items():
    blocks = extract_code_blocks(content, {"tsx", "jsx"})

    for block in blocks:
        code = block["code"]
        # Find JSX component usage: <ComponentName or <ComponentName> or <ComponentName/
        used_components = set(re.findall(r"<([A-Z][a-zA-Z]+)", code))
        used_components -= BUILTIN_COMPONENTS

        # Find imported components
        imported: set[str] = set()
        for m in re.finditer(
            r"import\s+(?:type\s+)?(?:\{([^}]+)\}|(\w+))\s+from", code
        ):
            if m.group(1):
                # Named imports: import { Foo, Bar } from ...
                for name in m.group(1).split(","):
                    name = name.strip()
                    # Handle "Foo as Bar" aliasing
                    if " as " in name:
                        name = name.split(" as ")[1].strip()
                    if name:
                        imported.add(name)
            if m.group(2):
                # Default import: import Foo from ...
                imported.add(m.group(2))

        missing = used_components - imported
        for comp in sorted(missing):
            block_line = block["start_line"]
            error(
                f"[1] {sf}:{block_line}: JSX component <{comp}> used but "
                f"not imported in code block"
            )

# ---------------------------------------------------------------------------
# Check 2: Makefile Target Guards
# ---------------------------------------------------------------------------

makefile_path = "Makefile"
if os.path.isfile(makefile_path):
    with open(makefile_path) as f:
        makefile_content = f.read()

    # Targets that don't need guards:
    # - Pre-bootstrap / meta: validate, clean, clean-all, help
    # - Post-bootstrap only: dev, deploy, test-e2e (user runs these after
    #   bootstrap; npm errors are self-explanatory in this context)
    EXEMPT_TARGETS = {
        "validate",
        "clean",
        "clean-all",
        "help",
        "test-e2e",
    }

    # Parse Makefile targets and their recipe lines
    # A target line looks like: target-name: [deps] ## comment
    # Recipe lines follow, indented with a tab
    target_pattern = re.compile(r"^([a-zA-Z0-9_-]+)\s*:(?!=)", re.MULTILINE)
    targets = {}
    matches = list(target_pattern.finditer(makefile_content))
    for i, m in enumerate(matches):
        name = m.group(1)
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(makefile_content)
        recipe = makefile_content[start:end]
        targets[name] = recipe

    for target_name, recipe in targets.items():
        if target_name in EXEMPT_TARGETS:
            continue
        if target_name.startswith("."):
            continue

        # Check if this target uses npm or node commands
        uses_npm = bool(re.search(r"\bnpm\b|\bnpx\b|\bnode\b", recipe))
        if not uses_npm:
            continue

        # Check for a package.json guard
        has_guard = bool(
            re.search(r"if\s+\[.*package\.json", recipe)
            or re.search(r"test\s+-f\s+package\.json", recipe)
            or re.search(r"-f\s+package\.json", recipe)
            or re.search(r"-e\s+package\.json", recipe)
        )

        if not has_guard:
            line_num = makefile_content[
                : makefile_content.index(f"{target_name}:")
            ].count("\n") + 1
            error(
                f"[2] {makefile_path}:{line_num}: target '{target_name}' uses "
                f"npm/node but has no package.json guard"
            )

# ---------------------------------------------------------------------------
# Check 3: Fixture Validation
# ---------------------------------------------------------------------------

fixture_dir = "tests/fixtures"
if os.path.isdir(fixture_dir):
    fixture_files = sorted(glob.glob(os.path.join(fixture_dir, "*.yaml")))

    if not fixture_files:
        error(f"[3] {fixture_dir}: no fixture files found")

    for ff in fixture_files:
        with open(ff) as f:
            try:
                fixture = yaml.safe_load(f)
            except yaml.YAMLError as e:
                error(f"[3] {ff}: invalid YAML: {e}")
                continue

        if not isinstance(fixture, dict):
            error(f"[3] {ff}: fixture must be a YAML mapping")
            continue

        # Check required top-level keys
        for key in ["idea", "events", "assertions"]:
            if key not in fixture:
                error(f"[3] {ff}: missing required key '{key}'")

        idea = fixture.get("idea", {})
        if not isinstance(idea, dict):
            error(f"[3] {ff}: 'idea' must be a mapping")
            continue

        # Validate idea.name format
        name = idea.get("name", "")
        if not re.match(r"^[a-z][a-z0-9-]*$", str(name)):
            error(
                f"[3] {ff}: idea.name '{name}' must be lowercase, start with "
                f"a letter, and use only a-z, 0-9, hyphens"
            )

        # Validate required idea fields
        for field in REQUIRED_IDEA_FIELDS:
            if not idea.get(field):
                error(f"[3] {ff}: idea.{field} is missing or empty")

        # Validate pages includes landing
        pages = idea.get("pages", [])
        if isinstance(pages, list):
            has_landing = any(
                isinstance(p, dict) and p.get("name") == "landing" for p in pages
            )
            if not has_landing:
                error(f"[3] {ff}: idea.pages must include a 'landing' entry")

        # Validate assertions
        assertions = fixture.get("assertions", {})
        if isinstance(assertions, dict):
            # If no payment stack, payment_funnel events should not be required
            stack = idea.get("stack", {})
            has_payment = "payment" in stack if isinstance(stack, dict) else False
            payment_required = assertions.get("payment_events_required", False)
            if payment_required and not has_payment:
                error(
                    f"[3] {ff}: assertions.payment_events_required is true but "
                    f"idea.stack has no payment entry"
                )

            # If no signup page, signup events should be in skippable
            has_signup = False
            if isinstance(pages, list):
                has_signup = any(
                    isinstance(p, dict) and p.get("name") == "signup" for p in pages
                )
            skippable = assertions.get("skippable_events", [])
            if not has_signup:
                for ev in ["signup_start", "signup_complete"]:
                    if ev not in skippable:
                        error(
                            f"[3] {ff}: no signup page but '{ev}' not in "
                            f"assertions.skippable_events"
                        )

            # Validate min_pages matches actual page count
            min_pages = assertions.get("min_pages")
            if min_pages is not None and isinstance(pages, list):
                if len(pages) < min_pages:
                    error(
                        f"[3] {ff}: idea has {len(pages)} page(s) but "
                        f"assertions.min_pages is {min_pages}"
                    )

        # Validate events structure
        events = fixture.get("events", {})
        if isinstance(events, dict):
            # If no payment stack, payment_funnel should be absent or empty
            if not has_payment:
                pf = events.get("payment_funnel", [])
                if pf:
                    error(
                        f"[3] {ff}: events.payment_funnel is non-empty but "
                        f"idea.stack has no payment entry"
                    )
else:
    # No fixture directory is not an error — fixtures are optional pre-creation
    pass

# ---------------------------------------------------------------------------
# Check 4: Frontmatter ↔ Content Sync
# ---------------------------------------------------------------------------

# 4a: Code block section headers (### `path`) should be in files: frontmatter
for sf, content in stack_contents.items():
    fm = parse_frontmatter(sf)
    if not fm:
        continue

    fm_files = set(fm.get("files", []) or [])
    header_paths = set(re.findall(r"###\s+`([^`]+)`", content))

    for path in sorted(header_paths):
        if path not in fm_files:
            error(
                f"[4] {sf}: code block header path '{path}' not listed in "
                f"frontmatter 'files'"
            )

# 4b: Makefile clean lines should match clean.files/clean.dirs frontmatter
if os.path.isfile(makefile_path):
    clean_match = re.search(
        r"^clean:.*?\n((?:\t.*\n)*)", makefile_content, re.MULTILINE
    )
    if clean_match:
        clean_recipe = clean_match.group(1)

        makefile_clean_items: dict[str, set[str]] = {}
        for line in clean_recipe.splitlines():
            line_s = line.strip()
            if not line_s:
                continue
            tag_match = re.search(r"#\s+(\w+/\w+)\s*$", line_s)
            if not tag_match:
                continue
            tag = tag_match.group(1)
            line_body = line_s[: tag_match.start()].strip()
            rm_match = re.match(r"rm\s+(?:-rf|-f)\s+(.*)", line_body)
            if rm_match:
                items = rm_match.group(1).split()
                makefile_clean_items.setdefault(tag, set()).update(items)

        for sf in stack_files:
            fm = parse_frontmatter(sf)
            if not fm or "clean" not in fm:
                continue
            cat_val = sf.replace(".claude/stacks/", "").replace(".md", "")
            clean_fm = fm.get("clean", {}) or {}
            fm_clean_files = set(clean_fm.get("files", []) or [])
            fm_clean_dirs = set(clean_fm.get("dirs", []) or [])
            fm_all = fm_clean_files | fm_clean_dirs

            if not fm_all:
                continue

            if cat_val not in makefile_clean_items:
                error(
                    f"[4] {sf}: clean frontmatter has entries but no "
                    f"Makefile clean line tagged '# {cat_val}'"
                )
                continue

            mk_items = makefile_clean_items[cat_val]

            for item in sorted(fm_all - mk_items):
                error(
                    f"[4] {sf}: clean item '{item}' not in Makefile "
                    f"clean target (# {cat_val})"
                )
            for item in sorted(mk_items - fm_all):
                error(
                    f"[4] Makefile clean (# {cat_val}): item '{item}' not in "
                    f"{sf} clean frontmatter"
                )

# ---------------------------------------------------------------------------
# Check 5: Conditional Dependency References
# ---------------------------------------------------------------------------

OPTIONAL_CATEGORIES = {"database", "auth", "payment", "testing"}

for sf, content in skill_contents.items():
    prose = extract_prose(content)
    for m in re.finditer(r"from the (\w+) stack file", prose):
        category = m.group(1)
        if category not in OPTIONAL_CATEGORIES:
            continue
        start = max(0, m.start() - 150)
        context_before = prose[start : m.start()]
        has_guard = bool(
            re.search(
                rf"(?i)(?:if\s+.*(?:stack\.{category}|`stack\.{category}`)|"
                rf"if\b.*\b{category}\b.*\bpresent\b)",
                context_before,
                re.DOTALL,
            )
        )
        if not has_guard:
            # Find line number in original content
            match_text = m.group(0)
            pos = content.find(match_text)
            line_num = content[:pos].count("\n") + 1 if pos >= 0 else "?"
            error(
                f"[5] {sf}:{line_num}: reference to optional '{category}' "
                f"stack file lacks conditional guard within 150 chars"
            )

# ---------------------------------------------------------------------------
# Check 6: Required Fields Consistency
# ---------------------------------------------------------------------------

if os.path.isfile(makefile_path):
    mk_required_match = re.search(
        r"required\s*=\s*\[([^\]]+)\]", makefile_content
    )
    if mk_required_match:
        mk_fields_raw = mk_required_match.group(1)
        mk_fields = [
            f.strip().strip("'\"")
            for f in mk_fields_raw.split(",")
            if f.strip()
        ]
        mk_fields_set = set(mk_fields)
        sem_fields_set = set(REQUIRED_IDEA_FIELDS)

        for field in sorted(mk_fields_set - sem_fields_set):
            error(
                f"[6] Makefile validate has required field '{field}' "
                f"missing from validate-semantics.py"
            )
        for field in sorted(sem_fields_set - mk_fields_set):
            error(
                f"[6] validate-semantics.py has required field '{field}' "
                f"missing from Makefile validate"
            )

# ---------------------------------------------------------------------------
# Check 7: Fixture Stack Coverage
# ---------------------------------------------------------------------------

if os.path.isdir(fixture_dir):
    fixture_files_cov = sorted(glob.glob(os.path.join(fixture_dir, "*.yaml")))

    # Collect category/value pairs from stack file paths
    stack_pairs = set()
    for sf in stack_files:
        pair = sf.replace(".claude/stacks/", "").replace(".md", "")
        stack_pairs.add(pair)

    # Collect stack coverage from all fixtures
    fixture_stack_coverage: dict[str, set[str]] = {}
    all_fixture_stacks: set[str] = set()

    for ff in fixture_files_cov:
        with open(ff) as f:
            try:
                fixture = yaml.safe_load(f)
            except yaml.YAMLError:
                continue
        if not isinstance(fixture, dict):
            continue
        idea = fixture.get("idea", {})
        stack = idea.get("stack", {})
        if isinstance(stack, dict):
            pairs = {f"{k}/{v}" for k, v in stack.items()}
            fixture_stack_coverage[ff] = pairs
            all_fixture_stacks |= pairs

    # Each stack file should be covered by at least one fixture
    for pair in sorted(stack_pairs):
        if pair not in all_fixture_stacks:
            error(
                f"[7] Stack file .claude/stacks/{pair}.md has no "
                f"fixture coverage in {fixture_dir}/"
            )

    # Parse bootstrap.md for mandatory categories
    bootstrap_path = ".claude/commands/bootstrap.md"
    if os.path.isfile(bootstrap_path):
        with open(bootstrap_path) as f:
            bootstrap_content = f.read()

        always_match = re.search(
            r"always:\s*([^;)]+?)(?:\)|;|$)", bootstrap_content
        )
        if always_match:
            mandatory_cats = [
                c.strip().rstrip(",")
                for c in always_match.group(1).split(",")
                if c.strip()
            ]

            for ff, pairs in fixture_stack_coverage.items():
                fixture_cats = {p.split("/")[0] for p in pairs}
                for cat in mandatory_cats:
                    if cat not in fixture_cats:
                        error(
                            f"[7] {ff}: missing mandatory stack category "
                            f"'{cat}' (must be in all fixtures)"
                        )

# ---------------------------------------------------------------------------
# Check 8: Tool & Prereq Validity
# ---------------------------------------------------------------------------

KNOWN_TOOLS = {
    "Read", "Write", "Edit", "Bash", "Glob", "Grep",
    "WebFetch", "WebSearch", "Task", "NotebookEdit",
    "AskUserQuestion", "EnterPlanMode", "ExitPlanMode",
    "Skill", "TaskCreate", "TaskUpdate", "TaskGet", "TaskList",
    "TaskOutput", "TaskStop",
}

for sf, content in skill_contents.items():
    prose = extract_prose(content)
    for m in re.finditer(r"using the (\w+) tool", prose):
        tool_name = m.group(1)
        if tool_name not in KNOWN_TOOLS:
            pos = content.find(m.group(0))
            line_num = content[:pos].count("\n") + 1 if pos >= 0 else "?"
            error(
                f"[8] {sf}:{line_num}: references unknown tool "
                f"'{tool_name}'"
            )

# ---------------------------------------------------------------------------
# Check 9: Env Loading Outside Next.js Runtime
# ---------------------------------------------------------------------------

for sf, content in stack_contents.items():
    # Get section header positions
    headers = [
        (m.start(), m.group(1))
        for m in re.finditer(r"###\s+`([^`]+)`", content)
    ]
    blocks = extract_code_blocks(content, {"ts", "tsx", "js"})

    # Check if any code block in this stack file already loads env
    # (e.g., playwright.config.ts loads env for all Playwright templates)
    file_has_env_loader = any(
        re.search(r"loadEnvConfig|dotenv|@next/env", b["code"])
        for b in blocks
    )

    for block in blocks:
        block_start = block["start_line"]
        # Find closest header before this block
        closest_path = None
        for hdr_pos, path in headers:
            hdr_line = content[:hdr_pos].count("\n") + 1
            if hdr_line < block_start:
                closest_path = path

        if not closest_path or closest_path.startswith("src/"):
            continue

        if "process.env." not in block["code"]:
            continue

        has_env_loading = bool(
            re.search(r"loadEnvConfig|dotenv|@next/env", block["code"])
        )
        if not has_env_loading and not file_has_env_loader:
            error(
                f"[9] {sf}: template for '{closest_path}' uses process.env "
                f"but doesn't load env config (loadEnvConfig/dotenv/@next/env)"
            )

# ---------------------------------------------------------------------------
# Check 10: Validate Warning Differentiation
# ---------------------------------------------------------------------------

if os.path.isfile(makefile_path):
    validate_recipe = targets.get("validate", "")

    has_conditional = bool(
        re.search(r"(?i)WARN|warning.*if|if.*warn", validate_recipe)
    )
    has_passed_message = bool(
        re.search(r"Validation passed", validate_recipe)
    )

    if has_passed_message and not has_conditional:
        error(
            f"[10] Makefile validate: success message is unconditional — "
            f"should differentiate between clean pass and pass with warnings"
        )

# ---------------------------------------------------------------------------
# Check 11: Hardcoded Provider Names Match Assumes
# ---------------------------------------------------------------------------

# Map provider-specific identifiers found in code to their category/value pair
PROVIDER_IDENTIFIERS: dict[str, str] = {
    "posthog": "analytics/posthog",
    "amplitude": "analytics/amplitude",
    "segment": "analytics/segment",
    "stripe": "payment/stripe",
}

for sf, content in stack_contents.items():
    fm = parse_frontmatter(sf)
    if not fm:
        continue
    assumes = set(fm.get("assumes", []) or [])
    blocks = extract_code_blocks(content, {"ts", "tsx", "js", "jsx"})

    for block in blocks:
        code_lower = block["code"].lower()
        for identifier, category_value in PROVIDER_IDENTIFIERS.items():
            if identifier in code_lower:
                # Check this isn't the stack file for that provider itself
                cat_val = sf.replace(".claude/stacks/", "").replace(".md", "")
                if cat_val == category_value:
                    continue
                if category_value not in assumes:
                    error(
                        f"[11] {sf}:{block['start_line']}: code block uses "
                        f"'{identifier}' but '{category_value}' not in "
                        f"assumes frontmatter"
                    )
                    break  # One error per file per provider is enough

# ---------------------------------------------------------------------------
# Check 12: Prose File References in Reads Frontmatter
# ---------------------------------------------------------------------------

# Spec files that should be in reads when referenced as a source of truth.
# Excludes runtime-check files (package.json, .env.example) which are existence
# checks, not files Claude reads for context.
SPEC_REFERENCE_FILES = {"CLAUDE.md", "EVENTS.yaml"}

for sf, content in skill_contents.items():
    fm = parse_frontmatter(sf)
    if not fm:
        continue
    reads = set(fm.get("reads", []) or [])
    prose = extract_prose(content)

    for ref_file in SPEC_REFERENCE_FILES:
        # Look for directive references (e.g., "CLAUDE.md Rule 4", "per CLAUDE.md")
        # Exclude example text like "(e.g., ... CLAUDE.md Rule Z)"
        for m_ref in re.finditer(
            rf"\b{re.escape(ref_file)}\b", prose
        ):
            # Skip if inside example parenthetical (e.g., ...)
            start = max(0, m_ref.start() - 100)
            context_before = prose[start : m_ref.start()]
            if re.search(r"e\.g\.\s*,", context_before):
                continue

            # Check if this file is in reads
            matched = any(ref_file in r or r in ref_file for r in reads)
            if not matched:
                pos = content.find(ref_file)
                line_num = content[:pos].count("\n") + 1 if pos >= 0 else "?"
                error(
                    f"[12] {sf}:{line_num}: prose references '{ref_file}' "
                    f"but it's not in 'reads' frontmatter"
                )
                break  # One error per file per reference is enough

# ---------------------------------------------------------------------------
# Check 13: Fixture Coverage for Stack File Branching Conditions
# ---------------------------------------------------------------------------

if os.path.isdir(fixture_dir):
    fixture_files_branch = sorted(glob.glob(os.path.join(fixture_dir, "*.yaml")))

    # Collect fixture stack configs
    fixture_stacks_13: list[dict[str, str]] = []
    for ff in fixture_files_branch:
        with open(ff) as f:
            try:
                fixture = yaml.safe_load(f)
            except yaml.YAMLError:
                continue
        if not isinstance(fixture, dict):
            continue
        idea = fixture.get("idea", {})
        stack = idea.get("stack", {})
        if isinstance(stack, dict):
            fixture_stacks_13.append(stack)

    # For each stack file, check for conditional branching
    for sf, content in stack_contents.items():
        prose = extract_prose(content)
        cat_val = sf.replace(".claude/stacks/", "").replace(".md", "")
        category = cat_val.split("/")[0]

        # Find "when stack.X is NOT Y" or "when stack.X is also Y" patterns
        for m in re.finditer(
            r"(?i)when\s+`?stack\.(\w+)`?\s+is\s+NOT\s+(\w+)",
            prose,
        ):
            dep_category = m.group(1)
            dep_value = m.group(2)

            # Check if any fixture exercises the "NOT" branch
            has_not_branch = any(
                dep_category not in fs or fs.get(dep_category) != dep_value
                for fs in fixture_stacks_13
                if category in fs  # Only fixtures that use this stack category
            )

            if not has_not_branch:
                error(
                    f"[13] {sf}: has conditional for 'stack.{dep_category} "
                    f"is NOT {dep_value}' but no fixture exercises this branch"
                )

# ---------------------------------------------------------------------------
# Check 14: Stack File Provides Fallback When Assumes Not Met
# ---------------------------------------------------------------------------

FALLBACK_INDICATORS = re.compile(
    r"(?i)\b(?:fallback|no[- ]auth|without|not met|absent|simplified|"
    r"when.*(?:not|missing|absent)|anonymous)\b"
)

# Only flag when assumes include optional categories — mandatory categories
# (framework, analytics, ui, hosting) are always present per bootstrap.md
OPTIONAL_ASSUME_CATEGORIES = {"database", "auth", "payment", "testing"}

for sf, content in stack_contents.items():
    fm = parse_frontmatter(sf)
    if not fm:
        continue
    assumes = fm.get("assumes", []) or []
    if not assumes:
        continue

    # Filter to only optional assumed dependencies
    optional_assumes = [
        a for a in assumes
        if a.split("/")[0] in OPTIONAL_ASSUME_CATEGORIES
    ]
    if not optional_assumes:
        continue

    prose = extract_prose(content)
    if not FALLBACK_INDICATORS.search(prose):
        error(
            f"[14] {sf}: has optional assumes {optional_assumes} but no "
            f"fallback section for when dependencies are absent"
        )

# ---------------------------------------------------------------------------
# Check 15: Makefile Deploy Hosting Guard
# ---------------------------------------------------------------------------

if os.path.isfile(makefile_path):
    deploy_recipe = targets.get("deploy", "")

    # Check for hosting-provider-specific commands
    provider_commands = {
        "vercel": r"\bvercel\b",
        "netlify": r"\bnetlify\b",
        "fly": r"\bfly\b|\bflyctl\b",
    }

    for provider, pattern in provider_commands.items():
        if re.search(pattern, deploy_recipe):
            # Check for a hosting stack guard
            has_hosting_guard = bool(
                re.search(
                    r"(?:HOSTING|hosting|stack.*hosting)",
                    deploy_recipe,
                )
            )
            if not has_hosting_guard:
                line_num = makefile_content[
                    : makefile_content.index("deploy:")
                ].count("\n") + 1
                error(
                    f"[15] Makefile:{line_num}: deploy target uses "
                    f"'{provider}' command without hosting stack guard"
                )

# ---------------------------------------------------------------------------
# Check 16: Change Payment-Auth Dependency
# ---------------------------------------------------------------------------

change_path = ".claude/commands/change.md"
if os.path.isfile(change_path):
    with open(change_path) as f:
        change_content = f.read()
    change_prose = extract_prose(change_content)

    # Check if change.md mentions adding payment
    has_payment_ref = bool(
        re.search(r"(?i)adding\s+.*payment|payment.*stack", change_prose)
    )
    if has_payment_ref:
        # Look for auth-presence validation near the payment reference
        has_auth_check = bool(
            re.search(
                r"(?i)payment.*auth.*present|auth.*present.*payment|"
                r"payment\s+requires\s+auth",
                change_prose,
            )
        )
        if not has_auth_check:
            error(
                f"[16] {change_path}: mentions adding payment stack "
                f"category without a preceding auth-presence validation"
            )

# ---------------------------------------------------------------------------
# Check 17: Stack File Env Vars in Prose Match Frontmatter Declarations
# ---------------------------------------------------------------------------

# Look for "Environment Variables" sections in stack files and check that any
# env var names mentioned in prose also appear in frontmatter env.server or env.client.
ENV_VAR_PATTERN = re.compile(r"`?(NEXT_PUBLIC_[A-Z_]+|[A-Z][A-Z_]{3,}(?:_KEY|_URL|_ID|_SECRET|_TOKEN|_ANON_KEY|_ROLE_KEY))`?")

for sf, content in stack_contents.items():
    fm = parse_frontmatter(sf)
    if not fm:
        continue

    env_section = fm.get("env", {}) or {}
    fm_server = set(env_section.get("server", []) or [])
    fm_client = set(env_section.get("client", []) or [])
    fm_all_env = fm_server | fm_client

    # Find "Environment Variables" section in prose
    env_section_match = re.search(
        r"##\s+Environment Variables\s*\n(.*?)(?=\n##\s|\Z)",
        content,
        re.DOTALL,
    )
    if not env_section_match:
        continue

    env_prose = env_section_match.group(1)
    # Extract env var names from prose (outside code blocks)
    env_prose_no_code = re.sub(r"```.*?```", "", env_prose, flags=re.DOTALL)
    prose_env_vars: set[str] = set()
    for m in ENV_VAR_PATTERN.finditer(env_prose_no_code):
        var_name = m.group(1) or m.group(0).strip("`")
        prose_env_vars.add(var_name)

    for var in sorted(prose_env_vars - fm_all_env):
        line_num = content[: env_section_match.start()].count("\n") + 1
        error(
            f"[17] {sf}:{line_num}: Environment Variables prose mentions "
            f"'{var}' but it's not in frontmatter env.server or env.client"
        )

# ---------------------------------------------------------------------------
# Check 18: Change Skill Validates Payment Requires Database
# ---------------------------------------------------------------------------

change_path_db = ".claude/commands/change.md"
if os.path.isfile(change_path_db):
    with open(change_path_db) as f:
        change_content_db = f.read()
    change_prose_db = extract_prose(change_content_db)

    # Check if change.md has a payment section in Feature constraints
    feature_constraints_match = re.search(
        r"(?i)####?\s+Feature constraints\s*\n(.*?)(?=\n####?\s|\Z)",
        change_content_db,
        re.DOTALL,
    )
    if feature_constraints_match:
        feature_section = feature_constraints_match.group(1)
        has_db_check = bool(
            re.search(
                r"(?i)payment.*database.*present|database.*present.*payment|"
                r"payment\s+requires.*database|"
                r"stack\.database.*(?:missing|present|also)|"
                r"both.*stack\.auth.*stack\.database",
                feature_section,
            )
        )
        if not has_db_check:
            error(
                f"[18] {change_path_db}: Feature constraints section "
                f"doesn't validate that `payment` in the stack requires "
                f"`database` to also be present"
            )

# ---------------------------------------------------------------------------
# Check 19: Fixture Coverage for Testing with Partial Assumes
# ---------------------------------------------------------------------------

if os.path.isdir(fixture_dir):
    fixture_files_testing = sorted(glob.glob(os.path.join(fixture_dir, "*.yaml")))

    # Collect fixture stack configs for testing fixtures only
    testing_fixtures_all_met: list[str] = []
    testing_fixtures_none_met: list[str] = []
    testing_fixtures_partial_met: list[str] = []

    # Get testing stack file assumes
    testing_assumes_categories: set[str] = set()
    for sf in stack_files:
        if "/testing/" in sf:
            fm_t = parse_frontmatter(sf)
            if fm_t:
                for a in fm_t.get("assumes", []) or []:
                    testing_assumes_categories.add(a.split("/")[0])

    # Only run check if we have testing assumes to validate against
    if testing_assumes_categories:
        optional_testing_assumes = testing_assumes_categories & OPTIONAL_CATEGORIES

        for ff in fixture_files_testing:
            with open(ff) as f:
                try:
                    fixture = yaml.safe_load(f)
                except yaml.YAMLError:
                    continue
            if not isinstance(fixture, dict):
                continue
            idea = fixture.get("idea", {})
            stack = idea.get("stack", {})
            if not isinstance(stack, dict):
                continue

            # Only consider fixtures with testing
            if "testing" not in stack:
                continue

            # Check which optional assumes are met
            met = {
                cat for cat in optional_testing_assumes
                if cat in stack
            }

            if met == optional_testing_assumes:
                testing_fixtures_all_met.append(ff)
            elif not met:
                testing_fixtures_none_met.append(ff)
            else:
                testing_fixtures_partial_met.append(ff)

        if testing_fixtures_all_met and testing_fixtures_none_met and not testing_fixtures_partial_met:
            error(
                f"[19] tests/fixtures/: testing fixtures only cover "
                f"all-met and none-met assumes scenarios without at least "
                f"one partial-met fixture (e.g., auth present, database absent)"
            )

# ---------------------------------------------------------------------------
# Check 20: Makefile Help Text Doesn't Hard-Code Optional Env Var Names
# ---------------------------------------------------------------------------

if os.path.isfile(makefile_path):
    with open(makefile_path) as f:
        makefile_content_help = f.read()

    # Parse target help comments: lines matching "target-name: ## help text"
    for m in re.finditer(r"^([a-zA-Z0-9_-]+):\s*.*?##\s*(.+)$", makefile_content_help, re.MULTILINE):
        target_name_20 = m.group(1)
        help_text = m.group(2)

        # Look for environment variable names in help text
        env_vars_in_help = re.findall(
            r"\b(?:NEXT_PUBLIC_[A-Z_]+|[A-Z][A-Z_]{3,}(?:_KEY|_URL|_ID|_SECRET|_TOKEN|_ANON_KEY|_ROLE_KEY))\b",
            help_text,
        )
        if env_vars_in_help:
            line_num = makefile_content_help[: m.start()].count("\n") + 1
            error(
                f"[20] Makefile:{line_num}: target '{target_name_20}' help "
                f"text contains environment variable name(s) "
                f"{env_vars_in_help} that are conditional on stack configuration"
            )

# ---------------------------------------------------------------------------
# Check 21: Stack File Packages in Prose Match Frontmatter Declarations
# ---------------------------------------------------------------------------

# Similar to Check 17 (env vars sync), but for packages.
# Look for "npm install <pkg>" in Packages prose sections and verify those
# packages appear in frontmatter packages.runtime or packages.dev.

PACKAGE_INSTALL_LINE_PATTERN = re.compile(
    r"^npm install\s+(.+)$", re.MULTILINE
)

for sf, content in stack_contents.items():
    fm = parse_frontmatter(sf)
    if not fm:
        continue

    pkg_section = fm.get("packages", {}) or {}
    fm_runtime = set(pkg_section.get("runtime", []) or [])
    fm_dev = set(pkg_section.get("dev", []) or [])
    fm_all_packages = fm_runtime | fm_dev

    # Find "Packages" section in prose (## Packages)
    pkg_section_match = re.search(
        r"##\s+Packages\s*\n(.*?)(?=\n##\s|\Z)",
        content,
        re.DOTALL,
    )
    if not pkg_section_match:
        continue

    pkg_prose = pkg_section_match.group(1)

    # Extract package names from "npm install ..." commands in code blocks
    # within the Packages section
    code_blocks_in_section = re.findall(
        r"```(?:bash|sh)\s*\n(.*?)```", pkg_prose, re.DOTALL
    )
    prose_packages: set[str] = set()
    for code_block in code_blocks_in_section:
        for m in PACKAGE_INSTALL_LINE_PATTERN.finditer(code_block):
            tokens = m.group(1).strip().split()
            # Filter out flags (e.g., -D, --save-dev) and keep only package names
            pkgs = [t for t in tokens if not t.startswith("-")]
            prose_packages.update(pkgs)

    for pkg in sorted(prose_packages - fm_all_packages):
        line_num = content[: pkg_section_match.start()].count("\n") + 1
        error(
            f"[21] {sf}:{line_num}: Packages prose contains 'npm install {pkg}' "
            f"but '{pkg}' is not in frontmatter packages.runtime or packages.dev"
        )

# ---------------------------------------------------------------------------
# Check 22: Bootstrap Payment-Database Dependency
# ---------------------------------------------------------------------------

bootstrap_path_22 = ".claude/commands/bootstrap.md"
if os.path.isfile(bootstrap_path_22):
    with open(bootstrap_path_22) as f:
        bootstrap_content_22 = f.read()

    # Find the Phase 1 Step 3 validation section (a numbered list item: "3. **Validate idea.yaml**")
    validate_section_match = re.search(
        r"(?i)(?:###?\s*|\d+\.\s*(?:\*\*)?)Validate idea\.yaml(?:\*\*)?\s*\n(.*?)(?=\n\d+\.\s*\*\*|\n###?\s|\n##\s|\Z)",
        bootstrap_content_22,
        re.DOTALL,
    )
    if validate_section_match:
        validate_section = validate_section_match.group(1)
        has_db_check = bool(
            re.search(
                r"(?i)payment.*database.*present|database.*present.*payment|"
                r"payment\s+requires.*database|"
                r"stack\.database.*(?:missing|present|also)|"
                r"stack\.payment.*(?:verify|check).*stack\.database",
                validate_section,
            )
        )
        if not has_db_check:
            error(
                f"[22] {bootstrap_path_22}: Validate idea.yaml section "
                f"doesn't validate that `stack.payment` requires "
                f"`stack.database` to also be present"
            )
    else:
        error(
            f"[22] {bootstrap_path_22}: could not find Validate idea.yaml "
            f"section to check payment-database dependency"
        )

# ---------------------------------------------------------------------------
# Check 23: Testing CI Template Includes Payment Env Vars When ci.yml Does
# ---------------------------------------------------------------------------

ci_yml_path_23 = ".github/workflows/ci.yml"
if os.path.isfile(ci_yml_path_23):
    with open(ci_yml_path_23) as f:
        ci_content_23 = f.read()

    # Check if ci.yml e2e job contains Stripe env vars
    e2e_match = re.search(
        r"e2e:.*?(?=\n  \w+:|\Z)", ci_content_23, re.DOTALL
    )
    if e2e_match:
        e2e_section = e2e_match.group(0)
        stripe_vars_in_ci = re.findall(
            r"(STRIPE_\w+|NEXT_PUBLIC_STRIPE_\w+)", e2e_section
        )

        if stripe_vars_in_ci:
            # Check that testing stack CI template also mentions them
            for sf, content in stack_contents.items():
                if "/testing/" not in sf:
                    continue
                ci_template_match = re.search(
                    r"## CI Job Template\s*\n(.*?)(?=\n## |\Z)",
                    content,
                    re.DOTALL,
                )
                if ci_template_match:
                    ci_template = ci_template_match.group(1)
                    for var in stripe_vars_in_ci:
                        if var not in ci_template:
                            error(
                                f"[23] {sf}: CI Job Template missing '{var}' "
                                f"which is present in ci.yml e2e job"
                            )

# ---------------------------------------------------------------------------
# Check 24: Testing Stack No-Auth Fallback Includes CI Job Template
# ---------------------------------------------------------------------------

for sf, content in stack_contents.items():
    if "/testing/" not in sf:
        continue
    fm = parse_frontmatter(sf)
    if not fm:
        continue

    # Check for No-Auth Fallback section
    fallback_match = re.search(
        r"## No-Auth Fallback\s*\n(.*?)(?=\n## [^#]|\Z)",
        content,
        re.DOTALL,
    )
    if fallback_match:
        fallback_section = fallback_match.group(1)
        # Check for a YAML code block with an e2e: job definition
        yaml_blocks = re.findall(
            r"```yaml\s*\n(.*?)```", fallback_section, re.DOTALL
        )
        has_e2e_job = any("e2e:" in block for block in yaml_blocks)
        if not has_e2e_job:
            error(
                f"[24] {sf}: No-Auth Fallback section missing a CI job "
                f"template (YAML code block with 'e2e:' job definition)"
            )

# ---------------------------------------------------------------------------
# Check 25: Change Skill Test Type Permits Adding Testing to idea.yaml Stack
# ---------------------------------------------------------------------------

change_path_25 = ".claude/commands/change.md"
if os.path.isfile(change_path_25):
    with open(change_path_25) as f:
        change_content_25 = f.read()

    # Look for text indicating the Test type can add testing to idea.yaml stack
    has_testing_addition = bool(
        re.search(
            r"(?i)(?:test.*(?:add|update).*(?:idea\.yaml|stack).*testing|"
            r"testing.*(?:idea\.yaml|stack)|"
            r"stack\.testing.*idea\.yaml)",
            change_content_25,
        )
    )
    if not has_testing_addition:
        error(
            f"[25] {change_path_25}: Test type constraints do not address "
            f"adding `testing` to idea.yaml stack section"
        )

# ---------------------------------------------------------------------------
# Check 26: Testing Stack Env Frontmatter Excludes Assumes-Dependent Vars
# ---------------------------------------------------------------------------

for sf in stack_files:
    if "/testing/" not in sf:
        continue
    fm = parse_frontmatter(sf)
    if not fm:
        continue

    assumes = fm.get("assumes", []) or []
    optional_assumes = [
        a for a in assumes
        if a.split("/")[0] in OPTIONAL_CATEGORIES
    ]
    if not optional_assumes:
        continue

    # Check if there's a fallback section (meaning assumes are truly optional)
    content = stack_contents.get(sf, "")
    has_fallback = bool(
        re.search(r"(?i)fallback|no[- ]auth", content)
    )
    if not has_fallback:
        continue

    # Get provider names from optional assumes
    provider_names = set()
    for a in optional_assumes:
        provider_names.add(a.split("/")[1].upper())

    env_section = fm.get("env", {}) or {}
    server_vars = env_section.get("server", []) or []
    client_vars = env_section.get("client", []) or []
    all_env = server_vars + client_vars

    for var in all_env:
        for provider in provider_names:
            if provider in var:
                error(
                    f"[26] {sf}: env frontmatter var '{var}' contains "
                    f"provider name '{provider}' from optional assumes — "
                    f"should not be unconditional when a fallback exists"
                )

# ---------------------------------------------------------------------------
# Check 27: Auth Template Post-Auth Redirects
# ---------------------------------------------------------------------------

for sf, content in stack_contents.items():
    if "/auth/" not in sf:
        continue

    blocks = extract_code_blocks(content, {"tsx", "jsx"})
    for block in blocks:
        code = block["code"]
        # Check if this is a signup or login page template
        is_signup = "signUp" in code or "handleSignup" in code
        is_login = "signInWithPassword" in code or "handleLogin" in code
        if not is_signup and not is_login:
            continue

        page_type = "signup" if is_signup else "login"

        # Check for a redirect call after the auth success path
        has_redirect = bool(
            re.search(r"router\.push\(|router\.replace\(|redirect\(", code)
        )
        has_only_todo = bool(
            re.search(r"//\s*TODO.*redirect", code, re.IGNORECASE)
        )

        if not has_redirect or has_only_todo:
            error(
                f"[27] {sf}:{block['start_line']}: {page_type} page template "
                f"has no post-auth redirect (router.push/redirect) — only a "
                f"TODO comment"
                if has_only_todo
                else f"[27] {sf}:{block['start_line']}: {page_type} page "
                f"template missing post-auth redirect (router.push/redirect)"
            )

# ---------------------------------------------------------------------------
# Check 28: Change Assumes Validation Matches Bootstrap Assumes Validation
# ---------------------------------------------------------------------------

change_path_28 = ".claude/commands/change.md"
bootstrap_path_28 = ".claude/commands/bootstrap.md"
if os.path.isfile(change_path_28) and os.path.isfile(bootstrap_path_28):
    with open(change_path_28) as f:
        change_content_28 = f.read()

    # Find assumes validation text in change.md
    assumes_refs = list(
        re.finditer(r"(?i)assumes.*list", change_content_28)
    )
    if assumes_refs:
        # Check if the change skill's assumes validation includes
        # value-matching language (not just category existence)
        change_assumes_text = change_content_28
        has_value_matching = bool(
            re.search(
                r"(?i)category[/:]value|value\s+(?:must\s+)?match|"
                r"matching\s+.*pair|category:\s*value.*pair|"
                r"not just.*(?:category|present)",
                change_assumes_text,
            )
        )
        has_category_only = bool(
            re.search(
                r"(?i)check if the corresponding stack category exists",
                change_assumes_text,
            )
        )
        if has_category_only and not has_value_matching:
            error(
                f"[28] {change_path_28}: assumes validation uses "
                f"category-existence language instead of value-matching "
                f"language (should match bootstrap's approach)"
            )

# ---------------------------------------------------------------------------
# Check 29: Change Payment Validation Before Plan Phase
# ---------------------------------------------------------------------------

change_path_29 = ".claude/commands/change.md"
if os.path.isfile(change_path_29):
    with open(change_path_29) as f:
        change_content_29 = f.read()

    # Find payment dependency validation text (the stop messages)
    payment_validation_pattern = re.compile(
        r"Payment requires (?:authentication|a database)",
        re.IGNORECASE,
    )
    payment_matches = list(payment_validation_pattern.finditer(change_content_29))

    if payment_matches:
        # Find the plan phase marker
        plan_phase_match = re.search(
            r"## Phase 1|### STOP",
            change_content_29,
        )
        if plan_phase_match:
            plan_phase_pos = plan_phase_match.start()
            # At least one payment validation instance must appear before plan phase
            has_pre_plan = any(
                m.start() < plan_phase_pos for m in payment_matches
            )
            if not has_pre_plan:
                error(
                    f"[29] {change_path_29}: all payment dependency "
                    f"validation appears after the plan phase — at least "
                    f"one check must be in preconditions (before Phase 1)"
                )

# ---------------------------------------------------------------------------
# Check 30: Analytics Stack Files Include Dashboard Navigation Section
# ---------------------------------------------------------------------------

analytics_stack_files = [
    sf for sf in stack_files if "/analytics/" in sf
]

for sf in analytics_stack_files:
    content = stack_contents[sf]
    has_dashboard_nav = bool(
        re.search(r"(?i)^## Dashboard Navigation", content, re.MULTILINE)
    )
    if not has_dashboard_nav:
        error(
            f"[30] {sf}: analytics stack file missing required "
            f"'## Dashboard Navigation' section (needed by /iterate skill)"
        )

# ---------------------------------------------------------------------------
# Check 31: Change Skill Revalidates Testing Assumes for All Change Types
# ---------------------------------------------------------------------------

change_path_31 = ".claude/commands/change.md"
if os.path.isfile(change_path_31):
    with open(change_path_31) as f:
        change_content_31 = f.read()

    # Find Step 3 (preconditions) section
    step3_match = re.search(
        r"## Step 3:.*?\n(.*?)(?=\n## Step \d|\n## Phase|\Z)",
        change_content_31,
        re.DOTALL,
    )
    if step3_match:
        step3_text = step3_match.group(1)

        # Look for testing assumes validation NOT gated by Test-type classification
        # There should be a check that runs when type is NOT Test
        has_non_test_assumes_check = bool(
            re.search(
                r"(?i)(?:NOT\s+Test|type\s+is\s+NOT\s+Test).*testing.*assumes|"
                r"testing.*assumes.*(?:NOT\s+Test|type\s+is\s+NOT\s+Test)",
                step3_text,
                re.DOTALL,
            )
        )
        if not has_non_test_assumes_check:
            error(
                f"[31] {change_path_31}: Step 3 preconditions do not "
                f"revalidate testing assumes for non-Test change types"
            )
    else:
        error(
            f"[31] {change_path_31}: could not find Step 3 section "
            f"to check testing assumes revalidation"
        )

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

print()
if ERRORS:
    print(f"FAILED: {len(ERRORS)} error(s)")
    sys.exit(1)
else:
    print("PASSED: All semantic checks passed.")
    sys.exit(0)
