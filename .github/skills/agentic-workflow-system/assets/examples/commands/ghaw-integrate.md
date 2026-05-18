---
description: Orchestrate the optimal integration sequence for multiple approved PRs
argument-hint: <merge-context-json>
---

# Merge Orchestration

**Input**: $ARGUMENTS (merge context with candidates, diffs, conflict map, issue metadata)

## Step 1: Parse and Understand All Candidates

Read the full input. For each approved PR extract:

- PR number, title, linked issue
- Files changed (from diff context)
- Issue labels: severity, priority, size
- `mergeStateStatus`: CLEAN, BEHIND, DIRTY, BLOCKED, UNKNOWN

Build a mental model of the full candidate set before making any decisions.

## Step 2: Build Dependency Graph

Analyse which PRs have logical dependencies on each other:

**Signals to look for:**

- PR B's issue description says "depends on #N" or "builds on PR #M"
- PR A introduces a new function/type/interface that PR B imports or calls
- PR A creates a file that PR B modifies
- PR A and B both modify the same file in potentially incompatible ways (conflict risk)

For each dependency found, document it:
    PR #A must merge BEFORE PR #B because: {reason}

For each conflict risk found:
    PR #A and PR #B touch {file} — one must merge first, other may need rebase

## Step 3: Risk Classification

Classify each PR as:

- **LOW** — isolated change (docs, tests, single-file feature in non-core area)
- **MEDIUM** — moderate change (multi-file, touches shared utilities)
- **HIGH** — architectural (schema changes, interface changes, core system refactor, large diff)

## Step 4: Determine Optimal Merge Sequence

Output a ranked merge plan. Example format:

    Merge Plan:
    1. PR #12 — "Add UserService interface" (LOW, foundation for #15 and #17)
    2. PR #15 — "Implement UserService for PostgreSQL" (MEDIUM, depends on #12)
    3. PR #8  — "Fix login redirect" (LOW, independent)
    4. PR #17 — "Add UserService caching layer" (MEDIUM, depends on #12, conflict risk with #15 on user_service.ts)
    5. DEFER PR #22 — "Refactor auth module" (HIGH, touches 14 files, high conflict risk — defer to next cycle after #15 stabilises)

Post the merge plan as a comment on the most complex PR:

    gh pr comment {pr} \
      --body "## Merge Orchestration Plan

      **{N} PRs queued for merge** in this sequence:
      {ordered list with rationale}

      Deferred: {list with reasons}"

## Step 5: Execute Merge Sequence

For each PR in the planned order:

### 5a: Pre-merge check

    git fetch origin
    git checkout main && git pull

Check if PR branch is behind main:

    git log --oneline HEAD..origin/{branch} 2>/dev/null | head -5

If BEHIND: update the branch

    gh pr comment {number} --body "🔄 Updating branch before merge..."
    git checkout {branch}
    git rebase origin/main
    git push --force-with-lease origin {branch}

### 5b: Merge

Merge using merge-commit strategy to preserve full git history from the PR branch.
GitHub automatically closes issues referenced with `Closes #N` in the PR body.

    gh pr merge {number} \
      --merge \
      --delete-branch \
      --subject "{type}: {title} (#{number})"

The workflow will reliably remove the `reviewed` label after confirming the merge.

**Coordination issue safety:** Do NOT close coordination/tracking issues (merge conflict
tracking, dependency coordination, or `type/coordination`-labelled issues) until **all**
dependent PRs are actually merged into main. A rebase that resolves a merge conflict does
**not** satisfy the dependency — the dependent PR must be merged first. Closing coordination
issues prematurely inflates sprint velocity and leaves features undelivered.

### 5c: Post-merge verification

After each merge, verify the build is not broken:

    git checkout main && git pull
    # Check for obvious structural issues (missing files, broken imports)
    # If a CI system is running, note it will confirm within minutes

If the merge introduced a conflict or obvious breakage, evaluate:

**Option A — Resolve inline:**

- Checkout branch, resolve conflict manually, push, re-merge

**Option B — Defer PR:**

    gh pr comment {number} \
      --body "⏸️ Merge deferred after conflict with previously merged PR #{earlier_pr}.
      Branch needs rebase. Dev Agent will pick up in next cycle.
      <!-- DEFERRED -->"

Do NOT call `gh issue edit` for state labels — the workflow detects the `<!-- DEFERRED -->` marker comment and applies `blocked` reliably.

### 5d: Rollback decision

If a merge causes a regression that blocks subsequent merges AND cannot be resolved inline:

    git revert -m 1 HEAD --no-edit
    git push origin main
    gh pr comment {number} \
      --body "🔙 Merge of PR #{number} reverted — caused regression affecting {subsequent-prs}.
      Please fix and re-submit."

## Step 6: Final Summary

After all merges (and deferrals) are processed, write the summary to the GitHub Actions job
summary and post it as a comment on the last merged PR.

**6a: GitHub Actions job summary** (always):

    cat >> $GITHUB_STEP_SUMMARY << 'EOF'
    ## Merge Orchestration Summary

    **Merged ({N}):** {list of PR numbers and titles}
    **Deferred ({M}):** {list with reasons}
    **Reverted ({K}):** {list with reasons}

    **Next recommended action:** {e.g. 'PR #22 needs rebase', 'CI confirming #15 and #17'}
    EOF

**6b: PR comment on the last merged PR** (always; skip only if no PR was merged):

    gh pr comment {last_merged_pr} \
      --body "## Merge Orchestration Summary

      **Merged ({N}):** {list of PR numbers and titles}
      **Deferred ({M}):** {list with reasons}
      **Reverted ({K}):** {list with reasons}

      **Next recommended action:** {e.g. 'PR #22 needs rebase', 'CI confirming #15 and #17'}"

Do NOT create a GitHub issue for the summary.
