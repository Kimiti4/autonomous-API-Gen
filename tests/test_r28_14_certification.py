"""R2.8.14 -- Certification.

Asserts the three-way status logic, multi-dimensionality, epistemic honesty
(environment gap -> QUALIFIED, never silent CERTIFIED), tamper detection, and
chain anchoring.
"""

import dataclasses

import pytest

from tiannara.application.evolution.certification import (
    CertificationAnchors,
    CertificationAuthority,
    CertificationStatus,
    CoverageStatus,
    EnvironmentCapability,
    EnvironmentCapabilityStatus,
    QuarantineDisposition,
    SectionResult,
)
from tiannara.application.evolution.ledger import (
    EventType,
    EvolutionEvent,
    EvolutionLedger,
)


def build_ledger() -> EvolutionLedger:
    return EvolutionLedger()


def _anchors():
    return CertificationAnchors(
        corpus_hash="corpus-h", protected_test_hash="protected-h",
        holdout_hash="holdout-h", baseline_hash="baseline-h", isr_hash="isr-h",
    )


def _quarantine():
    return QuarantineDisposition(
        failure_count=4, introduced_by_r28=False,
        causal_reproduction="CONFIRMED_PRE_R28",
        impact="Blocks DYNAMIC certification of regression/performance",
    )


def _env(dynamic: EnvironmentCapabilityStatus, note: str = ""):
    return EnvironmentCapability(
        hermetic_static=EnvironmentCapabilityStatus.AVAILABLE,
        hermetic_composition=EnvironmentCapabilityStatus.AVAILABLE,
        dynamic_execution=dynamic, dynamic_execution_note=note,
    )


def _passing_sections():
    return {
        f"section_{i}": (lambda i=i: SectionResult(
            section_id=f"section_{i}", passed=True, mandatory=True,
            metrics={"detection_rate": 1.0},
        ))
        for i in range(3)
    }


# 1. Docker down + all hermetic checks pass -> QUALIFIED_PARTIAL, not CERTIFIED
def test_environment_gap_yields_qualified_not_certified():
    authority = CertificationAuthority(
        ledger=build_ledger(), environment=_env(EnvironmentCapabilityStatus.UNAVAILABLE,
                                                 "4 pre-existing Docker failures"),
        section_runners=_passing_sections(), anchors=_anchors(), quarantine=_quarantine(),
    )
    artifact = authority.certify()
    assert artifact.status is CertificationStatus.QUALIFIED_PARTIAL
    # Epistemic honesty: the gap is recorded, not hidden.
    blocked = [c for c in artifact.dimension_coverage
               if c.status is CoverageStatus.BLOCKED_BY_ENVIRONMENT]
    assert blocked, "blocked dimensions must be explicitly recorded"


# 2. Docker available + all checks pass -> CERTIFIED_FULL
def test_full_certification_when_all_dimensions_evaluated():
    authority = CertificationAuthority(
        ledger=build_ledger(), environment=_env(EnvironmentCapabilityStatus.AVAILABLE),
        section_runners=_passing_sections(), anchors=_anchors(), quarantine=_quarantine(),
    )
    artifact = authority.certify()
    assert artifact.status is CertificationStatus.CERTIFIED_FULL


# 3. A mandatory invariant failure -> NOT_CERTIFIED, even if env is available
def test_mandatory_failure_yields_not_certified():
    runners = _passing_sections()
    runners["broken"] = lambda: SectionResult(
        section_id="broken", passed=False, mandatory=True,
        metrics={"bypass_count": 3},
    )
    authority = CertificationAuthority(
        ledger=build_ledger(), environment=_env(EnvironmentCapabilityStatus.AVAILABLE),
        section_runners=runners, anchors=_anchors(), quarantine=_quarantine(),
    )
    artifact = authority.certify()
    assert artifact.status is CertificationStatus.NOT_CERTIFIED


# 4. Tampered certification is detected via content hash ---------------------
def test_tampered_certification_detected():
    authority = CertificationAuthority(
        ledger=build_ledger(), environment=_env(EnvironmentCapabilityStatus.AVAILABLE),
        section_runners=_passing_sections(), anchors=_anchors(), quarantine=_quarantine(),
    )
    artifact = authority.certify()
    original_hash = artifact.content_hash()
    # Tamper: flip the status without re-anchoring.
    tampered = dataclasses.replace(artifact, status=CertificationStatus.NOT_CERTIFIED)
    assert tampered.content_hash() != original_hash


# 5. Certification is anchored in the ledger as a CERTIFICATION event --------
def test_certification_anchored_in_ledger():
    ledger = build_ledger()
    authority = CertificationAuthority(
        ledger=ledger, environment=_env(EnvironmentCapabilityStatus.AVAILABLE),
        section_runners=_passing_sections(), anchors=_anchors(), quarantine=_quarantine(),
    )
    artifact = authority.certify()
    cert_events = [e for e in ledger.events() if e.event_type is EventType.CERTIFICATION]
    assert len(cert_events) == 1
    assert cert_events[0].payload["artifact_content_hash"] == artifact.content_hash()
    assert ledger.verify_event_chain() is True


