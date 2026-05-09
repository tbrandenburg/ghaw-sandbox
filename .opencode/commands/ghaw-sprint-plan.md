---
description: WSJF ranking and sprint assignment for ready issues
argument-hint: <sprint-context-json>
---

# Sprint Planning

**Input**: $ARGUMENTS (JSON with ready issues, blocked issues, open PRs, MAX_WIP, CURRENT_WIP)

## Step 1: Handle Blocked Issues

For each blocked issue:
- Read blocker comments to determine if the blocking condition is resolved
- If resolved:

      gh issue edit {number} --add-label "ready" --remove-label "blocked"
      gh issue comment {number} --body "✅ Blocker resolved — returning to ready state."

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

For each ready issue with a confirmed <!-- PLAN --> comment:

Score using Fibonacci values from labels:
- severity_map:  critical=13, high=8, medium=5, low=3
- priority_map:  high=8, medium=5, low=3
- complexity_map: high=8, medium=5, low=3

    WSJF = (severity + priority) / complexity

Post score comment:

    gh issue comment {number} \
      --body "📊 WSJF: {score} (CoD: {severity}+{priority} / Size: {complexity})"

## Step 4: Assign Sprint

Sort issues by WSJF descending.

For the top N = MAX_WIP - CURRENT_WIP issues (skip if N <= 0), post a comment confirming assignment:

    gh issue comment {number} \
      --body "🚀 Assigned to sprint (WSJF rank: {rank}/{total})."

Do NOT call `gh issue edit` for state labels — the workflow assigns `in-progress` reliably based on WSJF scores.

## Step 5: Summary

If any reviewed issue has a stale review (>24h without merge decision), @mention PO:

    gh issue comment {number} \
      --body "⏰ Stale review — @{po_handle} please approve or request changes."
