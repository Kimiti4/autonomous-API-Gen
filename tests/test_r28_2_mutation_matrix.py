"""R2.8.2 -- Test-Gaming Corpus: mutation matrix certification.

Asserts each matrix row's declared security property (not just an enum),
verifies the information-hiding boundary (mutation label never reaches the
decider), anchors immutability under mutation, and determinism.
"""
from __future__ import annotations

import pytest

from tiannara.application.evolution.adversarial_lab import (
    MutationLab,
    MutationSpec,
    MUTATION_MATRIX,
)
from tiannara.application.evolution.evaluation_boundary import ProtectedTestSet
from tiannara.domain.models.evidence import DriftClass


# -- the canonical surface: 3 protected-visible + 1 hidden + 1 evolvable ---------
# (composition is asserted once; the matrix trusts the surface author.)

def test_canonical_surface_composition():
    lab = MutationLab()
    ids = [t.test_id for t in lab.surface.identities]
    assert "fsm::transition_await_handles_final" in ids
    assert "fsm::holdout_state_coverage" in ids
    assert "ev::mutation_score_canary" in ids
    assert lab.surface.has_protected_core
    visible = [t.test_id for t in lab.surface.visible_to_evolution()]
    # hidden holdout material is read-isolated (run only by the authority)
    holdout = lab.boundary.holdout_surface(lab.surface)
    assert holdout.hidden_ids == ("fsm::holdout_state_coverage",)
    assert "fsm::holdout_state_coverage" not in visible


# -- matrix certification: each row's declared security property ----------------

@pytest.mark.parametrize("spec", MUTATION_MATRIX, ids=[s.mutation_id for s in MUTATION_MATRIX])
def test_matrix_row_asserts_security_property(spec: MutationSpec):
    lab = MutationLab()
    evidence = spec.apply(lab.surface, lab.baseline_run)
    decision = lab.decider.decide(lab.surface, lab.baseline_run, evidence)

    # feasibility
    expected_feasible = spec.expected_feasibility == "feasible"
    assert decision.feasible is expected_feasible, (
        f"{spec.mutation_id}: expected feasible={expected_feasible} "
        f"got {decision.feasible} ({decision.detail})"
    )

    # catching layers: the declared layers must be a subset of what actually caught
    assert set(spec.expected_catching_layers) <= set(decision.catching_layers), (
        f"{spec.mutation_id}: expected catching layers {spec.expected_catching_layers} "
        f"⊆ {decision.catching_layers}"
    )

    # holdout invariant: hidden tests never mutated by a visible-surface attack
    # (behavioral masks are expected to be caught HERE by holdout divergence)
    assert decision.holdout_intact is spec.expected_holdout_intact, (
        f"{spec.mutation_id}: expected holdout_intact={spec.expected_holdout_intact} "
        f"got {decision.holdout_intact}"
    )
    assert decision.read_isolated is True, (
        f"{spec.mutation_id}: hidden test id leaked into evolution evidence"
    )

    # drift-class contract
    if spec.expected_drift_class == "accepted":
        assert decision.drift.accept is True
    elif spec.expected_drift_class == "allowed_drift":
        assert decision.drift.accept is True
        assert "ev::mutation_score_canary" in decision.drift.allowed_drift
    elif spec.expected_drift_class == "preserved":
        assert decision.drift.accept is True
        assert len(decision.drift.preserved) > 0
    else:
        dc = DriftClass(spec.expected_drift_class)
        buckets = {
            DriftClass.REMOVED_TEST: decision.drift.removed,
            DriftClass.CONTENT_GUTTING: decision.drift.protected_rejected,
            DriftClass.HIDDEN_LEAK: decision.drift.hidden_leaks,
            DriftClass.REQUIRES_JUSTIFICATION: decision.drift.requires_justification,
        }
        assert dc in buckets, f"{spec.mutation_id}: drift class {dc} not bucketed"
        assert len(buckets[dc]) > 0 or dc == DriftClass.REQUIRES_JUSTIFICATION, (
            f"{spec.mutation_id}: expected drift class {dc} to fire, "
            f"catching={decision.catching_layers}"
        )
        assert decision.drift.accept is False


# -- adversarial rows are all rejected; controls are accepted -------------------

def test_all_adversarial_mutations_are_rejected():
    attacks = [s for s in MUTATION_MATRIX if not s.is_control]
    for spec in attacks:
        lab = MutationLab()
        evidence = spec.apply(lab.surface, lab.baseline_run)
        decision = lab.decider.decide(lab.surface, lab.baseline_run, evidence)
        assert decision.feasible is False, (
            f"{spec.mutation_id} slipped through: {decision.detail}"
        )


def test_controls_are_accepted():
    lab = MutationLab()
    for spec in MUTATION_MATRIX:
        if not spec.is_control:
            continue
        evidence = spec.apply(lab.surface, lab.baseline_run)
        decision = lab.decider.decide(lab.surface, lab.baseline_run, evidence)
        assert decision.feasible is True, (
            f"control {spec.mutation_id} rejected (false positive): {decision.detail}"
        )
        assert decision.catching_layers == ()


# -- determinism: same seed + mutation = same hash + same verdict ---------------

def test_matrix_is_deterministic():
    """R2.8.12: same mutation -> identical candidate evidence hash + identical verdict."""
    for spec in MUTATION_MATRIX:
        lab1 = MutationLab()
        lab2 = MutationLab()
        e1 = spec.apply(lab1.surface, lab1.baseline_run)
        e2 = spec.apply(lab2.surface, lab2.baseline_run)
        d1 = lab1.decider.decide(lab1.surface, lab1.baseline_run, e1)
        d2 = lab2.decider.decide(lab2.surface, lab2.baseline_run, e2)
        assert e1.content_hash() == e2.content_hash(), f"{spec.mutation_id}: evidence hash differs"
        assert d1.feasible == d2.feasible
        assert d1.catching_layers == d2.catching_layers


# -- anchor immutability: mutations never touch the protected core --------------

def test_mutation_never_mutates_anchored_core():
    """R2.7.5-G invariant: the anchored protected core is read-only during evolution.

    Running every mutation must not change the surface's content hash or the
    ledger's anchored ANCHOR event hash (cascade-on-tamper integrity holds).
    """
    lab = MutationLab()
    anchor_hash_before = lab.surface.content_hash
    event_hash_before = lab.ledger.events()[0].event_hash
    for spec in MUTATION_MATRIX:
        evidence = spec.apply(lab.surface, lab.baseline_run)
        lab.decider.decide(lab.surface, lab.baseline_run, evidence)

    assert lab.surface.content_hash == anchor_hash_before, "protected core content hash changed"
    assert lab.ledger.events()[0].event_hash == event_hash_before, "anchor event hash changed"
    assert lab.ledger.verify_event_chain()
