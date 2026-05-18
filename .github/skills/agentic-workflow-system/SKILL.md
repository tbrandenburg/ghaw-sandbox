---
name: agentic-workflow-system
description: >
  Set up or extend a GitHub Actions–based agentic workflow system (GHAW — GitHub Agentic
  Workflow). Use when: creating a new autonomous issue-driven development system from scratch;
  adding new states, agents, or transitions to an existing system; designing state machines for
  GitHub issues; implementing OpenCode-based agents in GitHub Actions. Walks through full
  lifecycle: discovery interview → edge-case hardening → planning → implementation → validation.
  Triggered by: "set up agentic workflow", "create GHAW", "add agent to workflow",
  "extend state machine", "new state", "new agent".
argument-hint: 'Brief description of your project or the change you want to make'
---

# Agentic Workflow System

This skill guides you through designing, implementing, and validating a GitHub Actions–based
agentic workflow system from scratch, or extending an existing one. It follows the architecture
and patterns described in the authoritative reference:
[`references/AGENTIC_WORKFLOW_SYSTEM.md`](./references/AGENTIC_WORKFLOW_SYSTEM.md)

**Always read that reference first** — it defines the architecture, patterns, and invariants
your implementation must follow word-by-word.

---

## Overview: Six Phases

```
Phase 1 — Discovery        → interview user, understand system requirements
Phase 2 — Edge-Case Hardening → challenge design, expose gaps, iterate to water-tight
Phase 3 — Planning         → produce a concrete, minimal implementation plan
Phase 4 — Plan Review      → validate plan against AGENTIC_WORKFLOW_SYSTEM.md invariants
Phase 5 — Implementation   → create all files deterministically
Phase 6 — Validation       → run structural and live checks
```

---

## Phase 1: Discovery Interview

Read [`references/AGENTIC_WORKFLOW_SYSTEM.md`](./references/AGENTIC_WORKFLOW_SYSTEM.md)
before proceeding — it is your authoritative source for all architecture, naming conventions,
file formats, and invariants.

Use `vscode_askQuestions` to collect the following. Ask in one batched call; group logically.

### Questions to Ask

**Group A — System Identity**
1. **Goal, Purpose and Scope** — What is this system trying to do autonomously? What human
   work is being replaced or augmented? What repository does it operate on?

**Group B — State Machine Design**
2. **Issue States** — List all states an issue can be in (e.g. `open`, `ready`,
   `in-progress`, `reviewed`, `blocked`, `done`). Which is the entry state (when an issue is
   created)? Which is the terminal state?
3. **State Transitions** — For each state, what are the possible next states? What triggers
   each transition (schedule, label event, PR event)?
4. **Agent per State** — For each non-terminal state, which agent owns it and what is its
   core task in one sentence?

**Group C — Work Items and Types**
5. **Issue Types** — What types of work items exist? (e.g. `feature`, `bug`, `chore`,
   `spike`, `docs`). Are there size or priority dimensions that affect scheduling?
6. **PR Handling** — How are PRs linked to issues? Who approves merges (human PO, auto,
   CODEOWNERS)? What triggers a PR to be merged (label, approval, CI green)?

**Group D — Special Concerns**
7. **Special Events / Transitions / Stateless Agents** — Are there any event-driven
   transitions not tied to a state (e.g. CI failure, stale PR, periodic reporting)? Any
   stateless agents that operate opportunistically?
8. **Special Needs** — Are there any non-functional requirements?
   - Traceability / audit trail
   - Reporting / dashboards
   - Monitoring / alerting on stuck issues
   - Security constraints (token scopes, protected branches, secret scanning)
   - Data privacy (PII in issues, access controls)
   - Compliance gates (mandatory approvals, regulated change)

**Group E — Quality and Bootstrap**
9. **Testing Needs (beyond linting)** — Apart from `yamllint` and `actionlint`, are there
   behavioral tests needed? BATS tests for workflow logic? Contract tests for agent signals?
