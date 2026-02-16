#!/usr/bin/env bash
# Session-start hook: detects project state and injects context into every session.
# Output: JSON with hookSpecificOutput.additionalContext
# Always exits 0 — never blocks the session on error.

set -euo pipefail

PROJECT_ROOT="${CLAUDE_PROJECT_DIR:-}"
if [ -z "$PROJECT_ROOT" ]; then
  echo '{"hookSpecificOutput":{"additionalContext":"Could not determine project root (CLAUDE_PROJECT_DIR not set)."}}'
  exit 0
fi

escape_for_json() {
  local s="$1"
  s="${s//\\/\\\\}"
  s="${s//\"/\\\"}"
  s="${s//$'\n'/\\n}"
  s="${s//$'\t'/\\t}"
  echo "$s"
}

msg=""

if [ ! -f "$PROJECT_ROOT/idea/idea.yaml" ]; then
  msg="No idea.yaml found. Create one at idea/idea.yaml and fill in every field."
elif grep -qc 'TODO' "$PROJECT_ROOT/idea/idea.yaml" 2>/dev/null && [ "$(grep -c 'TODO' "$PROJECT_ROOT/idea/idea.yaml")" -gt 0 ]; then
  todo_count=$(grep -c 'TODO' "$PROJECT_ROOT/idea/idea.yaml")
  msg="idea.yaml has $todo_count TODO placeholders. Fill them in, then \`make validate\`."
elif [ ! -f "$PROJECT_ROOT/package.json" ]; then
  msg="idea.yaml is ready but not bootstrapped. Run \`/bootstrap\`."
else
  msg="Project is bootstrapped. Available skills: \`/change\`, \`/iterate\`, \`/retro\`."
  if [ ! -f "$PROJECT_ROOT/.env.local" ]; then
    msg="$msg Remember to create .env.local from .env.example before running the dev server."
  fi
fi

msg="$msg\nidea.yaml is the single source of truth. Read it before any task."

escaped=$(escape_for_json "$msg")
echo "{\"hookSpecificOutput\":{\"additionalContext\":\"$escaped\"}}"
exit 0
