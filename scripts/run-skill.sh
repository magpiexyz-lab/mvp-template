#!/usr/bin/env bash
set -euo pipefail

# run-skill.sh — Prepare a branch and launch Claude Code with a skill
#
# Usage: ./scripts/run-skill.sh <skill-name> [branch-prefix] [extra-args]
#
# Examples:
#   ./scripts/run-skill.sh bootstrap feat
#   ./scripts/run-skill.sh bugfix fix "123"
#   ./scripts/run-skill.sh instrument chore
#   ./scripts/run-skill.sh polish chore

# --- Helpers ---

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No color

info()  { echo -e "${GREEN}==>${NC} $*"; }
warn()  { echo -e "${YELLOW}==>${NC} $*"; }
error() { echo -e "${RED}==> ERROR:${NC} $*" >&2; }

# --- Check prerequisites ---

check_command() {
  if ! command -v "$1" &>/dev/null; then
    error "$1 is not installed. $2"
    exit 1
  fi
}

check_command git "Install from https://git-scm.com"
check_command node "Install from https://nodejs.org (v20+)"
check_command claude "Install from https://claude.ai/code"
check_command gh "Install from https://cli.github.com"

# Verify Node.js version is 20+
node -e "if(parseInt(process.version.slice(1))<20){console.error('Error: Node 20+ required (found '+process.version+'). Fix: run \"nvm use 20\" or install from https://nodejs.org');process.exit(1)}"

# Verify GitHub CLI is authenticated
if ! gh auth status &>/dev/null; then
  error "GitHub CLI is not authenticated. Run: gh auth login"
  exit 1
fi

# --- Parse arguments ---

SKILL="${1:?Usage: run-skill.sh <skill-name> [branch-prefix] [extra-args]}"
BRANCH_PREFIX="${2:-feat}"
# Sanitize extra args: strip backticks and backslashes to prevent shell expansion
EXTRA_ARGS=$(printf '%s' "${3:-}" | tr -d '`\\')

# Verify the skill file exists
SKILL_FILE=".claude/commands/${SKILL}.md"
if [[ ! -f "$SKILL_FILE" ]]; then
  error "Skill file not found: ${SKILL_FILE}"
  error "Available skills: $(ls .claude/commands/*.md 2>/dev/null | xargs -I{} basename {} .md | tr '\n' ' ')"
  exit 1
fi

# --- Analysis-only skills (no branch needed) ---

ANALYSIS_ONLY_SKILLS="iterate retro"
if [[ " $ANALYSIS_ONLY_SKILLS " == *" $SKILL "* ]]; then
  info "Analysis-only skill — no branch needed"
  echo ""
  if [[ -n "$EXTRA_ARGS" ]]; then
    claude "/${SKILL} ${EXTRA_ARGS}"
  else
    claude "/${SKILL}"
  fi
  exit 0
fi

# --- Verify git repository state ---

if ! git rev-parse --is-inside-work-tree &>/dev/null; then
  error "Not a git repository."
  echo "  Fix: run 'git init' or clone a repo first."
  exit 1
fi

if ! git symbolic-ref HEAD &>/dev/null; then
  error "HEAD is detached. You must be on a branch to run skills."
  echo "  Fix: run 'git checkout main' to switch to a branch."
  exit 1
fi

if ! git remote get-url origin &>/dev/null; then
  error "No 'origin' remote found. Skills need a remote to push branches."
  echo "  Fix: run 'git remote add origin <repo-url>' to set one up."
  exit 1
fi

# --- Build branch name ---

BRANCH="${BRANCH_PREFIX}/${SKILL}"
if [[ -n "$EXTRA_ARGS" ]]; then
  if [[ "$EXTRA_ARGS" =~ ^[0-9]+$ ]]; then
    # Issue number (e.g., bugfix 123)
    BRANCH="${BRANCH_PREFIX}/issue-${EXTRA_ARGS}"
  else
    # Text description (e.g., feature "add email reminders") → feat/add-email-reminders
    SLUG=$(echo "$EXTRA_ARGS" | tr '[:upper:]' '[:lower:]' | tr -cs '[:alnum:]' '-' | sed 's/^-//' | head -c 40 | sed 's/-$//')
    BRANCH="${BRANCH_PREFIX}/${SLUG}"
  fi
fi

# --- Check for uncommitted changes ---

if ! git diff --quiet || ! git diff --cached --quiet; then
  error "You have uncommitted changes. Please commit or stash them first."
  echo ""
  git status --short
  exit 1
fi

# --- Switch to default branch and pull latest ---

DEFAULT_BRANCH=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@')
if [[ -z "$DEFAULT_BRANCH" ]]; then
  DEFAULT_BRANCH="main"
  warn "Could not detect default branch — assuming 'main'. Run 'git remote set-head origin --auto' to fix."
fi

CURRENT_BRANCH=$(git branch --show-current)
if [[ "$CURRENT_BRANCH" != "$DEFAULT_BRANCH" ]]; then
  info "Switching from '${CURRENT_BRANCH}' to ${DEFAULT_BRANCH}..."
  git checkout "$DEFAULT_BRANCH"
fi

info "Pulling latest from ${DEFAULT_BRANCH}..."
if ! git pull --ff-only 2>/dev/null; then
  warn "Could not fast-forward main. Trying regular pull..."
  git pull --rebase || { git rebase --abort 2>/dev/null; error "Could not update main. Run 'git pull' on main manually and retry."; exit 1; }
fi

# --- Create feature branch (handle existing branches) ---

if git show-ref --verify --quiet "refs/heads/${BRANCH}"; then
  SUFFIX=2
  while git show-ref --verify --quiet "refs/heads/${BRANCH}-${SUFFIX}"; do
    ((SUFFIX++))
  done
  BRANCH="${BRANCH}-${SUFFIX}"
  warn "Branch already existed. Using: ${BRANCH}"
fi

info "Creating branch: ${BRANCH}"
git checkout -b "$BRANCH"

# --- Launch Claude Code interactively ---

info "Launching Claude Code with /${SKILL}..."
echo ""

if [[ -n "$EXTRA_ARGS" ]]; then
  claude "/${SKILL} ${EXTRA_ARGS}"
else
  claude "/${SKILL}"
fi
