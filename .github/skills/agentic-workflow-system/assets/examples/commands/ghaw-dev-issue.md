---
description: Implement an in-progress GitHub issue and open a pull request
argument-hint: <dev-context-json>
---

# Implement Issue

**Input**: $ARGUMENTS (JSON with in-progress issues without PR, and open PRs)

## For Each Candidate Issue

### Step 1: Read Implementation Plan

    gh issue view {number} --json number,title,body,labels,comments

Find the `<!-- PLAN -->` comment and extract the implementation plan.
If no plan found: skip this issue and comment a warning.

### Step 2: Determine Branch Name

Based on issue labels and title:
- `feature/issue-{number}` — new feature
- `fix/issue-{number}` — bug fix
- `chore/issue-{number}` — maintenance
- `docs/issue-{number}` — documentation
- `refactor/issue-{number}` — refactoring

### Step 3: Create or Checkout Branch

    git checkout -b {branch}
    # OR if branch already exists:
    git checkout {branch}

### Step 4: Explore and Implement

Use file-read tools to explore affected components (guided by implementation plan).
Implement the changes following existing patterns and conventions.

### Step 5: Write Tests

Write or update unit tests for the changed components.
Follow existing test structure — no new test frameworks.

### Step 6: Commit

    git add -A
    git commit -m "{type}({scope}): {description} (closes #{number})"

### Step 7: Open Pull Request

    gh pr create \
      --title "{type}({scope}): {description}" \
      --body "## Summary

    {brief description of changes}

    ## Changes
    - {change 1}
    - {change 2}

    Closes #{number}" \
      --head {branch} \
      --base main

If branch already has an open PR, update it instead of creating a new one.

### Step 8: Handle Blockers

If a blocker is discovered during implementation:

    gh issue edit {number} \
      --add-label "blocked" \
      --remove-label "in-progress" \
      --remove-label "ready" \
      --remove-label "open"
    gh issue comment {number} --body "🚧 Blocked: {reason}"

### Step 9: Handle Discovered Sub-Tasks

If sub-tasks are discovered that are out of scope for this PR:

    gh issue create \
      --title "{sub-task title}" \
      --body "Discovered during implementation of #{number}.\n\n{description}" \
      --label "severity/{val},priority/{val},size/{val},confidence/{val}"
    gh issue comment {number} --body "🔍 Sub-task created: #{new-number}"
