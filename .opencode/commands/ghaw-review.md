---
description: Review a pull request against Definition of Done and acceptance criteria
argument-hint: <review-context-json>
---

# Review Pull Request

**Input**: $ARGUMENTS (JSON with PR metadata, diff, and linked issue)

## For Each PR to Review

### Step 1: Load Definition of Done

Read the project's Definition of Done:

    cat DEFINITION_OF_DONE.md

If file does not exist, use the default DoD:
- Code Review by peer completed
- All automated tests passing
- Code quality standards met
- Documentation updated where relevant
- Security checks passed
- Production-ready

### Step 2: Verify Acceptance Criteria

Read the linked issue's acceptance criteria (from issue body or comments).
Check each criterion against the PR diff.

### Step 3: Code Review

Review the PR diff for:
- Correctness: does the code do what the issue requires?
- Test coverage: are new tests present and meaningful?
- Code quality: follows existing patterns and conventions?
- No regressions introduced
- Security: no obvious vulnerabilities

Post inline comments for specific findings:

    gh pr review {pr} \
      --comment \
      --body "{finding description}"

### Step 4: Out-of-Scope Findings

For any issue found that is outside this PR's scope:

    gh issue create \
      --title "{finding title}" \
      --body "Found during review of PR #{pr}.\n\n{description}" \
      --label "open,severity/{val},priority/{val},type/{bug|arch|feedback}"

### Step 5: Decision

**If all checks pass:**

    gh pr comment {pr} \
      --body "## Review Summary\n\n✅ Technical review passed. All acceptance criteria met and DoD satisfied.\n\n### Verification Results:\n{bullet list of checks}\n\n### Definition of Done Checklist:\n{checklist}\n\n      @{{ github.repository_owner }} — please review and approve this PR for merge when ready."

Do NOT call `gh issue edit` for state labels — the workflow detects the review summary comment and applies `reviewed` reliably.

**If critical issues found:**

    gh pr review {pr} --request-changes \
      --body "❌ Changes requested:\n{summary of blocking issues}"
    # Issue stays in-progress — Dev Agent picks up next cycle
