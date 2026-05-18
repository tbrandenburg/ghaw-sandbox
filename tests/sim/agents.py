"""
Abstract agent framework — reusable for any agentic workflow system.

Two base classes:
  StateAgent    — owns a state label, processes issues in that state,
                  transitions them out via a verify step
  StatelessAgent — no required input state; operates opportunistically

Four lifecycle hooks (the same for both):
  entry_trigger(event)         → bool        should this agent fire?
  entry_action(repo, event)    → list        which candidates to process?
  do_action(repo, candidate)   → AgentResult simulate the agent's work
  exit_action(repo, candidate, result) → VerifyOutcome  apply transitions

run() is the template method that sequences these hooks.
Subclasses may override run() for batch operations (e.g. sprint planner).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable

from .models import Repository, Issue, PullRequest


# ---------------------------------------------------------------------------
# Event
# ---------------------------------------------------------------------------


class EventKind(Enum):
    SCHEDULE = auto()
    LABEL_ADDED = auto()
    LABEL_REMOVED = auto()
    PR_EVENT = auto()
    MANUAL = auto()


@dataclass
class Event:
    kind: EventKind
    label: str | None = None
    issue_num: int | None = None
    pr_num: int | None = None
    data: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Agent result & verify outcome
# ---------------------------------------------------------------------------


@dataclass
class AgentResult:
    """What the agent produced during do_action.

    signals   — marker strings the agent posted (e.g. "<!-- PLAN -->")
    comments  — full comment bodies; engine appends these to issue/PR
    metadata  — open-ended payload (e.g. {"pr_created": 42})
    """
    signals: list[str] = field(default_factory=list)
    comments: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


@dataclass
class VerifyOutcome:
    """What the exit_action decided.

    action:  "promoted" | "blocked" | "skipped" | "unchanged"
    """
    action: str
    from_state: str | None = None
    to_state: str | None = None
    reason: str = ""
    labels_added: list[str] = field(default_factory=list)
    labels_removed: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Execution trace — one per candidate processed
# ---------------------------------------------------------------------------


@dataclass
class Trace:
    event: Event
    agent_name: str
    issue_num: int | None
    labels_before: frozenset[str]
    agent_result: AgentResult
    verify_outcome: VerifyOutcome
    labels_after: frozenset[str]
    healer_removed: list[str]


# ---------------------------------------------------------------------------
# Behavior type alias
# ---------------------------------------------------------------------------

Behavior = Callable[[Repository, Any], AgentResult]


# ---------------------------------------------------------------------------
# Abstract base classes
# ---------------------------------------------------------------------------


class StateAgent(ABC):
    """
    Owns a single state label.  Processes issues in that state and
    transitions them out.

    Subclass contract:
      owned_state   — declare the state label this agent owns
      entry_trigger — return True when this agent should fire
      entry_action  — return the list of candidate Issues to process
      do_action     — simulate what the OpenCode agent does (injectable)
      exit_action   — apply label transitions (mirrors bash verify step)
    """

    @property
    @abstractmethod
    def owned_state(self) -> str:
        """The state label this agent owns."""

    @abstractmethod
    def entry_trigger(self, event: Event) -> bool:
        """Should this agent fire for the given event?"""

    @abstractmethod
    def entry_action(self, repo: Repository, event: Event) -> list[Issue]:
        """Filter: which issues are candidates? (prepare phase)"""

    @abstractmethod
    def do_action(self, repo: Repository, issue: Issue) -> AgentResult:
        """
        Simulate the agent's work.  May post comments or mutate the repo
        (e.g. a groomer adding labels directly).  Returns AgentResult
        describing what the agent produced.
        """

    @abstractmethod
    def exit_action(
        self, repo: Repository, issue: Issue, result: AgentResult
    ) -> VerifyOutcome:
        """
        Apply label transitions based on the agent result.  Mirrors the
        bash verify step in the real workflow.  Always re-reads from repo
        (never trusts the in-memory result alone).
        """

    def run(self, repo: Repository, event: Event) -> list[Trace]:
        """Template method — sequences the four lifecycle hooks."""
        if not self.entry_trigger(event):
            return []
        candidates = self.entry_action(repo, event)
        traces: list[Trace] = []
        for issue in candidates:
            traces.append(_execute(self, repo, event, issue, issue.number))
        return traces


class StatelessAgent(ABC):
    """
    No required input state.  Operates opportunistically (e.g. CI fixer,
    integrator, review agent).

    Subclass contract: same four hooks as StateAgent.
    exit_action has a sensible default (no-op) — override when needed.
    """

    @abstractmethod
    def entry_trigger(self, event: Event) -> bool:
        """Should this agent fire for the given event?"""

    @abstractmethod
    def entry_action(self, repo: Repository, event: Event) -> list:
        """Find work to do.  Candidates may be Issues, PRs, or any object."""

    @abstractmethod
    def do_action(self, repo: Repository, candidate: Any) -> AgentResult:
        """Simulate the agent's work."""

    def exit_action(
        self, repo: Repository, candidate: Any, result: AgentResult
    ) -> VerifyOutcome:
        """Optional verify step.  Default: no state change."""
        return VerifyOutcome(action="unchanged", reason="no-verify")

    def run(self, repo: Repository, event: Event) -> list[Trace]:
        """Template method — sequences the four lifecycle hooks."""
        if not self.entry_trigger(event):
            return []
        candidates = self.entry_action(repo, event)
        traces: list[Trace] = []
        for candidate in candidates:
            issue_num = candidate.number if isinstance(candidate, Issue) else None
            traces.append(_execute(self, repo, event, candidate, issue_num))
        return traces


# ---------------------------------------------------------------------------
# Shared execution helper (keeps run() DRY across both base classes)
# ---------------------------------------------------------------------------


def _execute(
    agent: StateAgent | StatelessAgent,
    repo: Repository,
    event: Event,
    candidate: Any,
    issue_num: int | None,
) -> Trace:
    labels_before = frozenset(
        repo.get_issue(issue_num).labels if issue_num else set()
    )
    healer_log_start = len(repo.healer._log)

    result = agent.do_action(repo, candidate)

    # Engine applies comments from result onto the issue (or PR if candidate is PR)
    for body in result.comments:
        if isinstance(candidate, PullRequest):
            repo.add_pr_comment(candidate.number, body)
        elif issue_num is not None:
            repo.add_comment(issue_num, body)

    outcome = agent.exit_action(repo, candidate, result)

    labels_after = frozenset(
        repo.get_issue(issue_num).labels if issue_num else set()
    )
    healer_removed = [lbl for _, lbl in repo.healer._log[healer_log_start:]]

    return Trace(
        event=event,
        agent_name=type(agent).__name__,
        issue_num=issue_num,
        labels_before=labels_before,
        agent_result=result,
        verify_outcome=outcome,
        labels_after=labels_after,
        healer_removed=healer_removed,
    )
