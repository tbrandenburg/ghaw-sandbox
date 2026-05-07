# GHAW — GitHub Agentic Workflow

[![Version](https://img.shields.io/github/v/tag/tbrandenburg/ghaw-sandbox?label=version&sort=semver)](https://github.com/tbrandenburg/ghaw-sandbox/releases)

> GHAW is a GitHub Actions-based agentic workflow that autonomously manages your issue backlog — from planning and implementation through review and merge — using AI agents that run on every schedule trigger.

---

## Table of Contents

- [Quick Start](#quick-start)
- [Requirements](#requirements)
- [How It Works](#how-it-works)
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

GHAW manages issues through an automated lifecycle:

```text
open → ready → in-progress → reviewed → closed
```

Each issue moves through these states as AI agents analyse, implement, review, and merge work. Agents are triggered on schedules (hourly or daily) and respond to specific events like new issues or failing CI.

---

## Agents

GHAW includes eight specialised AI agents, each responsible for a distinct phase of the development cycle:

| Agent | Trigger | What It Does |
| --- | --- | --- |
| **Planner** | New issue opened | Analyses the issue, creates a step-by-step implementation plan, and assigns severity, priority, and complexity labels |
| **Groomer** | Daily at 06:00 UTC | Reviews open issues for clarity, feasibility, and scope — asks for missing details, splits large issues, or marks out-of-scope work |
| **Sprint Planner** | Daily at 07:00 UTC | Ranks ready issues using WSJF (Weighted Shortest Job First) scoring and assigns the highest-value issues to in-progress |
| **Dev** | Hourly | Picks up in-progress issues, explores the codebase, writes the implementation, commits changes, and opens a pull request |
| **CI/CD** | Hourly | Monitors open PRs for failing CI — diagnoses errors and pushes fixes automatically |
| **Review** | Hourly | Reviews open PRs against the Definition of Done and acceptance criteria, leaving feedback or approving when ready |
| **Integrator** | Hourly | Merges approved PRs (with green CI) via squash merge — no OpenCode interaction needed |
| **Demo** | Daily at 20:00 UTC | Runs end-to-end test analysis, creates follow-up issues from failures, and posts a daily sprint summary |

---

## Architecture

Every agent follows the same three-phase execution pattern:

```text
Bash Preparation  →  OpenCode Run  →  Bash Verification
```

1. **Bash Preparation** — Deterministic `gh` CLI calls collect context (issue body, comments, affected files) and build the agent-specific prompt.
2. **OpenCode Run** — The LLM performs all reasoning: analysing the issue, deciding on actions, and executing them via the `gh` CLI.
3. **Bash Verification** — Post-run checks confirm the expected GitHub state (labels applied, PR created, etc.) was achieved.

This design keeps reasoning in the LLM layer while using shell scripts for reliable, deterministic GitHub API interactions.

---

## Label Taxonomy

All labels follow the `key/value` namespace pattern to avoid conflicts:

| Namespace | Values |
| --- | --- |
| `severity/` | critical, high, medium, low, trivial |
| `priority/` | critical, high, medium, low, trivial |
| `complexity/` | xl, l, m, s, xs |
| `confidence/` | certain, high, medium, low, none |
| `status/` | ready, in-progress, reviewed, blocked, defocus |
| `type/` | bug, feature, arch, feedback, chore, docs, refactor |

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
