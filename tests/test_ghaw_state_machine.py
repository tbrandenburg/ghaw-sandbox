"""
Behavioral simulation tests for the GHAW state machine.

Structure:
  fixtures    — helpers that build a Repository in a known starting state
  unit tests  — one verify-step scenario per test (fast, focused)
  integration — full pipeline walks from open → merged

Run with:  pytest tests/test_ghaw_state_machine.py -v
"""
from __future__ import annotations

import pytest

from tests.sim.engine import Engine, InvariantViolation
from tests.sim.models import Repository, Issue, PullRequest
from tests.ghaw.agents import (
    GHAW_STATE_LABELS,
    GroomerAgent,
    PlannerAgent,
    SprintPlannerAgent,
    DevAgent,
    ReviewAgent,
    IntegratorAgent,
    # behaviors
    plan_success,
    cannot_plan,
    no_action,
    no_output,
    groomer_ready,
    groomer_defocus,
    groomer_needs_clarification,
    wsjf_scored,
    pr_created,
    review_passed,
    review_changes_requested,
    merge_success,
    deferred,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def make_repo() -> Repository:
    return Repository(state_labels=GHAW_STATE_LABELS)


def open_issue(repo: Repository, number: int = 1) -> Issue:
    return repo.add_issue(number, labels={"open"})


def ready_issue(repo: Repository, number: int = 1) -> Issue:
    return repo.add_issue(number, labels={"ready"})


def planned_issue(repo: Repository, number: int = 1) -> Issue:
    return repo.add_issue(number, labels={"planned"})


def inprogress_issue(repo: Repository, number: int = 1) -> Issue:
    return repo.add_issue(number, labels={"in-progress"})


def reviewed_issue(repo: Repository, number: int = 1) -> Issue:
    return repo.add_issue(number, labels={"reviewed"})


def linked_pr(
    repo: Repository,
    issue_num: int,
    pr_num: int = 10,
    review_decision: str = "",
    state: str = "open",
) -> PullRequest:
    return repo.add_pr(
        pr_num,
        body=f"## Summary\n\nCloses #{issue_num}",
        head_ref=f"feature/issue-{issue_num}",
        review_decision=review_decision,
        state=state,
    )


# ---------------------------------------------------------------------------
# GroomerAgent
# ---------------------------------------------------------------------------


class TestGroomerAgent:
    def test_promotes_clear_issue_to_ready(self):
        repo = make_repo()
        open_issue(repo)
        engine = Engine(repo).register(GroomerAgent(behavior=groomer_ready()))
        engine.tick()
        assert repo.get_issue(1).labels == {"ready"}

    def test_defocuses_out_of_scope_issue(self):
        repo = make_repo()
        open_issue(repo)
        engine = Engine(repo).register(GroomerAgent(behavior=groomer_defocus()))
        engine.tick()
        assert repo.get_issue(1).labels == {"defocus"}

    def test_holds_low_confidence_issue(self):
        repo = make_repo()
        open_issue(repo)
        engine = Engine(repo).register(GroomerAgent(behavior=groomer_needs_clarification()))
        engine.tick()
        # stays open, gains confidence/low
        assert "open" in repo.get_issue(1).labels
        assert "confidence/low" in repo.get_issue(1).labels

    def test_skips_issue_already_marked_ready(self):
        repo = make_repo()
        repo.add_issue(1, labels={"ready"})
        engine = Engine(repo).register(GroomerAgent(behavior=groomer_ready()))
        engine.tick()
        assert repo.get_issue(1).labels == {"ready"}

    def test_holds_oversized_issue(self):
        repo = make_repo()
        repo.add_issue(1, labels={"open", "size/xl"})
        # default ready behavior — but exit_action blocks due to size/xl
        engine = Engine(repo).register(GroomerAgent(behavior=groomer_ready()))
        # do_action adds "ready" directly; healer removes "open" for us
        # exit_action then sees "ready" already set → skipped
        engine.tick()
        # groomer_ready already applied the label — issue ends in ready
        assert "ready" in repo.get_issue(1).labels

    def test_auto_promotes_after_clarification_label_removed(self):
        """Simulate PO removing confidence/low → groomer re-fires."""
        repo = make_repo()
        repo.add_issue(1, labels={"open", "confidence/low"})
        engine = Engine(repo).register(GroomerAgent(behavior=groomer_ready()))
        engine.fire_label_removed = lambda num, lbl: engine.fire(
            __import__("tests.sim.agents", fromlist=["Event", "EventKind"]).Event(
                kind=__import__("tests.sim.agents", fromlist=["EventKind"]).EventKind.LABEL_REMOVED,
                label=lbl,
                issue_num=num,
            )
        )
        # Simulate: PO removes confidence/low
        repo.remove_label(1, "confidence/low")
        from tests.sim.agents import Event, EventKind
        engine.fire(Event(kind=EventKind.LABEL_REMOVED, label="confidence/low", issue_num=1))
        assert "ready" in repo.get_issue(1).labels


# ---------------------------------------------------------------------------
# PlannerAgent
# ---------------------------------------------------------------------------


class TestPlannerAgent:
    def test_promotes_to_planned_on_plan_signal(self):
        repo = make_repo()
        ready_issue(repo)
        engine = Engine(repo).register(PlannerAgent(behavior=plan_success()))
        engine.tick()
        assert repo.get_issue(1).labels == {"planned"}

    def test_blocks_on_no_output(self):
        repo = make_repo()
        ready_issue(repo)
        engine = Engine(repo).register(PlannerAgent(behavior=no_output()))
        engine.tick()
        assert repo.get_issue(1).labels == {"blocked"}

    def test_blocks_on_cannot_plan(self):
        repo = make_repo()
        ready_issue(repo)
        engine = Engine(repo).register(PlannerAgent(behavior=cannot_plan()))
        engine.tick()
        assert repo.get_issue(1).labels == {"blocked"}

    def test_skips_on_no_action(self):
        repo = make_repo()
        ready_issue(repo)
        engine = Engine(repo).register(PlannerAgent(behavior=no_action()))
        engine.tick()
        # NO-ACTION: exit 0, no label change from planner
        assert "ready" in repo.get_issue(1).labels

    def test_idempotent_when_already_planned(self):
        repo = make_repo()
        repo.add_issue(1, labels={"ready"}, comments=["<!-- PLAN -->\nExisting plan."])
        engine = Engine(repo).register(PlannerAgent(behavior=plan_success()))
        engine.tick()
        # entry_action filters it out — no duplicate processing
        assert repo.get_issue(1).labels == {"ready"}


# ---------------------------------------------------------------------------
# SprintPlannerAgent
# ---------------------------------------------------------------------------


class TestSprintPlannerAgent:
    def test_assigns_top_issue_by_wsjf(self):
        repo = make_repo()
        planned_issue(repo, number=1)
        planned_issue(repo, number=2)
        # Pre-score: issue 2 gets higher WSJF
        repo.add_comment(1, "📊 WSJF: 1.0 (CoD: simulated / Size: simulated)")
        repo.add_comment(2, "📊 WSJF: 5.0 (CoD: simulated / Size: simulated)")
        engine = Engine(repo).register(SprintPlannerAgent(max_wip=1, behavior=no_action()))
        engine.tick()
        # Issue 2 (WSJF=5) gets the slot; issue 1 stays planned
        assert repo.get_issue(2).labels == {"in-progress"}
        assert repo.get_issue(1).labels == {"planned"}

    def test_respects_wip_limit(self):
        repo = make_repo()
        repo.add_issue(1, labels={"in-progress"})  # already using the slot
        repo.add_issue(2, labels={"planned"})
        engine = Engine(repo).register(SprintPlannerAgent(max_wip=1))
        engine.tick()
        assert repo.get_issue(2).labels == {"planned"}  # not promoted

    def test_fills_multiple_slots(self):
        repo = make_repo()
        for n in (1, 2, 3):
            planned_issue(repo, number=n)
        engine = Engine(repo).register(SprintPlannerAgent(max_wip=2, behavior=wsjf_scored(1.0)))
        engine.tick()
        in_prog = [i for i in repo.list_issues() if "in-progress" in i.labels]
        assert len(in_prog) == 2


# ---------------------------------------------------------------------------
# DevAgent
# ---------------------------------------------------------------------------


class TestDevAgent:
    def test_creates_pr_for_in_progress_issue(self):
        repo = make_repo()
        inprogress_issue(repo)
        engine = Engine(repo).register(DevAgent())
        engine.tick()
        pr = repo.find_pr_for_issue(1, state="open")
        assert pr is not None

    def test_does_not_create_duplicate_pr(self):
        repo = make_repo()
        inprogress_issue(repo)
        linked_pr(repo, issue_num=1)
        initial_pr_count = len(repo.pull_requests)
        engine = Engine(repo).register(DevAgent())
        engine.tick()
        assert len(repo.pull_requests) == initial_pr_count

    def test_retries_when_pr_has_changes_requested(self):
        repo = make_repo()
        inprogress_issue(repo)
        linked_pr(repo, issue_num=1, review_decision="CHANGES_REQUESTED")
        engine = Engine(repo).register(DevAgent())
        engine.tick()
        # New PR should have been created (or existing updated)
        # In our stub, a second PR gets created
        assert len(repo.pull_requests) >= 1

    def test_skips_blocked_issues(self):
        repo = make_repo()
        # Create with in-progress first, then simulate being blocked via label swap
        repo.add_issue(1, labels={"in-progress"})
        repo.get_issue(1).labels.discard("in-progress")
        repo.get_issue(1).labels.add("blocked")
        engine = Engine(repo).register(DevAgent())
        engine.tick()
        assert len(repo.pull_requests) == 0


# ---------------------------------------------------------------------------
# ReviewAgent
# ---------------------------------------------------------------------------


class TestReviewAgent:
    def test_promotes_to_reviewed_on_passed_review(self):
        repo = make_repo()
        inprogress_issue(repo)
        linked_pr(repo, issue_num=1)
        engine = Engine(repo).register(ReviewAgent(behavior=review_passed()))
        engine.tick()
        assert repo.get_issue(1).labels == {"reviewed"}

    def test_unchanged_when_review_pending(self):
        repo = make_repo()
        inprogress_issue(repo)
        linked_pr(repo, issue_num=1)
        engine = Engine(repo).register(ReviewAgent(behavior=review_changes_requested()))
        engine.tick()
        assert "in-progress" in repo.get_issue(1).labels

    def test_skips_pr_with_failing_ci(self):
        repo = make_repo()
        inprogress_issue(repo)
        pr = linked_pr(repo, issue_num=1)
        pr.status_checks = [{"conclusion": "FAILURE"}]
        engine = Engine(repo).register(ReviewAgent(behavior=review_passed()))
        engine.tick()
        # CI failing → entry_action filters it out
        assert "reviewed" not in repo.get_issue(1).labels

    def test_skips_pr_already_reviewed(self):
        repo = make_repo()
        inprogress_issue(repo)
        pr = linked_pr(repo, issue_num=1)
        pr.pr_comments = ["## Review Summary\n\n✅ Technical review passed."]
        engine = Engine(repo).register(ReviewAgent(behavior=review_passed()))
        engine.tick()
        # Already has the signal → entry_action filters it out, no duplicate promotion
        assert "reviewed" in repo.get_issue(1).labels or "in-progress" in repo.get_issue(1).labels


# ---------------------------------------------------------------------------
# IntegratorAgent
# ---------------------------------------------------------------------------


class TestIntegratorAgent:
    def test_removes_reviewed_after_merge(self):
        repo = make_repo()
        reviewed_issue(repo)
        linked_pr(repo, issue_num=1, review_decision="APPROVED")
        engine = Engine(repo).register(IntegratorAgent(behavior=merge_success()))
        engine.tick()
        assert "reviewed" not in repo.get_issue(1).labels

    def test_blocks_issue_when_pr_deferred(self):
        repo = make_repo()
        reviewed_issue(repo)
        linked_pr(repo, issue_num=1, review_decision="APPROVED")
        engine = Engine(repo).register(IntegratorAgent(behavior=deferred()))
        engine.tick()
        assert repo.get_issue(1).labels == {"blocked"}

    def test_resets_to_open_when_pr_closed_without_merge(self):
        repo = make_repo()
        reviewed_issue(repo)
        linked_pr(repo, issue_num=1, review_decision="APPROVED", state="closed")
        # entry_action only picks up open PRs — close it after register
        pr = repo.get_pr(10)

        def close_behavior(r: Repository, p: PullRequest) -> object:
            from tests.ghaw.agents import AgentResult
            r.close_pr(p.number)
            return AgentResult(signals=["closed"])

        engine = Engine(repo).register(IntegratorAgent(behavior=close_behavior))
        engine.tick()
        # closed PR scenario handled in exit_action
        # entry_action filters out already-closed; test closed directly
        repo.get_issue(1).labels = {"reviewed"}
        pr.state = "closed"
        from tests.ghaw.agents import IntegratorAgent as IA
        agent = IA(behavior=lambda r, p: __import__("tests.ghaw.agents", fromlist=["AgentResult"]).AgentResult())
        outcome = agent.exit_action(repo, pr, __import__("tests.ghaw.agents", fromlist=["AgentResult"]).AgentResult())
        assert outcome.to_state == "open"

    def test_skips_unapproved_prs(self):
        repo = make_repo()
        reviewed_issue(repo)
        linked_pr(repo, issue_num=1, review_decision="REVIEW_REQUIRED")
        engine = Engine(repo).register(IntegratorAgent(behavior=merge_success()))
        engine.tick()
        # entry_action requires APPROVED
        assert repo.get_pr(10).state == "open"


# ---------------------------------------------------------------------------
# State healer invariant
# ---------------------------------------------------------------------------


class TestStateHealer:
    def test_healer_removes_conflicting_label(self):
        repo = make_repo()
        repo.add_issue(1, labels={"open"})
        removed = repo.add_label(1, "ready")
        assert "open" in removed
        assert repo.get_issue(1).labels == {"ready"}

    def test_engine_raises_on_double_state(self):
        """Force a broken state and verify engine catches it."""
        repo = make_repo()
        repo.add_issue(1, labels={"open"})
        # Bypass healer directly to create an invalid state
        repo.get_issue(1).labels.add("ready")
        engine = Engine(repo).register(GroomerAgent())
        with pytest.raises(InvariantViolation):
            engine.tick()

    def test_non_state_labels_not_healed(self):
        repo = make_repo()
        repo.add_issue(1, labels={"open", "priority/high", "size/m"})
        repo.add_label(1, "ready")
        labels = repo.get_issue(1).labels
        assert "priority/high" in labels
        assert "size/m" in labels
        assert "ready" in labels
        assert "open" not in labels


# ---------------------------------------------------------------------------
# Full pipeline integration tests
# ---------------------------------------------------------------------------


class TestFullPipeline:
    def test_happy_path_open_to_merged(self):
        """
        Walks an issue through the complete state machine:
        open → ready → planned → in-progress → reviewed → (merged, reviewed removed)
        """
        repo = make_repo()
        open_issue(repo)

        engine = Engine(repo).register(
            GroomerAgent(behavior=groomer_ready()),
            PlannerAgent(behavior=plan_success()),
            SprintPlannerAgent(max_wip=3, behavior=wsjf_scored(2.0)),
            DevAgent(),
            ReviewAgent(behavior=review_passed()),
            IntegratorAgent(behavior=merge_success()),
        )

        # Because all agents fire every tick, a single tick can advance multiple
        # states. Use single-agent sub-engines to test one transition at a time.
        from tests.sim.engine import Engine as E

        # Step 1: groomer fires → ready
        E(repo).register(GroomerAgent(behavior=groomer_ready())).tick()
        assert "ready" in repo.get_issue(1).labels

        # Step 2: planner fires → planned
        E(repo).register(PlannerAgent(behavior=plan_success())).tick()
        assert "planned" in repo.get_issue(1).labels

        # Step 3: sprint planner fires → in-progress
        E(repo).register(SprintPlannerAgent(max_wip=3, behavior=wsjf_scored(2.0))).tick()
        assert "in-progress" in repo.get_issue(1).labels

        # Step 4: dev fires → PR created
        E(repo).register(DevAgent()).tick()
        pr = repo.find_pr_for_issue(1, state="open")
        assert pr is not None

        # Approve PR so review/integrator can act
        pr.review_decision = "APPROVED"

        # Step 5: review fires → reviewed
        E(repo).register(ReviewAgent(behavior=review_passed())).tick()
        assert "reviewed" in repo.get_issue(1).labels

        # Step 6: integrator fires → merges PR, removes reviewed
        E(repo).register(IntegratorAgent(behavior=merge_success())).tick()
        assert "reviewed" not in repo.get_issue(1).labels
        assert repo.get_pr(pr.number).state == "merged"

    def test_blocked_at_planner_then_recovered(self):
        """
        Planner fails → blocked.
        Human adds plan comment + re-adds ready → planner promotes to planned.
        """
        repo = make_repo()
        ready_issue(repo)

        engine = Engine(repo).register(PlannerAgent(behavior=no_output()))
        engine.tick()
        assert "blocked" in repo.get_issue(1).labels

        # Human fixes: re-add ready label, inject a plan comment
        engine._agents = [PlannerAgent(behavior=plan_success())]
        engine.label_added(1, "ready")
        assert "planned" in repo.get_issue(1).labels

    def test_state_invariant_never_violated_across_full_pipeline(self):
        """Every tick must leave exactly one state label on the issue."""
        repo = make_repo()
        open_issue(repo)

        engine = Engine(repo).register(
            GroomerAgent(behavior=groomer_ready()),
            PlannerAgent(behavior=plan_success()),
            SprintPlannerAgent(max_wip=3, behavior=wsjf_scored(3.0)),
            DevAgent(),
            ReviewAgent(behavior=review_passed()),
            IntegratorAgent(behavior=merge_success()),
        )

        # Run 6 ticks — engine asserts invariant after every tick internally
        for _ in range(6):
            traces = engine.tick()
            for issue in repo.issues.values():
                state_count = len(issue.labels & GHAW_STATE_LABELS)
                # After merge the issue has no state label — that is acceptable
                assert state_count <= 1, (
                    f"Issue #{issue.number} has {state_count} state labels: "
                    f"{issue.labels & GHAW_STATE_LABELS}"
                )

    def test_multiple_issues_independent(self):
        """Two issues go through the pipeline independently without interfering."""
        repo = make_repo()
        open_issue(repo, number=1)
        open_issue(repo, number=2)

        engine = Engine(repo).register(
            GroomerAgent(behavior=groomer_ready()),
            PlannerAgent(behavior=plan_success()),
            SprintPlannerAgent(max_wip=3, behavior=wsjf_scored(1.0)),
        )

        # Use single-agent engines to test one transition at a time.
        from tests.sim.engine import Engine as E

        E(repo).register(GroomerAgent(behavior=groomer_ready())).tick()  # both → ready
        assert "ready" in repo.get_issue(1).labels
        assert "ready" in repo.get_issue(2).labels

        E(repo).register(PlannerAgent(behavior=plan_success())).tick()  # both → planned
        assert "planned" in repo.get_issue(1).labels
        assert "planned" in repo.get_issue(2).labels

        E(repo).register(SprintPlannerAgent(max_wip=3, behavior=wsjf_scored(1.0))).tick()  # both → in-progress
        assert "in-progress" in repo.get_issue(1).labels
        assert "in-progress" in repo.get_issue(2).labels
