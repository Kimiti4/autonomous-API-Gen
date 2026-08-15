"""Phase 28 - VotingSystem unit + property-based verification."""

from datetime import datetime, timedelta, timezone

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from constitutional_architecture.governance.schemas import (
    ApprovalStageISR,
    ApprovalWorkflowISR,
    VotingRuleKind,
)
from constitutional_architecture.governance.voting import (
    Ballot,
    VotingError,
    VotingSystem,
)

T0 = datetime(2026, 8, 7, 12, 0, tzinfo=timezone.utc)
VOTERS = ("a", "b", "c", "d", "e")


def make_workflow(rule=VotingRuleKind.SIMPLE_MAJORITY, voters=VOTERS[:3],
                  quorum=2, deadline=None, weights=None):
    stage = ApprovalStageISR(stage_id="s1", approvers=list(voters),
                             rule=rule, weights=weights or {})
    return ApprovalWorkflowISR(workflow_id="wf-1", purpose="test",
                               stages=[stage], quorum=quorum, deadline=deadline)


def ballots(votes: dict[str, bool], stage_id: str = "s1") -> list[Ballot]:
    return [
        Ballot(ballot_id=f"b-{voter}", stage_id=stage_id, voter=voter,
               approve=approve, cast_at=T0)
        for voter, approve in votes.items()
    ]


def test_simple_majority_approves():
    outcome = VotingSystem().conduct_vote(
        make_workflow(), ballots({"a": True, "b": True, "c": False}), T0)
    assert outcome.approved and outcome.reason == "all_stages_approved"


def test_tie_fails_closed():
    outcome = VotingSystem().conduct_vote(
        make_workflow(quorum=1), ballots({"a": True, "b": False}), T0)
    assert not outcome.approved
    assert "tie_or_minority" in outcome.reason


def test_unanimity_rejects_single_dissent():
    outcome = VotingSystem().conduct_vote(
        make_workflow(rule=VotingRuleKind.UNANIMITY),
        ballots({"a": True, "b": True, "c": False}), T0)
    assert not outcome.approved
    assert "unanimity_broken" in outcome.reason


def test_weighted_majority_respects_weights():
    system = VotingSystem()
    weights = {"a": 10.0, "b": 1.0, "c": 1.0}
    workflow = make_workflow(rule=VotingRuleKind.WEIGHTED_MAJORITY, weights=weights)
    approved = system.conduct_vote(workflow, ballots({"a": True, "b": False, "c": False}), T0)
    denied = system.conduct_vote(workflow, ballots({"a": False, "b": True, "c": True}), T0)
    assert approved.approved and not denied.approved


def test_quorum_shortfall_denies():
    outcome = VotingSystem().conduct_vote(make_workflow(quorum=3), ballots({"a": True}), T0)
    assert not outcome.approved
    assert "quorum_not_met" in outcome.reason


def test_expired_deadline_denies():
    workflow = make_workflow(deadline=T0)
    outcome = VotingSystem().conduct_vote(
        workflow, ballots({"a": True, "b": True}), T0 + timedelta(seconds=1))
    assert not outcome.approved and outcome.reason == "deadline_expired"


def test_late_ballots_are_ignored():
    workflow = make_workflow(deadline=T0 + timedelta(hours=1), quorum=1)
    late = Ballot(ballot_id="b-late", stage_id="s1", voter="c",
                  approve=True, cast_at=T0 + timedelta(hours=2))
    outcome = VotingSystem().conduct_vote(workflow, [late] + ballots({"a": True}), T0)
    assert outcome.approved
    assert outcome.stage_results[0].participating == 1


def test_unknown_stage_rejected():
    with pytest.raises(VotingError, match="unknown_stage"):
        VotingSystem().conduct_vote(make_workflow(), ballots({"a": True}, stage_id="ghost"), T0)


def test_duplicate_voter_rejected():
    dupes = ballots({"a": True}) + ballots({"a": False})
    with pytest.raises(VotingError, match="duplicate_voter"):
        VotingSystem().conduct_vote(make_workflow(), dupes, T0)


@given(data=st.data())
@settings(max_examples=50)
def test_vote_is_deterministic_under_ballot_order(data):
    approvals = data.draw(st.lists(st.booleans(), min_size=len(VOTERS), max_size=len(VOTERS)))
    base = ballots(dict(zip(VOTERS, approvals)))
    permuted = data.draw(st.permutations(base))
    system, workflow = VotingSystem(), make_workflow(voters=VOTERS, quorum=3)
    first = system.conduct_vote(workflow, base, T0)
    second = system.conduct_vote(workflow, permuted, T0)
    assert first.approved == second.approved
    assert first.reason == second.reason


@given(data=st.data())
@settings(max_examples=50)
def test_fail_closed_monotonicity(data):
    """Flipping an approval to a denial can never turn a denial into an approval."""
    approvals = data.draw(st.lists(st.booleans(), min_size=len(VOTERS), max_size=len(VOTERS)))
    index = data.draw(st.integers(min_value=0, max_value=len(VOTERS) - 1))
    votes = dict(zip(VOTERS, approvals))
    system, workflow = VotingSystem(), make_workflow(voters=VOTERS, quorum=1)
    original = system.conduct_vote(workflow, ballots(votes), T0)
    if votes[VOTERS[index]]:
        votes[VOTERS[index]] = False
        weakened = system.conduct_vote(workflow, ballots(votes), T0)
        assert not (weakened.approved and not original.approved)