10. **Bootstrap Needs (beyond states + labels)** — Apart from creating state labels and
    state workflows, what else needs to be installed into the target repo? (e.g.
    `DEFINITION_OF_DONE.md`, custom runner requirements, secrets, branch protection rules,
    specific GitHub settings)

---

## Phase 2: Edge-Case Hardening

After collecting answers from Phase 1, **challenge the design**. For each of the following
edge cases, verify the state machine handles it — or record it as a gap to resolve before
planning:

### State Machine Invariants (must all hold)
- [ ] Every issue carries **exactly one** state label at all times
      → `core-state-heal.yml` lists ALL state labels
- [ ] Every state has **exactly one** owning workflow that transitions issues *out* of it
      → No two workflows add the same "next state" label for the same "current state"
- [ ] The entry state is applied when an issue is created (either by default label automation
      or by a bootstrap step)
- [ ] Every state that is not terminal has an agent and a verify step
- [ ] `blocked` is reachable from every state (verify step always falls back to it)

### Transition Completeness
- [ ] What happens if an agent produces no output (timeout, crash, empty response)?
      → Verify step must set `blocked` and exit 1
- [ ] What happens if an issue is re-labeled by a human to an earlier state (manual retry)?
      → `core-state-heal.yml` removes conflicting labels; the owning workflow picks it up
- [ ] What happens if two workflow runs fire simultaneously for the same issue?
      → Entry condition check in `prepare` prevents double-processing (idempotency)
- [ ] What happens if the issue reaches terminal state but the PR is not merged?
      → Integrator agent or a post-merge verify must close the issue / remove labels

### Label Namespace Hygiene
- [ ] State labels have **no namespace prefix** (`open`, `in-progress`, not `state/open`)
- [ ] Metadata labels use namespace prefix (`type/bug`, `priority/high`, `size/m`)
- [ ] No metadata label name collides with any state label name

### PR Lifecycle Gaps
- [ ] What triggers the review agent? (PR opened, schedule, label on linked issue?)
- [ ] What happens if CI fails after a PR is created? (CI/CD agent, dev agent retry?)
- [ ] What happens if review requests changes and dev is slow to push? (schedule picks up)
- [ ] What happens if a merge conflict arises after a PR is approved?

### Verify Signal Coverage
- [ ] For every signal an agent can post (`<!-- MARKER -->`), the verify step checks for it
- [ ] Every success signal has a corresponding failure path (what if the marker is absent?)
- [ ] Signal markers are HTML comments so they are invisible in the GitHub UI

### Idempotency
- [ ] Running any workflow twice on the same issue produces the same state (no duplicates)
- [ ] `setup-labels` and `install` in Makefile.ghaw are safe to re-run

**For each gap found**: iterate with the user using `vscode_askQuestions` until the design
is gap-free. Do not proceed to Phase 3 until all gaps are resolved or explicitly accepted.

---

## Phase 3: Planning

Produce a concrete, minimal implementation plan. Focus on simplicity — add nothing that was
not asked for or that does not directly serve a stated requirement.

### Plan Format

Output the plan as a structured list:

```
## Implementation Plan

### New Files to Create
| File | Purpose |
|------|---------|
| .github/workflows/core-state-heal.yml | State exclusivity enforcer (required in every repo) |
| .github/workflows/core-opencode-run.yml | Reusable LLM runner |
| .github/workflows/sm-[state].yml | [One row per state] |
| .github/config/config.yml | Model and WIP config |
| .opencode/agent/[name].md | [One row per agent] |
| .opencode/commands/[name].md | [One row per command] |

### Existing Files to Modify (extension mode only)
| File | Change |
|------|--------|
| .github/workflows/core-state-heal.yml | Add [new-state] to state list |
| [upstream verify step] | Change --add-label to [new-state] |

### Labels to Create
| Label | Color | Description |
|-------|-------|-------------|
| [state label] | [hex] | [description] |
| [metadata label] | [hex] | [description] |

### Manual Post-Install Steps
1. GitHub Settings → Actions → Workflow permissions → Read and write
2. GitHub Settings → Actions → Allow GitHub Actions to create and approve pull requests
3. [Any secrets to configure]
4. [Any branch protection rules]

### Deferred (out of scope for this run)
- [anything explicitly decided not to implement now]
```

