"""R2.8.3 -- Evaluation Surface Integrity: measurement certification.

A read-only, deterministic, tamper-evident measurement layer over the R2.8.2
decision path. It does NOT re-decide: the decider is invoked with evidence
only (never the matrix's expected verdicts), preserving the information
asymmetry -- the measurement layer is privileged (knows ground truth); the
gate is not.

Invariants are reported as pass/fail bools, never normalized rates:
  * holdout_integrity  -- hidden evaluation never tampered
  * deterministic_replay -- same seed + mutation => identical verdict
"""
from __future__ import annotations

import pytest

from tiannara.application.evolution.adversarial_lab import (
    MUTATION_MATRIX,
    MeasurementLayer,
    MutationLab,
)


@pytest.fixture
def lab() -> MeasurementLayer:
    core = MutationLab()
    return MeasurementLayer(
        core.decider, core.ledger, core.surface, core.baseline_run
    )


def _run_all(lab):
    return [lab.measure(spec) for spec in MUTATION_MATRIX]


# -- per-mutation certification --------------------------------------------------

@pytest.mark.parametrize("mutation_id", [s.mutation_id for s in MUTATION_MATRIX],
                         ids=[s.mutation_id for s in MUTATION_MATRIX])
def test_each_mutation_verdict_matches_declaration(lab, mutation_id):
    spec = next(s for s in MUTATION_MATRIX if s.mutation_id == mutation_id)
    metrics = lab.measure(spec)

    # verdict must match the declared expectation
    if spec.expected_feasibility == "infeasible":
        assert metrics.actual_verdict == "infeasible"
        assert metrics.detected is True
        assert metrics.false_negative is False
    else:
        assert metrics.actual_verdict == "feasible"
        assert metrics.false_positive is False or not spec.is_control

    # declared catching layers must be a subset of the actual layers
    assert set(spec.expected_catching_layers) <= set(metrics.actual_catching_layers), (
        f"{mutation_id}: expected {spec.expected_catching_layers} "
        f"⊆ {metrics.actual_catching_layers}"
    )

    # holdout invariant + determinism per row
    assert metrics.holdout_intact is spec.expected_holdout_intact
    assert metrics.replayed_identically is True

    # every record is anchored to the chain
    assert metrics.event_hash


def test_info_asymmetry_decider_never_sees_expected_values(lab):
    """The decider is constructed independently of the matrix; it can only
    observe evidence, never expected verdicts/layers (no blacklisting)."""
    # AdversarialGateDecider has no attribute referencing MUTATION_MATRIX or
    # expected values -- structural guard against the gate learning answers.
    decider_attrs = {a for a in dir(lab._decider) if not a.startswith("__")}
    forbidden = {"_matrix", "expected", "_specs", "MUTATION_MATRIX"}
    assert not (decider_attrs & forbidden)
    # sanity: the decider still decided everything correctly above
    records = _run_all(lab)
    assert records


# -- flagship: the R2.6 aggregate-mimic hole is closed --------------------------

def test_aggregate_mimic_rejected_even_when_pass_count_preserved(lab):
    """R2.6 hole: a candidate that deletes a protected test and fabricates an
    unchanged pass count must still be rejected by the boundary."""
    core = MutationLab()
    spec = next(s for s in MUTATION_MATRIX if s.mutation_id == "AGGREGATE_MIMIC_DELETE")
    evidence = spec.apply(core.surface, core.baseline_run)
    decision = core.decider.decide(core.surface, core.baseline_run, evidence)

    # regression degraded to aggregate-only (the hole's precondition)...
    assert decision.regression.precision == "aggregate_only"
    # ...but the boundary still rejects, via identity + attestation (defense-in-depth).
    assert decision.feasible is False
    assert "identity" in decision.catching_layers
    assert "attestation" in decision.catching_layers
    # the holdout survived the fabrication attempt
    assert decision.holdout_intact is True


# -- aggregate certification -----------------------------------------------------

