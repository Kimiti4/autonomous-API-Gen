"""
Tests for Phase 22.8 production certification and closure.
"""

from civilization.certification.engine import (
    CertificationEngine,
    DOMAIN_REQUIREMENTS,
)
from civilization.certification.models import (
    CertificationDomain,
    CertificationEvidence,
    CertificationPolicy,
    CertificationStatus,
    EvidenceSeverity,
    ManualEvidencePayload,
)
from civilization.utils import utcnow


def make_all_pass_collectors():
    collectors = {}

    for domain in CertificationDomain:
        def collector(engines, context, domain=domain):
            return [
                CertificationEvidence(
                    domain=domain,
                    requirement=requirement,
                    satisfied=True,
                    severity=EvidenceSeverity.INFO,
                    source="test_collector",
                    details="Test evidence.",
                    override_allowed=True,
                    collected_at=utcnow().isoformat(),
                )
                for requirement in DOMAIN_REQUIREMENTS[domain]
            ]

        collectors[domain] = [collector]

    return collectors


def test_full_certification_passes_with_all_evidence():
    engine = CertificationEngine(
        policy=CertificationPolicy(),
        engines={},
        context={},
        collectors=make_all_pass_collectors(),
    )

    report = engine.certify(issued_by="test_certifier")

    assert report.status == CertificationStatus.CERTIFIED
    assert report.blocking_count == 0
    assert report.expires_at is not None


def test_default_certification_fails_without_evidence():
    engine = CertificationEngine(
        policy=CertificationPolicy(),
        engines={},
        context={},
    )

    report = engine.certify(issued_by="test_certifier")

    assert report.status == CertificationStatus.NOT_CERTIFIED
    assert report.blocking_count > 0


def test_manual_evidence_can_satisfy_documentation_domain():
    domain = CertificationDomain.DOCUMENTATION_ADRS

    engine = CertificationEngine(
        policy=CertificationPolicy(),
        engines={},
        context={},
        collectors={domain: []},
    )

    for requirement in DOMAIN_REQUIREMENTS[domain]:
        engine.add_manual_evidence(
            ManualEvidencePayload(
                domain=domain,
                requirement=requirement,
                satisfied=True,
                severity=EvidenceSeverity.INFO,
                source="test_documentation",
                details="Manual documentation evidence.",
            )
        )

    assessment = engine.assess_domain(domain)

    assert assessment.passed is True
    assert assessment.blocking_issues == []


def test_certification_can_be_revoked():
    engine = CertificationEngine(
        policy=CertificationPolicy(),
        engines={},
        context={},
        collectors=make_all_pass_collectors(),
    )

    report = engine.certify(issued_by="test_certifier")

    revoked = engine.revoke_certification(
        report_id=report.id,
        revoked_by="security_reviewer",
        reason="Critical security incident.",
    )

    assert revoked.status == CertificationStatus.REVOKED
    assert revoked.revocation_reason == "Critical security incident."


def test_revoke_nonexistent_report_raises():
    engine = CertificationEngine(
        policy=CertificationPolicy(),
        engines={},
        context={},
        collectors=make_all_pass_collectors(),
    )

    from civilization.certification.engine import CertificationError

    try:
        engine.revoke_certification(
            report_id="nonexistent",
            revoked_by="reviewer",
            reason="test",
        )
        assert False, "Expected CertificationError"
    except CertificationError:
        pass


def test_get_report_stores_and_retrieves():
    engine = CertificationEngine(
        policy=CertificationPolicy(),
        engines={},
        context={},
        collectors=make_all_pass_collectors(),
    )

    report = engine.certify(issued_by="test_certifier")

    retrieved = engine.get_report(report.id)

    assert retrieved.id == report.id
    assert retrieved.status == CertificationStatus.CERTIFIED


def test_get_nonexistent_report_raises():
    from civilization.certification.engine import CertificationError

    engine = CertificationEngine(
        policy=CertificationPolicy(),
        engines={},
        context={},
        collectors=make_all_pass_collectors(),
    )

    try:
        engine.get_report("nonexistent")
        assert False, "Expected CertificationError"
    except CertificationError:
        pass