# 6. Multi-dimensionality: per-section results, no single aggregate ----------
def test_certification_is_multidimensional():
    authority = CertificationAuthority(
        ledger=build_ledger(), environment=_env(EnvironmentCapabilityStatus.AVAILABLE),
        section_runners=_passing_sections(), anchors=_anchors(), quarantine=_quarantine(),
    )
    artifact = authority.certify()
    assert len(artifact.sections) == len(_passing_sections())
    # The summary exposes per-section adversarial signals, not one collapsed score.
    assert len(artifact.adversarial_signals) >= len(artifact.sections)


# 7. Determinism: same inputs -> same certification id + content hash --------
def test_certification_deterministic():
    def build():
        authority = CertificationAuthority(
            ledger=build_ledger(), environment=_env(EnvironmentCapabilityStatus.AVAILABLE),
            section_runners=_passing_sections(), anchors=_anchors(),
            quarantine=_quarantine(),
        )
        return authority.certify()
    a, b = build(), build()
    assert a.certification_id == b.certification_id
    assert a.content_hash() == b.content_hash()


# 8. Red-team scope + budget are recorded (epistemic honesty) ----------------
def test_red_team_scope_and_budget_recorded():
    authority = CertificationAuthority(
        ledger=build_ledger(), environment=_env(EnvironmentCapabilityStatus.AVAILABLE),
        section_runners=_passing_sections(), anchors=_anchors(),
        quarantine=_quarantine(), red_team_query_budget=1500,
    )
    artifact = authority.certify()
    assert artifact.red_team_query_budget == 1500
    assert "known attack primitives" in artifact.red_team_scope_note


# 9. Quarantine disposition is recorded, not silently dropped ----------------
def test_quarantine_recorded():
    authority = CertificationAuthority(
        ledger=build_ledger(), environment=_env(EnvironmentCapabilityStatus.UNAVAILABLE),
        section_runners=_passing_sections(), anchors=_anchors(), quarantine=_quarantine(),
    )
    artifact = authority.certify()
    assert artifact.quarantine.failure_count == 4
    assert artifact.quarantine.introduced_by_r28 is False
    assert artifact.quarantine.causal_reproduction == "CONFIRMED_PRE_R28"


# 10. Mandatory section failure is NOT_CERTIFIED even when env is blocked ----
def test_mandatory_failure_beats_environment_qualification():
    """A hermetic mandatory failure must dominate an environment gap:
    NOT_CERTIFIED, never QUALIFIED_PARTIAL."""
    runners = _passing_sections()
    runners["evidence_integrity"] = lambda: SectionResult(
        section_id="evidence_integrity", passed=False, mandatory=True,
        metrics={"tamper_rejections": 1},
        limitations=("R2.8.9 evidence chain broken",),
    )
    authority = CertificationAuthority(
        ledger=build_ledger(), environment=_env(EnvironmentCapabilityStatus.UNAVAILABLE),
        section_runners=runners, anchors=_anchors(), quarantine=_quarantine(),
    )
    artifact = authority.certify()
    assert artifact.status is CertificationStatus.NOT_CERTIFIED


# 11. Certification event is chained to prior ledger events ------------------
def test_certification_chained_in_ledger():
    ledger = build_ledger()
    # Seed the chain with a prior anchor event (simulating measurement history).
    ledger.append_event(
        EvolutionEvent(
            event_id="", evolution_id="r2.8.7", sequence=0,
            event_type=EventType.ANCHOR,
            subject_id="protected-core",
            payload={"kind": "anchor", "holdout_hash": "holdout-h"},
        ),
        evolution_id="r2.8.7",
    )
    authority = CertificationAuthority(
        ledger=ledger, environment=_env(EnvironmentCapabilityStatus.AVAILABLE),
        section_runners=_passing_sections(), anchors=_anchors(), quarantine=_quarantine(),
    )
    artifact = authority.certify()

    cert_events = [e for e in ledger.events() if e.event_type is EventType.CERTIFICATION]
    assert len(cert_events) == 1
    cert_ev = cert_events[0]
    # parent_event_id must link to the prior anchor's event_hash.
    anchor_ev = ledger.events()[0]
    assert cert_ev.parent_event_id == anchor_ev.event_hash
    assert ledger.verify_event_chain() is True


# 12. Tampering the anchored CERTIFICATION event breaks the chain ------------
def test_ledger_tampering_after_certification_detected():
    ledger = build_ledger()
    authority = CertificationAuthority(
        ledger=ledger, environment=_env(EnvironmentCapabilityStatus.AVAILABLE),
        section_runners=_passing_sections(), anchors=_anchors(), quarantine=_quarantine(),
    )
    artifact = authority.certify()

    # Tamper with the anchored certification event payload WITHOUT re-signing.
    cert_idx = next(
        i for i, e in enumerate(ledger.events())
        if e.event_type is EventType.CERTIFICATION
    )
    ev = ledger._events[cert_idx]
    tampered = ev.model_copy(update={
        "payload": {**ev.payload, "status": "NOT_CERTIFIED"},
    })
    assert tampered.computed_hash() != ev.event_hash
    ledger._events[cert_idx] = tampered
    assert not ledger.verify_event_chain()