#!/usr/bin/env python3
"""Validate YAML frontmatter in stack and skill files.

Checks:
  Stack structural:
    1. Required frontmatter keys present in every stack file
    2. Every `assumes` entry resolves to an existing stack file
  Skill structural:
    3. Required frontmatter keys present in every skill file
    4. Every `references` file path exists on disk
    5. code-writing skills must reference verify.md
    6. code-writing skills must reference branch.md
  Cross-file:
    7. CLAUDE.md Rule 0 skill list matches actual skill filenames
    8. Union of ci_placeholders keys appears in ci.yml
    9. All ci_placeholders values are covered by .gitleaks.toml allowlist
    10. Skill branch_prefix values appear in CLAUDE.md Rule 1
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


# ---------------------------------------------------------------------------
# Collect files
# ---------------------------------------------------------------------------

stack_files = sorted(
    f
    for f in glob.glob(".claude/stacks/**/*.md", recursive=True)
    if "TEMPLATE" not in f
)
skill_files = sorted(glob.glob(".claude/commands/*.md"))

STACK_REQUIRED_KEYS = [
    "assumes",
    "packages",
    "files",
    "env",
    "ci_placeholders",
    "clean",
    "gitignore",
]
SKILL_REQUIRED_KEYS = [
    "type",
    "reads",
    "stack_categories",
    "requires_approval",
    "references",
    "branch_prefix",
    "modifies_specs",
]

# ---------------------------------------------------------------------------
# Check 1: Stack files have all required frontmatter keys
# ---------------------------------------------------------------------------

stack_data: dict[str, dict] = {}
for sf in stack_files:
    data = parse_frontmatter(sf)
    if data is None:
        error(f"[1] {sf}: missing frontmatter")
        continue
    stack_data[sf] = data
    for key in STACK_REQUIRED_KEYS:
        if key not in data:
            error(f"[1] {sf}: missing required key '{key}'")

# ---------------------------------------------------------------------------
# Check 2: Every assumes entry resolves to an existing stack file
# ---------------------------------------------------------------------------

for sf, data in stack_data.items():
    for dep in data.get("assumes", []):
        dep_path = f".claude/stacks/{dep}.md"
        if not os.path.isfile(dep_path):
            error(f"[2] {sf}: assumes '{dep}' but {dep_path} does not exist")

# ---------------------------------------------------------------------------
# Check 3: Skill files have all required frontmatter keys
# ---------------------------------------------------------------------------

skill_data: dict[str, dict] = {}
for sf in skill_files:
    data = parse_frontmatter(sf)
    if data is None:
        error(f"[3] {sf}: missing frontmatter")
        continue
    skill_data[sf] = data
    for key in SKILL_REQUIRED_KEYS:
        if key not in data:
            error(f"[3] {sf}: missing required key '{key}'")

# ---------------------------------------------------------------------------
# Check 4: Every references file path exists on disk
# ---------------------------------------------------------------------------

for sf, data in skill_data.items():
    for ref in data.get("references", []):
        if not os.path.exists(ref):
            error(f"[4] {sf}: references '{ref}' but file does not exist")

# ---------------------------------------------------------------------------
# Check 5: code-writing skills must reference verify.md
# ---------------------------------------------------------------------------

for sf, data in skill_data.items():
    if data.get("type") != "code-writing":
        continue
    refs = data.get("references", [])
    ref_basenames = [os.path.basename(r) for r in refs]
    if "verify.md" not in ref_basenames:
        error(f"[5] {sf}: code-writing skill missing verify.md in references")

# ---------------------------------------------------------------------------
# Check 6: code-writing skills must reference branch.md
# ---------------------------------------------------------------------------

for sf, data in skill_data.items():
    if data.get("type") != "code-writing":
        continue
    refs = data.get("references", [])
    ref_basenames = [os.path.basename(r) for r in refs]
    if "branch.md" not in ref_basenames:
        error(f"[6] {sf}: code-writing skill missing branch.md in references")

# ---------------------------------------------------------------------------
# Check 7: CLAUDE.md Rule 0 parenthetical skill list matches actual filenames
# ---------------------------------------------------------------------------

if os.path.isfile("CLAUDE.md"):
    with open("CLAUDE.md") as f:
        claude_content = f.read()
    # Match the parenthetical list in Rule 0: (/bootstrap, /change, /iterate)
    m = re.search(
        r"outside a defined skill \((/[a-z, /-]+)\)", claude_content
    )
    if m:
        claude_skills = sorted(
            s.strip().lstrip("/") for s in m.group(1).split(",")
        )
        actual_skills = sorted(
            os.path.basename(f).replace(".md", "") for f in skill_files
        )
        if claude_skills != actual_skills:
            error(
                f"[7] CLAUDE.md Rule 0 skill list mismatch: "
                f"claude.md={claude_skills} vs actual={actual_skills}"
            )
    else:
        error("[7] Could not find Rule 0 skill list pattern in CLAUDE.md")

# ---------------------------------------------------------------------------
# Check 10: Skill branch_prefix values appear in CLAUDE.md Rule 1
# ---------------------------------------------------------------------------

if os.path.isfile("CLAUDE.md"):
    with open("CLAUDE.md") as f:
        claude_content_r1 = f.read()
    # Match Rule 1 branch naming line: `feat/<topic>`, `fix/<topic>`, etc.
    r1_match = re.search(
        r"Branch naming:\s*(.+)", claude_content_r1
    )
    if r1_match:
        allowed_prefixes = set(
            re.findall(r"`(\w+)/<", r1_match.group(1))
        )
        for sf, data in skill_data.items():
            prefix = data.get("branch_prefix", "")
            if prefix and prefix not in allowed_prefixes:
                error(
                    f"[10] {sf}: branch_prefix '{prefix}' not in "
                    f"CLAUDE.md Rule 1 allowed prefixes {sorted(allowed_prefixes)}"
                )
    else:
        error("[10] Could not find Rule 1 branch naming pattern in CLAUDE.md")

# ---------------------------------------------------------------------------
# Check 8: Union of ci_placeholders keys appears in ci.yml
# ---------------------------------------------------------------------------

ci_yml_path = ".github/workflows/ci.yml"
if os.path.isfile(ci_yml_path):
    with open(ci_yml_path) as f:
        ci_content = f.read()

    all_placeholder_keys: set[str] = set()
    for _sf, data in stack_data.items():
        for key in data.get("ci_placeholders", {}):
            all_placeholder_keys.add(key)

    for key in sorted(all_placeholder_keys):
        if key not in ci_content:
            error(f"[8] ci_placeholders key '{key}' not found in {ci_yml_path}")

# ---------------------------------------------------------------------------
# Check 9: All ci_placeholders values covered by .gitleaks.toml allowlist
# ---------------------------------------------------------------------------

gitleaks_path = ".gitleaks.toml"
if os.path.isfile(gitleaks_path):
    with open(gitleaks_path) as f:
        gitleaks_content = f.read()
    # Extract regex patterns from the allowlist
    gitleaks_patterns = re.findall(r"'''(.+?)'''", gitleaks_content)

    all_placeholder_values: set[str] = set()
    for _sf, data in stack_data.items():
        for val in data.get("ci_placeholders", {}).values():
            str_val = str(val)
            # Skip URLs — gitleaks won't flag them as secrets
            if str_val.startswith("https://") or str_val.startswith("http://"):
                continue
            all_placeholder_values.add(str_val)

    for val in sorted(all_placeholder_values):
        matched = False
        for pattern in gitleaks_patterns:
            try:
                if re.search(pattern, val):
                    matched = True
                    break
            except re.error:
                pass
        if not matched:
            error(
                f"[9] ci_placeholder value '{val}' not matched by any "
                f".gitleaks.toml allowlist pattern"
            )

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

print()
if ERRORS:
    print(f"FAILED: {len(ERRORS)} error(s)")
    sys.exit(1)
else:
    print("PASSED: All frontmatter checks passed.")
    sys.exit(0)
