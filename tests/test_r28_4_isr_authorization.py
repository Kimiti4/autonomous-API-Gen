"""R2.8.4 -- ISR-Authoritative Mutation Authorization.

Covers:
  * FSMTestSurfaceProjector: deterministic, Docker-free ISR-delta -> test-id
    projection (behavior-transition diff -> ``ev::<from>_to_<to>``).
  * Authorization.from_delta: ISR-derived grant construction (parent/candidate
    hashes, delta hash, authorized test-id set).
  * regression_infeasible_with_auth: R2.7+R2.8.4 gate semantics (no-auth
    falls back to original R2.7 reject, authorized evolvable gutting is
    permitted, everything else stays infeasible).
"""
from __future__ import annotations

import pytest

from constitutional_architecture.isr.model import (
    ISR, Module, System, Workflow, WorkflowState, WorkflowTransition,
)
from constitutional_architecture.isr.model.workflow import StateType
from tiannara.application.evolution.authorization import (
    Authorization,
    FSMTestSurfaceProjector,
    regression_infeasible_with_auth,
)
from tiannara.domain.models.evidence import (
    RegressionClass,
    RegressionResult,
    TestOutcome,
)
from tiannara.application.evolution.ledger import stable_isr_hash


# -- ISR fixtures ----------------------------------------------------------------

def _ts(tid: str) -> WorkflowState:
    if tid == "fin":
        return WorkflowState(id=tid, name="fin", state_type=StateType.FINAL)
    return WorkflowState(id=tid, name=tid, state_type=StateType.INTERMEDIATE)


def _make_isr(transitions: tuple[WorkflowTransition, ...]) -> ISR:
    states = tuple(
        {s for t in transitions for s in (t.from_state_id, t.to_state_id)}
    )
    unique_states = []
    seen = set()
    for s in states:
        if s not in seen:
            seen.add(s)
            unique_states.append(_ts(s))
    wf = Workflow(id="wf", name="wf", states=tuple(unique_states),
                  transitions=transitions)
    return ISR(system=System(id="s", name="S",
                             modules=(Module(id="m", name="M", workflows=(wf,)),)))


def _parent_isr() -> ISR:
    return _make_isr((
        WorkflowTransition(id="t1", name="submit", from_state_id="start",
                           to_state_id="processing"),
        WorkflowTransition(id="t2", name="done", from_state_id="processing",
                           to_state_id="fin"),
    ))


def _candidate_add_transition_isr() -> ISR:
    """Same as parent plus a new transition (``start -> canceled``)."""
    return _make_isr((
        WorkflowTransition(id="t1", name="submit", from_state_id="start",
                           to_state_id="processing"),
        WorkflowTransition(id="t2", name="done", from_state_id="processing",
                           to_state_id="fin"),
        WorkflowTransition(id="t3", name="cancel", from_state_id="start",
                           to_state_id="canceled"),
    ))


def _candidate_remove_transition_isr() -> ISR:
    """Same as parent but with one transition removed (``processing -> fin``)."""
    return _make_isr((
        WorkflowTransition(id="t1", name="submit", from_state_id="start",
                           to_state_id="processing"),
    ))


# -- FSMTestSurfaceProjector ----------------------------------------------------

def test_projector_detects_added_transition():
    proj = FSMTestSurfaceProjector()
    auth = Authorization.from_delta(_parent_isr(), _candidate_add_transition_isr(), proj)
    assert auth.authorized_test_ids == frozenset({"ev::start_to_canceled"})


def test_projector_detects_removed_transition():
    proj = FSMTestSurfaceProjector()
    auth = Authorization.from_delta(_parent_isr(), _candidate_remove_transition_isr(), proj)
    assert auth.authorized_test_ids == frozenset({"ev::processing_to_fin"})


def test_projector_identity_delta_authorizes_empty():
    proj = FSMTestSurfaceProjector()
    parent = _parent_isr()
    auth = Authorization.from_delta(parent, parent, proj)
    assert auth.authorized_test_ids == frozenset()


def test_projector_does_not_authorize_unrelated_test_ids():
    """A transition that didn't change must not be authorized."""
    proj = FSMTestSurfaceProjector()
    auth = Authorization.from_delta(_parent_isr(), _candidate_add_transition_isr(), proj)
    assert "ev::processing_to_fin" not in auth.authorized_test_ids


