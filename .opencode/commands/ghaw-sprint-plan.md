---
description: WSJF ranking and sprint assignment for planned issues
argument-hint: <sprint-context-json>
---

# Sprint Planning

**Input**: $ARGUMENTS (JSON with planned issues, blocked issues, open PRs, MAX_WIP, CURRENT_WIP)

## Step 1: Handle Blocked Issues

For each blocked issue:
- Read blocker comments to determine if the blocking condition is resolved
- If resolved:

      gh issue edit {number} --add-label "planned" --remove-label "blocked"
      gh issue comment {number} --body "✅ Blocker resolved — returning to planned state."

- If still blocked: leave as-is, note it in step summary

## Step 2: Handle reviewed + request-changes PRs

For PRs in the input with reviewDecision=CHANGES_REQUESTED:

    gh issue edit {linked-issue-number} \
      --remove-label "reviewed" \
      --remove-label "blocked" \
      --remove-label "open" \
      --add-label "in-progress"
    gh issue comment {linked-issue-number} --body "🔄 Changes requested — returning to in-progress."

## Step 3: WSJF Scoring

For each planned issue, score using Fibonacci values from labels:
- severity_map:  critical=13, high=8, medium=5, low=3
- priority_map:  high=8, medium=5, low=3
- size_map:      xl=13, l=8, m=5, s=3, xs=1

    WSJF = (severity + priority) / size

Post score comment:

    gh issue comment {number} \
      --body "📊 WSJF: {score} (CoD: {severity}+{priority} / Size: {size})"

## Step 4: Assign Sprint

Sort issues by WSJF descending.

For the top N = MAX_WIP - CURRENT_WIP issues (skip if N <= 0), post a comment confirming assignment:

    gh issue comment {number} \
      --body "🚀 Assigned to sprint (WSJF rank: {rank}/{total})."

Do NOT call `gh issue edit` for state labels — the workflow assigns `in-progress` reliably based on WSJF scores.

## Step 5: Summary

If any reviewed issue has a stale review (>24h without merge decision), @mention PO:

    gh issue comment {number} \
      --body "⏰ Stale review — @{{ github.repository_owner }} please approve or request changes."
