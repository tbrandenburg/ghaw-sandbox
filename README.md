# GHAW — GitHub Agentic Workflow

[![Version](https://img.shields.io/github/v/tag/tbrandenburg/ghaw-sandbox?label=version&sort=semver)](https://github.com/tbrandenburg/ghaw-sandbox/releases)

> GHAW is a GitHub Actions-based agentic workflow that autonomously manages your issue backlog — from planning and implementation through review and merge — using AI agents that run on every schedule trigger.

---

## Table of Contents

- [Quick Start](#quick-start)
- [Requirements](#requirements)
- [How It Works](#how-it-works)
- [State Machine](#state-machine)
- [Agents](#agents)
- [Architecture](#architecture)
- [Label Taxonomy](#label-taxonomy)
- [Makefile.ghaw Targets](#makefileghaw-targets)

---

## Quick Start

Get GHAW running in your repository in under 5 minutes:

### 1. Install GHAW

Run the installer from the root of your repository:

```bash
make -f Makefile.ghaw install
```

### 2. Create Required Labels

GHAW uses a structured label system for issue tracking. Create them all at once:

```bash
make -f Makefile.ghaw setup-labels
```

### 3. Configure Your Project

Edit `.github/config/config.yml` with your settings:

```yaml
max_wip: 1
model: opencode/big-pickle
po_handle: "@your-github-handle"
e2e_command: "npm run test:e2e"   # optional — remove if not applicable
```

### 4. Enable GitHub Actions Permissions

Navigate to your repository **Settings → Actions → General** and enable:

- **Read and write permissions** (workflow permissions)
- **Allow GitHub Actions to create and approve pull requests**

### 5. Create Your First Issue

Open a GitHub issue — the Planner Agent will automatically analyse it and produce an implementation plan within minutes.

---

## Requirements

Before installing and running GHAW, ensure the following are in place:

### Before Installing

| Requirement | Purpose |
| --- | --- |
| **`gh` CLI** installed and authenticated (`gh auth login`) | Required by Makefile.ghaw for label setup and repo detection |
| **`jq`** installed | JSON processing in the Makefile |
| **`python3`** installed | URL encoding and label management in the Makefile |

> **Note:** No external API keys or secrets are required — the model (`opencode/big-pickle`) runs on the free tier.

### Runtime

| Requirement | Details |
| --- | --- |
| **GitHub repository** with Actions enabled | All agents run as GitHub Actions workflows |
| **`GITHUB_TOKEN`** with read/write permissions | Provided automatically by GitHub Actions — enable under Settings → Actions → General |

---

## How It Works

GHAW manages issues through an automated lifecycle driven by state labels and AI agents. Each issue progresses through a well-defined state machine. Agents are triggered on schedules (hourly or every 6 hours) and react to specific GitHub events.

Every agent follows the same three-phase execution pattern:

```text
Bash Preparation  →  OpenCode Run  →  Bash Verification
```

1. **Bash Preparation** — Deterministic `gh` CLI calls collect context and build the agent prompt. Guards reject issues in unexpected states before the agent runs.
2. **OpenCode Run** — The LLM reasons, makes decisions, and acts via `gh` CLI.
3. **Bash Verification** — Post-run checks confirm expected GitHub state was achieved (PR created, plan comment present, etc.).

A dedicated background workflow (`core-state-heal.yml`) enforces the mutual-exclusion invariant on state labels: whenever any label is added to an issue, it fires instantly and removes any conflicting state labels — keeping only the one just set.

---

## State Machine

State labels are **mutually exclusive**. An issue carries exactly one state label at any time. The `core-state-heal.yml` workflow enforces this on every label-add event.

```mermaid
stateDiagram-v2
    [*] --> open : Issue opened\n(Planner creates plan)
    open --> ready : Groomer passes all checks\n(confidence ≠ low, complexity ≠ high)
    ready --> open : Sprint Planner: no plan found\n(demoted, Planner retriggered)
    ready --> in-progress : Sprint Planner: WSJF top-N\nwithin WIP limit
    in-progress --> reviewed : Review Agent:\n✅ Technical review passed
    in-progress --> blocked : Dev Agent: blocker found\nIntegrator: merge deferred
    reviewed --> blocked : Integrator: merge deferred\n(conflict detected)
    blocked --> ready : Sprint Planner:\nblocker resolved
    reviewed --> [*] : Integrator merges PR\n(GitHub closes issue)
    open --> defocus : Groomer: out of scope\nor hard blocker
    ready --> defocus : Groomer: out of scope
    in-progress --> defocus : Groomer: out of scope
    blocked --> defocus : Groomer: hard blocker
```

### State Transition Table

| Input State | Agent / Workflow | Output State | Output Artefact |
| --- | --- | --- | --- |
| *(new issue)* | **Planner** | `open` | `<!-- PLAN -->` comment; `open` label set |
| `open` | **Groomer** | `ready` | Labels updated; `ready` set, `open` removed |
| `open` | **Groomer** | `defocus` | Labels updated; issue closed |
| `ready` | **Sprint Planner** (gate) | `open` | Issue demoted — no plan found |
| `ready` | **Sprint Planner** | `in-progress` | `in-progress` set, `ready` removed |
| `in-progress` | **Dev** | PR opened | Branch, commits, pull request (`Closes #N`) |
| `in-progress` | **Dev** (blocker) | `blocked` | `blocked` set, `in-progress` removed; comment |
| `in-progress` | **Review** | `reviewed` | `reviewed` set, `in-progress` removed |
| `reviewed` | **Integrator** | *(closed)* | Merge commit on `main`; `reviewed` removed |
| `reviewed` | **Integrator** (deferred) | `blocked` | `blocked` set, `reviewed` removed; `⏸️ Merge deferred` comment |
| `blocked` | **Sprint Planner** | `ready` | `blocked` removed, `ready` restored |
| any | **State Healer** | last-set state | Conflicting state labels removed |

---

## Agents

GHAW includes eight specialised AI agents, each responsible for a distinct phase of the development cycle:

| Agent | Trigger | Schedule | What It Does |
| --- | --- | --- | --- |
| **Planner** | `issues: opened`, schedule, `workflow_dispatch` | Every 6h at :00 | Analyses issues, creates `<!-- PLAN -->` implementation plans, sets `open` label |
| **Groomer** | Schedule, `issues: unlabeled` (on `confidence/low` removal) | Every 6h at :00 | Reviews `open` issues for clarity, feasibility, scope — promotes to `ready` or marks `defocus` |
| **Sprint Planner** | Schedule, `workflow_dispatch` | Every 6h at :01 | WSJF-ranks `ready` issues, assigns top-N to `in-progress` within `MAX_WIP` limit |
| **Dev** | Schedule, `workflow_dispatch` | Every hour | Implements `in-progress` issues — creates branch, writes code, opens PR with `Closes #N` |
| **CI/CD** | Schedule, `workflow_dispatch` | Every hour | Detects failing CI on open PRs, diagnoses root cause, pushes fix commits |
| **Review** | Schedule, `workflow_dispatch` | Every hour | Reviews PRs against Definition of Done — posts `✅ Technical review passed` or `❌ Changes required` |
| **Integrator** | Schedule, `workflow_dispatch` | Every hour | Merges approved, CI-green PRs in safe WSJF-ordered sequence using merge-commit strategy |
| **Demo** | Schedule, `workflow_dispatch` | Every 6h at :05 | Analyses closed issues and E2E results, creates follow-up issues, posts sprint summary |
| **State Healer** | `issues: labeled` (any state label) | Event-driven | Instantly removes conflicting state labels — keeps the one just added |

---

## Architecture

### Workflow Overview

```text
.github/workflows/
├── core-opencode-run.yml     # Reusable: installs OpenCode, runs agent, uploads results
├── core-state-heal.yml       # Event-driven: enforces state label mutual exclusion
├── ghaw-planner.yml          # Planner Agent
├── ghaw-backlog-grooming.yml # Groomer Agent
├── ghaw-sprint-planning.yml  # Sprint Planner Agent
├── ghaw-dev.yml              # Dev Agent
├── ghaw-cicd.yml             # CI/CD Agent
├── ghaw-review.yml           # Review Agent
├── ghaw-integrator.yml       # Integrator Agent
├── ghaw-demo.yml             # Demo Agent
└── ci.yml                    # Repo CI (lint + BATS tests)
```

### Agent Definitions and Commands

```text
.opencode/agent/              # Agent system prompts
├── planner.md
├── groomer.md
├── dev.md
├── review.md
├── integrator.md
└── demo.md

.opencode/commands/           # Per-task command prompts
├── ghaw-plan-issue.md
├── ghaw-groom-issue.md
├── ghaw-sprint-plan.md
├── ghaw-dev-issue.md
├── ghaw-review.md
├── ghaw-integrate.md
├── ghaw-resolve-ci-errors.md
└── ghaw-demo.md
```

### Key Design Principles

- **Agents signal via comments, workflows apply labels.** Commands explicitly instruct agents not to set state labels directly — the verify step detects signals (`✅ Technical review passed`, `⏸️ Merge deferred`) and applies labels deterministically.
- **State healer runs independently.** No agent workflow calls the healer — it fires reactively on every `issues: labeled` event, keeping state consistent without coupling.
- **Guards before, verification after.** Prep steps filter out issues in wrong states before the agent runs. Verify steps confirm expected outcomes after.

---

## Label Taxonomy

All labels follow the `key/value` namespace pattern to avoid conflicts:

| Namespace | Values | Role |
| --- | --- | --- |
| *(state)* | `open`, `ready`, `in-progress`, `reviewed`, `blocked`, `defocus` | **Mutually exclusive state machine** |
| `severity/` | `critical`, `high`, `medium`, `low`, `trivial` | WSJF scoring input |
| `priority/` | `critical`, `high`, `medium`, `low`, `trivial` | WSJF scoring input |
| `complexity/` | `xl`, `l`, `m`, `s`, `xs` | WSJF scoring input |
| `confidence/` | `certain`, `high`, `medium`, `low`, `none` | Groomer gate — `confidence/low` blocks auto-promotion to `ready` |
| `type/` | `bug`, `feature`, `arch`, `coordination`, `feedback`, `chore`, `docs`, `refactor` | Classification |

Labels are created by running `make -f Makefile.ghaw setup-labels`. Without them, `gh issue edit --add-label` fails silently.

---

## Makefile.ghaw Targets

| Target | Description |
| --- | --- |
| `install` | Install all GHAW files into the current repo (skips existing) |
| `install-force` | Install and overwrite all existing files |
| `install-dry` | Preview what would be installed — no changes made |
| `setup-labels` | Create all required labels via `gh` CLI |
| `clean` | Remove all installed GHAW files |
| `info` | Show installed version and current config |
| `publish` | Bump version, create a git tag, and publish a GitHub release |