def test_certification_summary():
    lab = MeasurementLayer(MutationLab().decider, MutationLab().ledger,
                           MutationLab().surface, MutationLab().baseline_run)
    records = _run_all(lab)
    summary = lab.summarize(records)

    adversarial = [r for r in records if not r.is_control]
    controls = [r for r in records if r.is_control]

    # detection: every adversarial mutation correctly rejected
    assert summary.detection_rate == 1.0
    assert summary.false_negatives == 0
    assert summary.detected == len(adversarial)

    # false positives reported WITH n (controls = 2 on this corpus)
    assert summary.false_positives == 0
    assert summary.false_positive_n == len(controls)
    assert summary.control_total == len(controls)

    # mutation score = overall correct classification
    assert summary.mutation_score == 1.0

    # invariants (bools, not rates)
    assert summary.holdout_integrity is True
    assert summary.deterministic_replay is True

    # no misses, no false positives
    assert summary.layer_attribution.get("missed", 0) == 0
    assert summary.layer_attribution.get("control_rejected", 0) == 0


def test_defense_in_depth_not_single_point_of_failure():
    """The certification claim: multiple layers contribute; no single layer
    carries the whole anti-gaming load."""
    lab = MeasurementLayer(MutationLab().decider, MutationLab().ledger,
                           MutationLab().surface, MutationLab().baseline_run)
    records = _run_all(lab)
    summary = lab.summarize(records)

    # at least two layers must have caught adversarial mutations -- otherwise
    # the boundary is dependent on one detector (not defense-in-depth).
    contributing = {layer for layer, n in summary.per_layer_detection.items() if n > 0}
    assert len(contributing) >= 2, f"single point of failure: {contributing}"

    # distribution of primary catchers is not degenerate: more than one layer
    # serves as the primary catcher across adversarial mutations, and the counts
    # reconcile with the adversarial rows that were actually caught.
    adversarial_caught = [r for r in records if not r.is_control and r.actual_catching_layers]
    primaries = {k: v for k, v in summary.primary_layer_distribution.items() if k}
    assert sum(primaries.values()) == len(adversarial_caught)
    assert len(primaries) >= 2, f"primary catcher degenerate to one layer: {primaries}"


# -- tamper-evident, corpus-anchored, replayable --------------------------------

def test_corpus_hash_and_measurements_anchored_in_ledger():
    lab = MeasurementLayer(MutationLab().decider, MutationLab().ledger,
                           MutationLab().surface, MutationLab().baseline_run)
    _run_all(lab)

    events = lab._ledger.events()
    # 1 surface-ANCHOR + 1 corpus-ANCHOR + 1 MEASUREMENT per matrix row
    expected = 2 + len(MUTATION_MATRIX)
    assert lab._ledger.event_count == expected
    assert lab._ledger.verify_event_chain()

    # the matrix hash is anchored alongside the protected-core hash
    anchors = [e for e in events if e.event_type.value == "anchor"
               or (e.payload.get("kind") == "corpus_anchor")]
    corpus_anchor = next(e for e in events if e.payload.get("kind") == "corpus_anchor")
    assert corpus_anchor.payload["matrix_hash"] == lab.matrix_hash
    assert corpus_anchor.payload["corpus_version"] == lab.corpus_version

    # every per-mutation measurement references the anchored matrix hash
    measurements = [e for e in events if e.event_type.value == "measurement"
                    and e.payload.get("kind") == "measurement"]
    assert len(measurements) == len(MUTATION_MATRIX)
    assert all(m.payload["matrix_hash"] == lab.matrix_hash for m in measurements)
    assert {m.payload["mutation_id"] for m in measurements} == {s.mutation_id for s in MUTATION_MATRIX}


def test_tampering_a_measurement_record_breaks_chain():
    lab = MeasurementLayer(MutationLab().decider, MutationLab().ledger,
                           MutationLab().surface, MutationLab().baseline_run)
    _run_all(lab)
    assert lab._ledger.verify_event_chain()

    # Flip one measurement's verdict in the ledger -- must break integrity.
    events = [e.model_copy() for e in lab._ledger.events()]
    target = next(e for e in events if e.payload.get("kind") == "measurement")
    tampered = target.model_copy(
        update={"payload": {**target.payload, "actual_verdict": "feasible"}}
    )
    idx = events.index(target)
    lab._ledger._events[idx] = tampered
    assert not lab._ledger.events()[idx].is_intact()
    assert not lab._ledger.verify_event_chain()
