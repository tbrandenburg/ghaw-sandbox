---
description: Analyse CI/CD failures and apply fixes
argument-hint: <cicd-context-json>
---

# Resolve CI Errors

**Input**: $ARGUMENTS (JSON with failing PRs and their CI logs)

## For Each Failing PR

### Step 1: Analyse Failure

Read the CI log for the PR. Identify root cause:
- Compile error
- Test failure
- Lint / type check failure
- Logic error

### Step 2: Checkout Branch

    git checkout {branch}
    git pull origin {branch}

### Step 3: Explore Root Cause in Code

Use file-read tools to read the failing file(s) mentioned in the CI log.
Understand the error in context before applying a fix.

### Step 4: Apply Fix

Implement the minimal fix that resolves the CI failure.
Do NOT refactor unrelated code — scope fix tightly to the failure.

### Step 5: Commit Fix

    git add -A
    git commit -m "fix({scope}): resolve CI failure — {brief description}"
    git push origin {branch}

### Step 6: Comment on PR

    gh pr comment {pr} \
      --body "🔧 CI fix applied.
      Root cause: {description}
      Changes: {summary of what was changed}"

### Step 7: Out-of-Scope Issues

If the CI failure reveals a deeper problem that requires a separate fix:

    gh issue create \
      --title "CI: {discovered issue title}" \
      --body "Discovered while fixing CI on PR #{pr}.\n\n{description}" \
      --label "open,severity/{val},priority/{val},type/bug"