def test_list_reports_empty_initially():
    engine = CertificationEngine(
        policy=CertificationPolicy(),
        engines={},
        context={},
        collectors=make_all_pass_collectors(),
    )

    assert engine.list_reports() == []


def test_list_reports_returns_all_certified():
    engine = CertificationEngine(
        policy=CertificationPolicy(),
        engines={},
        context={},
        collectors=make_all_pass_collectors(),
    )

    report1 = engine.certify(issued_by="certifier_1")
    report2 = engine.certify(issued_by="certifier_2")

    reports = engine.list_reports()

    assert len(reports) == 2
    assert report1.id in [r.id for r in reports]
    assert report2.id in [r.id for r in reports]


def test_conditional_certification_with_warnings_allowed():
    engine = CertificationEngine(
        policy=CertificationPolicy(allow_conditional_on_warnings=True),
        engines={},
        context={},
        collectors=make_all_pass_collectors(),
    )

    report = engine.certify(issued_by="test_certifier")

    # No warnings with all-pass collectors, so should be fully CERTIFIED
    assert report.status == CertificationStatus.CERTIFIED


def test_manual_evidence_unknown_requirement_raises():
    from civilization.certification.engine import CertificationError

    engine = CertificationEngine(
        policy=CertificationPolicy(),
        engines={},
        context={},
    )

    payload = ManualEvidencePayload(
        domain=CertificationDomain.OBSERVABILITY,
        requirement="nonexistent_requirement",
        satisfied=True,
        severity=EvidenceSeverity.INFO,
        source="test",
        details="bad",
    )

    try:
        engine.add_manual_evidence(payload)
        assert False, "Expected CertificationError for unknown requirement"
    except CertificationError:
        pass


def test_critical_blocking_evidence_prevents_certification():
    from civilization.certification.engine import CertificationError

    domain = CertificationDomain.OBSERVABILITY

    def failing_collector(engines, context):
        return [
            CertificationEvidence(
                domain=domain,
                requirement="structured_events",
                satisfied=False,
                severity=EvidenceSeverity.BLOCKING,
                source="test",
                details="Critical failure.",
                override_allowed=False,
                collected_at=utcnow().isoformat(),
            )
        ]

    other_collectors = make_all_pass_collectors()
    other_collectors[domain] = [failing_collector]

    engine = CertificationEngine(
        policy=CertificationPolicy(),
        engines={},
        context={},
        collectors=other_collectors,
    )

    report = engine.certify(issued_by="test_certifier")

    assert report.status == CertificationStatus.NOT_CERTIFIED
    assert report.blocking_count > 0


def test_overrideable_blocking_evidence_produces_warning():
    domain = CertificationDomain.OBSERVABILITY

    def overrideable_failing(engines, context):
        return [
            CertificationEvidence(
                domain=domain,
                requirement="structured_events",
                satisfied=False,
                severity=EvidenceSeverity.BLOCKING,
                source="test",
                details="Overrideable failure.",
                override_allowed=True,
                collected_at=utcnow().isoformat(),
            ),
            CertificationEvidence(
                domain=domain,
                requirement="structured_events",
                satisfied=True,
                severity=EvidenceSeverity.INFO,
                source="compensating_test",
                details="Compensating evidence satisfies requirement.",
                override_allowed=True,
                collected_at=utcnow().isoformat(),
            ),
        ] + [
            CertificationEvidence(
                domain=domain,
                requirement=r,
                satisfied=True,
                severity=EvidenceSeverity.INFO,
                source="test",
                details="ok",
                override_allowed=True,
                collected_at=utcnow().isoformat(),
            )
            for r in DOMAIN_REQUIREMENTS[domain]
            if r != "structured_events"
        ]

    collectors = make_all_pass_collectors()
    collectors[domain] = [overrideable_failing]

    engine = CertificationEngine(
        policy=CertificationPolicy(),
        engines={},
        context={},
        collectors=collectors,
    )

    report = engine.certify(issued_by="test_certifier")

    assessment = [
        a for a in report.domains if a.domain == domain
    ][0]
    assert len(assessment.warnings) > 0


