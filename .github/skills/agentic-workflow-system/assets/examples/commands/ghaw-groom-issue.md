---
description: Groom open issues for clarity, feasibility, defocus, and splitting. Also triage blocked issues.
argument-hint: <issues-json>
---

# Groom Issues

**Input**: $ARGUMENTS (JSON array of open issues)

## Step 0: Blocked Issue Triage

Before grooming open issues, first handle all **blocked** issues in the input.

For each blocked issue, read all comments to understand the blocker reason.

### Hard Blocker

A blocker is **hard** (permanently unresolvable) if it is caused by:
- A GitHub platform constraint (e.g. `GITHUB_TOKEN` cannot write `.github/workflows/`)
- An architectural constraint that cannot be changed within this project's scope
- An external dependency or permission that will never be granted

If hard blocker detected:

1. Defocus and close the blocked issue:

       gh issue edit {number} --add-label "defocus" --remove-label "blocked" --remove-label "in-progress" --remove-label "ready" --remove-label "open"
       gh issue comment {number} --body "🚫 Hard blocker detected: {reason}\n\nThis issue cannot be resolved as stated. Closing and replacing with a reformulated alternative."
       gh issue close {number} --reason "not planned"

2. Open a replacement issue with an alternative approach that avoids the constraint:

       gh issue create \
         --title "{reformulated title}" \
         --body "Replaces #${number} which was blocked by: {reason}\n\n## Alternative Approach\n\n{description of approach that avoids the constraint}\n\n## Acceptance Criteria\n\n{criteria}" \
         --label "type/{type},priority/{val},severity/{val},size/{val},confidence/{val},open"
       gh issue comment {number} --body "♻️ Replaced by #{new-number}"

### Soft Blocker

A blocker is **soft** (circumstantial) if it is caused by:
- A flaky test or transient CI failure
- A secret or credential not yet configured
- Waiting on another PR or issue to merge first
- A missing clarification that can be provided

If soft blocker: leave the issue as-is with no changes. The planner agent handles unblocking.

## For Each Open Issue

Process each non-blocked issue in the input JSON sequentially.

### Step 1: Timeout Defocus Check

If the issue already has the `confidence/low` label:

1. Find the most recent grooming question comment (a comment containing "please reply to this comment with your answers").
2. Check whether any comment from the repo owner was posted **after** that grooming comment.
3. If no reply from the repo owner exists and the grooming comment is **older than 3 days**, defocus and close the issue:

       gh issue edit {number} --add-label "defocus" --remove-label "open" --remove-label "confidence/low"
       gh issue comment {number} --body "⏰ Defocused: no response received after 3 days. Closing until scope is clarified."
       gh issue close {number} --reason "not planned"

   Then **skip** all remaining steps for this issue.

### Step 2: Clarity Check

Read the issue description and comments.

If acceptance criteria are missing or ambiguous:

    gh issue comment {number} \
      --body "❓ Grooming: Acceptance criteria unclear. Please clarify:
      - {question 1}
      - {question 2}

      @{{ github.repository_owner }} — please reply to this comment with your answers, then remove the \`confidence/low\` label to trigger re-assessment."

    gh issue edit {number} --add-label "confidence/low"

### Step 3: Defocus Check

If the issue is out-of-scope, not actionable, or duplicates another issue:

    gh issue edit {number} --add-label "defocus" --remove-label "open" --remove-label "ready" --remove-label "in-progress" --remove-label "blocked"
    gh issue comment {number} --body "⚠️ Grooming: Marked as defocus. Reason: {reason}"
    gh issue close {number} --reason "not planned"

### Step 4: Feasibility Review

Use file-read tools to explore relevant code areas mentioned in the issue.

If architectural conflict or missing dependency found:

    gh issue comment {number} \
      --body "⚠️ Feasibility concern: {description of conflict or missing dependency}"

    gh issue edit {number} --add-label "confidence/low"

### Step 5: Story Splitting

If the issue scope is too large for a single sprint (size/xl or size/l and multiple independent concerns):

Create sub-issues:

    gh issue create \
      --title "{sub-issue title}" \
      --body "Parent: #{number}\n\n{description}" \
      --label "severity/{val},priority/{val},size/{val},confidence/{val}"

Add summary to parent:

    gh issue comment {number} --body "📦 Split into sub-issues: #{new1}, #{new2}, ..."

### Step 6: Re-evaluate Labels

If severity or priority labels are incorrect based on current understanding:

    gh issue edit {number} \
      --add-label "severity/{new}" \
      --remove-label "severity/{old}"

### Step 7: PO Handoff (if needed)

After completing all grooming checks, if the issue was NOT defocused and NOT flagged with unresolved questions, and has `confidence/low` OR `size/xl` or `size/l`:

    gh issue comment {number} \
      --body "✅ Grooming complete. Confidence or size requires PO review before sprint planning.

      @{{ github.repository_owner }} — please review and add the \`ready\` label when satisfied."

Do NOT call `gh issue edit` for `ready` or `open` labels — the workflow handles promotion reliably based on label data.
