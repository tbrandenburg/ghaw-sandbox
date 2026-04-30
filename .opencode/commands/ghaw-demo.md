---
description: Analyse sprint results, E2E tests, and create follow-up issues
argument-hint: <demo-context-json>
---

# Sprint Demo

**Input**: $ARGUMENTS (JSON with closed issues, main branch SHA, E2E results)

## Step 1: Analyse E2E Results

Read the E2E test output from the input.

For each failure or regression:
- Classify: bug / arch / feedback
- Determine severity and priority

Create a new issue:

    gh issue create \
      --title "[Demo] {finding title}" \
      --body "Found during sprint demo on {date}.

      ## Finding
      {description}

      ## E2E Output
      \`\`\`
      {relevant log excerpt}
      \`\`\`

      ## Triggered by
      Closed issues: {list of relevant closed issue numbers}" \
      --label "open,severity/{val},priority/{val},type/{bug|arch|feedback}"

## Step 2: Compare Against Sprint Goals

Review the closed issues from the input.
Identify:
- Goals fully achieved (issue closed, E2E confirms)
- Goals partially achieved (issue closed, but E2E shows gaps)
- Regressions in previously working features

## Step 3: Sprint Summary

Post a sprint summary (to milestone comment or as a repo discussion):

    gh api repos/${{ github.repository }}/milestones/{id}/comments \
      --field body="## Sprint Summary — {date}

      **Closed:** {N} issues
      **New from demo:** {M} issues

      ### What Worked
      - {item}

      ### Issues Found
      - {item}

      ### Next Priorities
      - {item}"

If no milestone is configured, post as a comment on the most recently closed issue.
