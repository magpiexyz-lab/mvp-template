# Makefile — Shortcuts for running experiment workflows
#
# Run `make` or `make help` to see available commands.

.DEFAULT_GOAL := help

.PHONY: help validate distribute test-e2e deploy clean clean-all

help: ## Show this help message
	@echo "Usage: make <command>"
	@echo ""
	@echo "Commands:"
	@grep -E '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-16s %s\n", $$1, $$2}'
	@echo ""
	@echo "AI skills (run in Claude Code):"
	@echo "  /bootstrap       Scaffold the full MVP from idea.yaml"
	@echo "  /change ...      Make a change (e.g., /change fix the signup button)"
	@echo "  /iterate         Review metrics and get recommendations"
	@echo "  /retro           Run a retrospective and file feedback"
	@echo "  /distribute      Generate Google Ads config from idea.yaml"
	@echo "  /verify          Run E2E tests and fix failures"

validate: ## Check idea.yaml for valid YAML, TODOs, name format, and landing page
	@echo "Validating idea/idea.yaml..."
	@if [ ! -f idea/idea.yaml ]; then \
		echo "Error: idea/idea.yaml not found. Copy the example: cp idea/idea.example.yaml idea/idea.yaml"; \
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
	@# validate-idea.py checks: name format, landing page, required fields, stack files, testing warning, assumes
	@STACK_WARN=0; \
	python3 scripts/validate-idea.py || STACK_WARN=$$?; \
	if [ "$$STACK_WARN" -ne 0 ] && [ "$$STACK_WARN" -ne 2 ]; then exit 1; fi; \
	if [ -f EVENTS.yaml ]; then \
		python3 scripts/validate-events.py || exit 1; \
		echo "EVENTS.yaml looks good — valid structure."; \
	else \
		echo "Warning: EVENTS.yaml not found — /bootstrap will fail. Ensure EVENTS.yaml exists in the repo root."; \
	fi; \
	python3 scripts/validate-semantics.py || exit 1; \
	if [ "$$STACK_WARN" -eq 2 ]; then \
		echo "Validation passed with warnings — review above."; \
	else \
		echo "Validation passed — idea.yaml and EVENTS.yaml look good."; \
	fi; \
	if [ -f package.json ]; then \
		echo "Note: project is already bootstrapped. Open Claude Code and run /change to make changes."; \
	fi

distribute: ## Validate idea/ads.yaml (valid YAML, schema, budget limits)
	@if [ ! -f idea/ads.yaml ]; then echo "No idea/ads.yaml found. Run /distribute in Claude Code to generate it."; exit 0; fi; \
	python3 -c "import yaml; yaml.safe_load(open('idea/ads.yaml'))" 2>/dev/null || { echo "Error: idea/ads.yaml has invalid YAML syntax."; exit 1; }; \
	python3 -c "\
	import yaml, sys; \
	data = yaml.safe_load(open('idea/ads.yaml')); \
	req = ['campaign_name','project_name','landing_url','keywords','ads','budget','targeting','conversions','guardrails','thresholds']; \
	errors = [f'missing required key: {k}' for k in req if k not in data]; \
	kw = data.get('keywords', {}); \
	kw_ok = isinstance(kw, dict); \
	errors += ['keywords.exact needs >= 3'] if kw_ok and len(kw.get('exact', []) or []) < 3 else []; \
	errors += ['keywords.phrase needs >= 2'] if kw_ok and len(kw.get('phrase', []) or []) < 2 else []; \
	errors += ['keywords.broad needs >= 1'] if kw_ok and len(kw.get('broad', []) or []) < 1 else []; \
	errors += ['keywords.negative needs >= 2'] if kw_ok and len(kw.get('negative', []) or []) < 2 else []; \
	al = data.get('ads', []); \
	al_ok = isinstance(al, list); \
	errors += ['ads needs >= 2 variations'] if al_ok and len(al) < 2 else []; \
	errors += [f'ads[{i}] needs >= 5 headlines' for i, a in enumerate(al or []) if isinstance(a, dict) and len(a.get('headlines', []) or []) < 5]; \
	errors += [f'ads[{i}] needs >= 2 descriptions' for i, a in enumerate(al or []) if isinstance(a, dict) and len(a.get('descriptions', []) or []) < 2]; \
	b = data.get('budget', {}); \
	t = b.get('total_budget_cents', 0) if isinstance(b, dict) else 0; \
	errors += [f'budget.total_budget_cents ({t}) exceeds max 50000'] if t and t > 50000 else []; \
	g = data.get('guardrails', {}); \
	g_ok = isinstance(g, dict); \
	errors += ['guardrails.max_cpc_cents missing'] if g_ok and g.get('max_cpc_cents') is None else []; \
	errors += [f'guardrails.max_cpc_cents must be int > 0 (got {g.get(\"max_cpc_cents\")!r})'] if g_ok and g.get('max_cpc_cents') is not None and (not isinstance(g.get('max_cpc_cents'), int) or g.get('max_cpc_cents') <= 0) else []; \
	th = data.get('thresholds', {}); \
	th_ok = isinstance(th, dict); \
	errors += ['thresholds.expected_activations missing'] if th_ok and th.get('expected_activations') is None else []; \
	errors += [f'thresholds.expected_activations must be int >= 0 (got {th.get(\"expected_activations\")!r})'] if th_ok and th.get('expected_activations') is not None and (not isinstance(th.get('expected_activations'), int) or th.get('expected_activations') < 0) else []; \
	errors += ['thresholds.go_signal must be a non-empty string'] if th_ok and (not th.get('go_signal') or not isinstance(th.get('go_signal'), str)) else []; \
	errors += ['thresholds.no_go_signal must be a non-empty string'] if th_ok and (not th.get('no_go_signal') or not isinstance(th.get('no_go_signal'), str)) else []; \
	[print(f'  - {e}') for e in errors] if errors else None; \
	sys.exit(1) if errors else print('idea/ads.yaml looks good — valid schema.'); \
	"