# -- Authorization.from_delta --------------------------------------------------

def test_from_delta_hashes_are_stable_and_distinct():
    proj = FSMTestSurfaceProjector()
    parent = _parent_isr()
    candidate = _candidate_add_transition_isr()
    auth = Authorization.from_delta(parent, candidate, proj)
    assert auth.parent_isr_hash == stable_isr_hash(parent)
    assert auth.candidate_isr_hash == stable_isr_hash(candidate)
    assert auth.delta_hash  # non-empty
    assert auth.parent_isr_hash != auth.candidate_isr_hash


def test_from_delta_authorization_hash_is_deterministic():
    proj = FSMTestSurfaceProjector()
    parent = _parent_isr()
    candidate = _candidate_add_transition_isr()
    auth1 = Authorization.from_delta(parent, candidate, proj)
    auth2 = Authorization.from_delta(parent, candidate, proj)
    assert auth1.authorization_hash == auth2.authorization_hash


# -- regression_infeasible_with_auth -------------------------------------------

def _reg_result(class_counts: dict[str, int],
                gutting: tuple[str, ...] = ()) -> RegressionResult:
    return RegressionResult(
        baseline_id="b1",
        class_counts=class_counts,
        gutting=gutting,
        accept=not any(
            RegressionClass(k) in {RegressionClass.CONTENT_GUTTING, RegressionClass.NEW_FAILURE}
            for k in class_counts
        ),
    )


def test_no_authorization_falls_back_to_r27():
    """With authorization=None, any reject-class is infeasible (original R2.7)."""
    reg = _reg_result({RegressionClass.CONTENT_GUTTING.value: 1}, gutting=("t::a",))
    assert regression_infeasible_with_auth(reg, None)


def test_authorized_evolvable_gutting_is_feasible():
    """Gutting of an authorized test id is permitted (R2.7.5-G)."""
    reg = _reg_result({RegressionClass.CONTENT_GUTTING.value: 1}, gutting=("ev::a_to_b",))
    auth = Authorization(
        parent_isr_hash="p", candidate_isr_hash="c", delta_hash="d",
        authorized_test_ids=frozenset({"ev::a_to_b"}),
    )
    assert not regression_infeasible_with_auth(reg, auth)


def test_unauthorized_evolvable_gutting_is_infeasible():
    """Gutting of a test NOT authorized by the ISR delta stays infeasible."""
    reg = _reg_result({RegressionClass.CONTENT_GUTTING.value: 1}, gutting=("ev::a_to_b",))
    auth = Authorization(
        parent_isr_hash="p", candidate_isr_hash="c", delta_hash="d",
        authorized_test_ids=frozenset({"ev::c_to_d"}),
    )
    assert regression_infeasible_with_auth(reg, auth)


def test_protected_regression_still_infeasible_with_auth():
    """New failure is always infeasible even with a broad authorization."""
    reg = _reg_result({RegressionClass.NEW_FAILURE.value: 1}, gutting=())
    auth = Authorization(
        parent_isr_hash="p", candidate_isr_hash="c", delta_hash="d",
        authorized_test_ids=frozenset({"ev::anything"}),
    )
    assert regression_infeasible_with_auth(reg, auth)


def test_partial_gutting_infeasible():
    """Gutting of one authorized + one unauthorized test is infeasible."""
    reg = _reg_result({RegressionClass.CONTENT_GUTTING.value: 2},
                      gutting=("ev::a_to_b", "protected::c"))
    auth = Authorization(
        parent_isr_hash="p", candidate_isr_hash="c", delta_hash="d",
        authorized_test_ids=frozenset({"ev::a_to_b"}),
    )
    assert regression_infeasible_with_auth(reg, auth)


def test_no_reject_classes_is_feasible():
    """No reject-class present -> always feasible."""
    reg = _reg_result({RegressionClass.PRESERVED_PASS.value: 3})
    auth = Authorization(
        parent_isr_hash="p", candidate_isr_hash="c", delta_hash="d",
        authorized_test_ids=frozenset(),
    )
    assert not regression_infeasible_with_auth(reg, auth)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
