"""
Tests for Phase 22.2 reputation, trust scoring, and capability certification.
"""

from datetime import timedelta

import pytest

from civilization.reputation.engine import (
    ReputationEngine,
    StaticReputationGovernanceGateway,
)
from civilization.reputation.models import (
    CapabilityCertificationPolicy,
    CertificationStatus,
    ReputationEventType,
    ReputationOutcome,
    ReputationSubjectType,
)
from civilization.utils import utcnow


def build_engine() -> ReputationEngine:
    engine = ReputationEngine()

    engine.certification_policies["test_capability"] = (
        CapabilityCertificationPolicy(
            capability="test_capability",
            name="Test Capability Certification",
            description="Test capability.",
            required_evidence_types=["test_evidence"],
            min_trust=0.5,
            min_completed_tasks=1,
            max_negative_events=1,
            ttl_days=30,
        )
    )

    return engine


def test_positive_events_increase_trust():
    engine = build_engine()

    for index in range(3):
        engine.record_event(
            subject_type=ReputationSubjectType.ORGANIZATION,
            subject_id="organization_1",
            event_type=ReputationEventType.TASK_OUTCOME,
            outcome=ReputationOutcome.POSITIVE,
            weight=0.2,
            task_id=f"task_{index}",
        )

    report = engine.trust_report(
        subject_type=ReputationSubjectType.ORGANIZATION,
        subject_id="organization_1",
    )

    assert report.score > 0.5
    assert report.event_count == 3
    assert report.confidence > 0.0


def test_negative_events_reduce_trust():
    engine = build_engine()

    engine.record_event(
        subject_type=ReputationSubjectType.ORGANIZATION,
        subject_id="organization_1",
        event_type=ReputationEventType.TASK_OUTCOME,
        outcome=ReputationOutcome.POSITIVE,
        weight=0.2,
        task_id="task_positive",
    )

    engine.record_event(
        subject_type=ReputationSubjectType.ORGANIZATION,
        subject_id="organization_1",
        event_type=ReputationEventType.TASK_OUTCOME,
        outcome=ReputationOutcome.NEGATIVE,
        weight=0.4,
        task_id="task_negative",
    )

    report = engine.trust_report(
        subject_type=ReputationSubjectType.ORGANIZATION,
        subject_id="organization_1",
    )

    assert report.score < 0.5


def test_certification_lifecycle():
    engine = build_engine()

    engine.record_task_outcome(
        subject_type=ReputationSubjectType.AGENT,
        subject_id="agent_1",
        task_id="task_1",
        outcome=ReputationOutcome.POSITIVE,
        capability="test_capability",
        task_type="test_task",
        evidence_refs=["test_evidence:task_1"],
    )

    application, certification = engine.apply_certification(
        subject_type=ReputationSubjectType.AGENT,
        subject_id="agent_1",
        capability="test_capability",
        evidence_refs=["test_evidence:task_1"],
    )

    assert application.status.value == "APPROVED"
    assert certification is not None
    assert certification.status == CertificationStatus.ACTIVE

    assert engine.can_perform(
        subject_type=ReputationSubjectType.AGENT,
        subject_id="agent_1",
        capability="test_capability",
    )

    revoked = engine.revoke_certification(
        certification_id=certification.id,
        reason="Test revocation.",
    )

    assert revoked.status == CertificationStatus.REVOKED

    assert not engine.can_perform(
        subject_type=ReputationSubjectType.AGENT,
        subject_id="agent_1",
        capability="test_capability",
    )


