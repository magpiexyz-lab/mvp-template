# Experiment Template

![CI](https://github.com/magpiexyz-lab/mvp-template/actions/workflows/ci.yml/badge.svg)

A template repository for running parallel MVP experiments. Fill in your idea, run a command, get a deployable app.

## How It Works

```
1. Fill in idea.yaml  →  /bootstrap  →  Review & merge PR  →  Deploy
                                                                  ↓
                                                           Share with users
                                                                  ↓
4. Act on recommendations  ←  3. /iterate  ←  2. Check analytics dashboards
   (/change ...)               (analysis only — no PR)
           ↓
   Review & merge PR  →  Deploy  →  Repeat
```

Every skill except `/iterate` and `/retro` creates a branch, does the work, and opens a PR for you to review and merge. `/iterate` and `/retro` are analysis-only — they don't create branches or PRs. AI skills are invoked directly in Claude Code (not through `make`).

**Plan-Approve-Execute**: Every code-writing skill follows a three-phase workflow. First, Claude reads your idea.yaml and presents a plain-language plan. Then it **stops and waits** for your approval. Only after you say "approve" does it write any code. This keeps you in control — you can adjust the plan before any files are changed.

## Prerequisites

Install these before starting:

- [Python 3](https://www.python.org/) with PyYAML — `python3 --version` to check; run `pip3 install pyyaml` if needed (used by `make validate` and CI)
- [Node.js](https://nodejs.org/) 20+ — `node --version` to check
- [Claude Code](https://claude.ai/code) — `claude --version` to check (requires a paid plan or API credits — see [pricing](https://claude.ai/pricing))
- **npm** (bundled with Node.js) — this template uses npm exclusively; do not use yarn or pnpm
- [GitHub CLI](https://cli.github.com/) — `gh --version` to check, then `gh auth login`
- [Supabase](https://supabase.com/) project — create one at supabase.com (free tier works) *(default stack — see idea.yaml `stack` section)*
- [PostHog](https://posthog.com/) project — one shared project for all experiments *(default stack)*
- [Vercel](https://vercel.com/) account — for deployment *(default stack)*

> **Note:** The prerequisites above assume the default stack (Supabase, PostHog, Vercel). If you change `stack` values in idea.yaml, substitute the corresponding services.

## Quick Start

### 1. Create your repo

Click **"Use this template"** on GitHub to create a new repository. Then clone it:

```bash
gh repo clone <your-username>/<your-repo-name>
cd <your-repo-name>
```

### 2. Describe your idea

Edit `idea/idea.yaml` — replace every `TODO` with your actual content. See `idea/idea.example.yaml` for a complete example.

The key fields:
- **name**: slug for your project (used in analytics)
- **pages**: every page in your app — Claude builds exactly these, no more
- **features**: up to ~5 capabilities
- **primary_metric**: the one number that tells you if this worked

### 3. Commit your idea, then validate and bootstrap

```bash
git add idea/idea.yaml && git commit -m "Fill in idea.yaml"
make validate    # Check for any unfilled TODOs
```

Then open Claude Code and run `/bootstrap` to generate the full MVP. Claude will:
1. Read your idea.yaml and present a build plan
2. Wait for your approval
3. Generate the full MVP (pages, auth, analytics, API routes)
4. Open a PR for you to review and merge

### 4. Set environment variables

After merging the bootstrap PR:

```bash
cp .env.example .env.local
```

Fill in your keys in `.env.local`:
- `NEXT_PUBLIC_SUPABASE_URL` — Supabase Dashboard → Settings → API → Project URL
- `NEXT_PUBLIC_SUPABASE_ANON_KEY` — Supabase Dashboard → Settings → API → `anon` `public` key
- `NEXT_PUBLIC_POSTHOG_KEY` — PostHog → Project Settings → Project API Key
- `NEXT_PUBLIC_POSTHOG_HOST` — usually `https://us.i.posthog.com` (or `https://eu.i.posthog.com` for EU)
- If you enabled `payment: stripe` in idea.yaml, also add: `STRIPE_SECRET_KEY`, `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY`, `STRIPE_WEBHOOK_SECRET` — Stripe Dashboard → Developers → API keys

> These env vars are for the default stack. After bootstrap, check `.env.example` for your actual required variables.

Add the same env vars in your Vercel project settings for production.

> **Important (default database stack):** Before running the app, you need to create the database tables. Open each SQL file in `supabase/migrations/` (starting with `001_initial.sql`), copy the contents, and run it in your Supabase Dashboard → SQL Editor. The bootstrap PR description has detailed instructions.

### 5. Run locally

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) to verify your app works.

### 6. Deploy to production

```bash
make deploy
```

First deploy will prompt you to link the repo to a Vercel project — follow the CLI prompts. After linking, future deploys work automatically.

### 7. Verify the deployment

Open Claude Code and run `/verify`. This runs E2E tests against the deployed app and auto-fixes any failures.

## Commands

Run `make` to see all available utility commands:

| Command | What it does |
|---------|-------------|
| `make validate` | Check idea.yaml for valid YAML, TODOs, name format, and landing page |
| `make test-e2e` | Run Playwright E2E tests |
| `make deploy` | Deploy to Vercel |
| `make clean` | Remove generated files (lets you re-run bootstrap) |
| `make clean-all` | Remove everything including migrations (full reset) |

AI skills are invoked directly in Claude Code:

| Skill | What it does |
|-------|-------------|
| `/bootstrap` | Generate the full MVP from `idea/idea.yaml` |
| `/change ...` | Make any change: add feature, fix bug, polish UI, fix analytics, add tests |
| `/iterate` | Review metrics and get recommendations for next steps |
| `/retro` | Run a retrospective and file feedback as GitHub issue |

## Workflow

After bootstrap, the typical workflow is:

> **Note:** The commands below assume the default stack. If you've changed your stack, some steps (e.g., deploy target, database setup) will differ — check your stack files in `.claude/stacks/` for details.

1. **Deploy and share** — `make deploy`, send to target users
2. **Collect data** — wait a few days, check your analytics dashboards
3. **Review progress** — `/iterate` to analyze your funnel and get recommendations (this is analysis-only — it does not create a branch or PR)
4. **Act on recommendations** — run the suggested skill:
   - `/change ...` to add a feature, fix a bug, polish UI, fix analytics, or add tests
5. **Review and merge PRs** — each skill opens a PR for you to review
6. **Repeat** — deploy, measure, iterate until you hit `target_value` or `measurement_window` ends
7. **Retrospective** — when the experiment ends, run `/retro` to generate structured feedback and file it on the template repo

## Retrospectives

At the end of an experiment (or when `measurement_window` ends), run a retrospective:

1. Open Claude Code and run **`/retro`**
2. Claude gathers git/PR data, asks you 4 questions, and generates a structured summary
3. Claude files the retro as a GitHub Issue on your template repo

The retro follows the template in `idea/retro-template.md`. Issues are labeled `retro` and accumulate on the template repo, giving the template owner a searchable archive of feedback across all experiments.

**Setup:** Add `template_repo: owner/repo-name` to your `idea/idea.yaml` so Claude knows where to file the issue. If not set, Claude will ask you during the retro.

## Analytics

All experiments share a single analytics project (PostHog by default). Every event includes `project_name` and `project_owner` properties so you can filter dashboards by experiment.

See [`EVENTS.yaml`](./EVENTS.yaml) for the full event dictionary.

## Post-Setup: Branch Protection

After your first PR is merged, protect the `main` branch:

1. Go to **Settings > Branches** in your GitHub repo
2. Click **Add branch ruleset** for `main`
3. Enable:
   - **Require a pull request before merging**
   - **Require status checks to pass** — select `validate`, `build`, `e2e`, and `secret-scan`
4. Save

## Troubleshooting

> **Note:** The troubleshooting steps below assume the default stack. If you've changed your stack, adjust service-specific steps accordingly.

**`make validate` fails with "TODO placeholders"**
→ Open `idea/idea.yaml` and replace every `TODO` with your actual content. See `idea/idea.example.yaml` for a complete example.

**`make validate` fails with "invalid YAML syntax"**
→ Check `idea/idea.yaml` for indentation errors or missing colons. YAML requires consistent spacing (2 spaces, no tabs). Use a YAML validator if unsure.

**`make validate` fails with "PyYAML is not installed"**
→ Run `pip3 install pyyaml` to install the required Python YAML library.

**`make validate` fails with "name must be lowercase"**
→ The `name` field in idea.yaml must start with a letter and use only lowercase letters, numbers, and hyphens (e.g., `my-experiment-1`).

**`make validate` fails with "pages must include landing"**
→ Add an entry with `name: landing` to the `pages` list in idea.yaml. Every experiment needs a landing page.

**`/bootstrap` fails with "Not a git repository"**
→ Make sure you're in a cloned repo. Run `git init` or clone your repo first.

**`/bootstrap` fails with "uncommitted changes"**
→ You need to commit your idea.yaml changes first: `git add idea/idea.yaml && git commit -m "Fill in idea.yaml"`. The branch setup requires a clean working tree before creating a feature branch.

**`/bootstrap` fails with "GitHub CLI is not authenticated"**
→ Run `gh auth login` and follow the prompts to authenticate.

**`/bootstrap` fails with "No origin remote"**
→ Your repo needs a remote. Run: `git remote add origin https://github.com/<your-username>/<your-repo-name>.git`

**Build fails after bootstrap**
→ Check that `.env.local` has all variables from `.env.example`

**App crashes with "relation does not exist"**
→ You haven't created the database tables yet. Open the SQL files in `supabase/migrations/` (starting with `001_initial.sql`), copy the SQL, and run it in your Supabase Dashboard → SQL Editor.

**PostHog events aren't showing up**
→ Check that `NEXT_PUBLIC_POSTHOG_KEY` in `.env.local` matches your PostHog project API key. Check that `NEXT_PUBLIC_POSTHOG_HOST` is `https://us.i.posthog.com` (US) or `https://eu.i.posthog.com` (EU). Open browser DevTools → Network tab and look for requests to `posthog`.

**`make deploy` asks to link a project**
→ This is normal on first deploy. Follow the Vercel CLI prompts to link your repo to a Vercel project. After linking, future deploys will work automatically.

**Vercel deploy fails with missing env vars**
→ Add your environment variables in the Vercel dashboard: Project → Settings → Environment Variables. Add the same keys from `.env.example`.

**Bootstrap partially failed (e.g., npm install worked but shadcn init didn't)**
→ Run `make clean` to remove generated files, then try `/bootstrap` again.

**Branch already exists**
→ The branch setup handles this automatically by appending `-2`, `-3`, etc.

**A skill failed partway through (e.g., build error, network issue)**
→ You have two options:
  1. **Resume:** switch to the branch (`git checkout <branch-name>`) and run `claude` to pick up where it left off.
  2. **Start fresh:** delete the branch (`git branch -D <branch-name>`) and re-run the skill.

**Two experiments won't run locally at the same time**
→ Run the second one on a different port: `npm run dev -- -p 3001`

## Project Structure

```
idea/idea.yaml           # Your experiment definition (edit this first)
idea/idea.example.yaml   # Worked example for reference
idea/retro-template.md   # Retrospective template (used at end of experiment)
CLAUDE.md                # Rules for Claude Code (don't edit unless you know what you're doing)
EVENTS.yaml              # Analytics event dictionary
.claude/commands/        # Claude Code skills (bootstrap, change, iterate, retro)
.claude/patterns/        # Shared patterns referenced by skills (verification procedure, etc.)
.claude/stacks/          # Stack implementation files (one per technology — framework, database, auth, testing, etc.)
.github/                 # PR template and CI workflow
.gitleaks.toml           # Secret scanning configuration
Makefile                 # Utility command shortcuts — run `make` to see all
.nvmrc                   # Node.js version (20)
supabase/migrations/     # Database migrations (default database stack) (generated by bootstrap/change, run in Supabase Dashboard)
src/                     # App code (generated by make bootstrap)
```

> **Tip:** `idea.example.yaml` shows a full 7-page app with payments. For a simpler starting point, you only need a `landing` page and one feature — everything else is optional.

## Extending This Template

### Adding a new stack option

To support a new technology (e.g., Firebase instead of Supabase):

1. Create a stack file at `.claude/stacks/<category>/<value>.md` (e.g., `.claude/stacks/database/firebase.md`)
2. Use `.claude/stacks/TEMPLATE.md` as a starting point — it documents the required and optional sections
3. Set the corresponding `stack.<category>` value in idea.yaml to match the filename
4. Skills will automatically read your new stack file — no changes to skill files needed

> **Note:** Swapping a framework or database stack may also require updates to `CLAUDE.md` (rules 9-10), the `Makefile` (`clean` and `deploy` targets), `.gitignore`, and `.github/workflows/ci.yml` (build env vars). Review each for stack-specific references.

> **Important:** Stack files may depend on other stacks. Each file declares its assumptions in an `> Assumes:` line at the top (e.g., `database/supabase.md` assumes `framework/nextjs`). When swapping a stack, check the `> Assumes:` lines in related files to see what else needs updating.

### Adding a new skill

Most code-writing changes should go through the unified `change` skill rather than creating new skills. Only add a new skill if it has a fundamentally different workflow (e.g., analysis-only like `iterate`).

1. Create a command file at `.claude/commands/<skill-name>.md` with the skill's instructions
2. Add YAML frontmatter at the top of the file with required keys: `type`, `reads`, `stack_categories`, `requires_approval`, `references`, `branch_prefix`, `modifies_specs`. See existing skill files for examples.
3. For code-writing skills: add `.claude/patterns/branch.md` and `.claude/patterns/verify.md` to the `references` list, and add a Step 0 that invokes the branch setup procedure
4. Update the skill tables in this README
5. Update the skill list in CLAUDE.md Rule 0 (the `/bootstrap, /change, /iterate, /retro` enumeration)
