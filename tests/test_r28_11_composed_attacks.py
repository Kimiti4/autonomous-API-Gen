"""R2.8.11 -- Adversarial composition tests.

Asserts that composed attacks are rejected, that defense-in-depth holds (no
expected layer goes silent), that the composer introduces no false positives,
and that the information-hiding boundary survives composition.
"""
import dataclasses

import pytest

from tiannara.application.evolution.adversarial_lab import (
    MutationLab,
    MutationSpec,
    CandidateEvidence,
    COMPOSED_MATRIX,
)
from tiannara.adversarial import (
    AttackPrimitive as P,
    DefenseLayer as D,
    analyze_composition,
    vulnerable_matrix,
    hardened_matrix,
    rooted_matrix,
    COMPOSITION_MATRIX,
)


# --- fixture ---------------------------------------------------------------

@pytest.fixture()
def lab():
    return MutationLab()


# --- the progression that motivates defense-in-depth ----------------------

def test_single_layer_is_bypassable_by_composition():
    """ARCH_BOUNDARY_REMOVAL + ATTACK_GATE_CONFIG slips past vulnerable_matrix:
    the gate-config attack disables the only layer (architectural) that catches
    boundary removal."""
    from tiannara.adversarial import CompositeAttack
    attack = CompositeAttack(
        composition_id="gate_bypass",
        primitives=(P.ARCH_BOUNDARY_REMOVAL, P.ATTACK_GATE_CONFIG),
        expected_defeated=True,
        expected_catching_layers={D.ARCHITECTURAL.value},
        holdout_intact=True,
        rationale="remove boundary + disable the architectural layer",
    )
    verdict = analyze_composition(attack, vulnerable_matrix())
    assert not verdict.defended
    assert P.ARCH_BOUNDARY_REMOVAL in verdict.bypassed_primitives


def test_two_layer_redundancy_closes_single_layer_bypass():
    """Under hardened_matrix (architectural + evidence-integrity), the same
    composition is defended because evidence-integrity still catches it."""
    from tiannara.adversarial import CompositeAttack
    attack = CompositeAttack(
        composition_id="gate_bypass",
        primitives=(P.ARCH_BOUNDARY_REMOVAL, P.ATTACK_GATE_CONFIG),
        expected_defeated=True,
        expected_catching_layers={D.ARCHITECTURAL.value},
        holdout_intact=True,
        rationale="remove boundary + disable the architectural layer",
    )
    verdict = analyze_composition(attack, hardened_matrix())
    assert verdict.defended
    assert D.EVIDENCE_INTEGRITY.value in verdict.catches[P.ARCH_BOUNDARY_REMOVAL.value]


def test_hardening_without_root_of_trust_is_still_bypassable():
    """Disabling BOTH redundant layers re-opens the bypass."""
    from tiannara.adversarial import CompositeAttack
    attack = CompositeAttack(
        composition_id="anchor_gate_bypass",
        primitives=(P.ARCH_BOUNDARY_REMOVAL, P.ATTACK_GATE_CONFIG, P.TAMPER_ANCHOR),
        expected_defeated=True,
        expected_catching_layers={D.ARCHITECTURAL.value, D.EVIDENCE_INTEGRITY.value},
        holdout_intact=True,
        rationale="remove boundary + disable architectural + tamper anchor",
    )
    verdict = analyze_composition(attack, hardened_matrix())
    assert not verdict.defended
    assert P.ARCH_BOUNDARY_REMOVAL in verdict.bypassed_primitives


def test_protected_core_backstop_is_unbypassable_for_defined_primitives():
    from tiannara.adversarial import CompositeAttack
    attack = CompositeAttack(
        composition_id="anchor_gate_bypass",
        primitives=(P.ARCH_BOUNDARY_REMOVAL, P.ATTACK_GATE_CONFIG, P.TAMPER_ANCHOR),
        expected_defeated=True,
        expected_catching_layers={D.ARCHITECTURAL.value, D.EVIDENCE_INTEGRITY.value},
        holdout_intact=True,
        rationale="remove boundary + disable architectural + tamper anchor",
    )
    verdict = analyze_composition(attack, rooted_matrix())
    assert verdict.defended
    assert D.PROTECTED_CORE.value in verdict.catches[P.ARCH_BOUNDARY_REMOVAL.value]


# --- no single primitive bypasses the rooted matrix -----------------------

def test_no_single_primitive_bypasses_rooted():
    matrix = rooted_matrix()
    for p in P:
        from tiannara.adversarial import CompositeAttack
        attack = CompositeAttack(
            composition_id=f"single:{p.value}",
            primitives=(p,),
            expected_defeated=True,
            expected_catching_layers=frozenset(),
            holdout_intact=True,
            rationale="single primitive check",
        )
        verdict = analyze_composition(attack, matrix)
        assert verdict.defended, f"primitive {p} bypasses rooted matrix"


