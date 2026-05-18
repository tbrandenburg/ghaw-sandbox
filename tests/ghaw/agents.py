"""
GHAW-specific agents — the <20% layer.

Each class:
  1. Declares which state/event it owns
  2. Implements entry_trigger / entry_action (the prepare-phase filter)
  3. Accepts an injectable 'behavior' for do_action (default = success)
  4. Implements exit_action mirroring the bash verify step 1:1

Built-in behaviors live at the bottom of this module as plain callables.
They can be passed to any agent constructor:

    PlannerAgent(behavior=cannot_plan())
    PlannerAgent(behavior=no_output())
"""
from __future__ import annotations

import re
from typing import Callable

from ..sim.agents import (
    AgentResult,
    Behavior,
    Event,
    EventKind,
    StateAgent,
    StatelessAgent,
    VerifyOutcome,
    _execute,
    Trace,
)
from ..sim.models import Issue, PullRequest, Repository

# ---------------------------------------------------------------------------
# GHAW state label set (injected into Repository at construction)
# ---------------------------------------------------------------------------

GHAW_STATE_LABELS = frozenset({
    "open", "ready", "planned", "in-progress", "reviewed", "blocked", "defocus",
})


# ---------------------------------------------------------------------------
# Built-in behaviors
# ---------------------------------------------------------------------------

def plan_success() -> Behavior:
    def _b(repo: Repository, issue: Issue) -> AgentResult:
        return AgentResult(
            signals=["<!-- PLAN -->"],
            comments=["<!-- PLAN -->\n## Implementation Plan\n\n### Approach\nSimulated plan.\n\n### Estimated Complexity\nmedium"],
        )
    return _b


def cannot_plan() -> Behavior:
    def _b(repo: Repository, issue: Issue) -> AgentResult:
        return AgentResult(
            signals=["<!-- CANNOT-PLAN -->"],
            comments=["<!-- CANNOT-PLAN -->\nCannot create plan: requirements unclear."],
        )
    return _b


def no_action() -> Behavior:
    def _b(repo: Repository, issue: Issue) -> AgentResult:
        return AgentResult(
            signals=["<!-- NO-ACTION -->"],
            comments=["<!-- NO-ACTION -->\nIssue already resolved — no implementation needed."],
        )
    return _b


def no_output() -> Behavior:
    """Simulates agent crash / timeout — no signal posted."""
    def _b(repo: Repository, issue: Issue) -> AgentResult:
        return AgentResult()
    return _b


def groomer_ready() -> Behavior:
    """Groomer decides the issue is clear and labels it ready."""
    def _b(repo: Repository, issue: Issue) -> AgentResult:
        repo.add_label(issue.number, "ready")
        repo.remove_label(issue.number, "open")
        return AgentResult(signals=["ready"])
    return _b


def groomer_defocus() -> Behavior:
    """Groomer decides the issue is out of scope."""
    def _b(repo: Repository, issue: Issue) -> AgentResult:
        repo.add_label(issue.number, "defocus")
        repo.remove_label(issue.number, "open")
        return AgentResult(signals=["defocus"])
    return _b


def groomer_needs_clarification() -> Behavior:
    """Groomer asks for clarification — adds confidence/low, stays in open."""
    def _b(repo: Repository, issue: Issue) -> AgentResult:
        repo.add_label(issue.number, "confidence/low")
        return AgentResult(
            signals=[],
            comments=["❓ Grooming: please clarify acceptance criteria."],
        )
    return _b


def wsjf_scored(score: float) -> Behavior:
    """Sprint planner posts a WSJF score comment on the issue."""
    def _b(repo: Repository, issue: Issue) -> AgentResult:
        return AgentResult(
            signals=[],
            comments=[f"📊 WSJF: {score} (CoD: simulated / Size: simulated)"],
        )
    return _b


