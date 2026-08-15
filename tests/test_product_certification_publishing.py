"""
Tests for Phase 24.7 Autonomous Product Certification and Publishing.
"""

import pytest

from product_factory.product_certification_publishing.certification import (
    CertificationGateways,
    ProductCertificationEngine,
)
from product_factory.product_certification_publishing.models import (
    CertificationGate,
    CertificationStatus,
    GateResult,
    ProductCertificationPolicy,
    PublicationStatus,
)
from product_factory.product_certification_publishing.publishing import (
    PublishingEngine,
)


def passing_gate(gate: CertificationGate):
    def gate_fn(product_id: str, product_version: str, evidence: dict):
        return GateResult(
            gate=gate,
            passed=True,
            reason="OK",
        )

    return gate_fn


def failing_gate(gate: CertificationGate):
    def gate_fn(product_id: str, product_version: str, evidence: dict):
        return GateResult(
            gate=gate,
            passed=False,
            severity="HIGH",
            reason=f"{gate.value} failed",
        )

    return gate_fn


def build_all_pass_gateways() -> CertificationGateways:
    return CertificationGateways(
        tests=passing_gate(CertificationGate.TESTS),
        security=passing_gate(CertificationGate.SECURITY),
        performance=passing_gate(CertificationGate.PERFORMANCE),
        documentation=passing_gate(CertificationGate.DOCUMENTATION),
        observability=passing_gate(CertificationGate.OBSERVABILITY),
        deployment=passing_gate(CertificationGate.DEPLOYMENT),
        rollback=passing_gate(CertificationGate.ROLLBACK),
        licensing=passing_gate(CertificationGate.LICENSING),
        marketplace_policy=passing_gate(CertificationGate.MARKETPLACE_POLICY),
        learning_certification=passing_gate(CertificationGate.LEARNING_CERTIFICATION),
    )


def test_product_certification_passes_when_all_gates_pass():
    policy = ProductCertificationPolicy()

    certification_engine = ProductCertificationEngine(
        policy=policy,
        gateways=build_all_pass_gateways(),
    )

    report = certification_engine.certify_product(
        product_id="product_1",
        product_version="1.0.0",
        evidence={},
        certified_by="test",
    )

    assert report.status == CertificationStatus.CERTIFIED
    assert report.expires_at is not None


def test_product_certification_fails_when_security_fails():
    gateways = build_all_pass_gateways()

    gateways.security = failing_gate(CertificationGate.SECURITY)

    policy = ProductCertificationPolicy()

    certification_engine = ProductCertificationEngine(
        policy=policy,
        gateways=gateways,
    )

    report = certification_engine.certify_product(
        product_id="product_1",
        product_version="1.0.0",
        evidence={},
        certified_by="test",
    )

    assert report.status == CertificationStatus.NOT_CERTIFIED
    assert any("SECURITY" in reason for reason in report.reasons)


def test_publication_requires_certification_and_approval():
    policy = ProductCertificationPolicy(
        require_human_first_publication=True,
        allow_autonomous_publishing=False,
    )

    certification_engine = ProductCertificationEngine(
        policy=policy,
        gateways=build_all_pass_gateways(),
    )

    report = certification_engine.certify_product(
        product_id="product_1",
        product_version="1.0.0",
        evidence={},
        certified_by="test",
    )

    publishing_engine = PublishingEngine(
        certification_engine=certification_engine,
        policy=policy,
    )

    publication = publishing_engine.request_publication(
        product_id="product_1",
        product_version="1.0.0",
        marketplace_id="marketplace_1",
        publisher_id="publisher_1",
        certification_report_id=report.id,
    )

    assert publication.status == PublicationStatus.PENDING_APPROVAL

    approved = publishing_engine.approve_publication(
        publication_id=publication.id,
        approver_id="human_approver",
    )

    assert approved.status == PublicationStatus.APPROVED

    published = publishing_engine.publish(publication.id)

    assert published.status == PublicationStatus.PUBLISHED


def test_guardrail_violation_delists_product():
    policy = ProductCertificationPolicy(
        require_human_first_publication=False,
        allow_autonomous_publishing=True,
    )

    certification_engine = ProductCertificationEngine(
        policy=policy,
        gateways=build_all_pass_gateways(),
    )

    report = certification_engine.certify_product(
        product_id="product_1",
        product_version="1.0.0",
        evidence={},
        certified_by="test",
    )

    publishing_engine = PublishingEngine(
        certification_engine=certification_engine,
        policy=policy,
    )

    publication = publishing_engine.request_publication(
        product_id="product_1",
        product_version="1.0.0",
        marketplace_id="marketplace_1",
        publisher_id="publisher_1",
        certification_report_id=report.id,
    )

    publishing_engine.publish(publication.id)

    delisted = publishing_engine.evaluate_guardrails(
        publication_id=publication.id,
        metrics={
            "refund_rate": 0.40,
            "fraud_score": 0.10,
            "conversion_rate": 0.02,
        },
    )

    assert delisted.status == PublicationStatus.DELISTED
    assert delisted.delisting_reason is not None
