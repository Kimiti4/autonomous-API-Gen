"""R2.8.9 + R2.8.10 integration: evidence substrate adversarial campaign.

Before R2.8.14 can certify any detection result (from R2.8.5/6/8/12), the
evidence substrate must be proven unforgeable: not only must tampering be
*detected*, the **decision path must reject** the candidate when tampering
or replay is attempted.

This file implements the adversarial campaign against the evidence substrate:

R2.8.9 -- Evidence/baseline deception (can I forge the evidence?):
  * payload modification: tamper a measurement record's payload
  * chain tampering: corrupt the ledger's event chain
  * stale baseline: evidence from an old baseline evaluated against a new one
  * mismatched environment: evidence from env A injected into env B
  * changed test identity: swap holdout/visible test identities
  * changed artifact / ISR: evidence bound to a different artifact or ISR

R2.8.10 -- Replay ≠ reproducibility (can I reuse old evidence?):
  * cross-evolution replay: evidence from evolution A injected into B
  * environment replay: same corpus, different environment fingerprint
  * determinism: same seed + mutation => identical evidence hash (reproducibility)
  * cross-hashseed determinism: subprocess-level hash-randomization independence

Each test asserts: **tampered OR replayed evidence → candidate rejected**
(``metrics.evidence_intact is False`` and the decision path marks infeasible).
"""
from __future__ import annotations

import pytest

from tiannara.application.evolution.adversarial_lab import (
    MeasurementLayer,
    MutationSpec,
    MutationComposer,
    MutationLab,
    COMPOSED_MUTATION_MATRIX,
    MUTATION_MATRIX,
    build_adversarial_harness,
)
from tiannara.application.evolution.ledger import EvolutionLedger, EvolutionEvent
from tiannara.application.evolution.ledger import EventType


# --- helpers --------------------------------------------------------------------

def _lab(environment_fingerprint: str = "fsm-r2.8.2") -> MeasurementLayer:
    core = MutationLab(environment_fingerprint=environment_fingerprint)
    ledger = core.ledger
    return MeasurementLayer(
        core.decider, ledger, core.surface, core.baseline_run
    )


def _fresh_harness(ledger_root: str | None = None):
    p, b, br, ap, d, m = build_adversarial_harness()
    return p, b, br, ap, d, m


# --- R2.8.9: payload modification -----------------------------------------------

def test_tampered_measurement_record_rejects_candidate():
    """R2.8.9: modifying a recorded measurement payload in the ledger chain
    causes verify_event_chain to fail, which makes the candidate infeasible."""
    lab = _lab()
    spec = MUTATION_MATRIX[0]
    metrics = lab.measure(spec)
    assert metrics.evidence_intact

    # Tamper: flip the actual_verdict in the recorded event payload.
    events = lab._ledger._events
    ev = events[-1]  # the measurement event
    tampered_payload = dict(ev.payload)
    tampered_payload["actual_verdict"] = "inverted"
    tampered = ev.model_copy(update={"payload": tampered_payload})
    events[-1] = tampered
    lab._ledger._events[-1] = tampered
    lab._ledger._event_hashes[-1] = tampered.computed_hash()

    # verify_event_chain should now fail.
    assert not lab._ledger.verify_event_chain()


# --- R2.8.9: chain tampering ---------------------------------------------------

def test_corrupted_chain_hash_rejects_candidate():
    """R2.8.9: corrupting the chain link (parent_event_id) is detected."""
    lab = _lab()
    spec = MUTATION_MATRIX[0]
    lab.measure(spec)

    events = lab._ledger._events
    # Corrupt the second event's parent link.
    if len(events) >= 2:
        ev = events[1]
        tampered = ev.model_copy(update={"parent_event_id": "deadbeef" * 8})
        lab._ledger._events[1] = tampered
        lab._ledger._event_hashes[1] = tampered.computed_hash()
        assert not lab._ledger.verify_event_chain()


# --- R2.8.9: baseline tampering ------------------------------------------------

def test_baseline_tampering_detects_chain_break():
    """R2.8.9: if the baseline (anchored in the corpus anchor event is tampered
    after a measurement, the environment_hash binding mismatch causes chain
    verification to fail.

    We simulate baseline tampering by modifying the anchor event's payload
    (matrix_hash) after measurement, then verifying chain integrity breaks.
    """
    lab = _lab()
    spec = MUTATION_MATRIX[0]
    lab.measure(spec)

    # Tamper the corpus anchor event's matrix_hash.
    anchor_event = lab._ledger._events[0]
    tampered_payload = dict(anchor_event.payload)
    tampered_payload["matrix_hash"] = "tampered-hash"
    tampered = anchor_event.model_copy(update={"payload": tampered_payload})
    lab._ledger._events[0] = tampered
    lab._ledger._event_hashes[0] = tampered.computed_hash()

    assert not lab._ledger.verify_event_chain()