def test_certification_expiration():
    engine = build_engine()

    engine.record_task_outcome(
        subject_type=ReputationSubjectType.AGENT,
        subject_id="agent_2",
        task_id="task_2",
        outcome=ReputationOutcome.POSITIVE,
        capability="test_capability",
        task_type="test_task",
        evidence_refs=["test_evidence:task_2"],
    )

    application, certification = engine.apply_certification(
        subject_type=ReputationSubjectType.AGENT,
        subject_id="agent_2",
        capability="test_capability",
        evidence_refs=["test_evidence:task_2"],
    )

    assert certification is not None

    future_time = utcnow() + timedelta(days=31)

    expired_ids = engine.check_expirations(now=future_time)

    assert certification.id in expired_ids

    assert not engine.can_perform(
        subject_type=ReputationSubjectType.AGENT,
        subject_id="agent_2",
        capability="test_capability",
        now=future_time,
    )


def test_certification_rejected_without_evidence():
    engine = build_engine()

    engine.record_task_outcome(
        subject_type=ReputationSubjectType.AGENT,
        subject_id="agent_3",
        task_id="task_3",
        outcome=ReputationOutcome.POSITIVE,
        capability="test_capability",
        task_type="test_task",
        evidence_refs=["wrong_evidence:task_3"],
    )

    application, certification = engine.apply_certification(
        subject_type=ReputationSubjectType.AGENT,
        subject_id="agent_3",
        capability="test_capability",
        evidence_refs=["wrong_evidence:task_3"],
    )

    assert application.status.value == "REJECTED"
    assert certification is None


def test_certification_rejected_low_trust():
    engine = build_engine()

    engine.record_event(
        subject_type=ReputationSubjectType.AGENT,
        subject_id="agent_4",
        event_type=ReputationEventType.TASK_OUTCOME,
        outcome=ReputationOutcome.NEGATIVE,
        weight=0.5,
        task_id="task_neg_1",
    )

    engine.record_event(
        subject_type=ReputationSubjectType.AGENT,
        subject_id="agent_4",
        event_type=ReputationEventType.TASK_OUTCOME,
        outcome=ReputationOutcome.NEGATIVE,
        weight=0.5,
        task_id="task_neg_2",
    )

    application, certification = engine.apply_certification(
        subject_type=ReputationSubjectType.AGENT,
        subject_id="agent_4",
        capability="test_capability",
        evidence_refs=["test_evidence:task_neg_1"],
    )

    assert application.status.value == "REJECTED"
    assert "Trust" in (application.reason or "")


def test_certification_rejected_too_few_completed_tasks():
    engine = build_engine()

    application, certification = engine.apply_certification(
        subject_type=ReputationSubjectType.AGENT,
        subject_id="agent_5",
        capability="test_capability",
        evidence_refs=["test_evidence:task_5"],
    )

    assert application.status.value == "REJECTED"
    assert "Completed task" in (application.reason or "")


def test_certification_rejected_too_many_negative_events():
    engine = build_engine()

    engine.record_task_outcome(
        subject_type=ReputationSubjectType.AGENT,
        subject_id="agent_6",
        task_id="task_pos_1",
        outcome=ReputationOutcome.POSITIVE,
        capability="test_capability",
        task_type="test_task",
        evidence_refs=["test_evidence:task_pos_1"],
    )

    engine.record_event(
        subject_type=ReputationSubjectType.AGENT,
        subject_id="agent_6",
        event_type=ReputationEventType.TASK_OUTCOME,
        outcome=ReputationOutcome.NEGATIVE,
        weight=0.1,
        task_id="task_neg_a",
    )

    engine.record_event(
        subject_type=ReputationSubjectType.AGENT,
        subject_id="agent_6",
        event_type=ReputationEventType.TASK_OUTCOME,
        outcome=ReputationOutcome.NEGATIVE,
        weight=0.1,
        task_id="task_neg_b",
    )

    application, certification = engine.apply_certification(
        subject_type=ReputationSubjectType.AGENT,
        subject_id="agent_6",
        capability="test_capability",
        evidence_refs=["test_evidence:task_pos_1"],
    )

    assert application.status.value == "REJECTED"
    assert "Negative event" in (application.reason or "")


def test_unknown_capability_rejected():
    engine = build_engine()

    with pytest.raises(Exception):
        engine.apply_certification(
            subject_type=ReputationSubjectType.AGENT,
            subject_id="agent_7",
            capability="nonexistent_capability",
            evidence_refs=["test_evidence:task_7"],
        )


