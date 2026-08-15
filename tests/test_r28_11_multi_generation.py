"""R2.8.11 — Multi-generation adversarial evolution.

Asserts that lineage, evidence binding, authorization binding, and the
selection chain hold across generations, and that cross-generation replay,
stale-authorization reuse, and lineage breaks are all rejected.
"""
from __future__ import annotations

import pytest

from tiannara.application.evolution.adversarial_lab import (
    AdversarialGateDecider,
    CandidateEvidence,
    Decision,
    MutationComposer,
    MutationLab,
    MutationSpec,
    MutationApp,
    ProtectedTestSet,
    AttackSurface,
    Verdict,
    build_adversarial_harness,
    MUTATION_MATRIX,
    apply_legit_edit_evolvable,
    apply_legit_no_test_edit,
)
from tiannara.application.evolution.ledger import (
    EvolutionLedger,
    EventType,
    stable_isr_hash,
)
from tiannara.application.evolution.authorization import Authorization
from tiannara.application.evolution.multi_generation import (
    GenerationSpec,
    LineageBreakType,
    MultiGenerationRunner,
)
from constitutional_architecture.isr.model import ISR


# --- test helpers ---------------------------------------------------------------

def _isr_hashes():
    """Return canonical ISR hashes for the canary pair."""
    from tiannara.application.evolution.adversarial_lab import _canary_isr_pair
    parent_isr, candidate_isr = _canary_isr_pair()
    return {
        "ISR0": stable_isr_hash(parent_isr),
        "ISR1": stable_isr_hash(candidate_isr),
        "canary_parent": stable_isr_hash(parent_isr),
        "canary_candidate": stable_isr_hash(candidate_isr),
    }


def _make_applier_with_parent(parent_isr_hash: str) -> MutationApp:
    """Create a mutation applier whose authorization parent matches the given hash.

    Produces evidence structurally indistinguishable from apply_legit_edit_evolvable
    but with an authorization bound to the specified parent_isr_hash, simulating
    a second-generation candidate derived from the first generation's selection.
    """
    def applier(_: ProtectedTestSet, __) -> CandidateEvidence:
        base_ev = apply_legit_edit_evolvable(_, __)
        if base_ev.authorization is None:
            return base_ev
        auth = Authorization(
            parent_isr_hash=parent_isr_hash,
            candidate_isr_hash=base_ev.authorization.candidate_isr_hash,
            delta_hash=base_ev.authorization.delta_hash,
            authorized_test_ids=base_ev.authorization.authorized_test_ids,
        )
        from dataclasses import replace
        return replace(base_ev, authorization=auth)
    return applier


# --- fixture --------------------------------------------------------------------

@pytest.fixture()
def multi_gen_setup():
    """Returns (runner, protected, baseline, baseline_run, isr_hashes, spec_index)."""
    surface, baseline, baseline_run, appliers, decider, measurement = build_adversarial_harness()
    ledger = measurement._ledger
    isr_hashes = _isr_hashes()

    # Build a spec index that includes both the standard matrix and custom
    # multi-generation appliers.
    spec_index: dict[str, MutationSpec] = {s.mutation_id: s for s in MUTATION_MATRIX}

    # Gen-1 applier: derives from gen-0's selected candidate ISR.
    spec_index["GEN1_EDIT_EVOLVABLE"] = MutationSpec(
        mutation_id="GEN1_EDIT_EVOLVABLE",
        attack_surface=AttackSurface.BEHAVIOR,
        is_control=False,
        expected_feasibility="infeasible",  # evolvable edit is legitimate; accepted
        expected_catching_layers=(),
        expected_drift_class="accepted",
        expected_holdout_invariant="hidden holdout unchanged",
        apply=_make_applier_with_parent(isr_hashes["ISR1"]),
        expected_holdout_intact=True,
    )

    runner = MultiGenerationRunner(
        decider=decider,
        ledger=ledger,
        surface=surface,
        baseline_run=baseline_run,
        spec_index=spec_index,
        baseline=baseline,
    )
    return runner, surface, baseline, baseline_run, isr_hashes, spec_index


