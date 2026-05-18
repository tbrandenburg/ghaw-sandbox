"""
Concrete agents for <YOUR-PROJECT-NAME>.

HOW TO USE THIS TEMPLATE
─────────────────────────
1. Copy this file to  tests/<project>/agents.py
2. Replace every [TODO] marker with your project-specific values.
3. Do NOT modify  tests/sim/  — it is the generic core.

STRUCTURE
─────────
• YOUR_STATE_LABELS   — must exactly match the labels in core-state-heal.yml
• Built-in behaviors  — injectable callables for test scenarios
• Concrete agent classes (one per state + stateless agents)

Reference implementation: .github/skills/agentic-workflow-system/assets/examples/
"""
from __future__ import annotations

from tests.sim.agents import (
    AgentResult,
    Behavior,
    Event,
    EventKind,
    StateAgent,
    StatelessAgent,
    VerifyOutcome,
)
from tests.sim.models import Issue, PullRequest, Repository


# ---------------------------------------------------------------------------
# TODO: define your state label set — must match core-state-heal.yml exactly
# ---------------------------------------------------------------------------

YOUR_STATE_LABELS: frozenset[str] = frozenset({
    # "state-a",
    # "state-b",
    # "state-c",
    # "blocked",
    # ...
})


# ---------------------------------------------------------------------------
# Built-in behaviors
#
# Each behavior is a factory returning a Callable[[Repository, Issue|PR], AgentResult].
# Keep them thin — they exist only to drive tests, not to re-implement agent logic.
#
# TODO: add one behavior per outcome your verify step can produce.
# ---------------------------------------------------------------------------

def action_success() -> Behavior:
    """Agent produces the success signal (e.g. <!-- SUCCESS -->)."""
    def _behavior(repo: Repository, issue: Issue) -> AgentResult:
        return AgentResult(
            comments=["<!-- SUCCESS -->\nSimulated success output."],
        )
    return _behavior


def action_failure() -> Behavior:
    """Agent produces the failure / cannot-proceed signal."""
    def _behavior(repo: Repository, issue: Issue) -> AgentResult:
        return AgentResult(
            comments=["<!-- FAILURE -->\nCould not proceed."],
        )
    return _behavior


def no_output() -> Behavior:
    """Agent crashes or times out — produces nothing."""
    def _behavior(repo: Repository, issue: Issue) -> AgentResult:
        return AgentResult()
    return _behavior


# ---------------------------------------------------------------------------
# TODO: implement one StateAgent subclass per state in YOUR_STATE_LABELS
#       (except "blocked" — that is a sink state, no agent owns it)
#
# Template below: replace [STATE-A], [SUCCESS-SIGNAL], [NEXT-STATE] etc.
# ---------------------------------------------------------------------------

class StateAAgent(StateAgent):
    """
    Owns '[STATE-A]'.  [One-sentence description of what this agent does.]

    Mirrors: .github/workflows/sm-[state-a].yml
    """

    # TODO: set this to the state label this agent owns
    owned_state = "[STATE-A]"

    def __init__(self, behavior: Behavior | None = None) -> None:
        self._behavior = behavior or action_success()

    def entry_trigger(self, event: Event) -> bool:
        # TODO: fire on SCHEDULE, or on LABEL_ADDED("[STATE-A]"), or both
        return (
            event.kind == EventKind.SCHEDULE
            or (event.kind == EventKind.LABEL_ADDED and event.label == "[STATE-A]")
        )

    def entry_action(self, repo: Repository, event: Event) -> list[Issue]:
        # TODO: filter to issues this agent should process
        # Common filters:
        #   • issues with the owned state label
        #   • exclude issues already carrying a success signal (idempotency)
        if event.issue_num and event.kind == EventKind.LABEL_ADDED:
            issue = repo.get_issue(event.issue_num)
            if "[STATE-A]" not in issue.labels:
                return []
            return [issue]
        return repo.list_issues(label="[STATE-A]")

    def do_action(self, repo: Repository, issue: Issue) -> AgentResult:
        return self._behavior(repo, issue)

    def exit_action(
        self, repo: Repository, issue: Issue, result: AgentResult
    ) -> VerifyOutcome:
        # TODO: mirror the bash verify step in sm-[state-a].yml
        #
        # Pattern A — signal-based promotion:
        #   if issue has success signal → promote to [NEXT-STATE]
        #   else → block
        #
        # Pattern B — direct label mutation (groomer-style):
        #   if labels show the agent already transitioned → return skipped
        #   else → promote / block based on result

        issue = repo.get_issue(issue.number)

        if issue.has_signal("<!-- SUCCESS -->"):
            repo.add_label(issue.number, "[NEXT-STATE]")
            repo.remove_label(issue.number, "[STATE-A]")
            return VerifyOutcome(
                action="promoted",
                from_state="[STATE-A]",
                to_state="[NEXT-STATE]",
                reason="success-signal",
                labels_added=["[NEXT-STATE]"],
                labels_removed=["[STATE-A]"],
            )

        # No signal → block
        repo.add_label(issue.number, "blocked")
        repo.remove_label(issue.number, "[STATE-A]")
        return VerifyOutcome(
            action="blocked",
            from_state="[STATE-A]",
            to_state="blocked",
            reason="no-signal",
            labels_added=["blocked"],
            labels_removed=["[STATE-A]"],
        )


# TODO: add more StateAgent subclasses for each remaining state
# TODO: add StatelessAgent subclasses for event-driven / opportunistic agents
#       (see StatelessAgent in tests/sim/agents.py)
