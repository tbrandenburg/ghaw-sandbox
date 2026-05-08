---
description: Groom open issues for clarity, feasibility, defocus, and splitting
argument-hint: <issues-json>
---

# Groom Issues

**Input**: $ARGUMENTS (JSON array of open issues)

## For Each Issue

Process each issue in the input JSON sequentially.

### Step 1: Clarity Check

Read the issue description and comments.

If acceptance criteria are missing or ambiguous:

    gh issue comment {number} \
      --body "❓ Grooming: Acceptance criteria unclear. Please clarify:
      - {question 1}
      - {question 2}

      @{po_handle} — please reply to this comment with your answers, then remove the \`confidence/low\` label to trigger re-assessment."

    gh issue edit {number} --add-label "confidence/low"

### Step 2: Defocus Check

If the issue is out-of-scope, not actionable, or duplicates another issue:

    gh issue edit {number} --add-label "defocus" --remove-label "open" --remove-label "ready" --remove-label "in-progress" --remove-label "blocked"
    gh issue comment {number} --body "⚠️ Grooming: Marked as defocus. Reason: {reason}"

### Step 3: Feasibility Review

Use file-read tools to explore relevant code areas mentioned in the issue.

If architectural conflict or missing dependency found:

    gh issue comment {number} \
      --body "⚠️ Feasibility concern: {description of conflict or missing dependency}"

### Step 4: Story Splitting

If the issue scope is too large for a single sprint (complexity/high and multiple independent concerns):

Create sub-issues:

    gh issue create \
      --title "{sub-issue title}" \
      --body "Parent: #{number}\n\n{description}" \
      --label "severity/{val},priority/{val},complexity/{val},confidence/{val}"

Add summary to parent:

    gh issue comment {number} --body "📦 Split into sub-issues: #{new1}, #{new2}, ..."

### Step 5: Re-evaluate Labels

If severity or priority labels are incorrect based on current understanding:

    gh issue edit {number} \
      --add-label "severity/{new}" \
      --remove-label "severity/{old}"

### Step 6: PO Handoff (if needed)

After completing all grooming checks, if the issue was NOT defocused and NOT flagged with unresolved questions, and has `confidence/low` OR `complexity/high`:

    gh issue comment {number} \
      --body "✅ Grooming complete. Confidence or complexity requires PO review before sprint planning.

      @{po_handle} — please review and add the \`ready\` label when satisfied."

Do NOT call `gh issue edit` for `ready` or `open` labels — the workflow handles promotion reliably based on label data.
