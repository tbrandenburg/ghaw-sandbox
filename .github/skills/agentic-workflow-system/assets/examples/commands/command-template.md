---
description: 'TEMPLATE — Replace this with a one-line description of what this command does'
argument-hint: '<description of the argument, e.g. issue-number or context-json>'
---

# [Command Title]

**Input**: $ARGUMENTS ([what the argument contains, e.g. "issue number" or "JSON with context"])

## Step 1: [Load / Parse Input]

[Describe how to read and validate the input, e.g.:]

    gh issue view $ARGUMENTS --json number,title,body,labels,comments

## Step 2: [Explore / Gather Context]

[Describe what to look for in the repo or API before acting, e.g.:]

    # Use file-read tools to explore affected components
    # No hardcoded paths — explore adaptively

## Step 3: [Act]

[Describe the core action the agent takes, e.g. write code, post a plan, create a PR]

## Step N-1: [Handle Errors]

If a blocker is discovered that prevents completion:

    gh issue comment {issue_number} \
      --body "<!-- [FAILURE-MARKER] -->
      Cannot complete: {specific reason}"

Then stop — do not post the success signal.

## Step N: Post Signal

**On success:**

    gh issue comment {issue_number} \
      --body "<!-- [SUCCESS-MARKER] -->
      [Brief human-readable summary of what was done]"

**On failure** (if not already handled above):

    gh issue comment {issue_number} \
      --body "<!-- [FAILURE-MARKER] -->
      [Reason]"