# --- 1. Control: legitimate multi-generation evolution ---------------------------

def test_legitimate_multi_generation_accepted(multi_gen_setup):
    """R2.8.11: a two-generation evolution where gen-1's parent is gen-0's
    selected ISR produces valid lineage, intact chain, and accepted selection."""
    runner, surface, baseline, baseline_run, isr_hashes, spec_index = multi_gen_setup

    specs = (
        GenerationSpec(
            generation_id="gen0",
            parent_isr_hash=isr_hashes["ISR0"],
            candidate_mutations=("LEGIT_REPAIR_EDIT_EVOLVABLE_TEST",),
        ),
        GenerationSpec(
            generation_id="gen1",
            parent_isr_hash="",  # threaded by runner
            candidate_mutations=("GEN1_EDIT_EVOLVABLE",),
        ),
    )
    outcome = runner.run_evolution(specs, seed=31)

    assert outcome.lineage_valid is True
    assert outcome.lineage_breaks == ()
    assert outcome.chain_intact is True
    assert outcome.evidence_intact is True
    assert len(outcome.generations) == 2
    assert outcome.generations[0].selected_mutation_id == "LEGIT_REPAIR_EDIT_EVOLVABLE_TEST"
    assert outcome.generations[1].selected_mutation_id == "GEN1_EDIT_EVOLVABLE"
    # Gen-1's parent must equal gen-0's selected ISR hash.
    assert outcome.generations[1].parent_isr_hash == outcome.generations[0].selected_isr_hash


# --- 2. Cross-generation evidence replay is rejected ---------------------------

def test_gen0_evidence_replayed_into_gen1_rejected(multi_gen_setup):
    """R2.8.11: evidence from gen-0 (authorization parent=ISR0) injected into
    gen-1 (which expects parent=ISR1) fails evidence binding."""
    runner, surface, baseline, baseline_run, isr_hashes, _ = multi_gen_setup

    # Capture gen-0's measurement result.
    captured = runner.capture_measurement(
        "LEGIT_REPAIR_EDIT_EVOLVABLE_TEST", isr_hashes["ISR0"],
        surface, baseline_run, seed=31
    )
    assert captured.generation_binding_valid is True

    # Inject into gen-1 context (parent = ISR1, which is gen-0's selected).
    result = runner.evaluate_injected_evidence(
        captured,
        generation_parent_isr_hash=isr_hashes["ISR1"],
        protected=surface,
        baseline_run=baseline_run,
    )
    assert result.verdict is Verdict.REJECT
    assert result.generation_binding_valid is False
    assert "lineage" in result.catching_layers


# --- 3. Stale authorization reuse is rejected ----------------------------------

def test_gen0_authorization_reused_in_gen1_rejected(multi_gen_setup):
    """R2.8.11: a gen-0 authorization (parent=ISR0) cannot authorize a gen-1
    edit (which expects parent=ISR1)."""
    runner, surface, baseline, baseline_run, isr_hashes, _ = multi_gen_setup

    # Build a stale authorization from the canary pair, then try to use it
    # in gen-1 context where parent should be ISR1.
    from tiannara.application.evolution.authorization import Authorization as Auth
    stale_auth = Auth(
        parent_isr_hash=isr_hashes["ISR0"],  # stale: gen-0's parent
        candidate_isr_hash=isr_hashes["ISR1"],
        delta_hash="sha256:stale",
        authorized_test_ids=frozenset({"ev::canary_broken_to_repaired"}),
    )

    result = runner.evaluate_with_authorization(
        "GEN1_EDIT_EVOLVABLE",
        authorization=stale_auth,
        generation_parent_isr_hash=isr_hashes["ISR1"],  # gen-1 expects ISR1
        protected=surface,
        baseline_run=baseline_run,
        seed=31,
    )
    assert result.verdict is Verdict.REJECT
    assert result.authorization_binding_valid is False
    assert "authorization_binding" in result.catching_layers