---

## Phase 4: Plan Review

Before implementing, validate the plan against the following checklist. **Do not implement
if any MUST item is violated.**

### Structure Checks (MUST)
- [ ] `core-state-heal.yml` includes ALL state labels in both `fromJSON([...])` and
      `STATE_LABELS` and the `--argjson states` passed to `jq` (three places, all in sync)
- [ ] Every `sm-[state].yml` has exactly three jobs: `prepare`, `run`, `verify`
- [ ] Every `run` job uses `uses: ./.github/workflows/core-opencode-run.yml`
- [ ] Every `run` and `verify` job is gated on `needs.prepare.outputs.has_candidates == 'true'`
- [ ] Every `verify` job declares `needs: [prepare, run]`
- [ ] Every `verify` job re-reads from the GitHub API (not from in-memory variables)
- [ ] Every `verify` job falls back to `blocked` if the expected signal is absent
- [ ] Every `prepare` job has an entry condition that prevents double-processing
- [ ] Every `prepare` job reads `model` from `.github/config/config.yml` via `yq`
- [ ] Every agent file has `description:` in frontmatter
- [ ] Every command file has `description:` and `argument-hint:` in frontmatter
- [ ] No agent calls `gh issue edit` for state labels — only verify steps do
- [ ] `github.event.label.name` guard is present in every event-triggered `prepare` job

### Naming Checks (MUST)
- [ ] Core workflows named `core-[name].yml`
- [ ] State workflows named `sm-[state].yml`
- [ ] Stateless agent workflows named `agent-[name].yml`
- [ ] Agent persona files in `.opencode/agent/[name].md`
- [ ] Command instruction files in `.opencode/commands/[name].md`

### Simplicity Checks (SHOULD)
- [ ] No new state is added without a documented reason
- [ ] No new agent is added if an existing agent can be extended
- [ ] No new label is added if an existing label can be reused

---

## Phase 5: Implementation

Work through the plan file by file in this order:

### Step 1: Core Infrastructure

**If creating from scratch:**

1. Copy `core-opencode-run.yml` verbatim from
   [`assets/examples/core-opencode-run.yml`](./assets/examples/core-opencode-run.yml)
   to `.github/workflows/core-opencode-run.yml` — this file requires no adaptation.

2. Create `core-state-heal.yml` using
   [`assets/examples/core-state-heal.yml`](./assets/examples/core-state-heal.yml)
   as the template, replacing the state label list with the user's states. Remember to
   update the three places: `fromJSON([...])`, `STATE_LABELS`, and `--argjson states`.

3. Create `.github/config/config.yml`:
   ```yaml
   model: opencode/big-pickle   # or user-specified model
   max_wip: 3                   # or user-specified WIP limit
   ```

**If extending (new state only):**

Update `core-state-heal.yml` — add the new state in all three places.

---

### Step 2: State Workflows (`sm-[state].yml`)

For each state workflow, use
[`assets/examples/sm-workflow-template.yml`](./assets/examples/sm-workflow-template.yml)
as the starting template and fill in:

- `[STATE-LABEL]` — the state label this workflow owns
- `[AGENT-NAME]` — the OpenCode agent to use
- `[COMMAND-NAME]` — the OpenCode command to use
- `[NEXT-STATE]` — the label to apply on success
- `[SIGNAL-MARKER]` — the HTML comment the agent posts on success
- `[FAILURE-MARKER]` — the HTML comment the agent posts on failure (optional)
- Cron schedule appropriate to the workflow's frequency