def pr_created(pr: PullRequest) -> Behavior:
    """Dev agent creates a PR linking the issue."""
    def _b(repo: Repository, issue: Issue) -> AgentResult:
        repo.pull_requests[pr.number] = pr
        return AgentResult(
            signals=["pr-created"],
            metadata={"pr_created": pr.number},
        )
    return _b


def review_passed() -> Behavior:
    """Review agent posts a passing review summary on the PR."""
    def _b(repo: Repository, pr: PullRequest) -> AgentResult:
        return AgentResult(
            signals=["✅ Technical review passed"],
            comments=["## Review Summary\n\n✅ Technical review passed. All acceptance criteria met."],
        )
    return _b


def review_changes_requested() -> Behavior:
    """Review agent requests changes on the PR."""
    def _b(repo: Repository, pr: PullRequest) -> AgentResult:
        pr.review_decision = "CHANGES_REQUESTED"
        return AgentResult(
            signals=["❌ Changes requested"],
            comments=["❌ Changes requested: please address the issues noted."],
        )
    return _b


def merge_success() -> Behavior:
    """Integrator merges the PR."""
    def _b(repo: Repository, pr: PullRequest) -> AgentResult:
        repo.merge_pr(pr.number)
        return AgentResult(
            signals=["merged"],
            metadata={"pr_merged": pr.number},
        )
    return _b


def deferred() -> Behavior:
    """Integrator defers a PR due to conflicts."""
    def _b(repo: Repository, pr: PullRequest) -> AgentResult:
        return AgentResult(
            signals=["<!-- DEFERRED -->"],
            comments=["<!-- DEFERRED -->\n⏸️ Merge deferred: conflicts detected."],
        )
    return _b


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _extract_wsjf(issue: Issue) -> float:
    return issue.extract_value(r"WSJF:\s*([0-9.]+)")


# ---------------------------------------------------------------------------
# Concrete GHAW agents
# ---------------------------------------------------------------------------


class GroomerAgent(StateAgent):
    """
    Owns 'open'.  Reviews issues for clarity, feasibility, and scope.
    Transitions to ready (via auto-promote verify) or defocus.

    Mirrors: ghaw-backlog-grooming.yml
    """
    owned_state = "open"

    def __init__(self, behavior: Behavior | None = None) -> None:
        self._behavior = behavior or groomer_ready()

    def entry_trigger(self, event: Event) -> bool:
        return (
            event.kind == EventKind.SCHEDULE
            or (event.kind == EventKind.LABEL_ADDED and event.label == "open")
            or (event.kind == EventKind.LABEL_REMOVED and event.label == "confidence/low")
        )

    def entry_action(self, repo: Repository, event: Event) -> list[Issue]:
        if event.issue_num and event.kind in (EventKind.LABEL_ADDED, EventKind.LABEL_REMOVED):
            issue = repo.get_issue(event.issue_num)
            return [issue] if "open" in issue.labels else []
        return repo.list_issues(label="open")[:10]

    def do_action(self, repo: Repository, issue: Issue) -> AgentResult:
        return self._behavior(repo, issue)

    def exit_action(self, repo: Repository, issue: Issue, result: AgentResult) -> VerifyOutcome:
        # Mirror: ghaw-backlog-grooming.yml jobs.verify auto-promote logic
        labels = repo.get_issue(issue.number).labels
        skip_states = {"defocus", "ready", "in-progress", "blocked"}
        if labels & skip_states:
            return VerifyOutcome(action="skipped", reason="already-transitioned")

        has_low_conf = "confidence/low" in labels
        has_large = bool({"size/xl", "size/l"} & labels)

        if not has_low_conf and not has_large:
            repo.add_label(issue.number, "ready")
            for lbl in ("open", "blocked", "in-progress", "defocus"):
                repo.remove_label(issue.number, lbl)
            return VerifyOutcome(
                action="promoted",
                from_state="open",
                to_state="ready",
                labels_added=["ready"],
                labels_removed=["open"],
            )
        return VerifyOutcome(
            action="unchanged",
            reason="po-handoff" if has_low_conf else "size-too-large",
        )


