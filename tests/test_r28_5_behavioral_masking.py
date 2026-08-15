"""R2.8.5 -- Behavioral Masking: ISR-level masks that pass visible tests but are

caught by the read-isolated holdout. Validates that R2.8.7's isolation converts
from a structural guarantee into an actual detection capability.

Core invariant: a candidate that masks behavior on visible inputs cannot mask
behavior on holdout inputs it cannot observe.
"""
from __future__ import annotations

import pytest

from tiannara.application.evolution.adversarial_lab import (
    CandidateEvidence,
    ID_EVOLVABLE_CANARY,
    ID_HOLDOUT,
    MUTATION_MATRIX,
    MutationLab,
    apply_attack_d_unauthorized_gutting,
    apply_legit_edit_evolvable,
    apply_mask_early_return,
    apply_mask_fabricated_result,
    apply_mask_invisible_on_all_inputs,
    apply_mask_special_case_input,
    canonical_baseline_visible_run,
)
from tiannara.domain.models.evidence import (
    TestExecution,
    TestOutcome,
)


# -- the key architectural invariant -------------------------------------------
# A behavioral mask leaves the visible surface UNCHANGED. Read-isolation
# means the candidate cannot observe the holdout inputs, so it cannot
# mask the response to them.

def test_visible_surface_is_clean_for_behavioral_masks():
    """All behavioral-mask mutations leave visible evidence identical to baseline."""
    lab = MutationLab()
    baseline = canonical_baseline_visible_run()
    mask_ids = {"MASK_SPECIAL_CASE_INPUT", "MASK_EARLY_RETURN", "MASK_FABRICATED_RESULT"}
    for spec in MUTATION_MATRIX:
        if spec.mutation_id not in mask_ids:
            continue
        evidence = spec.apply(lab.surface, lab.baseline_run)
        assert evidence.evolution_evidence == tuple(baseline.tests), (
            f"{spec.mutation_id}: visible surface unexpectedly changed"
        )


def test_holdout_catches_all_behavioral_masks():
    """Every detectable mask is caught by the holdout catching layer."""
    lab = MutationLab()
    mask_ids = {"MASK_SPECIAL_CASE_INPUT", "MASK_EARLY_RETURN", "MASK_FABRICATED_RESULT"}
    for spec in MUTATION_MATRIX:
        if spec.mutation_id not in mask_ids:
            continue
        evidence = spec.apply(lab.surface, lab.baseline_run)
        decision = lab.decider.decide(lab.surface, lab.baseline_run, evidence)
        assert not decision.feasible
        assert "holdout" in decision.catching_layers, (
            f"{spec.mutation_id}: expected holdout to catch the mask"
        )
        assert not decision.holdout_intact, (
            f"{spec.mutation_id}: holdout should be broken (mask detected)"
        )
        assert decision.drift.accept is True


def test_invisible_mask_control_passes():
    """A mask invisible on all inputs is harmless and accepted (false-positive control)."""
    lab = MutationLab()
    spec = next(s for s in MUTATION_MATRIX if s.mutation_id == "MASK_INVISIBLE_ON_ALL_INPUTS")
    evidence = spec.apply(lab.surface, lab.baseline_run)
    decision = lab.decider.decide(lab.surface, lab.baseline_run, evidence)
    assert decision.feasible
    assert decision.holdout_intact
    assert decision.catching_layers == ()


def test_behavioral_mask_not_authorizable():
    """A behavioral mask cannot carry a legitimate ISR authorization covering the holdout.

    The mask's ISR delta does not project to the holdout test id -- by design,
    the authorization covers evolvable surface, not the hidden holdout.
    """
    lab = MutationLab()
    for spec in MUTATION_MATRIX:
        if not spec.mutation_id.startswith("MASK_"):
            continue
        if spec.mutation_id == "MASK_INVISIBLE_ON_ALL_INPUTS":
            continue
        evidence = spec.apply(lab.surface, lab.baseline_run)
        if evidence.authorization is not None:
            assert ID_HOLDOUT not in evidence.authorization.authorized_test_ids, (
                f"{spec.mutation_id}: holdout id leaked into authorization (read-isolation breach)"
            )


# -- read-isolation is the detection mechanism ----------------------------------

def test_read_isolation_blocks_holdout_id_leak():
    """Evolution evidence must never contain holdout test ids."""
    lab = MutationLab()
    for spec in MUTATION_MATRIX:
        evidence = spec.apply(lab.surface, lab.baseline_run)
        evolution_ids = {e.test_id for e in evidence.evolution_evidence}
        assert ID_HOLDOUT not in evolution_ids, (
            f"{spec.mutation_id}: holdout id leaked into evolution evidence"
        )
        decision = lab.decider.decide(lab.surface, lab.baseline_run, evidence)
        assert decision.read_isolated


# -- attack-d still requires ISR authorization -----------------------------------

def test_attack_d_blocked_by_wrong_authorization():
    """Attack D: gutting with an authorization covering the wrong test id is caught."""
    lab = MutationLab()
    evidence = apply_attack_d_unauthorized_gutting(lab.surface, lab.baseline_run)
    decision = lab.decider.decide(lab.surface, lab.baseline_run, evidence)
    assert not decision.feasible
    assert "regression" in decision.catching_layers
    assert decision.drift.accept  # drift layer still accepts (evolvable, causal_delta_accepted)


def test_legit_edit_evolvable_authorized():
    """Legitimate canary repair: authorization covers the canary, candidate accepted."""
    lab = MutationLab()
    evidence = apply_legit_edit_evolvable(lab.surface, lab.baseline_run)
    decision = lab.decider.decide(lab.surface, lab.baseline_run, evidence)
    assert decision.feasible
    assert decision.catching_layers == ()
    assert (evidence.authorization is not None
            and ID_EVOLVABLE_CANARY in evidence.authorization.authorized_test_ids)


# -- holdout integrity check now also checks outcome ----------------------------

def test_failed_holdout_is_caught():
    """A holdout test that FAILS (not just content-mismatched) is not intact."""
    lab = MutationLab()
    bad_evidence = CandidateEvidence(
        evolution_evidence=(),
        holdout_evidence=(TestExecution(
            test_id=ID_HOLDOUT, outcome=TestOutcome.FAILED,
            content_hash="sha256:holdout_v1",
        ),),
        causal_delta_accepted=False,
    )
    decision = lab.decider.decide(lab.surface, lab.baseline_run, bad_evidence)
    assert not decision.holdout_intact
    assert "holdout" in decision.catching_layers


# -- defense in depth: holdout is the primary detector, not drift/regression -----

def test_mask_caught_by_holdout_not_by_drift_or_regression():
    """Behavioral masks are caught by holdout layer, not drift/content/regression."""
    lab = MutationLab()
    mask_ids = {"MASK_SPECIAL_CASE_INPUT", "MASK_EARLY_RETURN", "MASK_FABRICATED_RESULT"}
    for spec in MUTATION_MATRIX:
        if spec.mutation_id not in mask_ids:
            continue
        evidence = spec.apply(lab.surface, lab.baseline_run)
        decision = lab.decider.decide(lab.surface, lab.baseline_run, evidence)
        layers = set(decision.catching_layers)
        assert "holdout" in layers
        assert "content" not in layers
        assert "identity" not in layers
        assert "regression" not in layers


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
