"""
Pure data layer — no logic, no GitHub API.

Issue, PullRequest and Repository form the in-memory GitHub stand-in.
StateHealer enforces the one-state-label-at-a-time invariant and is wired
into Repository.add_label() so it fires automatically.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class Issue:
    number: int
    labels: set[str] = field(default_factory=set)
    comments: list[str] = field(default_factory=list)

    def has_label(self, label: str) -> bool:
        return label in self.labels

    def has_signal(self, marker: str) -> bool:
        """Return True if any comment contains the given marker string."""
        return any(marker in c for c in self.comments)

    def extract_value(self, pattern: str, default: float = 0.0) -> float:
        """Scan comments (newest first) for a regex capture group, return as float."""
        for comment in reversed(self.comments):
            m = re.search(pattern, comment)
            if m:
                return float(m.group(1))
        return default


@dataclass
class PullRequest:
    number: int
    body: str = ""
    head_ref: str = ""
    # APPROVED | CHANGES_REQUESTED | REVIEW_REQUIRED | ""
    review_decision: str = ""
    pr_comments: list[str] = field(default_factory=list)
    # open | merged | closed
    state: str = "open"
    # each entry: {"conclusion": "SUCCESS"|"FAILURE"|"TIMED_OUT"|...}
    status_checks: list[dict] = field(default_factory=list)

    def has_pr_signal(self, marker: str) -> bool:
        return any(marker in c for c in self.pr_comments)

    def links_issue(self, issue_num: int) -> bool:
        return bool(re.search(rf"closes\s+#{issue_num}", self.body, re.IGNORECASE))

    def ci_passing(self) -> bool:
        if not self.status_checks:
            return True
        return all(
            c.get("conclusion") not in ("FAILURE", "TIMED_OUT")
            for c in self.status_checks
        )


# ---------------------------------------------------------------------------
# State healer — enforces label exclusivity
# ---------------------------------------------------------------------------


class StateHealer:
    """
    Wired into Repository.add_label().  Whenever a state label is added,
    removes all *other* state labels from the same issue automatically.

    state_labels is injected so the healer is reusable across systems.
    """

    def __init__(self, state_labels: frozenset[str]) -> None:
        self.state_labels = state_labels
        self._log: list[tuple[int, str]] = []  # (issue_num, removed_label)

    def heal(self, issue: Issue, added_label: str) -> list[str]:
        """Remove conflicting state labels; return list of removed labels."""
        if added_label not in self.state_labels:
            return []
        removed: list[str] = []
        for lbl in list(issue.labels):
            if lbl in self.state_labels and lbl != added_label:
                issue.labels.discard(lbl)
                self._log.append((issue.number, lbl))
                removed.append(lbl)
        return removed

    def pop_log(self) -> list[tuple[int, str]]:
        log = list(self._log)
        self._log.clear()
        return log


# ---------------------------------------------------------------------------
# Repository — in-memory stand-in for the GitHub API
# ---------------------------------------------------------------------------


class Repository:
    """
    Holds all issues and PRs.  Provides the query interface that real
    workflows call via 'gh issue list', 'gh pr list', etc.

    StateHealer is wired in: add_label() triggers healing automatically.
    """

    def __init__(self, state_labels: frozenset[str]) -> None:
        self.issues: dict[int, Issue] = {}
        self.pull_requests: dict[int, PullRequest] = {}
        self.healer = StateHealer(state_labels)

    # -- Issue mutations ------------------------------------------------

    def add_label(self, issue_num: int, label: str) -> list[str]:
        """Add label and heal state conflicts.  Returns removed labels."""
        issue = self.issues[issue_num]
        issue.labels.add(label)
        return self.healer.heal(issue, label)

    def remove_label(self, issue_num: int, label: str) -> None:
        self.issues[issue_num].labels.discard(label)

    def add_comment(self, issue_num: int, body: str) -> None:
        self.issues[issue_num].comments.append(body)

    # -- PR mutations ---------------------------------------------------

    def add_pr_comment(self, pr_num: int, body: str) -> None:
        self.pull_requests[pr_num].pr_comments.append(body)

    def merge_pr(self, pr_num: int) -> None:
        self.pull_requests[pr_num].state = "merged"

    def close_pr(self, pr_num: int) -> None:
        self.pull_requests[pr_num].state = "closed"

    # -- Accessors -------------------------------------------------------

    def get_issue(self, num: int) -> Issue:
        return self.issues[num]

    def get_pr(self, num: int) -> PullRequest:
        return self.pull_requests[num]

    def list_issues(
        self,
        label: str | None = None,
        exclude_labels: list[str] | None = None,
    ) -> list[Issue]:
        result = list(self.issues.values())
        if label:
            result = [i for i in result if label in i.labels]
        if exclude_labels:
            result = [
                i for i in result
                if not any(lbl in i.labels for lbl in exclude_labels)
            ]
        return result

    def list_prs(self, state: str | None = None) -> list[PullRequest]:
        result = list(self.pull_requests.values())
        if state:
            result = [p for p in result if p.state == state]
        return result

    def find_pr_for_issue(
        self,
        issue_num: int,
        state: str | None = None,
    ) -> PullRequest | None:
        for pr in self.list_prs(state=state):
            if pr.links_issue(issue_num):
                return pr
        return None

    # -- Convenience factory --------------------------------------------

    def add_issue(self, number: int, labels: set[str], comments: list[str] | None = None) -> Issue:
        issue = Issue(number=number, labels=set(labels), comments=list(comments or []))
        self.issues[number] = issue
        return issue

    def add_pr(self, number: int, **kwargs: object) -> PullRequest:
        pr = PullRequest(number=number, **kwargs)  # type: ignore[arg-type]
        self.pull_requests[number] = pr
        return pr