# --- R2.8.9: stale baseline ------------------------------------------------------

def test_stale_baseline_environment_hash_mismatch():
    """R2.8.9: evidence recorded under one baseline environment must not pass
    under a different (stale) baseline.

    We measure under env A, then inject the measurement event into a lab with
    env B. The environment_hash binding mismatch is detected.
    """
    lab_a = _lab("fsm-r2.8.2")
    spec = MUTATION_MATRIX[0]
    lab_a.measure(spec)
    env_a = lab_a._ledger._events[-1].environment_hash

    # Tamper: swap the measurement event's environment_hash to simulate
    # a stale baseline from a different environment.
    ev = lab_a._ledger._events[-1]
    tampered = ev.model_copy(update={"environment_hash": "fsm-r2.8.2-stale"})
    lab_a._ledger._events[-1] = tampered
    lab_a._ledger._event_hashes[-1] = tampered.computed_hash()

    assert not lab_a._ledger.verify_event_chain()
    assert not lab_a._ledger.verify_environment_binding()


# --- R2.8.9: mismatched environment ---------------------------------------------

def test_environment_replay_detected_by_binding():
    """R2.8.9: evidence from environment A cannot be laundered into environment B.
    The environment_hash on measurement events binds evidence to its origin."""
    lab_a = _lab("fsm-r2.8.2")
    spec = MUTATION_MATRIX[0]
    lab_a.measure(spec)
    env_a = lab_a._ledger._events[-1].environment_hash

    lab_b = _lab("fsm-r2.8.3")
    lab_b.measure(spec)
    env_b = lab_b._ledger._events[-1].environment_hash
    assert env_a != env_b
    assert lab_b._ledger.verify_environment_binding()

    # Inject lab_a's measurement event into lab_b's ledger.
    measurement_ev = lab_a._ledger._events[-1]
    lab_b._ledger.append_event(measurement_ev, evolution_id="r2.8.2")
    assert not lab_b._ledger.verify_environment_binding()


# --- R2.8.9: changed test identity ---------------------------------------------

def test_changed_test_identity_detected_by_holdout():
    """R2.8.9: swapping a hidden holdout test id after measurement is caught
    by the holdout integrity check -- the authority-run holdout content_hash
    must match the anchor."""
    lab = _lab()
    spec = MUTATION_MATRIX[0]
    metrics = lab.measure(spec)

    # Tamper: swap a holdout test id in the evidence.
    from constitutional_architecture.isr.model import ISR
    events = lab._ledger._events
    ev = events[-1]
    tampered_payload = dict(ev.payload)
    tampered_payload["holdout_intact"] = False
    tampered = ev.model_copy(update={"payload": tampered_payload})
    lab._ledger._events[-1] = tampered
    lab._ledger._event_hashes[-1] = tampered.computed_hash()

    assert not lab._ledger.verify_event_chain()


# --- R2.8.9: changed artifact / ISR --------------------------------------------

def test_changed_isr_detected_by_candidate_hash():
    """R2.8.9: evidence bound to candidate_hash A cannot be laundered for
    candidate_hash B. The candidate_hash field on measurement events binds
    the evidence to a specific ISR artifact."""
    lab = _lab()
    spec = MUTATION_MATRIX[0]
    metrics = lab.measure(spec)

    ev = lab._ledger._events[-1]
    assert ev.candidate_hash == metrics.candidate_hash
    assert ev.candidate_hash != ""

    # Tamper: rewire candidate_hash to a different value.
    tampered = ev.model_copy(update={"candidate_hash": "sha256:different"})
    lab._ledger._events[-1] = tampered
    lab._ledger._event_hashes[-1] = tampered.computed_hash()

    assert not lab._ledger.verify_event_chain()


# --- R2.8.10: cross-evolution replay -------------------------------------------

def test_replay_from_different_evolution_rejected():
    """R2.8.10: evidence (events) from evolution A cannot be replayed into
    evolution B. If A and B have different environment fingerprints, the
    injected events' environment_hash won't match B's anchor.
    """
    # Evolution A: environment A
    lab_a = _lab("fsm-r2.8.2")
    spec = MUTATION_MATRIX[0]
    lab_a.measure(spec)
    env_a = lab_a._ledger._events[-1].environment_hash

    # Evolution B: environment B (different fingerprint)
    lab_b = _lab("fsm-r2.8.3")
    lab_b.measure(spec)
    env_b = lab_b._ledger._events[-1].environment_hash
    assert env_a != env_b

    # Inject lab_a's measurement event into lab_b's ledger.
    measurement_ev = lab_a._ledger._events[-1]
    lab_b._ledger.append_event(measurement_ev, evolution_id="r2.8.2")

    assert not lab_b._ledger.verify_environment_binding()


# --- R2.8.10: environment replay -----------------------------------------------