See the full GHAW example workflows in:
- [`assets/examples/workflows/ghaw-backlog-grooming.yml`](./assets/examples/workflows/ghaw-backlog-grooming.yml)
- [`assets/examples/workflows/ghaw-planner.yml`](./assets/examples/workflows/ghaw-planner.yml)
- [`assets/examples/workflows/ghaw-dev.yml`](./assets/examples/workflows/ghaw-dev.yml)
- [`assets/examples/workflows/ghaw-review.yml`](./assets/examples/workflows/ghaw-review.yml)
- [`assets/examples/workflows/ghaw-sprint-planning.yml`](./assets/examples/workflows/ghaw-sprint-planning.yml)
- [`assets/examples/workflows/ghaw-integrator.yml`](./assets/examples/workflows/ghaw-integrator.yml)

---

### Step 3: Stateless Agent Workflows (`agent-[name].yml`)

For stateless agents (no required input state), use
[`assets/examples/agent-workflow-template.yml`](./assets/examples/agent-workflow-template.yml)
as the template. The `verify` job is optional for stateless agents.

---

### Step 4: Agent Persona Files (`.opencode/agent/[name].md`)

For each agent, create a persona file following the format in
[`assets/examples/agents/`](./assets/examples/agents/).

Required elements:
```markdown
---
description: One-line summary of this agent's role
---

You are a [role] agent. Your job is to [primary responsibility].

[Behavioural principles]

**Critical output contract**: [Exact signal comment format the verify step depends on]

Act directly via gh CLI and git. No structured return value needed.
```

If the verify step checks for a signal comment, document:
- The exact HTML comment marker (e.g. `<!-- PLAN -->`)
- Where it must appear (first line of comment body)
- Under what condition it must be posted (success vs. failure paths)

---

### Step 5: Command Instruction Files (`.opencode/commands/[name].md`)

For each command, create an instruction file following the format in
[`assets/examples/commands/`](./assets/examples/commands/).

Required elements:
```markdown
---
description: One-line description of what this command does
argument-hint: <description of the argument>
---

# [Command Title]

**Input**: $ARGUMENTS ([what the argument contains])

## Step 1: [First action]
...

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

Command signals must exactly match what the verify step in the corresponding workflow checks.

---

### Step 6: Makefile.ghaw Labels (bootstrap mode only)

If implementing from scratch, add the new labels to the `setup-labels` target in
`Makefile.ghaw`, or create a standalone bootstrap script that calls:

```bash
gh api -X POST "repos/$REPO/labels" \
  --field name="[label-name]" \
  --field color="[hex-without-#]" \
  --field description="[description]"
```

---

### Step 7: DEFINITION_OF_DONE.md (if required)

If the review agent references `DEFINITION_OF_DONE.md`, create it in the repo root.
Standard checklist items:
- Code review by peer completed
- All automated tests passing
- Code quality standards met (linting, formatting)
- Documentation updated where relevant
- Security checks passed
- Production-ready (no debug code, no TODO-for-prod)

---

## Phase 6: Validation

After creating all files, run the structural validation checks from
[`references/AGENTIC_WORKFLOW_SYSTEM.md`](./references/AGENTIC_WORKFLOW_SYSTEM.md)
(Validation Rules section).

### Structural Checks
```bash
# Core files must exist
[ -f .github/workflows/core-opencode-run.yml ] || echo "FAIL: missing core-opencode-run.yml"
[ -f .github/workflows/core-state-heal.yml ]   || echo "FAIL: missing core-state-heal.yml"
[ -f .github/config/config.yml ]               || echo "FAIL: missing config.yml"

# Config must have required keys
yq '.model'   .github/config/config.yml | grep -v '^null$' || echo "FAIL: config missing model"
yq '.max_wip' .github/config/config.yml | grep -E '^[0-9]+$' || echo "FAIL: config missing max_wip"

