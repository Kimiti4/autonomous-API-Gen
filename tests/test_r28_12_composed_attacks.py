"""R2.8.12 -- Adversarial Composition: gate-level certification tests.

Asserts that composed attacks are rejected through the real gate
(AdversarialGateDecider), that defense-in-depth holds (no expected layer goes
silent, i.e. detector_cancellation_count == 0), that the composer is
deterministic across PYTHONHASHSEED (dynamic determinism), and that
CandidateEvidence carries no composition structure (information hiding).
"""
from __future__ import annotations

import dataclasses

import pytest

from tiannara.application.evolution.adversarial_lab import (
    CandidateEvidence,
    COMPOSED_MUTATION_MATRIX,
    MutationComposer,
    Baseline,
    build_adversarial_harness,
)


def _harness():
    protected, baseline, baseline_run, _appliers, decider, measurement = build_adversarial_harness()
    return protected, baseline, baseline_run, decider, measurement


# --- each composition produces the declared verdict through the gate -----------

def test_each_composition_verdict_matches_declaration():
    protected, baseline, baseline_run, decider, _ = _harness()
    composer = MutationComposer()
    for spec in COMPOSED_MUTATION_MATRIX:
        evidence = composer.compose(spec, baseline, seed=11)
        decision = decider.decide(protected, baseline_run, evidence)
        actual = decision.verdict.value
        expected = spec.expected_verdict.value
        assert actual == expected, (
            f"{spec.composition_id}: expected verdict={expected} got={actual} "
            f"layers={decision.catching_layers}"
        )


# --- defense-in-depth: no expected layer goes silent (detector_cancellation) ---

def test_no_detector_cancellation_count_is_zero():
    """The headline R2.8.12 invariant: detector_cancellation_count must be 0.

    If a layer that should catch a composition goes silent, that is a
    defense-depth failure. A clean run has zero cancellations.
    """
    protected, baseline, baseline_run, _decider, measurement = _harness()
    rows, summary = measurement.measure_composed_corpus(baseline, seed=11)
    assert summary.detector_cancellation_count == 0, (
        f"{summary.detector_cancellation_count} detectors cancelled across compositions"
    )


def test_every_expected_catching_layer_fires_for_adversarial_compositions():
    """For each adversarial composition, every expected catching layer must
    actually fire through the gate."""
    protected, baseline, baseline_run, decider, _ = _harness()
    composer = MutationComposer()
    for spec in COMPOSED_MUTATION_MATRIX:
        evidence = composer.compose(spec, baseline, seed=11)
        decision = decider.decide(protected, baseline_run, evidence)
        actual = set(decision.catching_layers)
        expected = set(spec.expected_catching_layers)
        cancelled = expected - actual
        assert not cancelled, (
            f"{spec.composition_id}: expected layers {expected} "
            f"but gate caught only {actual}; cancelled={cancelled}"
        )


# --- control: composer does not corrupt legit candidates -----------------------

def test_control_composition_is_accepted():
    protected, baseline, baseline_run, decider, _ = _harness()
    composer = MutationComposer()
    spec = next(s for s in COMPOSED_MUTATION_MATRIX
                if s.composition_id == "COMPOSED_CONTROL_SINGLE")
    evidence = composer.compose(spec, baseline, seed=11)
    decision = decider.decide(protected, baseline_run, evidence)
    assert decision.feasible is True


# --- determinism: same composition -> same evidence_hash + verdict ---------------

def test_composition_deterministic_replay_in_process():
    """Same seed + spec -> identical evidence_hash and verdict (in-process)."""
    protected, baseline, baseline_run, decider, _ = _harness()
    composer = MutationComposer()
    for spec in COMPOSED_MUTATION_MATRIX:
        e1 = composer.compose(spec, baseline, seed=11)
        e2 = composer.compose(spec, baseline, seed=11)
        assert e1.content_hash() == e2.content_hash(), spec.composition_id
        d1 = decider.decide(protected, baseline_run, e1)
        d2 = decider.decide(protected, baseline_run, e2)
        assert d1.feasible == d2.feasible, spec.composition_id
        assert d1.catching_layers == d2.catching_layers, spec.composition_id


# --- information hiding: CandidateEvidence has no composition fields -----------

def test_evidence_has_no_composition_fields():
    """CandidateEvidence must not carry composition metadata -- the gate cannot
    tell a candidate is a composition (no blacklist by another name)."""
    field_names = {f.name for f in dataclasses.fields(CandidateEvidence)}
    leaked = {n for n in field_names if "compos" in n or "component" in n}
    assert not leaked, (
        f"CandidateEvidence leaks composition structure ({leaked}); "
        f"the gate must not be able to see that a candidate is a composition"
    )


# --- holdout integrity across every composition --------------------------------

@pytest.mark.parametrize("spec", COMPOSED_MUTATION_MATRIX,
                         ids=[s.composition_id for s in COMPOSED_MUTATION_MATRIX])
def test_holdout_integrity_per_composition(spec):
    protected, baseline, baseline_run, decider, _ = _harness()
    composer = MutationComposer()
    evidence = composer.compose(spec, baseline, seed=11)
    decision = decider.decide(protected, baseline_run, evidence)
    assert decision.holdout_intact is spec.expected_holdout_intact, spec.composition_id


# --- corpus-level summary invariants -------------------------------------------

def test_composed_corpus_summary_invariants():
    """The full composed-corpus measurement summary must satisfy the
    certification invariants: 0 false negatives, 0 false positives,
    holdout integrity, and deterministic replay."""
    protected, baseline, baseline_run, _decider, measurement = _harness()
    rows, summary = measurement.measure_composed_corpus(baseline, seed=11)

    assert summary.total_compositions == len(COMPOSED_MUTATION_MATRIX)
    assert summary.false_negative_rate == 0.0
    assert summary.false_positive_rate == 0.0
    assert summary.holdout_integrity is True
    assert summary.deterministic_replay is True


def test_build_adversarial_harness_returns_all_components():
    """The composition root returns all 6 required components."""
    protected, baseline, baseline_run, appliers, decider, measurement = build_adversarial_harness()
    assert protected is not None
    assert isinstance(baseline, Baseline)
    assert baseline_run is not None
    assert isinstance(appliers, dict)
    assert decider is not None
    assert measurement is not None
