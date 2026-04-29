# GHAW — GitHub Agentic Workflow

> **Autonomous Scrum** — 8 AI agents run your issue backlog end-to-end on GitHub Actions.

## What It Does

GHAW implements a fully autonomous development cycle on top of GitHub Issues and Pull Requests:

```
open → ready → in-progress → reviewed → closed
```

| Agent | Trigger | Job |
|---|---|---|
| **Planner** | Issue opened | Creates implementation plan + sets severity/priority/complexity labels |
| **Groomer** | Daily 06:00 UTC | Checks clarity, feasibility, defocus; splits large issues |
| **Sprint Planner** | Daily 07:00 UTC | WSJF ranking; assigns top N to in-progress |
| **Dev** | Hourly | Implements issue, commits, opens PR |
| **CI/CD** | Hourly | Fixes failing CI on open PRs |
| **Review** | Hourly | Reviews PR against DoD + acceptance criteria |
| **Integrator** | Hourly | Squash-merges approved PRs (no OpenCode) |
| **Demo** | Daily 20:00 UTC | E2E analysis, new issues, sprint summary |

---

## Quick Start

### 1. Install GHAW into your repo

```bash
make -f Makefile.ghaw install
```

### 2. Create required labels

```bash
make -f Makefile.ghaw setup-labels
```

### 3. Enable required GitHub Actions permissions

Go to: `Settings → Actions → General`

- ✅ **Read and write permissions** (workflow permissions)
- ✅ **Allow GitHub Actions to create and approve pull requests**

### 4. Configure

Edit `.github/config/config.yml`:

```yaml
max_wip: 1
model: opencode/big-pickle
po_handle: "@your-github-handle"
e2e_command: "npm run test:e2e"   # optional
```

### 5. Create your first issue

Open an issue — the Planner Agent will create an implementation plan within minutes.

---

## Requirements

- GitHub repository with Actions enabled
- `GITHUB_TOKEN` with read/write permissions (automatic in GitHub Actions)
- No external secrets required — `opencode/big-pickle` is free-tier

---

## Label Taxonomy

All labels follow the `key:value` namespace pattern:

| Namespace | Values |
|---|---|
| `severity:` | critical, high, medium, low, trivial |
| `priority:` | critical, high, medium, low, trivial |
| `complexity:` | xl, l, m, s, xs |
| `confidence:` | certain, high, medium, low, none |
| `status:` | ready, in-progress, reviewed, blocked, defocus |
| `type:` | bug, feature, arch, feedback, chore, docs, refactor |

Labels are created by `make setup-labels`. Without them, `gh issue edit --add-label` fails silently.

---

## Architecture

All agents follow the same three-phase pattern:

```
Bash Preparation  →  OpenCode Run  →  Bash Verification
```

- **Bash Preparation:** Deterministic `gh` CLI calls — collects context, builds prompt
- **OpenCode:** All LLM reasoning — analyses, decides, acts via `gh` CLI directly
- **Bash Verification:** Confirms expected GitHub state after OpenCode ran

See [GitHubDevStates](https://github.com/tbrandenburg/eddy) for full architecture documentation.

---

## Makefile.ghaw Targets

| Target | Description |
|---|---|
| `install` | Install all files (skip existing) |
| `install-force` | Overwrite all existing files |
| `install-dry` | Preview only — no changes |
| `setup-labels` | Create all required labels via `gh` CLI |
| `clean` | Remove all installed files |
| `info` | Show installed version + config |
| `publish` | Bump version + tag + GitHub release |
