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

## Step 3: Draft Implementation Plan

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
    {xs / s / m / l / xl} — {brief justification}

## Step 4: Post Plan + Set Labels

Post plan as issue comment with marker:

    gh issue comment $ARGUMENTS --body "<!-- PLAN -->
    {plan from Step 3}"

Set all four labels (Fibonacci scale):

    gh issue edit $ARGUMENTS \
      --add-label "severity:{val}" \
      --add-label "priority:{val}" \
      --add-label "complexity:{val}" \
      --add-label "confidence:{val}"

Label value mappings:
- severity / priority: critical=13, high=8, medium=5, low=3, trivial=1
- complexity:          xl=13, l=8, m=5, s=3, xs=1
- confidence:          certain=13, high=8, medium=5, low=3, none=1
