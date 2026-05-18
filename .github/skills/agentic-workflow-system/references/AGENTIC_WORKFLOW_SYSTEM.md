# Agentic GitHub Workflow System

A pattern for running an **LLM-driven state machine** entirely inside GitHub Actions, with no external infrastructure. Issues move through states autonomously — agents reason and act, workflows enforce transitions deterministically.

---

## Table of Contents

1. [Core Idea](#core-idea)
2. [Architecture](#architecture)
3. [File Naming Conventions](#file-naming-conventions)
4. [Core Files](#core-files)
5. [State Machine Fundamentals](#state-machine-fundamentals)
6. [Three-Phase Workflow Pattern](#three-phase-workflow-pattern)
7. [Agent Definitions](#agent-definitions)
8. [Command Definitions](#command-definitions)
9. [Configuration](#configuration)
10. [Tooling & Bootstrap](#tooling--bootstrap)
11. [Reliability Principles](#reliability-principles)
12. [Extending the System](#extending-the-system)
13. [Validation Rules](#validation-rules)

---

## Core Idea

GitHub issue labels are used as **state**. Each state has an owning workflow. Workflows follow a strict three-phase pattern: collect context (Prepare), run an LLM agent (Run), then verify and apply the state transition (Verify).

Agents act via `gh` CLI and `git`. They signal intent through structured comments. Workflows detect those signals and apply label transitions. This separation means:

- A bad LLM response cannot corrupt the state machine — the verify step catches it
- Every transition is auditable — recorded in the issue timeline
- Agents are swappable — the workflow contract is the signal format, not the agent implementation

**Nothing runs outside GitHub** — no servers, no queues, no databases. Scheduling uses GitHub Actions `schedule`, event delivery uses `issues: labeled`, and state is stored in issue labels.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         GitHub Repository                           │
│                                                                     │
│  Issues ─── carry exactly one state label at a time                │
│  PRs    ─── linked to issues via "Closes #N" in PR body            │
│                                                                     │
│  Workflows                                                          │
│  ───────────────────────────────────────────────────────────────   │
│  core-state-heal.yml    fires on every issues: labeled event        │
│  sm-[state].yml         one workflow per state label                │
│  agent-[name].yml       stateless agents (no required state)        │
│  core-opencode-run.yml  reusable LLM runner (called by all above)  │
│                                                                     │
│  OpenCode agent files                                               │
│  ───────────────────────────────────────────────────────────────   │
│  .opencode/agent/[name].md    persona / system prompt              │
│  .opencode/commands/[name].md task-specific instruction prompt     │
│                                                                     │
│  Configuration                                                      │
│  ───────────────────────────────────────────────────────────────   │
│  .github/config/config.yml    model, WIP limits, thresholds        │
│                                                                     │
│  Tooling (local, not committed to target repos)                     │
│  ───────────────────────────────────────────────────────────────   │
│  Makefile          lint, test, git hooks                           │
│  Makefile.ghaw     install system into target repo, setup labels,  │
│                    manage releases                                  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## File Naming Conventions

| Pattern | Purpose | Example |
|---|---|---|
| `core-[name].yml` | Reusable workflows, called by others | `core-opencode-run.yml`, `core-state-heal.yml` |
| `sm-[state].yml` | State-owned workflow — one per state label | `sm-open.yml`, `sm-in-progress.yml` |
| `agent-[name].yml` | Stateless agent — no required state label | `agent-cicd.yml` |

OpenCode files:

| Pattern | Purpose |
|---|---|
| `.opencode/agent/[name].md` | Agent persona definition |
| `.opencode/commands/[name].md` | Task instruction prompt |

---

## Core Files

These two files are required in every repo that uses this system. Copy them verbatim and adapt the state label list to your own states.

### `core-state-heal.yml`

Fires on every `issues: labeled` event. If the newly added label is a state label and the issue already carries other state labels, removes all conflicting ones — keeping only the label just added. This is the only mechanism that guarantees state exclusivity, and it must always be present.

**Adaptation:** replace the label list in the `if:` condition and in `STATE_LABELS` with your own state label names.

```yaml
name: Core - Issue State Healer

# Event-driven: fires whenever a label is added to any issue.
# If the label is a state label and the issue now carries more than one
# state label, heals it by keeping the one just added and removing the rest.
#
# State labels (mutually exclusive): replace this list with your own states

on:
  issues:
    types: [labeled]

jobs:
  heal:
    # Only run if the added label is one of your state labels
    if: |
      contains(fromJSON('["state-a","state-b","state-c","blocked"]'),
               github.event.label.name)
    runs-on: ubuntu-latest
    env:
      GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
    steps:
      - name: Heal ambiguous state labels on issue ${{ github.event.issue.number }}
        run: |
          set -euo pipefail

          # Keep this list in sync with the fromJSON array above
          STATE_LABELS="state-a state-b state-c blocked"
          REPO="${{ github.repository }}"
          NUMBER="${{ github.event.issue.number }}"
          ADDED="${{ github.event.label.name }}"

          # Fetch current labels
          CURRENT=$(gh api "repos/$REPO/issues/$NUMBER" \
            --jq '[.labels[].name]')

          # Count state labels currently set
          STATE_COUNT=$(echo "$CURRENT" | jq \
            --argjson states '["state-a","state-b","state-c","blocked"]' \
            '[.[] | select(. as $l | $states | index($l) != null)] | length')

          if [ "$STATE_COUNT" -le "1" ]; then
            echo "✅ #$NUMBER — state is clean (\`$ADDED\`), nothing to heal" >> $GITHUB_STEP_SUMMARY
            exit 0
          fi

          echo "⚠️ #$NUMBER — $STATE_COUNT state labels detected, healing to \`$ADDED\`" >> $GITHUB_STEP_SUMMARY

          # Remove every state label except the one just added
          for LABEL in $STATE_LABELS; do
            [ "$LABEL" = "$ADDED" ] && continue
            IS_SET=$(echo "$CURRENT" | jq --arg l "$LABEL" 'contains([$l])')
            if [ "$IS_SET" = "true" ]; then
              gh issue edit "$NUMBER" --repo "$REPO" --remove-label "$LABEL"
              echo "  removed \`$LABEL\`" >> $GITHUB_STEP_SUMMARY
            fi
          done

          echo "✅ #$NUMBER healed → \`$ADDED\`" >> $GITHUB_STEP_SUMMARY
```

**The three places to update when adding a state:**
1. `fromJSON([...])` in the `if:` condition on the `heal` job
2. `STATE_LABELS` shell variable
3. `--argjson states '[...]'` passed to `jq` inside the run step

All three must stay in sync or the healer will silently skip the new state.

### `core-opencode-run.yml`

The reusable LLM runner called by every `sm-*.yml` and `agent-*.yml` via `uses:`. See [AGENTIC_WORKFLOW_SYSTEM_GHAW.md](AGENTIC_WORKFLOW_SYSTEM_GHAW.md) for the full verbatim source — it requires no adaptation and should be copied as-is.

---

## State Machine Fundamentals

### States are mutually exclusive labels

An issue carries **exactly one** state label at all times. `core-state-heal.yml` enforces this by firing on every `issues: labeled` event and removing any conflicting state labels automatically.

### Each state has one owning workflow

`sm-[state].yml` is the only workflow that transitions issues **out of** its state. It is triggered by schedule, by event (e.g., the state label being applied), or both.

### Transitions are applied by verify steps, not agents

Agents post structured HTML comments as signals. The verify step reads those comments from the GitHub API and applies label transitions. Agents never call `gh issue edit` for state labels.

### Blocked is a universal escape

Any verify step that detects a failure adds `blocked` and removes the current state. The issue surfaces for human review without silently stalling.

### Example state flow

A concrete implementation might look like:

```
[new issue created]
        │
        ▼
      open  ──── sm-open.yml ────────────────────▶  ready
                  (groomer agent)                      │
                  reviews for clarity,                 │
                  scope, feasibility              sm-ready.yml
                                                  (planner agent)
                                                  creates impl plan
                                                        │
                                                        ▼
                                                    planned
                                                        │
                                                 sm-planned.yml
                                                 (planner agent)
                                                 WSJF ranking,
                                                 sprint assignment
                                                        │
                                                        ▼
                                                  in-progress
                                                        │
                                               sm-in-progress.yml
                                               (dev agent)
                                               implement + open PR
                                                        │
                                                        ▼
                                                  sm-review.yml
                                                  (review agent)
                                                  review PR vs DoD
                                                        │
                                                        ▼
                                                    reviewed
                                                        │
                                               sm-reviewed.yml
                                               (integrator agent)
                                               merge PR
                                                        │
                                                        ▼
                                                  MERGED / CLOSED ✓
```

Any state can transition to `blocked` on agent failure. The groomer can also transition to `defocus` for out-of-scope issues.

### Minimum viable state machine

A working system needs only three files beyond `core-opencode-run.yml`:

```
core-state-heal.yml          # always required
sm-[your-entry-state].yml    # at least one state workflow
core-opencode-run.yml        # the LLM runner
```

Add more `sm-*.yml` files as your process grows.

---

## Three-Phase Workflow Pattern

Every `sm-[state].yml` and `agent-[name].yml` follows exactly this structure. Never skip or reorder phases.

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   PREPARE    │────▶│     RUN      │────▶│    VERIFY    │
│              │     │              │     │              │
│ Entry check  │     │ core-opencode│     │ Re-read API  │
│ Fetch context│     │ -run.yml     │     │ Detect signal│
│ Build prompt │     │ (LLM agent)  │     │ Apply labels │
│ Guard output │     │              │     │ Assert state │
└──────────────┘     └──────────────┘     └──────────────┘
        │                   │
   has_candidates       uses: ./...
   gates Run            core-opencode
   and Verify           -run.yml
```

### Phase 1: Prepare

The workflow-level trigger and the `prepare` job's `if:` condition work together to handle both event-driven and scheduled execution:

```yaml
on:
  issues:
    types: [labeled]          # React immediately when a state label is applied
  schedule:
    - cron: '...'             # Catch-up: process any issues missed by the event
  workflow_dispatch:          # Manual trigger for debugging or re-runs
    inputs:
      issue_number:
        required: false
        type: number

jobs:
  prepare:
    # Guard: only run for the correct label event, or for schedule/dispatch.
    # github.event.label.name ensures this workflow ignores label events
    # from other workflows (e.g., adding priority/high should not trigger
    # a state workflow unless that is your state label).
    if: |
      (github.event_name == 'issues' && github.event.label.name == '[state-label]') ||
      github.event_name == 'schedule' ||
      github.event_name == 'workflow_dispatch'
    runs-on: ubuntu-latest
    outputs:
      has_candidates: ${{ steps.filter.outputs.has_candidates }}
      prompt:         ${{ steps.build.outputs.prompt }}
      model:          ${{ steps.config.outputs.model }}
    env:
      GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
    steps:
      - uses: actions/checkout@v4

      - name: Read config
        id: config
        run: echo "model=$(yq '.model' .github/config/config.yml)" >> $GITHUB_OUTPUT

      - name: Check entry condition
        id: filter
        run: |
          # For labeled events, resolve the single issue from the event.
          # For schedule/dispatch, scan all issues in this state.
          if [ "${{ github.event_name }}" = "issues" ]; then
            ISSUE_NUMBER=${{ github.event.issue.number }}
          elif [ -n "${{ inputs.issue_number }}" ]; then
            ISSUE_NUMBER=${{ inputs.issue_number }}
          else
            ISSUE_NUMBER=""
          fi

          if [ -n "$ISSUE_NUMBER" ]; then
            # Single-issue mode: check whether processing is still needed
            # (e.g. no existing signal comment)
            ALREADY_DONE=$(gh issue view "$ISSUE_NUMBER" \
              --repo ${{ github.repository }} \
              --json comments \
              --jq '[.comments[].body | contains("<!-- MY-SIGNAL -->")] | any')
            [ "$ALREADY_DONE" = "true" ] \
              && echo "has_candidates=false" >> $GITHUB_OUTPUT \
              || echo "has_candidates=true"  >> $GITHUB_OUTPUT
            echo "issue_number=$ISSUE_NUMBER" >> $GITHUB_OUTPUT
          else
            # Batch mode: find all issues in this state not yet processed
            COUNT=$(gh issue list \
              --repo ${{ github.repository }} \
              --label "[state-label]" \
              --json number | jq length)
            [ "$COUNT" = "0" ] \
              && echo "has_candidates=false" >> $GITHUB_OUTPUT \
              || echo "has_candidates=true"  >> $GITHUB_OUTPUT
          fi

      - name: Build prompt
        id: build
        run: |
          # Assemble structured context for the agent
          echo "prompt=$(echo "$CONTEXT" | jq -Rs .)" >> $GITHUB_OUTPUT
```

**Why `github.event.label.name` matters:** Every label operation on any issue fires the `issues: labeled` event. Without the `github.event.label.name == '[state-label]'` guard on the `prepare` job, a state workflow would trigger whenever *any* label — including `priority/high` or `type/bug` — is added to an issue. The guard narrows execution to only the transition that this workflow owns.

### Phase 2: Run

```yaml
run:
  needs: prepare
  if: needs.prepare.outputs.has_candidates == 'true'
  uses: ./.github/workflows/core-opencode-run.yml
  with:
    run-name:        my-state-agent
    command:         my-command        # maps to .opencode/commands/my-command.md
    prompt:          ${{ needs.prepare.outputs.prompt }}
    agent:           my-agent          # maps to .opencode/agent/my-agent.md
    model:           ${{ needs.prepare.outputs.model }}
    timeout-minutes: 60
  permissions:
    issues:   write
    contents: read
  secrets: inherit
```

### Phase 3: Verify

```yaml
verify:
  needs: [prepare, run]
  if: needs.prepare.outputs.has_candidates == 'true'
  runs-on: ubuntu-latest
  env:
    GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
  steps:
    - name: Apply state transition
      run: |
        set -euo pipefail
        ISSUE=${{ needs.prepare.outputs.issue_number }}

        # Always re-read from the API — never trust workflow-level variables
        COMMENTS=$(gh issue view "$ISSUE" \
          --repo ${{ github.repository }} \
          --json comments --jq '[.comments[].body]')

        HAS_SIGNAL=$(echo "$COMMENTS" | jq '[.[] | contains("<!-- MY-SIGNAL -->")] | any')

        if [ "$HAS_SIGNAL" = "true" ]; then
          gh issue edit "$ISSUE" \
            --repo ${{ github.repository }} \
            --add-label "next-state" \
            --remove-label "current-state"
          echo "✅ #$ISSUE → next-state" >> $GITHUB_STEP_SUMMARY
        else
          gh issue edit "$ISSUE" \
            --repo ${{ github.repository }} \
            --add-label "blocked" \
            --remove-label "current-state"
          gh issue comment "$ISSUE" \
            --repo ${{ github.repository }} \
            --body "❌ Agent did not produce required signal. Blocked for human review."
          echo "❌ #$ISSUE → blocked" >> $GITHUB_STEP_SUMMARY
          exit 1
        fi
```

---

## Agent Definitions

Agents are Markdown files in `.opencode/agent/`. They define persona, behavioural constraints, and output contracts.

### Format

```markdown
---
description: One-line summary of this agent's role
---

You are a [role] agent. Your job is to [primary responsibility].

[Behavioural principles — what to look for, how to decide, what to avoid]

**Critical output contract**: [Exact format of the signal comment this agent must post.
The verify step depends on this contract — deviations cause the verify step to set blocked.]

Act directly via gh CLI and git. No structured return value needed.
```

### Output contract rule

If the verify step checks for a comment signal, the agent definition **must** document:
- The exact text or HTML comment marker to post
- Where it must appear (first line, PR comment, issue comment)
- Under what conditions it should be posted

Example:

```markdown
**Critical output contract**: When the task completes successfully, post an issue comment
whose body starts with `<!-- DONE -->` on the very first line. If the task cannot be
completed, post `<!-- CANNOT-COMPLETE -->` with the reason. Any other output will cause
the verify step to set the issue to `blocked`.
```

---

## Command Definitions

Commands are Markdown files in `.opencode/commands/`. They are step-by-step task instructions passed to OpenCode alongside the agent persona.

### Format

```markdown
---
description: One-line description of what this command does
argument-hint: <description of the argument>
---

# [Command Title]

**Input**: $ARGUMENTS ([what the argument contains])

## Step 1: [First action]
[Concrete instructions with exact gh CLI commands to run]

## Step 2: [Second action]
[...]

## Step N: Post Signal

If success:

    gh issue comment $ISSUE_NUMBER \
      --body "<!-- MY-SIGNAL -->
      [human-readable summary]"

If failure:

    gh issue comment $ISSUE_NUMBER \
      --body "<!-- MY-FAILURE-SIGNAL -->
      [reason]"
```

`$ARGUMENTS` is replaced by OpenCode with the `prompt` input from `core-opencode-run.yml`.

---

## Configuration

`.github/config/config.yml` holds values read by all workflows:

```yaml
model: opencode/big-pickle   # OpenCode model used by all agents
max_wip: 3                   # Maximum issues in the active working state simultaneously
```

Workflows read this file in the prepare phase:

```bash
MODEL=$(yq '.model'   .github/config/config.yml)
WIP=$(yq '.max_wip'   .github/config/config.yml)
```

Add any additional thresholds or feature flags here rather than hardcoding them in workflows.

---

## Tooling & Bootstrap

Two Makefiles ship alongside the system. They are used locally and in the source repo — they are **not** deployed into target repos as runtime dependencies.

| File | Purpose |
|---|---|
| `Makefile` | Local developer tooling: lint, test, git hooks |
| `Makefile.ghaw` | Bootstrap installer: copy system files into a target repo, create labels idempotently, manage releases |

### `Makefile` — Developer Tooling

Used to validate the system files themselves during development.

```bash
make install        # Install lint tools (yamllint, actionlint, markdownlint) + configure git hooks
make lint           # Run all linters (lint-yaml + lint-actions + lint-markdown)
make lint-yaml      # yamllint on .github/
make lint-actions   # actionlint on .github/workflows/*.yml
make lint-markdown  # markdownlint on all *.md files
make test           # lint + BATS behavioral tests
```

### `Makefile.ghaw` — Bootstrap Installer

Used once when adopting the system in a new repo, and again whenever files need updating.

**Installation:**

```bash
make -f Makefile.ghaw install           # Copy system files into current repo (skip existing)
make -f Makefile.ghaw install-force     # Copy and overwrite all files
make -f Makefile.ghaw install-dry       # Preview what would be copied, no changes
make -f Makefile.ghaw clean             # Remove all installed files
```

**Label management** (idempotent — safe to run multiple times):

```bash
make -f Makefile.ghaw setup-labels      # Create or update all required labels in the repo
make -f Makefile.ghaw setup-labels-dry  # Preview label changes without applying
make -f Makefile.ghaw list-labels       # Show all current labels in the repo
```

The `setup-labels` target uses the GitHub API (`gh api`) to create labels that do not exist and patch labels whose colour or description has drifted. It is safe to re-run at any time. Labels are grouped into categories and applied in batches:

```bash
# Under the hood, each label is applied via:
gh api -X POST "repos/$REPO/labels"          # create
gh api -X PATCH "repos/$REPO/labels/$NAME"   # update if already exists
```

URL-encoding of label names (e.g., `in-progress` → `in-progress`, `type/bug` → `type%2Fbug`) is handled automatically via `python3 -c 'import urllib.parse,...'`.

**Configuration and release management:**

```bash
make -f Makefile.ghaw info                   # Show installed version and config.yml
make -f Makefile.ghaw publish BUMP=patch     # Bump patch version, tag, push, create GitHub release
make -f Makefile.ghaw publish BUMP=minor     # Bump minor version
make -f Makefile.ghaw publish BUMP=major     # Bump major version
make -f Makefile.ghaw initial-release        # Create release for current version without bumping
```

The `publish` target enforces:
- There must be at least one new commit since the last tag (prevents empty releases)
- `RELEASE_NOTES.md` must not contain unedited placeholder HTML comments before the release is created

**Options:**

```bash
make -f Makefile.ghaw setup-labels REPO=owner/name   # Override target repo
make -f Makefile.ghaw setup-labels VERBOSE=true      # Show full gh API calls
make -f Makefile.ghaw setup-labels DEBUG=true        # Show label parameters before each API call
```

### Post-install steps

After running `make -f Makefile.ghaw install`, two GitHub repository settings must be enabled manually (not configurable via API):

1. **Settings → Actions → General → Workflow permissions** → set to *Read and write permissions*
2. **Settings → Actions → General** → enable *Allow GitHub Actions to create and approve pull requests*

---

## Reliability Principles

### 1. State labels are mutually exclusive

`core-state-heal.yml` fires on every `issues: labeled` event. If the added label is a state label and other state labels are present, it removes all but the one just added. This means even if two workflows apply labels simultaneously, the healer converges to a clean single-state.

**To implement:** List all your state labels in `core-state-heal.yml` and keep that list in sync as you add new states.

### 2. `github.event.label.name` scopes event-driven triggers

Every label operation on every issue fires the `issues: labeled` event. A state workflow that only uses `on: issues: types: [labeled]` without a filter would trigger on *any* label addition — including metadata labels like `priority/high`. The `prepare` job's `if:` condition uses `github.event.label.name == '[state-label]'` to ensure the workflow only acts when its own state label is applied.

Combined with the `schedule` branch of the same condition, this gives two delivery paths for the same logic: immediate reaction via the event and periodic catch-up via cron.

### 3. Entry conditions prevent double-processing

The prepare phase always checks whether the current issue/PR actually needs processing. If it has already been handled (e.g., a plan comment exists), `has_candidates=false` is set and the entire run+verify is skipped. Every workflow is safe to trigger multiple times.

### 4. Verify always re-reads from the API

The verify step never uses in-memory variables from the prepare or run phases to make decisions. It calls the GitHub API fresh. This makes it resilient to:
- Run phase timeouts (partial agent output)
- GitHub event delivery delays
- Stale cached data

### 4. Agents signal intent; workflows apply state

Agents post HTML comment markers (`<!-- MARKER -->`). Verify steps detect them with `jq contains(...)`. This separation means:
- Workflow behaviour is auditable and testable without running an LLM
- Verify can add business logic (e.g., auto-promotion rules) independently of the agent
- Swapping the agent does not change the workflow contract

HTML comment markers are preferred over prose because they are unambiguous, invisible in the GitHub UI, and survive Markdown rendering changes.

### 5. Blocked is the universal failure state

Any verify step that cannot confirm success sets `blocked` and exits with code 1. This ensures:
- Issues never stall silently
- Failures are visible in the Actions UI (red workflow run)
- A human can inspect the issue, resolve the cause, and re-trigger

### 6. Catch-up scheduling

Workflows that react to label events also run on a schedule (e.g., every few hours). This catches issues that missed the event trigger due to workflow failures, race conditions, or issues added during downtime.

---

## Extending the System

### Adding a new state

1. **Create the label** in GitHub (via `gh label create` or settings UI)

2. **Update `core-state-heal.yml`** — add the new label to both:
   - The `if:` condition `contains(fromJSON([...]))` check
   - The `STATE_LABELS` shell variable

3. **Create `sm-[new-state].yml`** following the three-phase template above

4. **Update the upstream verify step** — the state that transitions *into* your new state must be changed to add `new-state` instead of (or before) whatever it currently transitions to

5. **Create agent and command files**:
   - `.opencode/agent/[new-agent].md` with persona and output contract
   - `.opencode/commands/[new-command].md` with step-by-step instructions

6. **Document the state** — update any `AGENTS.md` or equivalent in your repo with:
   - What the agent MUST add / MUST remove
   - What the agent MUST NOT touch

### Adding a new label (non-state)

Non-state labels (e.g., `type/feature`, `priority/high`) can be added freely without updating `core-state-heal.yml`. They are additive metadata.

If a new label is used in WSJF scoring or auto-promotion logic, update the relevant command file and agent definition to reflect the new value mapping.

### Adding a stateless agent workflow

Stateless agents run on a schedule and act opportunistically without requiring a specific input state:

```yaml
name: Agent - [Name]

on:
  schedule:
    - cron: '...'
  workflow_dispatch:

jobs:
  prepare:
    # Entry: detect work that needs doing (e.g., failing CI, stale PRs)
    # If nothing found: has_candidates=false

  run:
    needs: prepare
    if: needs.prepare.outputs.has_candidates == 'true'
    uses: ./.github/workflows/core-opencode-run.yml
    with:
      run-name: [name]-agent
      command:  [command-name]
      prompt:   ${{ needs.prepare.outputs.prompt }}
      agent:    [agent-name]
      model:    ${{ needs.prepare.outputs.model }}
    secrets: inherit

  # verify is optional for stateless agents
  # add it if the agent must produce a specific measurable output
```

---

## Validation Rules

Shell checks an agent can run to verify a repo correctly implements this system.

### Linting

See [Tooling & Bootstrap](#tooling--bootstrap) for full tool installation instructions. Quick reference:

```bash
make install      # install yamllint, actionlint, markdownlint + configure git hooks
make lint         # run all linters
make lint-yaml    # yamllint -c .yamllint.yml .github/
make lint-actions # ./actionlint -shellcheck= .github/workflows/*.yml
```

`actionlint` validates Actions-specific concerns: expression syntax, context variable references, `uses:` action versions, and step `id` references. The `-shellcheck=` flag disables shell script linting inside `run:` steps — remove it if `shellcheck` is installed.

### Structural

```bash
# core files must exist
[ -f .github/workflows/core-opencode-run.yml ] || echo "FAIL: missing core-opencode-run.yml"
[ -f .github/workflows/core-state-heal.yml ]   || echo "FAIL: missing core-state-heal.yml"
[ -f .github/config/config.yml ]               || echo "FAIL: missing config.yml"

# config must have required keys
yq '.model'   .github/config/config.yml | grep -v '^null$' || echo "FAIL: config missing model"
yq '.max_wip' .github/config/config.yml | grep -E '^[0-9]+$' || echo "FAIL: config missing max_wip"

# every sm- workflow must have all three phases
for f in .github/workflows/sm-*.yml; do
  grep -q "^  prepare:" "$f" || echo "FAIL: $f missing prepare job"
  grep -q "^  run:"     "$f" || echo "FAIL: $f missing run job"
  grep -q "^  verify:"  "$f" || echo "FAIL: $f missing verify job"
done

# every sm- run job must call core-opencode-run.yml
for f in .github/workflows/sm-*.yml; do
  grep -q "uses: ./.github/workflows/core-opencode-run.yml" "$f" \
    || echo "FAIL: $f run job does not use core-opencode-run.yml"
done

# run and verify must be gated on has_candidates
for f in .github/workflows/sm-*.yml .github/workflows/agent-*.yml; do
  grep -q "has_candidates == 'true'" "$f" \
    || echo "FAIL: $f not gated on has_candidates"
done

# verify must depend on both prepare and run
for f in .github/workflows/sm-*.yml; do
  grep -A3 "^  verify:" "$f" | grep -q "needs: \[prepare, run\]" \
    || echo "FAIL: $f verify does not declare needs: [prepare, run]"
done
```

### Agent and command files

```bash
# every agent must have a description in frontmatter
for f in .opencode/agent/*.md; do
  grep -q "^description:" "$f" || echo "FAIL: $f missing description"
done

# every command must have description and argument-hint
for f in .opencode/commands/*.md; do
  grep -q "^description:"   "$f" || echo "FAIL: $f missing description"
  grep -q "^argument-hint:" "$f" || echo "FAIL: $f missing argument-hint"
done
```

### Live state invariant

```bash
REPO="owner/repo"
# All open issues must carry exactly one state label
# Replace the states array with your own state labels
STATE_LABELS='["state-a","state-b","state-c","blocked"]'

gh issue list --repo "$REPO" --state open --limit 200 \
  --json number,labels \
  --jq --argjson states "$STATE_LABELS" '
    .[] |
    (.labels | map(.name) | map(select(. as $l | $states | index($l) != null))) as $sl |
    select(($sl | length) != 1) |
    "VIOLATION: issue #\(.number) has \($sl | length) state labels: \($sl)"
  '
```

### Signal coverage

For every agent signal produced by a command, verify the corresponding verify step checks for it:

```bash
# Example: if plan-issue.md posts <!-- PLAN --> and <!-- CANNOT-PLAN -->
# then sm-ready.yml verify must check for both
grep -q "PLAN"         .github/workflows/sm-ready.yml || echo "FAIL: PLAN signal not checked"
grep -q "CANNOT-PLAN"  .github/workflows/sm-ready.yml || echo "FAIL: CANNOT-PLAN signal not checked"
```

---

## Quick Reference

### The pattern in one sentence per component

| Component | Does |
|---|---|
| `core-state-heal.yml` | Fires on every label event; removes duplicate state labels |
| `core-opencode-run.yml` | Installs OpenCode, runs the agent, saves output as artifact |
| `sm-[state].yml` | Owns one state: prepares context, runs agent, verifies and transitions |
| `agent-[name].yml` | Stateless: detects work, runs agent, optionally verifies |
| `.opencode/agent/*.md` | Defines agent persona, principles, and output contract |
| `.opencode/commands/*.md` | Defines step-by-step task instructions |

### Invariants to maintain

1. Every state label appears in `core-state-heal.yml`'s state list
2. Every state label has exactly one `sm-*.yml` that transitions issues *out* of it
3. Every agent that signals a verify step documents the exact signal format in its definition
4. No agent applies state labels directly — only verify steps do
5. Every verify step re-reads from the GitHub API before making decisions