def test_revoke_certification_not_found():
    engine = build_engine()

    with pytest.raises(Exception):
        engine.revoke_certification(
            certification_id="cert_nonexistent",
            reason="Not found.",
        )


def test_list_certifications_filtered():
    engine = build_engine()

    engine.record_task_outcome(
        subject_type=ReputationSubjectType.AGENT,
        subject_id="agent_a",
        task_id="task_a",
        outcome=ReputationOutcome.POSITIVE,
        capability="test_capability",
        task_type="test_task",
        evidence_refs=["test_evidence:task_a"],
    )

    engine.record_task_outcome(
        subject_type=ReputationSubjectType.AGENT,
        subject_id="agent_b",
        task_id="task_b",
        outcome=ReputationOutcome.POSITIVE,
        capability="test_capability",
        task_type="test_task",
        evidence_refs=["test_evidence:task_b"],
    )

    engine.apply_certification(
        subject_type=ReputationSubjectType.AGENT,
        subject_id="agent_a",
        capability="test_capability",
        evidence_refs=["test_evidence:task_a"],
    )

    engine.apply_certification(
        subject_type=ReputationSubjectType.AGENT,
        subject_id="agent_b",
        capability="test_capability",
        evidence_refs=["test_evidence:task_b"],
    )

    agent_a_certs = engine.list_certifications(
        subject_type=ReputationSubjectType.AGENT,
        subject_id="agent_a",
    )

    assert len(agent_a_certs) == 1
    assert agent_a_certs[0].subject_id == "agent_a"

    all_certs = engine.list_certifications(
        subject_type=ReputationSubjectType.AGENT,
        active_only=False,
    )

    assert len(all_certs) == 2

    no_agent_a_after_revoke = engine.list_certifications(
        subject_id="agent_a",
    )

    assert len(no_agent_a_after_revoke) == 1

    revoked = engine.revoke_certification(
        certification_id=agent_a_certs[0].id,
        reason="Review failed.",
    )

    assert revoked.status == CertificationStatus.REVOKED

    active_after_revoke = engine.list_certifications(
        subject_type=ReputationSubjectType.AGENT,
        active_only=True,
    )

    assert len(active_after_revoke) == 1
    assert active_after_revoke[0].subject_id == "agent_b"


def test_trust_decay_over_time():
    engine = build_engine()

    event_time = utcnow()

    engine.record_event(
        subject_type=ReputationSubjectType.ORGANIZATION,
        subject_id="org_decay",
        event_type=ReputationEventType.TASK_OUTCOME,
        outcome=ReputationOutcome.POSITIVE,
        weight=0.5,
        created_at=event_time.isoformat(),
    )

    report_recent = engine.trust_report(
        subject_type=ReputationSubjectType.ORGANIZATION,
        subject_id="org_decay",
    )

    report_old = engine.trust_report(
        subject_type=ReputationSubjectType.ORGANIZATION,
        subject_id="org_decay",
        now=event_time + timedelta(days=180),
    )

    assert report_old.factors["weighted_event_count"] < report_recent.factors["weighted_event_count"]


def test_trust_score_clamped():
    engine = build_engine()

    for index in range(100):
        engine.record_event(
            subject_type=ReputationSubjectType.ORGANIZATION,
            subject_id="org_clamp",
            event_type=ReputationEventType.TASK_OUTCOME,
            outcome=ReputationOutcome.POSITIVE,
            weight=1.0,
            task_id=f"task_clamp_{index}",
        )

    report = engine.trust_report(
        subject_type=ReputationSubjectType.ORGANIZATION,
        subject_id="org_clamp",
    )

    assert report.score <= 1.0