# Every sm- workflow must have all three phases
for f in .github/workflows/sm-*.yml; do
  grep -q "^  prepare:" "$f" || echo "FAIL: $f missing prepare job"
  grep -q "^  run:"     "$f" || echo "FAIL: $f missing run job"
  grep -q "^  verify:"  "$f" || echo "FAIL: $f missing verify job"
done

# Every sm- run job must call core-opencode-run.yml
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

### Agent and Command File Checks
```bash
for f in .opencode/agent/*.md; do
  grep -q "^description:" "$f" || echo "FAIL: $f missing description in frontmatter"
done

for f in .opencode/commands/*.md; do
  grep -q "^description:"   "$f" || echo "FAIL: $f missing description in frontmatter"
  grep -q "^argument-hint:" "$f" || echo "FAIL: $f missing argument-hint in frontmatter"
done
```

### Lint Checks (if tools available)
```bash
# yamllint
yamllint .github/workflows/*.yml .github/config/config.yml

# actionlint
actionlint -shellcheck= .github/workflows/*.yml

# markdownlint (agent and command files)
markdownlint .opencode/agent/*.md .opencode/commands/*.md
```

### State Healer Sync Check
```bash
# All three places in core-state-heal.yml must have the same state list
STATES_FROMJSON=$(grep -o '"[a-z-]*"' .github/workflows/core-state-heal.yml \
  | grep -v 'GITHUB_STEP_SUMMARY\|REPO\|NUMBER\|ADDED\|LABEL\|CURRENT\|IS_SET' \
  | sort -u)
echo "State labels found: $STATES_FROMJSON"
echo "Verify these appear in ALL THREE locations: fromJSON, STATE_LABELS var, --argjson states"
```

### Signal Coverage Check
```bash
# For each command file, verify the signal marker appears in the corresponding sm- workflow
for CMD in .opencode/commands/*.md; do
  SIGNALS=$(grep -oP '<!-- [A-Z-]+ -->' "$CMD" | sort -u)
  for SIGNAL in $SIGNALS; do
    MARKER=$(echo "$SIGNAL" | tr -d '<>! -')
    grep -rl "$MARKER" .github/workflows/ || echo "WARNING: $SIGNAL from $CMD not found in any workflow"
  done
done
```

### Final Checklist
After all checks pass, confirm:
- [ ] No `FAIL:` lines in structural check output
- [ ] No lint errors in `yamllint` or `actionlint` output
- [ ] Every state label from the design appears in `core-state-heal.yml`
- [ ] Every signal in every command file has a corresponding check in its workflow's verify step
- [ ] Post-install manual steps documented and communicated to user

---

## Reference Files

| File | Description |
|------|-------------|
| [`references/AGENTIC_WORKFLOW_SYSTEM.md`](./references/AGENTIC_WORKFLOW_SYSTEM.md) | Authoritative architecture reference — read before every session |
| [`assets/examples/core-state-heal.yml`](./assets/examples/core-state-heal.yml) | Real `core-state-heal.yml` from GHAW sandbox |
| [`assets/examples/core-opencode-run.yml`](./assets/examples/core-opencode-run.yml) | Real `core-opencode-run.yml` from GHAW sandbox |
| [`assets/examples/sm-workflow-template.yml`](./assets/examples/sm-workflow-template.yml) | Generic three-phase sm- workflow template |
| [`assets/examples/agent-workflow-template.yml`](./assets/examples/agent-workflow-template.yml) | Generic stateless agent workflow template |
| [`assets/examples/workflows/`](./assets/examples/workflows/) | Full GHAW workflow examples |
| [`assets/examples/agents/`](./assets/examples/agents/) | Full GHAW agent persona examples |
| [`assets/examples/commands/`](./assets/examples/commands/) | Full GHAW command instruction examples |
| [`assets/examples/config.yml`](./assets/examples/config.yml) | Example config.yml |
