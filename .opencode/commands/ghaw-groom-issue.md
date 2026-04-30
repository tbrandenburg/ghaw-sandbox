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
      cc: @{po_handle}"

### Step 2: Defocus Check

If the issue is out-of-scope, not actionable, or duplicates another issue:

    gh issue edit {number} --add-label "defocus" --remove-label "open"
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

### Step 6: Ready Gate

After completing all grooming checks, if the issue was NOT defocused and NOT flagged with unresolved questions:

Check the issue's `confidence` and `complexity` labels:

- If `confidence/high` or `confidence/medium` **AND** `complexity/low` or `complexity/medium`:

      gh issue edit {number} --add-label "ready" --remove-label "open"
      gh issue comment {number} \
        --body "✅ Grooming complete. Confidence and complexity qualify for automatic promotion.
        Issue has been marked \`ready\` for sprint planning."

- Otherwise (confidence/low OR complexity/high):

      gh issue comment {number} \
        --body "✅ Grooming complete. Issue is clear and correctly labelled.

        @{po_handle} — confidence or complexity requires your review before sprint planning.
        Please add the \`ready\` label when satisfied."