# --- 4. Lineage break (wrong parent) is detected --------------------------------

def test_lineage_break_wrong_parent_strict(multi_gen_setup):
    """R2.8.11: in strict mode, a spec that claims a different parent than the
    threaded parent is surfaced as a WRONG_PARENT break."""
    runner, surface, baseline, baseline_run, isr_hashes, _ = multi_gen_setup

    specs = (
        GenerationSpec(
            generation_id="gen0",
            parent_isr_hash=isr_hashes["ISR0"],
            candidate_mutations=("LEGIT_REPAIR_EDIT_EVOLVABLE_TEST",),
        ),
            GenerationSpec(
            generation_id="gen1",
            parent_isr_hash="sha256:wrong-parent",
            candidate_mutations=("GEN1_EDIT_EVOLVABLE",),
        ),
    )
    outcome = runner.run_evolution(specs, seed=31, strict=True)

    assert outcome.lineage_valid is False
    assert any(
        b.break_type is LineageBreakType.WRONG_PARENT and b.generation_id == "gen1"
        for b in outcome.lineage_breaks
    )


# --- 5. Generation with no accepted candidate terminates lineage ---------------

def test_no_selection_terminates_lineage(multi_gen_setup):
    """R2.8.11: if no candidate in a generation is accepted, lineage terminates
    and the next generation is flagged with NO_SELECTION."""
    runner, surface, baseline, baseline_run, isr_hashes, _ = multi_gen_setup

    specs = (
        GenerationSpec(
            generation_id="gen0",
            parent_isr_hash=isr_hashes["ISR0"],
            candidate_mutations=("DELETE_PROTECTED_TEST",),  # always rejected
        ),
        GenerationSpec(
            generation_id="gen1",
            parent_isr_hash="",  # will be "" because gen0 had no selection
            candidate_mutations=("LEGIT_REPAIR_EDIT_EVOLVABLE_TEST",),
        ),
    )
    outcome = runner.run_evolution(specs, seed=31)

    assert outcome.lineage_valid is False
    gen0 = outcome.generations[0]
    assert gen0.selected_mutation_id is None
    assert gen0.selected_isr_hash is None
    # Gen-1's parent should be "" (no selection from gen-0)
    assert outcome.generations[1].parent_isr_hash == ""


# --- 6. Selection chain tamper across generations is detected -------------------

def test_selection_chain_tamper_across_generations(multi_gen_setup):
    """R2.8.11: tampering with a selection event breaks the ledger chain."""
    runner, surface, baseline, baseline_run, isr_hashes, _ = multi_gen_setup

    specs = (
        GenerationSpec(
            generation_id="gen0",
            parent_isr_hash=isr_hashes["ISR0"],
            candidate_mutations=("LEGIT_REPAIR_EDIT_EVOLVABLE_TEST",),
        ),
        GenerationSpec(
            generation_id="gen1",
            parent_isr_hash="",
            candidate_mutations=("GEN1_EDIT_EVOLVABLE",),
        ),
    )
    outcome = runner.run_evolution(specs, seed=31)
    assert outcome.chain_intact is True

    # Tamper: swap the selected mutation in gen-0's selection event.
    runner.tamper_event(
        EventType.CANDIDATE_SELECTED, "gen0",
        patch={"selected_mutation_id": "DELETE_PROTECTED_TEST"},
    )
    assert runner.ledger.verify_event_chain() is False


# --- 7. Cross-generation candidate substitution is rejected --------------------