def test_trust_score_not_clamped_below_minimum():
    engine = build_engine()

    for index in range(100):
        engine.record_event(
            subject_type=ReputationSubjectType.ORGANIZATION,
            subject_id="org_floor",
            event_type=ReputationEventType.TASK_OUTCOME,
            outcome=ReputationOutcome.NEGATIVE,
            weight=1.0,
            task_id=f"task_floor_{index}",
        )

    report = engine.trust_report(
        subject_type=ReputationSubjectType.ORGANIZATION,
        subject_id="org_floor",
    )

    assert report.score >= 0.0


def test_trust_no_events():
    engine = build_engine()

    report = engine.trust_report(
        subject_type=ReputationSubjectType.ORGANIZATION,
        subject_id="org_unknown",
    )

    assert report.score == 0.5
    assert report.event_count == 0
    assert report.confidence == 0.0


def test_list_events_filtered():
    engine = build_engine()

    engine.record_event(
        subject_type=ReputationSubjectType.ORGANIZATION,
        subject_id="org_1",
        event_type=ReputationEventType.TASK_OUTCOME,
        outcome=ReputationOutcome.POSITIVE,
    )

    engine.record_event(
        subject_type=ReputationSubjectType.AGENT,
        subject_id="agent_1",
        event_type=ReputationEventType.SECURITY_REVIEW,
        outcome=ReputationOutcome.NEGATIVE,
    )

    org_events = engine.list_events(
        subject_type=ReputationSubjectType.ORGANIZATION,
    )

    assert len(org_events) == 1

    agent_events = engine.list_events(
        subject_type=ReputationSubjectType.AGENT,
    )

    assert len(agent_events) == 1

    neg_events = engine.list_events(
        subject_id="agent_1",
        event_type=ReputationEventType.SECURITY_REVIEW,
    )

    assert len(neg_events) == 1
    assert neg_events[0].outcome == ReputationOutcome.NEGATIVE


def test_record_task_outcome_with_metadata():
    engine = build_engine()

    engine.record_task_outcome(
        subject_type=ReputationSubjectType.AGENT,
        subject_id="agent_meta",
        task_id="task_meta",
        outcome=ReputationOutcome.POSITIVE,
        capability="backend_engineering",
        task_type="backend_design",
    )

    events = engine.list_events(
        subject_type=ReputationSubjectType.AGENT,
        subject_id="agent_meta",
    )

    assert len(events) == 1
    assert events[0].metadata["task_type"] == "backend_design"
    assert events[0].capability == "backend_engineering"


def test_capability_report():
    engine = build_engine()

    engine.record_task_outcome(
        subject_type=ReputationSubjectType.AGENT,
        subject_id="agent_report",
        task_id="task_report",
        outcome=ReputationOutcome.POSITIVE,
        capability="test_capability",
        task_type="test_task",
        evidence_refs=["test_evidence:task_report"],
    )

    engine.apply_certification(
        subject_type=ReputationSubjectType.AGENT,
        subject_id="agent_report",
        capability="test_capability",
        evidence_refs=["test_evidence:task_report"],
    )

    report = engine.capability_report(
        subject_type=ReputationSubjectType.AGENT,
        subject_id="agent_report",
        capability="test_capability",
    )

    assert report["policy"].capability == "test_capability"
    assert report["trust"].score > 0.5
    assert report["completed_task_count"] >= 1
    assert report["negative_event_count"] == 0
    assert report["authorized"] is True
    assert report["active_certification"] is not None


def test_capability_report_no_policy():
    engine = build_engine()

    with pytest.raises(Exception):
        engine.capability_report(
            subject_type=ReputationSubjectType.AGENT,
            subject_id="agent_nopolicy",
            capability="nonexistent_capability",
        )


def test_can_perform_without_certification():
    engine = build_engine()

    engine.record_task_outcome(
        subject_type=ReputationSubjectType.AGENT,
        subject_id="agent_no_cert",
        task_id="task_no_cert",
        outcome=ReputationOutcome.POSITIVE,
        capability="test_capability",
        task_type="test_task",
        evidence_refs=["test_evidence:task_no_cert"],
    )

    assert not engine.can_perform(
        subject_type=ReputationSubjectType.AGENT,
        subject_id="agent_no_cert",
        capability="test_capability",
    )