class PlannerAgent(StateAgent):
    """
    Owns 'ready'.  Produces an implementation plan.
    Transitions to planned on success, blocked on failure.

    Mirrors: ghaw-planner.yml
    """
    owned_state = "ready"

    def __init__(self, behavior: Behavior | None = None) -> None:
        self._behavior = behavior or plan_success()

    def entry_trigger(self, event: Event) -> bool:
        return (
            event.kind == EventKind.SCHEDULE
            or (event.kind == EventKind.LABEL_ADDED and event.label == "ready")
        )

    def entry_action(self, repo: Repository, event: Event) -> list[Issue]:
        if event.issue_num and event.kind == EventKind.LABEL_ADDED:
            issue = repo.get_issue(event.issue_num)
            if "ready" not in issue.labels:
                return []
            if issue.has_signal("<!-- PLAN -->") or issue.has_signal("<!-- NO-ACTION -->"):
                return []
            return [issue]
        return [
            i for i in repo.list_issues(label="ready")
            if not i.has_signal("<!-- PLAN -->") and not i.has_signal("<!-- NO-ACTION -->")
        ]

    def do_action(self, repo: Repository, issue: Issue) -> AgentResult:
        return self._behavior(repo, issue)

    def exit_action(self, repo: Repository, issue: Issue, result: AgentResult) -> VerifyOutcome:
        # Mirror: ghaw-planner.yml jobs.verify
        comments = repo.get_issue(issue.number).comments
        has_plan = any("<!-- PLAN -->" in c for c in comments)
        has_no_action = any("<!-- NO-ACTION -->" in c for c in comments)
        has_cannot_plan = any("<!-- CANNOT-PLAN -->" in c for c in comments)

        if has_no_action:
            return VerifyOutcome(action="skipped", reason="no-action")

        if has_cannot_plan or not has_plan:
            repo.add_label(issue.number, "blocked")
            repo.remove_label(issue.number, "ready")
            if not has_cannot_plan:
                repo.add_comment(
                    issue.number,
                    "❌ Planner Agent produced no plan — blocked for PO clarification.",
                )
            return VerifyOutcome(
                action="blocked",
                from_state="ready",
                to_state="blocked",
                reason="cannot-plan" if has_cannot_plan else "no-signal",
                labels_added=["blocked"],
                labels_removed=["ready"],
            )

        repo.add_label(issue.number, "planned")
        repo.remove_label(issue.number, "ready")
        return VerifyOutcome(
            action="promoted",
            from_state="ready",
            to_state="planned",
            labels_added=["planned"],
            labels_removed=["ready"],
        )