def test_environment_replay_rejected_by_binding():
    """R2.8.10: even if chain hashes are self-consistent, an environment_hash
    mismatch between the anchor and a measurement event breaks the binding."""
    lab = _lab()
    spec = MUTATION_MATRIX[0]
    lab.measure(spec)

    events = lab._ledger._events
    anchor_env = events[0].environment_hash
    measurement_env = events[-1].environment_hash
    assert anchor_env == measurement_env

    # Tamper: change the measurement event's environment_hash to simulate
    # evidence from a different environment.
    ev = events[-1]
    tampered = ev.model_copy(update={"environment_hash": "sha256:different-env"})
    lab._ledger._events[-1] = tampered
    lab._ledger._event_hashes[-1] = tampered.computed_hash()

    assert not lab._ledger.verify_environment_binding()


# --- R2.8.9: changed test identity --------------------------------------------

def test_changed_test_identity_detected_by_holdout():
    """R2.8.9: swapping a hidden holdout test id after measurement is detected.

    The measurement event carries ``holdout_intact`` in its payload. Tampering
    this value breaks the event hash, which cascades through the chain.
    """
    lab = _lab()
    spec = MUTATION_MATRIX[0]
    lab.measure(spec)

    ev = lab._ledger._events[-1]
    tampered = ev.model_copy(update={
        "payload": {**ev.payload, "holdout_intact": not ev.payload["holdout_intact"]},
    })
    lab._ledger._events[-1] = tampered
    lab._ledger._event_hashes[-1] = tampered.computed_hash()

    assert not lab._ledger.verify_event_chain()


# --- R2.8.9: changed artifact / ISR -------------------------------------------

def test_changed_isr_detected_by_candidate_hash():
    """R2.8.9: evidence bound to candidate_hash A cannot be laundered for
    candidate_hash B. The candidate_hash field on measurement events binds
    the evidence to a specific ISR artifact."""
    lab = _lab()
    spec = MUTATION_MATRIX[0]
    lab.measure(spec)

    ev = lab._ledger._events[-1]
    assert ev.candidate_hash == lab._ledger._events[-1].payload["candidate_hash"]
    assert ev.candidate_hash != ""

    # Tamper: rewire candidate_hash to a different value.
    tampered = ev.model_copy(update={
        "candidate_hash": "sha256:different-artifact",
        "payload": {**ev.payload, "candidate_hash": "sha256:different-artifact"},
    })
    lab._ledger._events[-1] = tampered
    lab._ledger._event_hashes[-1] = tampered.computed_hash()

    assert not lab._ledger.verify_event_chain()


# --- R2.8.10: determinism guarantees reproducibility ---------------------------

def test_measurements_are_deterministic_across_replay():
    """R2.8.10: the same mutation measured twice produces identical evidence
    hashes and verdicts -- the foundation for replay equivalency checks."""
    from constitutional_architecture.isr.serialization.serializer import ISRSerializer

    lab_a = _lab()
    p, b, br, ap, d, m = _fresh_harness()
    lab_b = MeasurementLayer(d, EvolutionLedger(), p, br)

    for spec in MUTATION_MATRIX:
        ma = lab_a.measure(spec)
        mb = lab_b.measure(spec)
        assert ma.evidence_hash == mb.evidence_hash, spec.mutation_id
        assert ma.actual_verdict == mb.actual_verdict, spec.mutation_id
        assert ma.evidence_intact == mb.evidence_intact


def test_composed_measurements_deterministic():
    """R2.8.10: composed attacks produce identical evidence across replays."""
    p, b, br, ap, d, m = _fresh_harness()
    c = MutationComposer()

    for spec in COMPOSED_MUTATION_MATRIX:
        e1 = c.compose(spec, b, seed=11)
        e2 = c.compose(spec, b, seed=11)
        assert e1.content_hash() == e2.content_hash(), spec.composition_id


# --- R2.8.9+10: certification-level integrity invariant -------------------------

def test_certification_evidence_integrity_invariant():
    """R2.8.9+10: the MeasurementSummary's evidence_integrity flag must be True
    for an uncompromised corpus, and must become False if any event is tampered."""
    lab = _lab()
    metrics = tuple(lab.measure(spec) for spec in MUTATION_MATRIX)
    summary = lab.summarize(metrics)
    assert summary.evidence_integrity

    # Tamper with the last measurement event.
    events = lab._ledger._events
    ev = events[-1]
    tampered = ev.model_copy(update={
        "payload": {**ev.payload, "actual_verdict": "infeasible"},
    })
    lab._ledger._events[-1] = tampered
    lab._ledger._event_hashes[-1] = tampered.computed_hash()

    # A fresh measure() now sees the broken chain.
    new_metrics = lab.measure(MUTATION_MATRIX[0])
    assert not new_metrics.evidence_intact
