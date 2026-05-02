# AGENTS.md

> Operational guidance for AI agents working on this repository.
> Do NOT duplicate README content — this file covers what agents commonly get wrong.

## Project Overview

GHAW is a **shell scripts + GitHub Actions + YAML configs** project — not a typical app codebase.
Agents run via OpenCode in GitHub Actions workflows.

## Commands

| Command | Purpose |
| --- | --- |
| `make -f Makefile.ghaw install` | Install GHAW files into current repo |
| `make -f Makefile.ghaw setup-labels` | Create required issue labels |
| `make -f Makefile.ghaw publish` | Bump version, tag, and create release |
| `make -f Makefile.ghaw initial-release` | Create release for current version (no bump) |
| `make -f Makefile.ghaw info` | Show version and config |
| `actionlint .github/workflows/*.yml` | Validate workflow syntax |
| `yamllint .github/**/*.yml` | Validate YAML files |

## Project Structure

```
.github/workflows/    → Agent workflows (Bash Prep → OpenCode Run → Bash Verify)
.github/config/       → Runtime config (config.yml)
.opencode/agents/     → Agent definitions (planner.md, dev.md, etc.)
.opencode/commands/   → OpenCode command prompts
.ghaw-version         → Current project version
```

## Git Workflow

- **Branch naming:** `feature/issue-{N}`, `fix/issue-{N}`, `chore/issue-{N}`, `docs/issue-{N}`, `refactor/issue-{N}`
- **Commits:** conventional commits — `type(scope): description (closes #N)`
- **PRs:** use `gh pr create --head {branch} --base main`
- **Always** check `git status` and `git diff` before committing

## Label Taxonomy

Follow the `key:value` namespace pattern. See README.md#label-taxonomy for the full table.
Key namespaces: `severity:`, `priority:`, `complexity:`, `confidence:`, `type:`

## Code Style

- **YAML:** 2-space indent, validated with `yamllint`
- **Shell scripts:** always start with `set -euo pipefail`
- **Markdown:** follow `.markdownlint.json` rules

## Boundaries — Never Do

- **Never** commit secrets, API keys, or `.env` files
- **Never** modify `.github/workflows/` without understanding the three-phase pattern
- **Never** edit `node_modules/` — it is managed by package.json
- **Always** use `make -f Makefile.ghaw` targets for label/config changes — not raw `gh` calls
- **Always** follow the existing `.PHONY` and define patterns when adding Makefile targets