# --- spec compositions are defended when rooted ----------------------------

def test_spec_composites_are_defended_when_rooted():
    matrix = rooted_matrix()
    for spec in COMPOSITION_MATRIX:
        verdict = analyze_composition(spec, matrix)
        assert verdict.defended, f"{spec.composition_id} bypasses rooted matrix"


# --- behavioral: composed attacks are caught by the gate ------------------

@pytest.mark.parametrize("spec", COMPOSITION_MATRIX,
                         ids=[s.composition_id for s in COMPOSITION_MATRIX])
def test_composed_attack_rejected_by_gate(lab, spec):
    protected = lab.surface
    baseline_run = lab.baseline_run

    applier_map = {
        "COMPOSE_WEAKEN_PLUS_MASK": _apply_weaken_plus_mask,
        "COMPOSE_DELETE_PLUS_MASK": _apply_delete_plus_mask,
        "COMPOSE_ARCH_BOUNDARY_PLUS_MASK": _apply_arch_boundary_plus_mask,
        "COMPOSE_ARCH_AUTH_REMOVAL_PLUS_MASK": _apply_arch_auth_removal_plus_mask,
        "COMPOSED_CONTROL_SINGLE": _apply_composed_control_single,
    }
    applier = applier_map.get(spec.composition_id)
    if applier is None:
        pytest.skip(f"no applier for {spec.composition_id}")
    evidence = applier(protected, baseline_run)
    decision = lab.decider.decide(protected, baseline_run, evidence)
    expected_feasible = not spec.expected_defeated
    assert decision.feasible is expected_feasible, (
        f"{spec.composition_id}: expected feasible={expected_feasible} "
        f"got {decision.feasible} ({decision.detail})"
    )


# --- defense-in-depth: no expected layer goes silent in the gate ----------

def test_no_detector_cancellation_in_gate(lab):
    """For each adversarial composition, every expected catching layer must
    actually fire. If a layer that should catch a primitive goes silent, that
    is a defense-depth failure."""
    protected = lab.surface
    baseline_run = lab.baseline_run

    applier_map = {
        "COMPOSE_WEAKEN_PLUS_MASK": _apply_weaken_plus_mask,
        "COMPOSE_DELETE_PLUS_MASK": _apply_delete_plus_mask,
        "COMPOSE_ARCH_BOUNDARY_PLUS_MASK": _apply_arch_boundary_plus_mask,
        "COMPOSE_ARCH_AUTH_REMOVAL_PLUS_MASK": _apply_arch_auth_removal_plus_mask,
    }

    for spec in COMPOSITION_MATRIX:
        if not spec.primitives:
            continue
        applier = applier_map.get(spec.composition_id)
        if applier is None:
            continue
        evidence = applier(protected, baseline_run)
        decision = lab.decider.decide(protected, baseline_run, evidence)
        actual = set(decision.catching_layers)
        expected = set(spec.expected_catching_layers)
        cancelled = expected - actual
        assert not cancelled, (
            f"{spec.composition_id}: expected layers {expected} "
            f"but gate caught only {actual}; cancelled={cancelled}"
        )


# --- control: composer does not corrupt legit candidates ------------------

def test_control_composition_accepted(lab):
    protected = lab.surface
    baseline_run = lab.baseline_run
    evidence = _apply_composed_control_single(protected, baseline_run)
    decision = lab.decider.decide(protected, baseline_run, evidence)
    assert decision.feasible is True


# --- determinism: same composition → same evidence_hash --------------------

def test_composition_deterministic_replay(lab):
    protected = lab.surface
    baseline_run = lab.baseline_run
    applier_map = {
        "COMPOSE_WEAKEN_PLUS_MASK": _apply_weaken_plus_mask,
        "COMPOSE_DELETE_PLUS_MASK": _apply_delete_plus_mask,
        "COMPOSE_ARCH_BOUNDARY_PLUS_MASK": _apply_arch_boundary_plus_mask,
        "COMPOSE_ARCH_AUTH_REMOVAL_PLUS_MASK": _apply_arch_auth_removal_plus_mask,
        "COMPOSED_CONTROL_SINGLE": _apply_composed_control_single,
    }
    for spec in COMPOSITION_MATRIX:
        applier = applier_map.get(spec.composition_id)
        if applier is None:
            continue
        e1 = applier(protected, baseline_run)
        e2 = applier(protected, baseline_run)
        assert e1.content_hash() == e2.content_hash(), spec.composition_id


# --- holdout integrity across every composition --------------------------

@pytest.mark.parametrize("spec", COMPOSITION_MATRIX,
                         ids=[s.composition_id for s in COMPOSITION_MATRIX])
