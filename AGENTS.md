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
| `make -f Makefile.ghaw publish` | Bump version, tag, and create release (interactive) |
| `make -f Makefile.ghaw publish BUMP=patch` | Bump patch version non-interactively |
| `make -f Makefile.ghaw publish BUMP=minor` | Bump minor version non-interactively |
| `make -f Makefile.ghaw publish BUMP=major` | Bump major version non-interactively |
| `make -f Makefile.ghaw initial-release` | Create release for current version (no bump) |
| `make -f Makefile.ghaw info` | Show version and config |
| `make test` | Run linters and behavioral tests |
| `make test-bats` | Run BATS behavioral tests only |
| `actionlint .github/workflows/*.yml` | Validate workflow syntax |
| `yamllint .github/**/*.yml` | Validate YAML files |

## Project Structure

```text
.github/workflows/    → Agent workflows (Bash Prep → OpenCode Run → Bash Verify)
                        + core-opencode-run.yml (reusable executor)
                        + core-state-heal.yml (event-driven state label enforcer)
.github/config/       → Runtime config (config.yml)
.opencode/agent/      → Agent definitions (planner.md, dev.md, etc.)
.opencode/commands/   → OpenCode command prompts (one per task type)
tests/                → BATS behavioral tests
RELEASE_NOTES.md      → Release notes template (fill before publishing)
.ghaw-version         → Current project version
```

## Design Philosophy

Since handling issues autonomously is already complex enough, every design decision must favour simplicity and reduction over adding. New workflows, steps, and edge-case handlers must be justified — prefer reordering or extending existing code. The workflow must be human-understandable and easily describable in a single sentence per agent.

## State Machine — Critical Rules

State labels (`open`, `ready`, `in-progress`, `reviewed`, `blocked`, `defocus`) are **mutually exclusive**.
`core-state-heal.yml` fires on every `issues: labeled` event and removes any conflicting state labels automatically.

### What each agent MUST and MUST NOT do with state labels

| Agent | MUST add | MUST remove | MUST NOT touch labels |
| --- | --- | --- | --- |
| Planner (verify step) | `open` | `ready`, `in-progress`, `blocked`, `defocus`, `reviewed` | — |
| Groomer → ready | `ready` | `open`, `blocked`, `in-progress`, `defocus` | — |
| Groomer → defocus | `defocus` | `open`, `ready`, `in-progress`, `blocked` | — |
| Sprint Planner (gate) | `open` | `ready` | — |
| Sprint Planner (assign) | `in-progress` | `ready`, `open`, `blocked`, `reviewed` | — |
| Dev → blocked | `blocked` | `in-progress` | — |
| Review (verify step) | `reviewed` | `in-progress`, `ready`, `open`, `blocked` | — |
| Integrator (post-merge) | *(none)* | `reviewed` | — |
| Integrator (deferred) | `blocked` | `in-progress`, `ready`, `open`, `reviewed` | — |

**Agents signal intent via comments; workflows apply state labels deterministically.**
Command prompts explicitly say: do NOT call `gh issue edit` for state labels — the verify step handles it.
This separation keeps label transitions reliable and auditable.

## Git Workflow

- **Branch naming:** `feature/issue-{N}`, `fix/issue-{N}`, `chore/issue-{N}`, `docs/issue-{N}`, `refactor/issue-{N}`
- **Commits:** conventional commits — `type(scope): description (closes #N)`
- **PRs:** use `gh pr create --head {branch} --base main`
- **Always** check `git status` and `git diff` before committing

## Label Taxonomy

Follow the `key/value` namespace pattern. See README.md#label-taxonomy for the full table.
Key namespaces: `severity/`, `priority/`, `complexity/`, `confidence/`, `type/`

State labels (no namespace prefix): `open`, `ready`, `in-progress`, `reviewed`, `blocked`, `defocus`

## Three-Phase Workflow Pattern

Every agent workflow follows this structure — never skip or reorder phases:

```text
Bash Preparation  →  OpenCode Run (core-opencode-run.yml)  →  Bash Verification
```

- **Prep:** collect context via `gh` CLI, filter out issues in wrong states, build prompt
- **Run:** LLM reasons and acts; outputs signals via comments (not labels)
- **Verify:** detect signal comments, apply label transitions, assert expected outcomes

## Code Style

- **YAML:** 2-space indent, validated with `yamllint`
- **Shell scripts:** always start with `set -euo pipefail`
- **Markdown:** follow `.markdownlint.json` rules

## Boundaries — Never Do

- **Never** commit secrets, API keys, or `.env` files
- **Never** modify `.github/workflows/` without understanding the three-phase pattern
- **Never** edit `node_modules/` — it is managed by package.json
- **Never** apply state labels directly in agent code — use the comment signal pattern
- **Always** use `make -f Makefile.ghaw` targets for label/config changes — not raw `gh` calls
- **Always** follow the existing `.PHONY` and define patterns when adding Makefile targets

## Testing

Behavioral tests use **BATS** (Bash Automated Testing System) and live in `tests/`.

| Test File | Purpose |
| --- | --- |
| `tests/makefile.bats` | Makefile target behavior (exit codes, hook config) |
| `tests/prompts.bats` | Agent command/agent file frontmatter validation |
| `tests/workflows.bats` | Workflow YAML structural validation |

### Running Tests

```bash
make test        # lint + bats
make test-bats   # bats only
```

### Adding Tests

- Each `.bats` file contains `@test` blocks with assertions
- Use `setup()` to define shared variables (e.g., `REPO_ROOT`)
- Use `run <command>` to capture output and exit status
- Use `[ "$status" -eq 0 ]` for exit code assertions
- Use `[[ "$output" == *"pattern"* ]]` for output assertions