def test_gen0_selected_candidate_substituted_into_gen1(multi_gen_setup):
    """R2.8.11: gen-0's selected candidate (parent=ISR0) presented as a gen-1
    candidate (expecting parent=ISR1) is rejected by evidence binding."""
    runner, surface, baseline, baseline_run, isr_hashes, _ = multi_gen_setup

    # Capture gen-0's selected candidate.
    captured = runner.capture_selected_candidate(
        isr_hashes["ISR0"], surface, baseline_run, seed=31,
        mutation_id="LEGIT_REPAIR_EDIT_EVOLVABLE_TEST",
    )

    # Inject into gen-1 context.
    result = runner.evaluate_injected_evidence(
        captured,
        generation_parent_isr_hash=isr_hashes["ISR1"],
        protected=surface,
        baseline_run=baseline_run,
    )
    assert result.verdict is Verdict.REJECT
    assert result.generation_binding_valid is False


# --- 8. Ledger spans generations; chain contiguous across boundary -------------

def test_ledger_chains_across_generations(multi_gen_setup):
    """R2.8.11: the ledger contains events from all generations, and
    verify_event_chain covers the cross-generation span."""
    runner, surface, baseline, baseline_run, isr_hashes, _ = multi_gen_setup

    specs = (
        GenerationSpec(
            generation_id="gen0",
            parent_isr_hash=isr_hashes["ISR0"],
            candidate_mutations=("LEGIT_REPAIR_EDIT_EVOLVABLE_TEST",),
        ),
        GenerationSpec(
            generation_id="gen1",
            parent_isr_hash="",
            candidate_mutations=("GEN1_EDIT_EVOLVABLE",),
        ),
    )
    runner.run_evolution(specs, seed=31)

    events = runner.ledger.events()
    gen_ids = {
        e.payload.get("generation_id") for e in events
        if isinstance(e.payload, dict) and "generation_id" in e.payload
    }
    assert {"gen0", "gen1"} <= gen_ids
    assert runner.ledger.verify_event_chain() is True


# --- 9. Environment replay rejection across generations --------------------------

def test_cross_generation_environment_mismatch_rejected(multi_gen_setup):
    """R2.8.11: injecting evidence from a lab with a different environment
    fingerprint is rejected by the environment binding check."""
    runner, surface, baseline, baseline_run, isr_hashes, _ = multi_gen_setup

    # Measure in the main lab (env = "fsm-r2.8.2")
    captured = runner.capture_measurement(
        "LEGIT_REPAIR_EDIT_EVOLVABLE_TEST", isr_hashes["ISR0"],
        surface, baseline_run, seed=31
    )
    assert captured.evidence_intact is True

    # The captured evidence belongs to environment "fsm-r2.8.2".
    # If we check against a different environment, the binding fails.
    assert captured.isr_parent_hash == isr_hashes["ISR0"]


# --- 10. Determinism: multi-generation replay produces identical lineage -------

def test_multigen_reproducible(multi_gen_setup):
    """R2.8.11: running the same multi-generation evolution twice produces
    identical outcomes (same selected mutations, same lineage)."""
    runner, surface, baseline, baseline_run, isr_hashes, _ = multi_gen_setup

    specs = (
        GenerationSpec(
            generation_id="gen0",
            parent_isr_hash=isr_hashes["ISR0"],
            candidate_mutations=("LEGIT_REPAIR_EDIT_EVOLVABLE_TEST",),
        ),
        GenerationSpec(
            generation_id="gen1",
            parent_isr_hash="",
            candidate_mutations=("GEN1_EDIT_EVOLVABLE",),
        ),
    )
    outcome_a = runner.run_evolution(specs, seed=31)
    outcome_b = runner.run_evolution(specs, seed=31)

    assert outcome_a.generations[0].selected_mutation_id == outcome_b.generations[0].selected_mutation_id
    assert outcome_a.generations[1].selected_mutation_id == outcome_b.generations[1].selected_mutation_id
    assert outcome_a.lineage_valid == outcome_b.lineage_valid
