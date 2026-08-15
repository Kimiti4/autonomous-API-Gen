"""R2.7.5-G -- Evaluation Trust Boundary.

Covers:
  * TestIdentity / Provenance / Visibility policy invariants.
  * EvaluationBoundary.anchor(): the non-empty protected-core guarantee
    (content-hash pinned to the canonical ledger via an ANCHOR event).
  * classify_drift(): policy-driven drift classification against the
    anchored protected core -- protected gutting/deletion rejected, hidden
    leaks rejected, evolvable drift flagged then allowed under causal
    justification.

Only the canonical in-memory ledger is used (no Docker): anchor() writes a real
anchored EvolutionEvent into the event chain, so the protected core is bound by
cascade-on-tamper integrity, exercising the boundary in isolation.
"""
from __future__ import annotations

import pytest

from tiannara.application.evolution.evaluation_boundary import (
    EvaluationAuthority,
    EvaluationBoundary,
    HoldoutSurface,
    ReadIsolationResult,
)
from tiannara.application.evolution.ledger import EvolutionLedger
from tiannara.domain.models.evidence import (
    Provenance,
    TestExecution,
    TestIdentity,
    TestOutcome,
    Visibility,
)


@pytest.fixture
def authority() -> EvaluationAuthority:
    return EvaluationAuthority()


@pytest.fixture
def boundary(authority) -> EvaluationBoundary:
    # Real in-memory ledger (root=None): exercises the actual canonical
    # event-chain (parent_event_id -> computed_hash) that anchors the protected
    # core. No Docker / no backing file required.
    return EvaluationBoundary(authority=authority, ledger=EvolutionLedger(), evolution_id="ev-1")


# -- policy invariants --------------------------------------------------------

def test_default_identity_is_evolvable_and_visible():
    ti = TestIdentity.from_provenance("t1", Provenance.ISR_GENERATED, content_hash="abc")
    assert ti.is_protected() is False
    assert ti.is_hidden() is False
    assert ti.protected is False
    assert ti.visibility == Visibility.VISIBLE
    assert ti.provenance == Provenance.ISR_GENERATED


def test_eval_authority_holdout_is_protected_and_hidden():
    ei = TestIdentity.from_provenance(
        "e1", Provenance.EVALUATION_AUTHORITY, content_hash="xyz",
        visibility=Visibility.HIDDEN,
    )
    assert ei.is_protected()
    assert ei.is_hidden()


def test_evolvable_plus_hidden_is_disallowed_by_construction():
    with pytest.raises(ValueError, match="evolvable \\+ hidden"):
        TestIdentity.from_provenance("bad", Provenance.ISR_GENERATED, visibility=Visibility.HIDDEN)


def test_protected_flag_must_match_provenance():
    with pytest.raises(ValueError, match="protection is granted only"):
        TestIdentity(test_id="bad", provenance=Provenance.EVALUATION_AUTHORITY, protected=False)


# -- anchoring / protected-core invariant ------------------------------------

def test_anchor_binds_protected_core_and_hides_holdout_from_evolution(boundary, authority):
    ps = boundary.anchor(
        (
            authority.identity("regress_1", "h_regress_1", visibility=Visibility.VISIBLE),
            authority.identity("holdout_1", "h_holdout_1", visibility=Visibility.HIDDEN),
        ),
        environment_fingerprint="fp-1",
    )
    assert ps.has_protected_core
    assert len(ps.protected_core) == 2
    assert [t.test_id for t in ps.visible_to_evolution()] == ["regress_1"]
    assert all(t.anchor_event_id == ps.anchor_event_id for t in ps.identities)
    assert ps.anchor_event_id  # a real event_id was minted by the ledger


def test_empty_protected_core_rejected_at_anchor(boundary, authority):
    ev = TestIdentity.from_provenance("ev", Provenance.ISR_GENERATED, content_hash="h")
    with pytest.raises(ValueError, match="non-empty protected core"):
        boundary.anchor((ev,))


