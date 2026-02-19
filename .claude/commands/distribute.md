---
description: "Generate Google Ads campaign config from idea.yaml. Requires a deployed MVP."
type: code-writing
reads:
  - idea/idea.yaml
  - EVENTS.yaml
  - idea/ads.yaml
stack_categories: [analytics, hosting]
requires_approval: true
references:
  - .claude/patterns/verify.md
  - .claude/patterns/branch.md
branch_prefix: chore
modifies_specs: true
---
Generate a Google Ads campaign configuration from idea.yaml and implement distribution tracking.

This skill generates `idea/ads.yaml` with keywords, ad copy, budgets, and thresholds, then adds UTM/gclid capture and a feedback widget to the deployed app. Phase 1 is manual — the human creates the campaign in Google Ads UI using the generated config.

## Step 0: Branch setup

Follow `.claude/patterns/branch.md`. Branch: `chore/distribute`.

## Step 1: Validate preconditions

1. Verify `idea/idea.yaml` exists and is complete. If not, stop: "No experiment found. Create `idea/idea.yaml` from the template first, then run `/bootstrap`."
2. Verify `EVENTS.yaml` exists. If not, stop: "EVENTS.yaml not found. This file defines all analytics events and is required."
3. Verify `EVENTS.yaml` contains a `custom_events` key that is a list (empty list `[]` is valid). If not, stop: "EVENTS.yaml is malformed — the `custom_events` key is missing or not a list. Run `make validate` to diagnose, or restore the file from the template."
4. Verify `package.json` exists. If not, stop: "No app found. Run `/bootstrap` first to create the app, deploy it, then run `/distribute`."
5. Verify the app is deployed: check `landing_url` in existing `idea/ads.yaml`, or ask the user for the deployed URL.
6. Verify `stack.analytics` is present in idea.yaml. If not, stop: "Analytics is required for distribution tracking. Add `analytics: posthog` (or another provider) to idea.yaml `stack` and run `/bootstrap` first."
7. Verify the analytics stack is configured: check for a `NEXT_PUBLIC_` analytics key in `.env.example` (the specific key name depends on the analytics stack file — read it to find the client env var). If not found, stop: "Analytics is not configured. Verify `.env.example` contains a `NEXT_PUBLIC_` analytics key, or run `/bootstrap` first to scaffold the app with analytics."
8. If `idea/ads.yaml` already exists, ask: "An ads config already exists. Generate a new version (v2)?"

## Step 2: Research keywords

Read `idea/idea.yaml`: `problem`, `solution`, `target_user`, `title`, `features`.

Generate keyword research analysis:

```
## Keyword Research

**Target user intent:** [what the target_user would search for when experiencing the problem]
**Competitor landscape:** [known alternatives mentioned in problem statement]
**Search volume estimate:** [high/medium/low for this niche]

**Recommended keywords:**
- Exact match: [5-8 keywords] — highest intent, most specific
- Phrase match: [3-5 keywords] — moderate intent
- Broad match: [2-3 keywords] — discovery, wider net
- Negative: [5+ keywords] — exclude irrelevant traffic (enterprise, existing tools, etc.)
```

### Keyword rules
- Minimum 3 exact, 2 phrase, 1 broad, 2 negative
- Exact match keywords target users actively looking for this type of solution
- Phrase match captures related searches with moderate intent
- Broad match casts a wider net for discovery
- Negative keywords exclude enterprise, existing well-known tools, and irrelevant traffic

## Step 3: Generate ad copy

Derive from idea.yaml `title`, `solution`, and `primary_metric`.

### Google RSA constraints
- Headlines: 3-30 characters each
- Descriptions: up to 90 characters each
- Minimum 2 ad variations
- Each ad: 5+ headlines, 2 descriptions

### Copy principles
- Headline = outcome for target_user (what they get)
- Description = proof + CTA (why believe + what to do next)
- Include the landing URL with UTM parameters: `?utm_source=google&utm_medium=cpc&utm_campaign={campaign_name}`

## Step 4: Generate thresholds

Use first-principles reasoning specific to this MVP:

1. Parse `budget.total_budget_cents` and estimate CPC for the keyword category
2. Estimate funnel conversion rates:
   - Landing → signup: 5-15% for cold paid traffic
   - Signup → activate: 20-40% depending on activation friction
3. Calculate expected volume at each stage
4. Define go/no-go signals based on idea.yaml `target_value` and `measurement_window`

Show the reasoning chain, not just the numbers:

```
## Threshold Reasoning

Budget: $100 over 7 days
Estimated CPC for [keyword category]: ~$X.XX
Expected clicks: [budget / CPC]
Expected signups: [clicks * landing-to-signup rate] ([rate]% — [reasoning])
Expected activations: [signups * signup-to-activate rate] ([rate]% — [reasoning])

Go signal: [N]+ activations from paid traffic in [measurement_window]
No-go signal: 0 activations after $[half-budget] spend, or <1% CTR after 500 impressions
```

