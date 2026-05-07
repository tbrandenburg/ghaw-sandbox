# Git History

> This document explains why the repository has a single-commit git history and
> what measures are in place to prevent future history loss.

## Background

The GHAW sandbox repository was bootstrapped from a template with an initial
commit containing the full codebase (~38 files). All development prior to PR #28
(April 29 – May 4, 2026) used a **squash-merge** strategy for pull requests.

### How the History Was Lost

The integrator agent was configured to merge pull requests using
`gh pr merge --squash`, which collapses all commits in a PR into a single commit
on `main`. Over 11 merged PRs (PRs #2 through #23), this resulted in:

- **Every line** in the repository attributed to the initial commit, making
  `git blame` and `git bisect` useless for historical changes.
- **Empty release notes** between tags (`v0.2.0`, `v0.2.1`) because the
  squash-merge strategy produced no intermediate commits between releases.
- **No audit trail** for how the 38-file initial codebase was assembled or what
  changes each PR introduced.

### Timeline

| Date | Event | Notes |
| --- | --- | --- |
| ~2026-04-29 | Repository bootstrap with initial commit | Full 38-file codebase committed as a single commit |
| 2026-04-29 | PR #2 – README.md | Merged via squash |
| 2026-04-30 | PRs #6, #7, #8, #10 – License, docs, README fixes | Merged via squash |
| 2026-05-01 | PR #15 – Dynamic version badge | Merged via squash |
| 2026-05-02 | PRs #17, #18, #19 – Makefile targets, AGENTS.md | Merged via squash |
| 2026-05-03 | PR #23 – Code block language specifier | Merged via squash |
| 2026-05-04 | **PR #28** – Switched to merge-commit strategy | Forward-looking fix; does not restore past history |
| 2026-05-04 | PR #29 – Pre-publish guard | Merged via squash (before #28 took effect) |
| 2026-05-05 | PRs #35, #36 – Lint fixes | Merged via merge-commit |
| 2026-05-06 | PR #41 – Hook installation via hooksPath | Merged via squash (bypassing #28 strategy) |
| 2026-05-06 | PRs #42, #43, #53 – BATS tests, release notes | Merged via merge-commit |

### What Was Lost

All commits from PRs #2 through #23 and PR #29 were squashed into the initial
commit. The exact commit messages, authorship details, and intermediate changes
from those PRs are permanently unrecoverable.

### What Was Preserved

PR metadata remains intact in GitHub's issue/PR tracker:

- PR bodies, comments, and review discussions
- Changed file listings (visible in the "Files changed" tab)
- Merge timestamps and author information

## Preventive Measures

Since PR #28, the integrator agent uses `gh pr merge --merge` (merge-commit
strategy). This ensures:

- All commits from a PR are preserved in `main` with their original authorship
  and messages.
- `git blame` and `git bisect` work correctly going forward.
- Release notes can be generated from meaningful commit history.

### Known Gap

PR #41 (hooks fix) was merged with `--squash` despite the #28 policy. This
happened because the integrator's merge command was invoked without the updated
strategy flag. Issue #32 tracks the observation that history is still a single
commit; this document serves as the concrete remediation.

## Related References

| Reference | Description |
| --- | --- |
| [#28](https://github.com/tbrandenburg/ghaw-sandbox/pull/28) | Switched integrator from squash-merge to merge-commit strategy |
| [#32](https://github.com/tbrandenburg/ghaw-sandbox/issues/32) | Observation that git history remains a single commit |
| [#50](https://github.com/tbrandenburg/ghaw-sandbox/issues/50) | Demo finding that history is permanently lost (this document's parent issue) |

## Recovery Options

The compressed history cannot be restored from git. The only options are:

1. **Git grafts / replace refs** – Technically possible but adds complexity
   without meaningful benefit for a sandbox repository.
2. **Documentation (this file)** – Captures what is known about the lost
   history with references to original PRs.
3. **Accept the loss** – Ensure all future PRs use merge-commit strategy
   (addressed by PR #28).

The project has chosen **option 2** as the most practical approach.