def test_holdout_integrity_preserved(lab, spec):
    protected = lab.surface
    baseline_run = lab.baseline_run
    applier_map = {
        "COMPOSE_WEAKEN_PLUS_MASK": _apply_weaken_plus_mask,
        "COMPOSE_DELETE_PLUS_MASK": _apply_delete_plus_mask,
        "COMPOSE_ARCH_BOUNDARY_PLUS_MASK": _apply_arch_boundary_plus_mask,
        "COMPOSE_ARCH_AUTH_REMOVAL_PLUS_MASK": _apply_arch_auth_removal_plus_mask,
        "COMPOSED_CONTROL_SINGLE": _apply_composed_control_single,
    }
    applier = applier_map.get(spec.composition_id)
    if applier is None:
        pytest.skip(f"no applier for {spec.composition_id}")
    evidence = applier(protected, baseline_run)
    decision = lab.decider.decide(protected, baseline_run, evidence)
    assert decision.holdout_intact is spec.holdout_intact, spec.composition_id


# --- information-hiding: evidence has no composition metadata ------------

def test_evidence_has_no_composition_fields():
    field_names = {f.name for f in dataclasses.fields(CandidateEvidence)}
    leaked = {n for n in field_names if "compos" in n or "component" in n}
    assert not leaked, (
        f"CandidateEvidence leaks composition structure ({leaked}); "
        f"the gate must not be able to see that a candidate is a composition"
    )


# --- composed appliers (reusing atomic mutation helpers) ------------------

# Re-export the helpers from adversarial_lab for test-local composition
from tiannara.application.evolution.adversarial_lab import (
    ID_REG_AWAIT,
    _visible_baseline_evidence,
    _holdout_run,
    _swap_content,
    _drop,
    _masked_holdout_diff_content,
    _canonical_arch_isr,
    _isr_without_auth,
    _isr_remove_boundary,
)


def _apply_weaken_plus_mask(_, __) -> CandidateEvidence:
    """Weaken visible assertion (regression) + mask holdout content (holdout)."""
    weakened = _swap_content(ID_REG_AWAIT, "sha256:await_WEAKENED")
    return CandidateEvidence(
        evolution_evidence=weakened,
        holdout_evidence=_masked_holdout_diff_content(),
        causal_delta_accepted=False,
    )


def _apply_delete_plus_mask(_, __) -> CandidateEvidence:
    """Delete visible test (identity) + mask holdout content (holdout)."""
    evolution = _drop(ID_REG_AWAIT)
    return CandidateEvidence(
        evolution_evidence=evolution,
        holdout_evidence=_masked_holdout_diff_content(),
        causal_delta_accepted=False,
    )


def _apply_arch_boundary_plus_mask(_, __) -> CandidateEvidence:
    """Remove architectural boundary (invariant) + mask holdout (holdout)."""
    parent_isr = _canonical_arch_isr()
    candidate = _isr_remove_boundary(parent_isr)
    return CandidateEvidence(
        evolution_evidence=_visible_baseline_evidence(),
        holdout_evidence=_masked_holdout_diff_content(),
        causal_delta_accepted=False,
        candidate_isr=candidate,
    )


def _apply_arch_auth_removal_plus_mask(_, __) -> CandidateEvidence:
    """Remove architectural auth (invariant) + mask holdout (holdout)."""
    parent_isr = _canonical_arch_isr()
    candidate = _isr_without_auth(parent_isr)
    return CandidateEvidence(
        evolution_evidence=_visible_baseline_evidence(),
        holdout_evidence=_masked_holdout_diff_content(),
        causal_delta_accepted=False,
        candidate_isr=candidate,
    )


def _apply_composed_control_single(_, __) -> CandidateEvidence:
    """Control: a legitimate candidate (no attacks) must be accepted."""
    return CandidateEvidence(
        evolution_evidence=_visible_baseline_evidence(),
        holdout_evidence=_holdout_run(),
        causal_delta_accepted=False,
    )


# --- architectural catch attribution discipline ---------------------------

def test_architectural_primitives_caught_by_architecture_aware_layers(lab):
    """When an architectural primitive is caught, the catching layer must be
    architecture-aware (architectural/invariant), NOT a generic regression catch."""
    protected = lab.surface
    baseline_run = lab.baseline_run

    cases = [
        ("COMPOSE_ARCH_BOUNDARY_PLUS_MASK", _apply_arch_boundary_plus_mask),
        ("COMPOSE_ARCH_AUTH_REMOVAL_PLUS_MASK", _apply_arch_auth_removal_plus_mask),
    ]
    for name, applier in cases:
        evidence = applier(protected, baseline_run)
        decision = lab.decider.decide(protected, baseline_run, evidence)
        assert not decision.feasible, f"{name}: should be rejected"
        layers = set(decision.catching_layers)
        # The architectural attack must produce an invariant-layer catch
        assert "invariant" in layers, (
            f"{name}: architectural circumvention not caught by invariant layer; "
            f"caught only by {layers}"
        )