test-e2e: ## Run Playwright E2E tests
	@if [ -f playwright.config.ts ]; then \
		npx playwright test; \
	else \
		echo "No playwright.config.ts found — add 'testing: playwright' to idea.yaml stack and re-run /bootstrap, or run '/change add E2E smoke tests'"; \
	fi

# Default: Vercel. Update this target if you change stack.hosting.
deploy: ## Deploy to Vercel (first run will prompt to link project)
	@if [ ! -f package.json ]; then \
		echo "Error: No package.json found. Run /bootstrap first."; \
		exit 1; \
	fi
	@if [ -f idea/idea.yaml ]; then \
		HOSTING=$$(python3 -c "import yaml; d=yaml.safe_load(open('idea/idea.yaml')); print(d.get('stack',{}).get('hosting',''))" 2>/dev/null); \
		if [ -n "$$HOSTING" ] && [ "$$HOSTING" != "vercel" ]; then \
			echo "Warning: stack.hosting is '$$HOSTING', but this Makefile only has a Vercel deploy command."; \
			echo "To deploy: replace 'npx vercel deploy --prod' on the last line of the deploy target with your hosting provider's CLI command (e.g., 'npx netlify deploy --prod', 'fly deploy')."; \
			echo "Or deploy directly from your terminal — this Makefile target is optional."; \
			exit 1; \
		fi; \
	fi
	@echo "Deploying to Vercel..."
	npx vercel deploy --prod

# Default: Next.js + shadcn artifacts. Update if you change stack.framework or stack.ui.
clean: ## Remove generated files (lets you re-run bootstrap)
	rm -rf node_modules .next out                          # framework/nextjs
	rm -f .nvmrc package.json package-lock.json tsconfig.json next.config.ts next-env.d.ts  # framework/nextjs
	rm -f components.json tailwind.config.ts .eslintrc.json eslint.config.mjs postcss.config.mjs  # ui/shadcn
	rm -rf src                                             # all generated app code
	rm -f .env.example                                     # all stacks
	rm -rf e2e playwright.config.ts test-results playwright-report blob-report  # testing/playwright
	@echo "Cleaned. You can now open Claude Code and run /bootstrap again."
	@echo "Note: idea/idea.yaml, EVENTS.yaml, and supabase/ were NOT removed. Use 'make clean-all' for a full reset."

clean-all: ## Remove everything including migrations (full reset)
	@echo "This will delete ALL generated files including database migrations."
	@read -p "Are you sure? [y/N] " confirm && [ "$$confirm" = "y" ] || { echo "Cancelled."; exit 1; }
	$(MAKE) clean
	rm -rf supabase
	@echo "Full reset complete. You can now open Claude Code and run /bootstrap again."
