#!/usr/bin/env python3
"""Validate semantic correctness across stack files, skill files, and fixtures.

Checks:
  1. TODO Resolution Coverage — every code-block TODO has resolution guidance
  2. Import Completeness in TSX Templates — JSX components have matching imports
  3. Error Message Actionability — error messages contain fix hints
  4. Makefile Target Guards — npm/node targets guard on package.json
  5. Fixture Validation — test fixture files are structurally correct
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


def ngrams(text: str, n: int) -> list[str]:
    """Generate n-grams from text."""
    words = re.findall(r"[a-zA-Z_]+", text)
    return [" ".join(words[i : i + n]) for i in range(len(words) - n + 1)]


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

# Collect all prose from skill files and stack files for cross-referencing
all_skill_prose = "\n".join(extract_prose(c) for c in skill_contents.values())
all_stack_prose = {sf: extract_prose(c) for sf, c in stack_contents.items()}

# ---------------------------------------------------------------------------
# Check 1: TODO Resolution Coverage
# ---------------------------------------------------------------------------

for sf, content in stack_contents.items():
    blocks = extract_code_blocks(content, {"tsx", "ts", "js", "jsx"})
    same_file_prose = all_stack_prose[sf]

    for block in blocks:
        for i, line in enumerate(block["code"].splitlines()):
            if "TODO" not in line and "FIXME" not in line:
                continue

            # Skip TODOs that are placeholders replaced by bootstrap
            # (e.g., PROJECT_NAME = "TODO"; // Replaced by bootstrap)
            if "Replaced by bootstrap" in line or "replaced by bootstrap" in line:
                continue

            todo_text = line.strip().lstrip("/ ").lstrip("*").strip()
            line_num = block["start_line"] + i + 1

            # Generate n-grams from the TODO text and search for them
            # in skill prose and the same stack file's prose.
            # Try 3-grams first, then fall back to 2-grams for flexibility.
            grams = ngrams(todo_text, 3) + ngrams(todo_text, 2)
            found = False
            skill_prose_lower = all_skill_prose.lower()
            file_prose_lower = same_file_prose.lower()
            for gram in grams:
                gram_lower = gram.lower()
                # Skip n-grams that are only stop words
                meaningful = [w for w in gram_lower.split() if len(w) > 2]
                if not meaningful:
                    continue
                if gram_lower in skill_prose_lower:
                    found = True
                    break
                if gram_lower in file_prose_lower:
                    found = True
                    break

            if not found:
                error(
                    f"[1] {sf}:{line_num}: TODO has no resolution guidance in "
                    f"skill or stack prose: {todo_text[:80]}"
                )

# ---------------------------------------------------------------------------
# Check 2: Import Completeness in TSX Templates
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
                f"[2] {sf}:{block_line}: JSX component <{comp}> used but "
                f"not imported in code block"
            )

# ---------------------------------------------------------------------------
# Check 3: Error Message Actionability
# ---------------------------------------------------------------------------

# Patterns indicating an actionable fix hint
ACTIONABLE_PATTERNS = re.compile(
    r"(?i)"
    r"(?:run\s|fix:|try\s|install\s|check\s|use\s|add\s|set\s|create\s|merge\s|"
    r"ensure\s|update\s|replace\s|change\s|verify\s|see\s|read\s|visit\s|open\s|"
    r"`[^`]+`|"   # backtick-wrapped command
    r"make\s|"
    r"https?://)"  # URL as guidance
)

# Check skill files for "stop and tell the user" error messages
for sf, content in skill_contents.items():
    # Pattern: text after "stop and tell the user" up to end of sentence/line
    for m in re.finditer(
        r"stop and tell the user[:\s]+[\"']?([^\"'\n]+)", content, re.IGNORECASE
    ):
        msg = m.group(1).strip()
        if not ACTIONABLE_PATTERNS.search(msg):
            line_num = content[: m.start()].count("\n") + 1
            error(
                f"[3] {sf}:{line_num}: error message lacks actionable fix hint: "
                f"\"{msg[:80]}\""
            )

# Check Makefile for echo "Error: ..." lines
makefile_path = "Makefile"
if os.path.isfile(makefile_path):
    with open(makefile_path) as f:
        makefile_content = f.read()

    for m in re.finditer(r'echo\s+"(Error:[^"]+)"', makefile_content):
        msg = m.group(1)
        # Check the next few lines too (error message + fix hint may be separate echo)
        pos = m.end()
        context = makefile_content[m.start() : pos + 200]
        if not ACTIONABLE_PATTERNS.search(context):
            line_num = makefile_content[: m.start()].count("\n") + 1
            error(
                f"[3] {makefile_path}:{line_num}: error message lacks actionable "
                f"fix hint: \"{msg[:80]}\""
            )

# ---------------------------------------------------------------------------
# Check 4: Makefile Target Guards
# ---------------------------------------------------------------------------

if os.path.isfile(makefile_path):
    with open(makefile_path) as f:
        makefile_content = f.read()

    # Targets that don't need guards:
    # - Pre-bootstrap / meta: bootstrap, validate, clean, clean-all, help
    # - Post-bootstrap only: dev, deploy, test-e2e (user runs these after
    #   bootstrap; npm errors are self-explanatory in this context)
    EXEMPT_TARGETS = {
        "bootstrap",
        "validate",
        "clean",
        "clean-all",
        "help",
        "dev",
        "deploy",
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
                f"[4] {makefile_path}:{line_num}: target '{target_name}' uses "
                f"npm/node but has no package.json guard"
            )

# ---------------------------------------------------------------------------
# Check 5: Fixture Validation
# ---------------------------------------------------------------------------

fixture_dir = "tests/fixtures"
if os.path.isdir(fixture_dir):
    fixture_files = sorted(glob.glob(os.path.join(fixture_dir, "*.yaml")))

    if not fixture_files:
        error(f"[5] {fixture_dir}: no fixture files found")

    for ff in fixture_files:
        with open(ff) as f:
            try:
                fixture = yaml.safe_load(f)
            except yaml.YAMLError as e:
                error(f"[5] {ff}: invalid YAML: {e}")
                continue

        if not isinstance(fixture, dict):
            error(f"[5] {ff}: fixture must be a YAML mapping")
            continue

        # Check required top-level keys
        for key in ["idea", "events", "assertions"]:
            if key not in fixture:
                error(f"[5] {ff}: missing required key '{key}'")

        idea = fixture.get("idea", {})
        if not isinstance(idea, dict):
            error(f"[5] {ff}: 'idea' must be a mapping")
            continue

        # Validate idea.name format
        name = idea.get("name", "")
        if not re.match(r"^[a-z][a-z0-9-]*$", str(name)):
            error(
                f"[5] {ff}: idea.name '{name}' must be lowercase, start with "
                f"a letter, and use only a-z, 0-9, hyphens"
            )

        # Validate required idea fields
        required_idea_fields = [
            "name",
            "title",
            "owner",
            "problem",
            "solution",
            "target_user",
            "pages",
            "features",
            "primary_metric",
            "target_value",
            "measurement_window",
            "stack",
        ]
        for field in required_idea_fields:
            if not idea.get(field):
                error(f"[5] {ff}: idea.{field} is missing or empty")

        # Validate pages includes landing
        pages = idea.get("pages", [])
        if isinstance(pages, list):
            has_landing = any(
                isinstance(p, dict) and p.get("name") == "landing" for p in pages
            )
            if not has_landing:
                error(f"[5] {ff}: idea.pages must include a 'landing' entry")

        # Validate assertions
        assertions = fixture.get("assertions", {})
        if isinstance(assertions, dict):
            # If no payment stack, payment_funnel events should not be required
            stack = idea.get("stack", {})
            has_payment = "payment" in stack if isinstance(stack, dict) else False
            payment_required = assertions.get("payment_events_required", False)
            if payment_required and not has_payment:
                error(
                    f"[5] {ff}: assertions.payment_events_required is true but "
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
                            f"[5] {ff}: no signup page but '{ev}' not in "
                            f"assertions.skippable_events"
                        )

            # Validate min_pages matches actual page count
            min_pages = assertions.get("min_pages")
            if min_pages is not None and isinstance(pages, list):
                if len(pages) < min_pages:
                    error(
                        f"[5] {ff}: idea has {len(pages)} page(s) but "
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
                        f"[5] {ff}: events.payment_funnel is non-empty but "
                        f"idea.stack has no payment entry"
                    )
else:
    # No fixture directory is not an error — fixtures are optional pre-creation
    pass

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
