#!/usr/bin/env python3
"""Validate idea.yaml structure: name format, landing page, required fields,
stack file existence, testing warning, and stack assumes consistency.

Exit codes:
  0 — all checks passed
  1 — hard error (validation failed)
  2 — passed with warnings (missing stack files, testing in stack, etc.)
"""

import os
import re
import sys

import yaml


data = yaml.safe_load(open("idea/idea.yaml"))
warnings = False

# --- Name format ---
name = data.get("name", "")
if not re.fullmatch(r"[a-z][a-z0-9-]*", name):
    print(
        f'Error: name "{name}" must be lowercase, start with a letter, '
        "and use only a-z, 0-9, hyphens."
    )
    print("Example: my-experiment-1")
    sys.exit(1)

# --- Landing page ---
pages = data.get("pages", [])
if not any(p.get("name") == "landing" for p in pages):
    print("Error: pages must include an entry with name: landing")
    print("Add a landing page to the pages list in idea.yaml.")
    sys.exit(1)

# --- Required fields ---
required = [
    "name", "title", "owner", "problem", "solution", "target_user",
    "distribution", "pages", "features", "primary_metric", "target_value",
    "measurement_window", "stack",
]
missing = [f for f in required if not data.get(f)]
if missing:
    print("Error: these required fields are missing or empty: " + ", ".join(missing))
    sys.exit(1)
if not data.get("template_repo"):
    print(
        "  Warning: template_repo not set. "
        "/retro will ask where to file the retrospective."
    )

# --- Stack file existence ---
stack = data.get("stack", {})
stack_warnings = [
    f"stack.{k}: {v} — no file at .claude/stacks/{k}/{v}.md"
    for k, v in stack.items()
    if not os.path.isfile(f".claude/stacks/{k}/{v}.md")
]
if stack_warnings:
    for w in stack_warnings:
        print(f"  Warning: {w}")
    print(
        "  Claude will use general knowledge for these. "
        "To fix: create the stack file or change the value."
    )
    warnings = True

# --- Testing in stack warning ---
if "testing" in stack:
    print("  Warning: stack.testing is set but /bootstrap will reject it.")
    print("  Testing must be added after the initial bootstrap PR is merged.")
    print("  Remove 'testing:' now, or add it later with '/change add E2E smoke tests'.")

# --- Stack assumes consistency ---
assumes_warnings = []
for cat, val in stack.items():
    sf = f".claude/stacks/{cat}/{val}.md"
    if not os.path.isfile(sf):
        continue
    with open(sf) as f:
        content = f.read()
    m = re.match(r"^---\n(.*?\n)---", content, re.DOTALL)
    if not m:
        continue
    fm = yaml.safe_load(m.group(1)) or {}
    for assume in fm.get("assumes") or []:
        parts = assume.split("/")
        if len(parts) != 2:
            continue
        a_cat, a_val = parts
        actual = stack.get(a_cat)
        if actual is None:
            assumes_warnings.append(
                f"stack.{cat}/{val} assumes {assume}, but stack.{a_cat} is not set"
            )
        elif actual != a_val:
            assumes_warnings.append(
                f"stack.{cat}/{val} assumes {assume}, but stack.{a_cat} is {actual}"
            )

if assumes_warnings:
    print("  Warning: stack assumes mismatches:")
    for w in assumes_warnings:
        print(f"    - {w}")
    print(
        "  /bootstrap will reject these. "
        "Fix idea.yaml stack values or create compatible stack files."
    )
    warnings = True

sys.exit(2 if warnings else 0)
