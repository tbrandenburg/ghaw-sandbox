"""
Simulation engine — wires agents to a repository and enforces invariants.

Engine.fire(event)  runs all matching agents and asserts state invariants.
Engine.tick()       simulates a schedule pulse (fires SCHEDULE to all agents).
Engine.label_added() applies a label to an issue and fires LABEL_ADDED event.

InvariantViolation is raised (not just logged) so tests fail fast and loudly
with a descriptive message pointing at the offending issue.
"""
from __future__ import annotations

from .models import Repository
from .agents import StateAgent, StatelessAgent, Event, EventKind, Trace


class InvariantViolation(Exception):
    """Raised when an issue holds != 1 state label after any transition."""


class Engine:
    def __init__(self, repo: Repository) -> None:
        self.repo = repo
        self._agents: list[StateAgent | StatelessAgent] = []
        self.traces: list[Trace] = []

    def register(self, *agents: StateAgent | StatelessAgent) -> "Engine":
        self._agents.extend(agents)
        return self

    # -- Event firing ---------------------------------------------------

    def fire(self, event: Event) -> list[Trace]:
        """Run all agents whose entry_trigger matches, then assert invariants."""
        self._assert_state_invariant()  # catch invalid state BEFORE agents can mask it
        batch: list[Trace] = []
        for agent in self._agents:
            batch.extend(agent.run(self.repo, event))
        self.traces.extend(batch)
        self._assert_state_invariant()  # catch invalid state introduced BY agents
        return batch

    def tick(self) -> list[Trace]:
        """Simulate a single schedule pulse."""
        return self.fire(Event(kind=EventKind.SCHEDULE))

    def label_added(self, issue_num: int, label: str) -> list[Trace]:
        """
        Apply a label to an issue (with healing) then fire LABEL_ADDED so
        event-driven agents can react — mirrors the GitHub 'issues: labeled' event.
        """
        removed = self.repo.add_label(issue_num, label)
        event = Event(
            kind=EventKind.LABEL_ADDED,
            label=label,
            issue_num=issue_num,
            data={"healer_removed": removed},
        )
        return self.fire(event)

    # -- Invariant ------------------------------------------------------

    def _assert_state_invariant(self) -> None:
        """Raise if any issue holds >1 state label simultaneously.

        0 state labels is allowed — it represents a terminal/closed issue
        (e.g. after the integrator removes 'reviewed' following a merge).
        """
        state_labels = self.repo.healer.state_labels
        for issue in self.repo.issues.values():
            held = issue.labels & state_labels
            if len(held) > 1:
                raise InvariantViolation(
                    f"Issue #{issue.number} holds {len(held)} state label(s) "
                    f"{held!r} — expected at most 1.  "
                    f"Full label set: {issue.labels!r}"
                )

    # -- Query helpers --------------------------------------------------

    def transitions_for(self, issue_num: int) -> list[tuple[frozenset[str], frozenset[str]]]:
        """Return (labels_before, labels_after) pairs for every trace touching this issue."""
        return [
            (t.labels_before, t.labels_after)
            for t in self.traces
            if t.issue_num == issue_num
        ]

    def outcomes_for(self, issue_num: int) -> list[str]:
        """Return the list of verify outcome actions for an issue in trace order."""
        return [
            t.verify_outcome.action
            for t in self.traces
            if t.issue_num == issue_num
        ]
