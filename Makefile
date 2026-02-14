# Makefile — Shortcuts for running experiment workflows
#
# Run `make` or `make help` to see available commands.

.DEFAULT_GOAL := help

.PHONY: help validate bootstrap change iterate retro test-e2e dev test deploy clean clean-all

help: ## Show this help message
	@echo "Usage: make <command>"
	@echo ""
	@echo "Commands:"
	@grep -E '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-16s %s\n", $$1, $$2}'

validate: ## Check idea.yaml for valid YAML, TODOs, name format, and landing page
	@echo "Validating idea/idea.yaml..."
	@if [ ! -f idea/idea.yaml ]; then \
		echo "Error: idea/idea.yaml not found"; \
		exit 1; \
	fi
	@command -v python3 >/dev/null 2>&1 || { \
		echo "Error: Python3 is required for validation but was not found."; \
		echo "Fix: install Python3 from https://python.org (or: brew install python3)"; \
		exit 1; \
	}
	@python3 -c "import yaml" 2>/dev/null || { \
		echo "Error: PyYAML is not installed (needed for YAML validation)."; \
		echo "Fix: run 'pip3 install pyyaml' (if that fails: 'pip3 install --user pyyaml' or 'brew install python-pyyaml')"; \
		exit 1; \
	}
	@python3 -c "import yaml; yaml.safe_load(open('idea/idea.yaml'))" 2>/dev/null || { \
		echo "Error: idea/idea.yaml has invalid YAML syntax."; \
		echo "Check for indentation errors or missing colons."; \
		exit 1; \
	}
	@if grep -q 'TODO' idea/idea.yaml; then \
		echo ""; \
		echo "Found TODO placeholders that need to be filled in:"; \
		grep -n 'TODO' idea/idea.yaml; \
		echo ""; \
		echo "Replace every TODO before running make bootstrap."; \
		exit 1; \
	fi
	@python3 -c "\
	import yaml, re, sys; \
	data = yaml.safe_load(open('idea/idea.yaml')); \
	name = data.get('name', ''); \
	if not re.match(r'^[a-z][a-z0-9-]*$$', name): \
	    print(f'Error: name \"{name}\" must be lowercase, start with a letter, and use only a-z, 0-9, hyphens.'); \
	    print('Example: my-experiment-1'); \
	    sys.exit(1); \
	"
	@python3 -c "\
	import yaml, sys; \
	data = yaml.safe_load(open('idea/idea.yaml')); \
	pages = data.get('pages', []); \
	if not any(p.get('name') == 'landing' for p in pages): \
	    print('Error: pages must include an entry with name: landing'); \
	    print('Add a landing page to the pages list in idea.yaml.'); \
	    sys.exit(1); \
	"
	@python3 -c "\
	import yaml, sys; \
	data = yaml.safe_load(open('idea/idea.yaml')); \
	required = ['name','title','owner','problem','solution','target_user','distribution','pages','features','primary_metric','target_value','measurement_window','stack']; \
	missing = [f for f in required if not data.get(f)]; \
	if missing: \
	    print('Error: these required fields are missing or empty: ' + ', '.join(missing)); \
	    sys.exit(1); \
	"
	@python3 -c "\
	import yaml, os; \
	data = yaml.safe_load(open('idea/idea.yaml')); \
	stack = data.get('stack', {}); \
	warnings = [f'stack.{k}: {v} — no file at .claude/stacks/{k}/{v}.md' for k, v in stack.items() if not os.path.isfile(f'.claude/stacks/{k}/{v}.md')]; \
	[print(f'  Warning: {w}') for w in warnings]; \
	print('  Claude will use general knowledge for these. To fix: create the stack file or change the value.') if warnings else None; \
	"
	@if [ -f EVENTS.yaml ]; then \
		python3 -c "\
		import yaml, sys; \
		data = yaml.safe_load(open('EVENTS.yaml')); \
		errors = []; \
		if not data: errors.append('EVENTS.yaml is empty'); \
		else: \
		    for key in ['standard_funnel', 'custom_events']: \
		        if key not in data: errors.append(f'missing required key \"{key}\"'); \
		    for section in ['standard_funnel', 'payment_funnel']: \
		        if section in data and data[section]: \
		            for i, ev in enumerate(data[section]): \
		                if 'event' not in ev: errors.append(f'{section}[{i}] missing \"event\"'); \
		                if 'trigger' not in ev: errors.append(f'{section}[{i}] missing \"trigger\"'); \
		if errors: \
		    print('EVENTS.yaml issues:'); \
		    [print(f'  - {e}') for e in errors]; \
		    sys.exit(1); \
		" || exit 1; \
		echo "EVENTS.yaml looks good — valid structure."; \
	fi
	@python3 scripts/validate-semantics.py
	@echo "Validation passed — idea.yaml and EVENTS.yaml look good."
	@if [ -f package.json ]; then \
		echo "Note: project is already bootstrapped. Use make change DESC=\"...\" to make changes."; \
	fi

bootstrap: ## Scaffold the full MVP from idea.yaml
	./scripts/run-skill.sh bootstrap feat

change: ## Make a change (usage: make change DESC="fix the signup button")
ifndef DESC
	$(error DESC is required. Usage: make change DESC="fix the signup button")
endif
	./scripts/run-skill.sh change change "$(DESC)"

iterate: ## Review metrics and get recommendations for next steps
	./scripts/run-skill.sh iterate chore

retro: ## Run a retrospective and file feedback as GitHub issue
	./scripts/run-skill.sh retro chore

test-e2e: ## Run Playwright E2E tests (requires SUPABASE_SERVICE_ROLE_KEY in .env.local)
	@if [ -f playwright.config.ts ]; then \
		npx playwright test; \
	else \
		echo "No playwright.config.ts found — run 'make change DESC=\"add E2E smoke tests\"' first"; \
	fi

dev: ## Start the local development server
	npm run dev

test: ## Run tests (skips if no test script)
	@if [ -f package.json ] && node -e "process.exit(require('./package.json').scripts?.test ? 0 : 1)" 2>/dev/null; then \
		npm test; \
	else \
		echo "No test script found — skipping"; \
	fi

# Default: Vercel. Update this target if you change stack.hosting.
deploy: ## Deploy to Vercel (first run will prompt to link project)
	@echo "Deploying to Vercel..."
	npx vercel deploy --prod

# Default: Next.js + shadcn artifacts. Update if you change stack.framework or stack.ui.
clean: ## Remove generated files (lets you re-run bootstrap)
	rm -rf node_modules .next out                          # framework/nextjs
	rm -f .nvmrc package.json package-lock.json tsconfig.json next.config.ts next-env.d.ts postcss.config.mjs  # framework/nextjs
	rm -f components.json tailwind.config.ts .eslintrc.json eslint.config.mjs  # ui/shadcn
	rm -rf src                                             # all generated app code
	rm -f .env.example                                     # all stacks
	rm -rf e2e playwright.config.ts test-results playwright-report blob-report  # testing/playwright
	@echo "Cleaned. You can now run 'make bootstrap' again."
	@echo "Note: idea/idea.yaml, EVENTS.yaml, and supabase/ were NOT removed. Use 'make clean-all' for a full reset."

clean-all: ## Remove everything including migrations (full reset)
	@echo "This will delete ALL generated files including database migrations."
	@read -p "Are you sure? [y/N] " confirm && [ "$$confirm" = "y" ] || { echo "Cancelled."; exit 1; }
	$(MAKE) clean
	rm -rf supabase
	@echo "Full reset complete. You can now run 'make bootstrap' again."
