---
type: analysis-only
reads:
  - idea/idea.yaml
  - EVENTS.yaml
stack_categories: [analytics]
requires_approval: false
references: []
branch_prefix: chore
modifies_specs: false
---
Review the experiment's progress and recommend what to do next.

This skill does NOT write code. It helps you decide what action to take, then points you to the right skill to execute it.

## Step 1: Read the experiment definition

- Read `idea/idea.yaml` — understand the hypothesis:
  - What are we building? (`title`, `solution`)
  - For whom? (`target_user`)
  - What does success look like? (`primary_metric`, `target_value`)
  - How long do we have? (`measurement_window`)
  - What features exist? (`features`)
  - What pages exist? (`pages`)
- Read `EVENTS.yaml` — understand what's being tracked (this is the canonical list of all events)

## Step 2: Ask the user for current data

First, tell the user how to get the numbers. See the analytics stack file's "Dashboard navigation" section for provider-specific instructions on how to pull funnel numbers. If no stack file exists, give general guidance.

> **How to get your funnel numbers:**
> Follow the dashboard instructions in your analytics stack file (`.claude/stacks/analytics/<value>.md`). Create a funnel using the events from EVENTS.yaml `standard_funnel` in the order listed, then append `payment_funnel` events if `stack.payment` is present. Filter by `project_name` equals your idea.yaml `name` value. Present the actual event names to the user so they can find them in their dashboard.
>
> If you haven't set up analytics yet, rough estimates are fine too (e.g., "about 200 landing page visits, maybe 20 signups").

Then ask the user to provide whatever they have. Not all of these will be available — use what you get:

1. **Funnel numbers** — for each event in EVENTS.yaml `standard_funnel` (and `payment_funnel` if `stack.payment` is present), how many users? Present the actual event names from EVENTS.yaml so the user knows what to look for in their dashboard.

2. **Timeline** — how far into the `measurement_window` are we?

3. **Qualitative feedback** — any user quotes, complaints, feature requests, support messages?

4. **Observations** — anything the team has noticed (e.g., "users sign up but never create an invoice", "landing page bounce rate is high")

## Step 3: Diagnose the funnel

Analyze the data to find where the funnel breaks. Present a funnel visualization:

```
## Funnel Analysis

| Stage | Count | Conversion | Diagnosis |
|-------|-------|-----------|-----------|
| [1st standard_funnel event] | [count] | — | [diagnosis] |
| [2nd standard_funnel event] | [count] | [%] | ⚠️/✅/❌ [specific diagnosis] |
| ... (one row per EVENTS.yaml standard_funnel event) | ... | ... | ... |
| [payment_funnel events if stack.payment present] | ... | ... | ... |
| [retain_return] | [count] | — | [retention diagnosis] |

If `stack.payment` is absent from idea.yaml, omit the `pay_start` and `pay_success` rows from the funnel table.

> Note: `retain_return` is a retention metric, not a conversion step. Show it below the funnel or as a separate row — it does not have a meaningful conversion rate relative to the row above it.

## Biggest Bottleneck
Activation (signup → first value): 22% conversion
Users sign up but don't [complete the core action].
```

Focus on the **biggest drop-off** in the funnel. That's where effort has the highest leverage.

## Step 4: Recommend actions

Based on the diagnosis, recommend 1-3 specific actions. For each:
- **What**: concrete description of the change
- **Why**: how it addresses the bottleneck
- **Skill to use**: which make command to run
- **Expected impact**: what metric should improve

Common patterns:

| Bottleneck | Typical Actions |
|-----------|----------------|
| Low visit → signup | `make change DESC="improve landing page copy and CTA"` |
| Low signup_start → complete | `make change DESC="fix signup errors"` or `make change DESC="reduce signup form friction"` |
| Low activation | `make change DESC="simplify [first-value action]"` |
| Low pay conversion | `make change DESC="improve pricing/payment UX"` |
| Low retention | `make change DESC="add [engagement hook]"` |
| Everything low | Reconsider `target_user` or `distribution` — may be a positioning problem, not a product problem |

Present recommendations in priority order (highest impact first).

## Step 5: Update the experiment plan (if needed)

If the diagnosis reveals a need to change direction:

### Minor pivot (keep same target user, adjust features)
- Propose the changes to the user and list the specific edits to idea.yaml
- The user should edit idea.yaml manually, then run `make change DESC="..."` or `make bootstrap` to implement

### Major pivot (change target user, problem, or solution)
- Present the case: "The data suggests [current approach] isn't working because [reason]. Consider targeting [new user] or solving [different problem]."
- Do NOT update idea.yaml for major pivots — the user should think about this and manually edit idea.yaml
- Remind them: "After updating idea.yaml, run `make bootstrap` on a fresh repo to start a new experiment, or `make change DESC=\"...\"` to iteratively shift the existing one."

### On track (metrics are progressing toward target_value)
- Say so clearly: "You're on track. [X] of [target_value] achieved with [Y days] remaining."
- Recommend: keep going, focus on distribution, or run `make change DESC="improve conversion"` to improve conversion

## Step 6: Summarize next steps

End with a clear, numbered action list:

```
## Recommended Next Steps

1. Run `make change DESC="sharpen landing page headline to address [specific user pain]"`
2. Run `make change DESC="add onboarding checklist after signup"`
3. Post in [distribution channel from idea.yaml] — drive more top-of-funnel traffic

Your measurement window ends in [X days]. Focus on the activation bottleneck first.
```

### Retro reminder
If the experiment is near the end of its `measurement_window` or the user is considering stopping:
> Your measurement window ends in [X days]. When you're ready to wrap up, run **`make retro`** to generate a structured retrospective and file it as feedback on the template repo.

## Do NOT
- Write code or modify source files — this skill is analysis only
- Recommend more than 3 actions — focus is more valuable than breadth
- Recommend actions outside the defined commands (bootstrap, change, iterate, retro)
- Be vague — every recommendation must be specific enough to act on
- Ignore the data — don't recommend features if the funnel shows a landing page problem
- Recommend adding features when the real problem is distribution or positioning
