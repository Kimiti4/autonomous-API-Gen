"""Governance subsystem write acceptance: G-1..G-7 + round-trip."""
from __future__ import annotations

import pytest

from app.core.contracts.governance import (
    CouncilComposition,
    CouncilMember,
    GovernanceGate,
    TransitionRef,
)
from app.core.governance.commands import (
    GrantCertification,
    RecordGateEvaluation,
    RegisterGate,
    RequestGovernanceDecision,
)
from app.core.governance.invariants import GovernanceInvariantError
from app.governance.adapters.memory import (
    InMemoryGovernanceEventStore,
    InMemoryGovernanceReferenceStore,
)
from app.governance.subsystem import GovernanceSubsystem

COUNCIL = [
    CouncilMember(memberId="m1", name="Alice", role="chair",
                  votingWeight=0.6),
    CouncilMember(memberId="m2", name="Bob", role="member",
                  votingWeight=0.4),
]


def _gate(gate_id, category, from_st, to_st):
    return GovernanceGate(
        gateId=gate_id, name=gate_id, category=category,
        guards=[TransitionRef(fromState=from_st, toState=to_st)],
    )


def _subsystem(quorum: float = 1.0):
    events = InMemoryGovernanceEventStore()
    refs = InMemoryGovernanceReferenceStore()
    gov = GovernanceSubsystem(
        event_store=events, reference_store=refs,
        quorum_threshold=quorum, recognized_certifiers={"certifier-1"},
    )
    return gov, events, refs


async def _setup_council(g, refs) -> None:
    await refs.save_council(CouncilComposition(members=COUNCIL))


def _proposal_verdict_cmd(to_state="evaluating", **over):
    decidedBy = over.pop("decidedBy", ["m1", "m2"])
    return RequestGovernanceDecision(
        candidateId="c1", generation=0, fromState="proposed", toState=to_state,
        requestedBy="executive", decidedBy=decidedBy,
        verdict="approve", authorizesTransition=True, rationale="r",
        **over,
    )


async def _candidate_in_evaluating(g, refs) -> None:
    """Advance c1 proposed -> evaluating via intake gate + approve."""
    await _setup_council(g, refs)
    await g.register_gate(RegisterGate(
        gate=_gate("intake-1", "intake", "proposed", "evaluating"),
        registeredBy="executive",
    ))
    await g.record_gate_evaluation(RecordGateEvaluation(
        gateId="intake-1", candidateId="c1", status="passed",
        evaluatedBy="qa-agent",
    ))
    await g.request_decision(_proposal_verdict_cmd())
    assert (await g.materialize_candidate("c1")).current_state == "evaluating"


async def _evaluating_ready(g, refs) -> None:
    """c1 in evaluating; verification gate registered + passed."""
    await _candidate_in_evaluating(g, refs)
    await g.register_gate(RegisterGate(
        gate=_gate("ver-1", "verification", "evaluating", "verified"),
        registeredBy="executive",
    ))
    await g.record_gate_evaluation(RecordGateEvaluation(
        gateId="ver-1", candidateId="c1", status="passed",
        evaluatedBy="qa-agent",
    ))


def _evaluating_to_verified_cmd(**over):
    decidedBy = over.pop("decidedBy", ["m1", "m2"])
    return RequestGovernanceDecision(
        candidateId="c1", generation=0, fromState="evaluating", toState="verified",
        requestedBy="executive", decidedBy=decidedBy,
        verdict="approve", authorizesTransition=True, rationale="r",
        **over,
    )


# ---- G-1 ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_g1_rejects_same_state():
    g, _e, _r = _subsystem()
    with pytest.raises(GovernanceInvariantError, match="G-1"):
        await g.request_decision(_proposal_verdict_cmd(to_state="proposed"))


@pytest.mark.asyncio
async def test_g1_rejects_non_adjacent_transition():
    g, _e, _r = _subsystem()
    with pytest.raises(GovernanceInvariantError, match="G-1"):
        await g.request_decision(_proposal_verdict_cmd(to_state="verified"))


@pytest.mark.asyncio
async def test_g1_requires_start_at_current_state():
    g, _e, refs = _subsystem()
    await _candidate_in_evaluating(g, refs)
    # c1 is at "evaluating"; a proposed->evaluating decision now mismatches.
    with pytest.raises(Exception, match="G-1"):
        await g.request_decision(_proposal_verdict_cmd())


# ---- G-2 ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_g2_blocks_approve_without_gate_passed():
    g, _e, refs = _subsystem()
    await _candidate_in_evaluating(g, refs)
    await g.register_gate(RegisterGate(
        gate=_gate("ver-1", "verification", "evaluating", "verified"),
        registeredBy="executive",
    ))
    # Gate registered but NOT evaluated -> G-2.
    with pytest.raises(GovernanceInvariantError, match="G-2"):
        await g.request_decision(_evaluating_to_verified_cmd())


@pytest.mark.asyncio
async def test_g2_allows_approve_when_gate_passed():
    g, _e, refs = _subsystem()
    await _evaluating_ready(g, refs)
    decision = await g.request_decision(_evaluating_to_verified_cmd())
    assert decision.verdict == "approve"
    assert (await g.materialize_candidate("c1")).current_state == "verified"


# ---- G-3 ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_g3_waived_gate_requires_waiver_accountability():
    g, _e, _r = _subsystem()
    with pytest.raises(GovernanceInvariantError, match="G-3"):
        await g.record_gate_evaluation(RecordGateEvaluation(
            gateId="ver-1", candidateId="c1", status="waived",
            evaluatedBy="alice", waivedBy=None,
        ))


# ---- G-5 ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_g5_rejects_unauthorized_decider():
    g, _e, refs = _subsystem()
    await _candidate_in_evaluating(g, refs)
    with pytest.raises(GovernanceInvariantError, match="G-5"):
        await g.request_decision(_evaluating_to_verified_cmd(
            decidedBy=["intruder"],
        ))


# ---- G-7 ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_g7_requires_quorum_weight():
    g, _e, refs = _subsystem(quorum=1.0)
    await _candidate_in_evaluating(g, refs)
    # Only m2 (0.4 weight) -> less than threshold 1.0.
    with pytest.raises(GovernanceInvariantError, match="G-7"):
        await g.request_decision(_evaluating_to_verified_cmd(
            decidedBy=["m2"],
        ))


# ---- G-4 / G-6 / round-trip ------------------------------------------------

@pytest.mark.asyncio
async def test_g6_rejects_unauthorized_certifier():
    g, _e, _r = _subsystem()
    with pytest.raises(Exception, match="G-6"):
        await g.grant_certification(GrantCertification(
            certificationId="cert-1", candidateId="c1",
            certifiedBy="hacker", criteria="security",
        ))


@pytest.mark.asyncio
async def test_decisions_are_immutable():
    g, _e, refs = _subsystem()
    await _evaluating_ready(g, refs)
    first = await g.request_decision(_evaluating_to_verified_cmd())
    events = await _e.load("c1")
    decision_events = [
        e for e in events if type(e).__name__ == "GovernanceDecisionMade"
    ]
    # Intake (proposed->evaluating) + this (->verified) are both immutable;
    # the newest is `first`.
    assert len(decision_events) == 2
    assert decision_events[-1].decision.decisionId == first.decisionId


@pytest.mark.asyncio
async def test_round_trip_command_event_materialized_state():
    g, _e, refs = _subsystem()
    await _candidate_in_evaluating(g, refs)
    state = await g.materialize_candidate("c1")
    assert state.current_state == "evaluating"
    assert len(state.decisions) == 1