def test_governance_rejects_certification():
    engine = ReputationEngine(
        governance_gateway=StaticReputationGovernanceGateway(
            decision="DENY",
            reason="Governance denies test capability certification.",
        ),
    )

    engine.certification_policies["governed_capability"] = (
        CapabilityCertificationPolicy(
            capability="governed_capability",
            name="Governed Capability",
            description="Requires governance.",
            require_governance=True,
            min_trust=0.4,
            min_completed_tasks=0,
            max_negative_events=5,
            ttl_days=30,
            required_evidence_types=[],
        )
    )

    engine.record_task_outcome(
        subject_type=ReputationSubjectType.AGENT,
        subject_id="agent_gov",
        task_id="task_gov",
        outcome=ReputationOutcome.POSITIVE,
        capability="governed_capability",
        task_type="governed_task",
        evidence_refs=["test_evidence:task_gov"],
    )

    application, certification = engine.apply_certification(
        subject_type=ReputationSubjectType.AGENT,
        subject_id="agent_gov",
        capability="governed_capability",
        evidence_refs=["test_evidence:task_gov"],
    )

    assert application.status.value == "REJECTED"
    assert certification is None
    assert "Governance" in (application.reason or "")


def test_default_certification_policies_present():
    engine = ReputationEngine()

    expected_capabilities = {
        "architecture_review",
        "security_review",
        "backend_engineering",
        "database_engineering",
        "qa_verification",
        "documentation_engineering",
        "evolution_coordination",
    }

    actual_capabilities = set(engine.certification_policies.keys())

    assert expected_capabilities.issubset(actual_capabilities)


def test_event_id_is_deterministic():
    engine1 = build_engine()
    engine2 = build_engine()

    fixed_time = "2024-01-15T12:00:00+00:00"

    event1 = engine1.record_event(
        subject_type=ReputationSubjectType.ORGANIZATION,
        subject_id="org_deterministic",
        event_type=ReputationEventType.TASK_OUTCOME,
        outcome=ReputationOutcome.POSITIVE,
        weight=0.1,
        task_id="task_det",
        created_at=fixed_time,
    )

    event2 = engine2.record_event(
        subject_type=ReputationSubjectType.ORGANIZATION,
        subject_id="org_deterministic",
        event_type=ReputationEventType.TASK_OUTCOME,
        outcome=ReputationOutcome.POSITIVE,
        weight=0.1,
        task_id="task_det",
        created_at=fixed_time,
    )

    assert event1.id == event2.id


def test_trust_report_recent_counts():
    engine = build_engine()

    now = utcnow()

    engine.record_event(
        subject_type=ReputationSubjectType.ORGANIZATION,
        subject_id="org_recent",
        event_type=ReputationEventType.TASK_OUTCOME,
        outcome=ReputationOutcome.POSITIVE,
        weight=0.1,
        created_at=now.isoformat(),
    )

    engine.record_event(
        subject_type=ReputationSubjectType.ORGANIZATION,
        subject_id="org_recent",
        event_type=ReputationEventType.TASK_OUTCOME,
        outcome=ReputationOutcome.NEGATIVE,
        weight=0.1,
        created_at=(now - timedelta(days=10)).isoformat(),
    )

    engine.record_event(
        subject_type=ReputationSubjectType.ORGANIZATION,
        subject_id="org_recent",
        event_type=ReputationEventType.TASK_OUTCOME,
        outcome=ReputationOutcome.POSITIVE,
        weight=0.1,
        created_at=(now - timedelta(days=60)).isoformat(),
    )

    report = engine.trust_report(
        subject_type=ReputationSubjectType.ORGANIZATION,
        subject_id="org_recent",
        now=now,
    )

    assert report.recent_positive_count == 1
    assert report.recent_negative_count == 1