# -- drift policy: rejects ---------------------------------------------------

def test_hidden_holdout_leak_rejects_and_preserves_visible(boundary, authority):
    ps = boundary.anchor((
        authority.identity("regress_1", "h_regress_1", visibility=Visibility.VISIBLE),
        authority.identity("holdout_1", "h_holdout_1", visibility=Visibility.HIDDEN),
    ))
    dr = boundary.classify_drift(ps, (
        TestExecution(test_id="regress_1", outcome=TestOutcome.PASSED, content_hash="h_regress_1"),
        TestExecution(test_id="holdout_1", outcome=TestOutcome.PASSED, content_hash="h_holdout_1"),
    ))
    assert dr.accept is False
    assert "holdout_1" in dr.hidden_leaks
    assert "regress_1" in dr.preserved


def test_protected_content_gutting_rejects(boundary, authority):
    ps = boundary.anchor((
        authority.identity("regress_1", "h_regress_1", visibility=Visibility.VISIBLE),
        authority.identity("holdout_1", "h_holdout_1", visibility=Visibility.HIDDEN),
    ))
    dr = boundary.classify_drift(ps, (
        TestExecution(test_id="regress_1", outcome=TestOutcome.PASSED, content_hash="GUTTED"),
    ))
    assert dr.accept is False
    assert "regress_1" in dr.protected_rejected
    # holdout_1 (hidden) is out of the candidate surface -> not a removal
    assert "holdout_1" not in dr.removed


def test_protected_visible_removal_rejects(boundary, authority):
    ps = boundary.anchor((
        authority.identity("regress_1", "h_regress_1", visibility=Visibility.VISIBLE),
        authority.identity("holdout_1", "h_holdout_1", visibility=Visibility.HIDDEN),
    ))
    dr = boundary.classify_drift(ps, ())  # candidate run vanishes
    assert dr.accept is False
    assert "regress_1" in dr.removed
    assert "holdout_1" not in dr.removed  # hidden holdout never in candidate surface


# -- drift policy: evolvable (not auto-rejected) -----------------------------

def _evolvable_surface(boundary, authority):
    ev = TestIdentity.from_provenance("ev_1", Provenance.ISR_GENERATED, content_hash="h_ev")
    r_2 = authority.identity("r_2", "h_r2", visibility=Visibility.VISIBLE)
    ps = boundary.anchor((ev, r_2))
    return ps, ev, r_2


def test_evolvable_drift_without_justification_is_flagged_not_rejected(boundary, authority):
    ps, _ev, r_2 = _evolvable_surface(boundary, authority)
    dr = boundary.classify_drift(ps, (
        TestExecution(test_id="r_2", outcome=TestOutcome.PASSED, content_hash="h_r2"),
        TestExecution(test_id="ev_1", outcome=TestOutcome.PASSED, content_hash="h_ev_CHANGED"),
    ))
    assert dr.accept is True
    assert "ev_1" in dr.requires_justification
    assert "r_2" in dr.preserved


def test_evolvable_drift_with_justification_is_allowed(boundary, authority):
    ps, _ev, r_2 = _evolvable_surface(boundary, authority)
    dr = boundary.classify_drift(ps, (
        TestExecution(test_id="r_2", outcome=TestOutcome.PASSED, content_hash="h_r2"),
        TestExecution(test_id="ev_1", outcome=TestOutcome.PASSED, content_hash="h_ev_CHANGED"),
    ), causal_justification=True)
    assert dr.accept is True
    assert "ev_1" in dr.allowed_drift


def test_evolvable_unchanged_is_preserved(boundary, authority):
    ps, _ev, r_2 = _evolvable_surface(boundary, authority)
    dr = boundary.classify_drift(ps, (
        TestExecution(test_id="r_2", outcome=TestOutcome.PASSED, content_hash="h_r2"),
        TestExecution(test_id="ev_1", outcome=TestOutcome.PASSED, content_hash="h_ev"),
    ))
    assert dr.accept is True
    assert "ev_1" in dr.preserved
    assert "r_2" in dr.preserved


