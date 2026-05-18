"""
Behavioral state machine tests for <YOUR-PROJECT-NAME>.

HOW TO USE THIS TEMPLATE
─────────────────────────
1. Copy this file to  tests/test_<project>_state_machine.py
2. Replace every [TODO] marker with your project-specific values.
3. Fill in the import block below with your concrete agents and behaviors.

IMPORTANT: all agents fire on every engine.tick().
           Use single-agent Engine instances for step-by-step assertions
           (see TestFullPipeline.test_happy_path below).
"""
import pytest

from tests.sim.engine import Engine, InvariantViolation
from tests.sim.models import Repository

# TODO: replace <project> with your module name and fill in the imports
# from tests.<project>.agents import (
#     YOUR_STATE_LABELS,
#     StateAAgent,
#     StateBAgent,
#     # ... one per state
#     action_success,
#     action_failure,
#     no_output,
#     # ... one per outcome
# )

# ---------------------------------------------------------------------------
# TODO: paste your actual state label set here (mirrors core-state-heal.yml)
# ---------------------------------------------------------------------------
YOUR_STATE_LABELS: frozenset[str] = frozenset({
    # "state-a", "state-b", "blocked", ...
})


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def make_repo() -> Repository:
    return Repository(state_labels=YOUR_STATE_LABELS)


# TODO: one helper per state
def issue_in_state_a(repo: Repository, number: int = 1) -> None:
    repo.add_issue(number, labels={"[STATE-A]"})   # TODO: real label name


# ---------------------------------------------------------------------------
# TODO: one TestClass per agent
# ---------------------------------------------------------------------------

class TestStateAAgent:
    """Tests for the agent that owns '[STATE-A]'."""

    def test_promotes_on_success(self):
        repo = make_repo()
        issue_in_state_a(repo)
        engine = Engine(repo).register(
            # TODO: StateAAgent(behavior=action_success())
        )
        engine.tick()
        # TODO: assert repo.get_issue(1).labels == {"[NEXT-STATE]"}

    def test_blocks_on_no_output(self):
        repo = make_repo()
        issue_in_state_a(repo)
        engine = Engine(repo).register(
            # TODO: StateAAgent(behavior=no_output())
        )
        engine.tick()
        assert "blocked" in repo.get_issue(1).labels

    def test_blocks_on_failure_signal(self):
        repo = make_repo()
        issue_in_state_a(repo)
        engine = Engine(repo).register(
            # TODO: StateAAgent(behavior=action_failure())
        )
        engine.tick()
        assert "blocked" in repo.get_issue(1).labels

    def test_idempotent_when_already_promoted(self):
        """Agent does not reprocess an issue that is already in the next state."""
        repo = make_repo()
        repo.add_issue(1, labels={"[NEXT-STATE]"})  # TODO: real label
        engine = Engine(repo).register(
            # TODO: StateAAgent(behavior=action_success())
        )
        engine.tick()
        # TODO: assert repo.get_issue(1).labels == {"[NEXT-STATE]"}  # unchanged


# TODO: repeat for each remaining state agent


# ---------------------------------------------------------------------------
# State invariant tests — keep as-is, only update YOUR_STATE_LABELS above
# ---------------------------------------------------------------------------

class TestStateHealer:
    def test_healer_removes_conflicting_label(self):
        """Adding a state label automatically removes all others."""
        repo = make_repo()
        # Use two real state labels from YOUR_STATE_LABELS
        labels = list(YOUR_STATE_LABELS - {"blocked"})
        if len(labels) < 2:
            pytest.skip("Need at least 2 non-blocked state labels")
        repo.add_issue(1, labels={labels[0]})
        removed = repo.add_label(1, labels[1])
        assert labels[0] in removed
        assert repo.get_issue(1).labels == {labels[1]}

    def test_engine_raises_on_double_state(self):
        """Engine catches pre-existing broken state before agents can mask it."""
        repo = make_repo()
        labels = list(YOUR_STATE_LABELS)
        if len(labels) < 2:
            pytest.skip("Need at least 2 state labels")
        repo.add_issue(1, labels={labels[0]})
        repo.get_issue(1).labels.add(labels[1])   # bypass healer
        engine = Engine(repo)
        with pytest.raises(InvariantViolation):
            engine.tick()

    def test_non_state_labels_not_healed(self):
        """Metadata labels (priority/, size/, …) survive healing."""
        repo = make_repo()
        labels = list(YOUR_STATE_LABELS)
        if len(labels) < 2:
            pytest.skip("Need at least 2 state labels")
        repo.add_issue(1, labels={labels[0], "priority/high", "size/m"})
        repo.add_label(1, labels[1])
        issue_labels = repo.get_issue(1).labels
        assert "priority/high" in issue_labels
        assert "size/m" in issue_labels
        assert labels[1] in issue_labels
        assert labels[0] not in issue_labels


# ---------------------------------------------------------------------------
# Full pipeline tests
# ---------------------------------------------------------------------------

class TestFullPipeline:
    def test_happy_path(self):
        """
        Walk an issue through every state from entry to terminal.

        NOTE: Because all agents fire on every tick(), use a separate
        single-agent Engine per step so you can assert intermediate states.
        """
        from tests.sim.engine import Engine as E

        repo = make_repo()
        issue_in_state_a(repo)   # TODO: entry-state fixture

        # Step 1: first agent → [NEXT-STATE]
        # E(repo).register(StateAAgent(behavior=action_success())).tick()
        # assert "[NEXT-STATE]" in repo.get_issue(1).labels

        # TODO: add one block per state transition

        pass   # remove once implemented

    def test_blocked_then_recovered(self):
        """
        Agent fails → blocked.
        Human re-labels to the owned state → agent fires again and succeeds.
        """
        repo = make_repo()
        issue_in_state_a(repo)
        engine = Engine(repo).register(
            # TODO: StateAAgent(behavior=no_output())
        )
        engine.tick()
        assert "blocked" in repo.get_issue(1).labels

        # Recovery: swap behavior, re-add owned state via label_added
        engine._agents = [
            # TODO: StateAAgent(behavior=action_success())
        ]
        engine.label_added(1, "[STATE-A]")   # TODO: real label
        # TODO: assert "[NEXT-STATE]" in repo.get_issue(1).labels

    def test_state_invariant_never_violated(self):
        """Engine enforces at-most-one-state-label after every tick."""
        repo = make_repo()
        issue_in_state_a(repo)
        engine = Engine(repo).register(
            # TODO: register all agents
        )
        for _ in range(10):
            engine.tick()
            for issue in repo.issues.values():
                state_count = len(issue.labels & YOUR_STATE_LABELS)
                assert state_count <= 1, (
                    f"Issue #{issue.number} carries {state_count} state labels: "
                    f"{issue.labels & YOUR_STATE_LABELS}"
                )