class SprintPlannerAgent(StateAgent):
    """
    Owns 'planned'.  Ranks issues by WSJF and assigns top N to the sprint.
    Overrides run() because ranking requires seeing all candidates at once.

    Mirrors: ghaw-sprint-planning.yml
    """
    owned_state = "planned"

    def __init__(self, max_wip: int = 3, behavior: Behavior | None = None) -> None:
        self.max_wip = max_wip
        self._behavior = behavior or wsjf_scored(1.0)

    def entry_trigger(self, event: Event) -> bool:
        return event.kind == EventKind.SCHEDULE

    def entry_action(self, repo: Repository, event: Event) -> list[Issue]:
        current_wip = len(repo.list_issues(label="in-progress"))
        if current_wip >= self.max_wip:
            return []
        return repo.list_issues(label="planned", exclude_labels=["reviewed"])

    def do_action(self, repo: Repository, issue: Issue) -> AgentResult:
        return self._behavior(repo, issue)

    def exit_action(self, repo: Repository, issue: Issue, result: AgentResult) -> VerifyOutcome:
        # Unused — see run() override below.
        return VerifyOutcome(action="unchanged", reason="deferred-to-batch")

    def run(self, repo: Repository, event: Event) -> list[Trace]:
        """Batch override: score all candidates, rank by WSJF, assign top N."""
        if not self.entry_trigger(event):
            return []
        candidates = self.entry_action(repo, event)
        if not candidates:
            return []

        # Score all issues
        scored: list[tuple[Issue, AgentResult, frozenset[str], int]] = []
        for issue in candidates:
            labels_before = frozenset(issue.labels)
            healer_start = len(repo.healer._log)
            result = self.do_action(repo, issue)
            for body in result.comments:
                repo.add_comment(issue.number, body)
            scored.append((issue, result, labels_before, healer_start))

        # Rank by WSJF descending
        scored.sort(key=lambda x: _extract_wsjf(repo.get_issue(x[0].number)), reverse=True)

        current_wip = len(repo.list_issues(label="in-progress"))
        slots = self.max_wip - current_wip

        traces: list[Trace] = []
        for idx, (issue, result, labels_before, healer_start) in enumerate(scored):
            if idx < slots:
                repo.add_label(issue.number, "in-progress")
                repo.remove_label(issue.number, "planned")
                outcome = VerifyOutcome(
                    action="promoted",
                    from_state="planned",
                    to_state="in-progress",
                    reason=f"wsjf-rank-{idx + 1}",
                    labels_added=["in-progress"],
                    labels_removed=["planned"],
                )
            else:
                outcome = VerifyOutcome(action="skipped", reason="wip-limit")

            healer_removed = [lbl for _, lbl in repo.healer._log[healer_start:]]
            traces.append(Trace(
                event=event,
                agent_name=type(self).__name__,
                issue_num=issue.number,
                labels_before=labels_before,
                agent_result=result,
                verify_outcome=outcome,
                labels_after=frozenset(repo.get_issue(issue.number).labels),
                healer_removed=healer_removed,
            ))
        return traces


class DevAgent(StatelessAgent):
    """
    Operates on in-progress issues that lack a PR (or have CHANGES_REQUESTED).
    Creates a PR for each.  Verify checks the PR exists.

    Mirrors: ghaw-dev.yml
    """

    def __init__(self, behavior: Behavior | None = None) -> None:
        self._behavior = behavior

    def entry_trigger(self, event: Event) -> bool:
        return event.kind == EventKind.SCHEDULE

    def entry_action(self, repo: Repository, event: Event) -> list[Issue]:
        candidates: list[Issue] = []
        for issue in repo.list_issues(label="in-progress", exclude_labels=["blocked", "reviewed"]):
            pr = repo.find_pr_for_issue(issue.number, state="open")
            if pr is None or pr.review_decision == "CHANGES_REQUESTED":
                candidates.append(issue)
        return candidates

    def do_action(self, repo: Repository, issue: Issue) -> AgentResult:
        if self._behavior:
            return self._behavior(repo, issue)
        # Default: create a stub PR
        pr_num = max((p.number for p in repo.pull_requests.values()), default=0) + 1
        pr = PullRequest(
            number=pr_num,
            body=f"## Summary\n\nImplemented.\n\nCloses #{issue.number}",
            head_ref=f"feature/issue-{issue.number}",
            state="open",
        )
        repo.pull_requests[pr_num] = pr
        return AgentResult(signals=["pr-created"], metadata={"pr_created": pr_num})

    def exit_action(self, repo: Repository, issue: Issue, result: AgentResult) -> VerifyOutcome:
        # Mirror: ghaw-dev.yml jobs.verify
        pr = repo.find_pr_for_issue(issue.number, state="open")
        if pr is not None:
            return VerifyOutcome(action="unchanged", reason="pr-exists")
        repo.add_comment(
            issue.number,
            "❌ Dev Agent ran but did not create a PR. Will retry on next cycle.",
        )
        return VerifyOutcome(action="unchanged", reason="no-pr-created")