### Schema rules for ads.yaml
- `campaign_name`: auto-generated as `{idea.name}-search-v{N}` (N increments if re-running)
- `budget.total_budget_cents`: defaults to 10000 ($100), max 50000 ($500) without explicit override
- `budget.duration_days`: defaults to idea.yaml `measurement_window` parsed to days
- `guardrails.max_cpc_cents`: auto-calculated as `total_budget / expected_clicks * 1.5` (50% buffer)
- `thresholds`: AI-generated from idea.yaml context using first-principles reasoning

## Step 5: Generate ads.yaml

Write the complete `idea/ads.yaml` file. See `idea/ads.example.yaml` for the full schema and format.

Present the full config for review.

## Step 6: STOP for approval

> Review the ads config above. Reply **approve** to proceed, or tell me what to change.
> After approval, I'll set up conversion tracking and open a PR.

**Do not proceed until the user approves.**

## Step 7: Implement (after approval)

### 7a: UTM capture on landing page

- Read the analytics stack file (`.claude/stacks/analytics/<value>.md`) to understand the tracking API
- Ensure `visit_landing` event captures `utm_source`, `utm_medium`, `utm_campaign` from URL params
- EVENTS.yaml has these as optional properties on `visit_landing` — the landing page must parse them from `window.location.search` and pass them to the tracking call
- Update the landing page to parse URL params and include them in the visit tracking call

### 7b: Add gclid capture

- `gclid` (Google Click ID) is an optional property on `visit_landing` in EVENTS.yaml
- Capture from URL params on landing page load alongside UTM params
- This enables Google Ads offline conversion import matching

### 7c: Feedback widget (post-activation)

Add `feedback_submitted` to EVENTS.yaml `custom_events`:

```yaml
custom_events:
  - event: feedback_submitted
    trigger: User submits post-activation feedback widget
    properties:
      source:
        type: string
        required: false
        description: "How the user found the product (e.g., google, friend, social)"
      feedback:
        type: string
        required: false
        description: Free-text feedback from the user
      activation_action:
        type: string
        required: true
        description: What activation action preceded this (from idea.yaml primary_metric)
```

Add a `FeedbackWidget` component at `src/components/feedback-widget.tsx`:

- Uses shadcn `Dialog`, `Button`, `Label`, `Textarea`, and `Select` components (read the UI stack file for import conventions)
- Appears after the user completes the activation action (triggered via prop callback)
- Stores "shown" flag in localStorage to show only once per user
- Fires `feedback_submitted` custom event via `track()` from the analytics library (see analytics stack file for the import path and `track()` usage)
- Fields: "How did you find us?" (select: Google Search, Social Media, Friend/Referral, Other), "Any feedback?" (textarea)
- Non-blocking: user can dismiss without submitting

### 7d: Demo mode recommendation

If the app requires signup/auth before the user can see value, add a note to the PR body recommending a demo/preview mode. This is a recommendation only — implementing the demo is a separate `/change` task.

### 7e: Analytics → Google Ads conversion sync setup instructions

Add a `## Distribution Setup` section to the PR body with step-by-step instructions for:

1. Create Google Ads MCC (Manager Account) — see `docs/google-ads-setup.md` for details
2. Create a child account for this MVP under the MCC
3. Set up offline conversion import in Google Ads
4. Configure the analytics provider's Google Ads destination (see analytics stack file for provider-specific instructions)
5. Map the `activate` event -> Google Ads conversion action
6. Verify with a test conversion

Also include analytics dashboard setup instructions (read the analytics stack file's Dashboard Navigation section for provider-specific terminology):

### Ads Dashboard Setup

1. Go to the analytics dashboard -> New dashboard -> "Ads Performance: {project_name}"
2. Add these insights:
   - **Traffic by Source**: Trend chart, event `visit_landing`, breakdown by `utm_source`, last 7 days
   - **Paid Funnel**: Funnel chart, events `visit_landing` (filtered: utm_source = google) -> `signup_complete` -> `activate`, last 7 days
   - **Cost per Activation**: Number (manual calculation) — Total Google Ads spend / activate count where utm_source = google
   - **Feedback Summary**: Trend chart, event `feedback_submitted`, breakdown by `source` property, last 7 days

## Step 8: Verify and open PR

Run the verification procedure per `.claude/patterns/verify.md`.

Commit, push, and open a PR with:
- **Summary**: what was generated and why
- **Distribution Setup**: step-by-step Google Ads + analytics setup instructions
- **What Changed**: files modified (landing page UTM capture, EVENTS.yaml, ads.yaml, FeedbackWidget)
- The full `ads.yaml` content in the PR body for easy review

## Do NOT

- Launch any ads automatically — Phase 1 is manual campaign creation from the generated config
- Modify idea.yaml — this skill reads it but does not change it
- Add new packages — the feedback widget uses existing shadcn components and the analytics library
- Skip the approval step — the operator must review keywords, ad copy, and budget before proceeding
- Hardcode analytics import paths or provider names — always read the analytics stack file for the correct imports