def test_certification_report_has_ttl():
    from datetime import datetime, timedelta

    from civilization.utils import utcnow
    from datetime import timezone

    engine = CertificationEngine(
        policy=CertificationPolicy(certification_ttl_days=30),
        engines={},
        context={},
        collectors=make_all_pass_collectors(),
    )

    report = engine.certify(issued_by="test_certifier")

    created = datetime.fromisoformat(report.created_at)
    expires = datetime.fromisoformat(report.expires_at)

    assert (expires - created) == timedelta(days=30)


def test_revoked_report_keeps_status():
    engine = CertificationEngine(
        policy=CertificationPolicy(),
        engines={},
        context={},
        collectors=make_all_pass_collectors(),
    )

    report = engine.certify(issued_by="test_certifier")

    assert report.status == CertificationStatus.CERTIFIED

    revoked = engine.revoke_certification(
        report_id=report.id,
        revoked_by="reviewer",
        reason="revocation",
    )

    assert revoked.status == CertificationStatus.REVOKED
    assert revoked.revoked_at is not None
    assert revoked.issued_by == "reviewer"


def test_domain_assessment_tracks_missing_requirements():
    engine = CertificationEngine(
        policy=CertificationPolicy(),
        engines={},
        context={},
        collectors=make_all_pass_collectors(),
    )

    assessment = engine.assess_domain(CertificationDomain.SECURITY_PRIVACY_AUDIT)

    assert assessment.passed is True
    assert assessment.evidence_count > 0


def test_default_collectors_defined_for_all_domains():
    from civilization.certification.engine import DEFAULT_COLLECTORS

    for domain in CertificationDomain:
        assert domain in DEFAULT_COLLECTORS
        assert len(DEFAULT_COLLECTORS[domain]) > 0


def test_certify_generates_unique_report_ids():
    engine = CertificationEngine(
        policy=CertificationPolicy(),
        engines={},
        context={},
        collectors=make_all_pass_collectors(),
    )

    report1 = engine.certify(issued_by="certifier_1")
    report2 = engine.certify(issued_by="certifier_2")

    assert report1.id != report2.id


def test_normalize_evidence_assigns_id():
    engine = CertificationEngine(
        policy=CertificationPolicy(),
        engines={},
        context={},
        collectors=make_all_pass_collectors(),
    )

    evidence = CertificationEvidence(
        domain=CertificationDomain.OBSERVABILITY,
        requirement="structured_events",
        satisfied=True,
        severity=EvidenceSeverity.INFO,
        source="test",
        details="raw",
        override_allowed=True,
        collected_at=utcnow().isoformat(),
    )

    normalized = engine._normalize_evidence(evidence)

    assert normalized.id is not None
    assert len(normalized.id) > 0


def test_all_domains_covered_in_requirements():
    for domain in CertificationDomain:
        requirements = DOMAIN_REQUIREMENTS[domain]
        assert len(requirements) > 0


def test_certify_issued_by_persisted_in_report():
    engine = CertificationEngine(
        policy=CertificationPolicy(),
        engines={},
        context={},
        collectors=make_all_pass_collectors(),
    )

    report = engine.certify(issued_by="production_certification_review_board")

    assert report.issued_by == "production_certification_review_board"


def test_manual_evidence_appended_to_assessment():
    domain = CertificationDomain.OBSERVABILITY

    engine = CertificationEngine(
        policy=CertificationPolicy(),
        engines={},
        context={},
        collectors={domain: []},
    )

    for requirement in DOMAIN_REQUIREMENTS[domain]:
        engine.add_manual_evidence(
            ManualEvidencePayload(
                domain=domain,
                requirement=requirement,
                satisfied=True,
                severity=EvidenceSeverity.INFO,
                source="manual_evidence_test",
                details="Manual evidence.",
            )
        )

    assessment = engine.assess_domain(domain)

    assert assessment.passed is True
    assert assessment.evidence_count > 0