# -- visible_test_ids helper -------------------------------------------------

def test_visible_test_ids_excludes_hidden():
    from tiannara.application.evolution.evaluation_boundary import visible_test_ids
    ids = visible_test_ids((
        TestIdentity.from_provenance("a", Provenance.ISR_GENERATED, visibility=Visibility.VISIBLE),
        TestIdentity.from_provenance("b", Provenance.EVALUATION_AUTHORITY, visibility=Visibility.HIDDEN),
    ))
    assert ids == ("a",)


# -- R2.8.7: hidden / holdout read-isolation ------------------------------------

def test_holdout_surface_contains_only_hidden_tests(boundary, authority):
    ps = boundary.anchor((
        authority.identity("regress_1", "h_r1", visibility=Visibility.VISIBLE),
        authority.identity("holdout_1", "h_h1", visibility=Visibility.HIDDEN),
        authority.identity("holdout_2", "h_h2", visibility=Visibility.HIDDEN),
    ))
    ho = boundary.holdout_surface(ps)
    assert isinstance(ho, HoldoutSurface)
    assert ho.hidden_ids == ("holdout_1", "holdout_2")
    assert ho.hidden_hashes == ("h_h1", "h_h2")
    # holdout set is content-hash pinned as a unit for tamper detection
    assert ho.content_hash


def test_read_isolation_rejects_operators_that_observed_hidden(boundary, authority):
    ps = boundary.anchor((
        authority.identity("regress_1", "h_r1", visibility=Visibility.VISIBLE),
        authority.identity("holdout_1", "h_h1", visibility=Visibility.HIDDEN),
    ))
    # Operator handed the hidden id it must never have seen -> leak.
    bad = boundary.read_isolation_report(ps, ("regress_1", "holdout_1"))
    assert isinstance(bad, ReadIsolationResult)
    assert bad.accept is False
    assert bad.leaked_hidden == ("holdout_1",)
    # Operator handed only visible surface -> clean.
    good = boundary.read_isolation_report(ps, ("regress_1",))
    assert good.accept is True
    assert good.leaked_hidden == ()


def test_hidden_holdout_content_hash_is_anchored_in_ledger(boundary, authority):
    """R2.8.7: hidden hashes must be anchored -- tamper with a holdout is a chain break.

    The anchor event's payload carries every identity (incl. hidden) with its
    content_hash, so the holdout material is committed to the canonical chain
    and verified by verify_event_chain().
    """
    ps = boundary.anchor((
        authority.identity("regress_1", "h_r1", visibility=Visibility.VISIBLE),
        authority.identity("holdout_1", "h_h1", visibility=Visibility.HIDDEN),
    ))
    ledger = boundary.ledger
    assert ledger.event_count == 1
    assert ledger.verify_event_chain()

    event = ledger.events()[0]
    ids = {i["test_id"]: i for i in event.payload["identities"]}
    assert ids["holdout_1"]["content_hash"] == "h_h1"
    assert ids["holdout_1"]["visibility"] == "hidden"
    assert ids["holdout_1"]["provenance"] == "evaluation_authority"

    # Tampering the anchored hidden content_hash must break chain verification:
    # is_intact() recomputes event_hash from the (now altered) payload content,
    # so the stored hash no longer matches -> cascade-on-tamper detects it.
    tampered_payload = {
        **event.payload,
        "identities": list(event.payload["identities"]),
    }
    tampered_payload["identities"][1] = {
        **tampered_payload["identities"][1], "content_hash": "TAMPERED",
    }
    tampered = event.model_copy(update={"payload": tampered_payload})
    ledger._events[0] = tampered
    assert not tampered.is_intact()
    assert not ledger.verify_event_chain()
