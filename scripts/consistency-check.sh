#!/usr/bin/env bash
set -euo pipefail

# consistency-check.sh — Verify facts live in canonical sources, not in rules/skills
#
# Canonical (facts SHOULD appear here):
#   EVENTS.yaml, .claude/stacks/**/*.md, idea/idea.yaml
#
# Reference-only (facts should NOT appear here):
#   CLAUDE.md, .claude/commands/*.md

ERRORS=0

# Derive code-writing skills dynamically from frontmatter type
CODE_WRITING_SKILLS=()
for f in .claude/commands/*.md; do
  [ -f "$f" ] || continue
  if head -20 "$f" | grep -q 'type: code-writing'; then
    CODE_WRITING_SKILLS+=("$f")
  fi
done

check_absent() {
  local file="$1" pattern="$2" desc="$3"
  [ -f "$file" ] || return 0
  if grep -qE "$pattern" "$file"; then
    echo "FAIL: $file — $desc"
    grep -nE "$pattern" "$file" | head -5
    echo ""
    ERRORS=$((ERRORS + 1))
  fi
}

echo "=== Consistency Check: Reference, Never Restate ==="
echo ""

# 1. Event name enumerations in CLAUDE.md (bullet + backtick-event + dash)
check_absent "CLAUDE.md" \
  '^\s*-\s*`(visit_landing|signup_start|signup_complete|activate|retain_return|pay_start|pay_success)` — ' \
  "enumerated event definitions (should reference EVENTS.yaml)"

# 2. Event name enumerations in skill files
for f in .claude/commands/*.md; do
  [ -f "$f" ] || continue
  check_absent "$f" \
    '^\s*[\-\|]\s*`?(visit_landing|signup_start|signup_complete|activate|retain_return|pay_start|pay_success)`?\s*(on |— |\| )' \
    "enumerated event names (should reference EVENTS.yaml)"
done

# 3. Hardcoded analytics import path in skills
for f in .claude/commands/*.md; do
  [ -f "$f" ] || continue
  check_absent "$f" '@/lib/analytics' \
    "hardcoded import path (should reference analytics stack file)"
done

# 4. Framework-specific terms in CLAUDE.md
check_absent "CLAUDE.md" \
  'Server Actions|parallel routes|intercepting routes' \
  "framework-specific terms (belong in framework stack file)"

# 5. Framework-specific terms in skill files
for f in .claude/commands/*.md; do
  [ -f "$f" ] || continue
  check_absent "$f" '"use client"' \
    "Next.js directive (should reference framework stack file)"
  check_absent "$f" 'Server Actions' \
    "Next.js term (should reference framework stack file)"
  check_absent "$f" '\buseEffect\b' \
    "React-specific term (use generic or reference framework stack file)"
done

# 6. Hardcoded analytics constants in CLAUDE.md
check_absent "CLAUDE.md" 'PROJECT_NAME|PROJECT_OWNER' \
  "hardcoded constant names (should reference analytics stack file)"

# 7. Hardcoded framework paths in feature skill
check_absent ".claude/commands/change.md" 'src/app/api/' \
  "hardcoded API path (should reference framework stack file)"
check_absent ".claude/commands/change.md" 'src/lib/types\.ts' \
  "hardcoded types path (should reference database stack file)"

# 8. (removed)

# 9. Hardcoded analytics path in PR template
check_absent ".github/PULL_REQUEST_TEMPLATE.md" 'src/lib/analytics' \
  "hardcoded analytics path (should say 'the analytics library')"

# 10. All code-writing skills reference verify.md
for f in "${CODE_WRITING_SKILLS[@]}"; do
  [ -f "$f" ] || continue
  if ! grep -q 'patterns/verify.md' "$f"; then
    echo "FAIL: $f — missing verify.md reference (all code-writing skills must reference the verification procedure)"
    ERRORS=$((ERRORS + 1))
  fi
done

# 11. (removed)

echo ""
if [ "$ERRORS" -gt 0 ]; then
  echo "FAILED: $ERRORS violation(s). Move facts to canonical sources (EVENTS.yaml, stack files)."
  exit 1
else
  echo "PASSED: No consistency violations."
fi
