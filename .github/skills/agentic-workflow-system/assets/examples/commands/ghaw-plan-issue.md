---
description: Create an implementation plan for a GitHub issue
argument-hint: <issue-number>
---

# Plan Issue

**Input**: $ARGUMENTS (issue number)

## Step 1: Load Issue

Use gh CLI to read the full issue:

    gh issue view $ARGUMENTS --json number,title,body,labels,comments

Extract: title, description, acceptance criteria, existing labels.

## Step 2: Explore Repo

Use file-read tools to understand:
- Project structure and language / framework
- Components affected by the issue description
- Existing patterns, conventions, test structure

No hardcoded paths — explore adaptively.

## Step 3: NO-ACTION Check

Before drafting a plan, determine if implementation is actually needed.

Post `<!-- NO-ACTION -->` **only** when ALL of the following are true:
- The issue is already fully resolved (fix already in codebase or file already gone)
- OR the issue is invalid / a duplicate of a closed issue
- OR zero code changes are required to satisfy the acceptance criteria

Do NOT use NO-ACTION for issues that are merely simple or small — those still need a plan.

If NO-ACTION applies:

    gh issue comment $ARGUMENTS --body "<!-- NO-ACTION -->
    This issue requires no implementation. Reason: {brief justification}"

    gh issue close $ARGUMENTS --reason "completed" --comment "Closing: no implementation needed. {summary}"

Then stop — do not proceed to Step 4 or 5.

## Step 3b: CANNOT-PLAN Check

If the issue description is too unclear to produce a concrete plan (missing acceptance criteria,
contradictory requirements, or unresolved ambiguities that block implementation), post:

    gh issue comment $ARGUMENTS --body "<!-- CANNOT-PLAN -->
    Cannot create implementation plan. Reason: {specific explanation of what is unclear or missing}"

Then stop — do not proceed to Step 4 or 5. The verify step will set the issue to `blocked`
so a human can clarify before re-grooming.

## Step 4: Draft Implementation Plan

Structure the plan as:

    ## Implementation Plan

    ### Approach
    {1-2 sentences on chosen approach}

    ### Affected Components
    - `{file or module}` — {reason}

    ### Steps
    1. {concrete step}
    2. {concrete step}

    ### Risks / Unknowns
    - {risk or open question}

    ### Estimated Complexity
    {high / medium / low} — {brief justification}

## Step 5: Post Plan + Set Labels

Post plan as issue comment with marker:

    gh issue comment $ARGUMENTS --body "<!-- PLAN -->
    {plan from Step 3}"

Set all four labels:

    gh issue edit $ARGUMENTS \
      --add-label "severity/{val}" \
      --add-label "priority/{val}" \
      --add-label "size/{val}" \
      --add-label "confidence/{val}"

Label value mappings:
- severity:   critical, high, medium, low
- priority:   high, medium, low
- size:       xl, l, m, s, xs
- confidence: high, medium, low