class ReviewAgent(StatelessAgent):
    """
    Reviews open PRs with passing CI.  Promotes linked issue to reviewed.

    Mirrors: ghaw-review.yml
    """

    def __init__(self, behavior: Behavior | None = None) -> None:
        self._behavior = behavior or review_passed()

    def entry_trigger(self, event: Event) -> bool:
        return event.kind == EventKind.SCHEDULE

    def entry_action(self, repo: Repository, event: Event) -> list[PullRequest]:
        return [
            pr for pr in repo.list_prs(state="open")
            if pr.ci_passing() and not pr.has_pr_signal("✅ Technical review passed")
        ]

    def do_action(self, repo: Repository, pr: PullRequest) -> AgentResult:
        return self._behavior(repo, pr)

    def exit_action(self, repo: Repository, pr: PullRequest, result: AgentResult) -> VerifyOutcome:
        # Mirror: ghaw-review.yml jobs.verify
        linked_issue = next(
            (i for i in repo.issues.values() if pr.links_issue(i.number)), None
        )
        if linked_issue is None:
            return VerifyOutcome(action="unchanged", reason="no-linked-issue")

        if pr.has_pr_signal("✅ Technical review passed"):
            repo.add_label(linked_issue.number, "reviewed")
            for lbl in ("in-progress", "ready", "open", "blocked"):
                repo.remove_label(linked_issue.number, lbl)
            return VerifyOutcome(
                action="promoted",
                from_state="in-progress",
                to_state="reviewed",
                reason="review-passed",
                labels_added=["reviewed"],
                labels_removed=["in-progress"],
            )
        return VerifyOutcome(action="unchanged", reason="review-pending")


class IntegratorAgent(StatelessAgent):
    """
    Merges approved, CI-green PRs.  Also handles deferred PRs and
    PRs closed without merging.

    Mirrors: ghaw-integrator.yml
    """

    def __init__(self, behavior: Behavior | None = None) -> None:
        self._behavior = behavior or merge_success()

    def entry_trigger(self, event: Event) -> bool:
        return event.kind == EventKind.SCHEDULE

    def entry_action(self, repo: Repository, event: Event) -> list[PullRequest]:
        # Approved, CI-green open PRs
        return [
            pr for pr in repo.list_prs(state="open")
            if pr.review_decision == "APPROVED" and pr.ci_passing()
        ]

    def do_action(self, repo: Repository, pr: PullRequest) -> AgentResult:
        return self._behavior(repo, pr)

    def exit_action(self, repo: Repository, pr: PullRequest, result: AgentResult) -> VerifyOutcome:
        # Mirror: ghaw-integrator.yml jobs.verify — three sub-cases
        linked_issue = next(
            (i for i in repo.issues.values() if pr.links_issue(i.number)), None
        )

        # Case 1: PR was merged → remove "reviewed" from linked issue
        if pr.state == "merged" and linked_issue and "reviewed" in linked_issue.labels:
            repo.remove_label(linked_issue.number, "reviewed")
            return VerifyOutcome(
                action="promoted",
                from_state="reviewed",
                to_state=None,
                reason="merged",
                labels_removed=["reviewed"],
            )

        # Case 2: PR has DEFERRED signal → block linked issue
        if pr.has_pr_signal("<!-- DEFERRED -->") and linked_issue:
            repo.add_label(linked_issue.number, "blocked")
            for lbl in ("in-progress", "ready", "open", "reviewed"):
                repo.remove_label(linked_issue.number, lbl)
            return VerifyOutcome(
                action="blocked",
                from_state="reviewed",
                to_state="blocked",
                reason="deferred",
                labels_added=["blocked"],
                labels_removed=["reviewed"],
            )

        # Case 3: PR closed without merge → reset linked issue to open
        if pr.state == "closed" and linked_issue and "reviewed" in linked_issue.labels:
            repo.add_label(linked_issue.number, "open")
            repo.remove_label(linked_issue.number, "reviewed")
            return VerifyOutcome(
                action="promoted",
                from_state="reviewed",
                to_state="open",
                reason="pr-closed-without-merge",
                labels_added=["open"],
                labels_removed=["reviewed"],
            )

        return VerifyOutcome(action="unchanged", reason="pending")
