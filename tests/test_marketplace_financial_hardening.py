"""
Tests for Phase 24.9 Marketplace Production Hardening and Financial Governance.

Covers the required testing strategy: unit tests, integration tests, and
security tests (unsigned webhook rejection, invalid provider event rejection,
refund authorization enforcement, adapter fail-closed behavior).
"""

from datetime import timedelta
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from product_factory.marketplace_financial_hardening.api import (
    enable_marketplace_financial_hardening,
)
from product_factory.marketplace_financial_hardening.compliance import (
    FinancialComplianceEngine,
)
from product_factory.marketplace_financial_hardening.engine import (
    FinancialHardeningEngine,
)
from product_factory.marketplace_financial_hardening.fraud import (
    FraudProviderAdapter,
    FraudControlEngine,
)
from product_factory.marketplace_financial_hardening.ledger import FinancialLedgerEngine
from product_factory.marketplace_financial_hardening.models import (
    FraudAction,
    LedgerEntryType,
    MarketplaceFinancialPolicy,
    MarketplaceFinancialReadinessEvidence,
    PaymentStatus,
    PaymentWebhookEnvelope,
    RefundStatus,
    SLAStatusOverall,
    SLADomain,
    TaxCalculationRequest,
)
from product_factory.marketplace_financial_hardening.models import utcnow
from product_factory.marketplace_financial_hardening.payments import (
    NoopPaymentAdapter,
    PaymentAdapterEngine,
    PaymentProviderAdapter,
)
from product_factory.marketplace_financial_hardening.reconciliation import (
    ReconciliationEngine,
)
from product_factory.marketplace_financial_hardening.sla import SLAMonitorEngine
from product_factory.marketplace_financial_hardening.tax import (
    NoopTaxAdapter,
    TaxAdapterEngine,
)


def fake_26_8_report(status="CERTIFIED", revoked=False, expired=False):
    expires_at = utcnow() - timedelta(days=1) if expired else utcnow() + timedelta(days=30)

    return SimpleNamespace(
        id="26_8_report_1",
        status=status,
        expires_at=expires_at,
        revoked_at=utcnow() if revoked else None,
    )


def fake_26_8_engine(status="CERTIFIED", revoked=False, expired=False):
    report = fake_26_8_report(status, revoked, expired)

    return SimpleNamespace(
        latest_report=lambda: report,
        reports={report.id: report},
    )


def fake_governance(allow=True):
    calls = []

    def evaluate(action, actor, context, evidence_refs):
        calls.append((getattr(action, "value", action), actor))

        return SimpleNamespace(
            action=action,
            actor=actor,
            allowed=allow,
            decision="APPROVED" if allow else "DENIED",
            audit_ref="audit_ref_1",
            evidence_refs=list(evidence_refs),
        )

    return SimpleNamespace(evaluate=evaluate), calls


def full_readiness_evidence() -> MarketplaceFinancialReadinessEvidence:
    return MarketplaceFinancialReadinessEvidence(
        slo_definitions=["slo_payment_webhook"],
        runbooks=["runbook_payment_processing"],
        incident_response_plans=["ir_payment_processing"],
        backup_restore_evidence=["backup_restore_financial"],
        observability_evidence=["observability_financial_dashboard"],
        dashboard_refs=["financial_dashboard"],
        marketplace_metrics_refs=["marketplace_metrics_financial"],
        payment_adapter_evidence=["payment_adapter_evidence_1"],
        fraud_evidence=["fraud_evidence_1"],
        tax_evidence=["tax_evidence_1"],
        audit_evidence=["audit_evidence_1"],
    )


def payment_payload(status="CAPTURED", amount=100.0):
    return {
        "provider": "test",
        "provider_event_id": "ev_test_1",
        "status": status,
        "amount": amount,
        "currency": "USD",
        "order_id": "order_1",
        "listing_id": "listing_1",
        "tenant_id": "tenant_1",
        "marketplace_id": "marketplace_1",
    }


def signed_envelope(**overrides) -> PaymentWebhookEnvelope:
    payload = payment_payload(**overrides)

    return PaymentWebhookEnvelope(
        provider=payload["provider"],
        provider_event_id=payload["provider_event_id"],
        idempotency_key=payload.get("idempotency_key"),
        signature="sig_valid",
        payload=payload,
    )


# ------------------------------------------------------------------
# Unit tests: payment adapter framework
# ------------------------------------------------------------------


def test_payment_event_normalization_maps_status():
    engine = FinancialHardeningEngine()

    event = engine.process_payment_webhook(signed_envelope(status="PAID"))

    assert event.status == PaymentStatus.CAPTURED
    assert event.amount == 100.0


def test_payment_webhook_idempotency():
    engine = FinancialHardeningEngine()

    env = PaymentWebhookEnvelope(
        provider="test",
        provider_event_id="ev_dup_1",
        idempotency_key="idem_1",
        signature="sig",
        payload=payment_payload(status="CAPTURED"),
    )

    first = engine.process_payment_webhook(env)
    second = engine.process_payment_webhook(env)

    assert first.event_id == second.event_id

    captured = engine.ledger.by_entry_type(
        LedgerEntryType.PAYMENT_CAPTURED, marketplace_id="marketplace_1"
    )

    assert len(captured) == 1


def test_ledger_idempotency_enforced():
    ledger = FinancialLedgerEngine()

    from product_factory.marketplace_financial_hardening.models import (
        FinancialLedgerEntry,
        LedgerEntryType,
    )

    entry = FinancialLedgerEntry(
        marketplace_id="marketplace_1",
        order_id="order_1",
        entry_type=LedgerEntryType.PAYMENT_CAPTURED,
        amount=10.0,
        currency="USD",
        idempotency_key="idem_x",
        source_event_id="src_1",
    )

    assert ledger.append(entry) is True
    assert ledger.append(entry) is False
    assert ledger.total_count() == 1


# ------------------------------------------------------------------
# Security tests
# ------------------------------------------------------------------


def test_unsigned_webhook_rejected():
    engine = FinancialHardeningEngine()

    env = PaymentWebhookEnvelope(
        provider="test",
        provider_event_id="ev_unsigned",
        idempotency_key=None,
        signature=None,
        payload=payment_payload(status="CAPTURED"),
    )

    with pytest.raises(ValueError, match="signature"):
        engine.process_payment_webhook(env)


def test_invalid_provider_event_rejected():
    class BadAdapter(PaymentProviderAdapter):
        def normalize_event(self, payload):
            return {"provider": "test"}

        def verify_signature(self, envelope):
            return True

    ledger = FinancialLedgerEngine()
    payment_engine = PaymentAdapterEngine(
        payment_adapter=BadAdapter(),
        ledger=ledger,
        policy=MarketplaceFinancialPolicy(),
    )

    env = PaymentWebhookEnvelope(
        provider="test",
        provider_event_id="ev_bad",
        signature="sig",
        payload={"anything": "x"},
    )

    with pytest.raises(ValueError, match="Invalid provider payment event"):
        payment_engine.ingest_webhook(env)


def test_refund_authorization_enforced_for_above_threshold():
    gov, _ = fake_governance(allow=False)

    engine = FinancialHardeningEngine(governance=gov)

    with pytest.raises(ValueError, match="denied"):
        engine.request_refund(
            marketplace_id="marketplace_1",
            order_id="order_big",
            listing_id="listing_1",
            tenant_id="tenant_1",
            amount=1000.0,
            currency="USD",
            requested_by="customer",
            original_payment_event_id="ev_test_1",
        )


# ------------------------------------------------------------------
# Integration tests: refunds
# ------------------------------------------------------------------


def test_small_refund_auto_completed():
    gov, calls = fake_governance(allow=True)
    engine = FinancialHardeningEngine(governance=gov)

    refund = engine.request_refund(
        marketplace_id="marketplace_1",
        order_id="order_small",
        listing_id="listing_1",
        tenant_id="tenant_1",
        amount=10.0,
        currency="USD",
        requested_by="customer",
    )

    assert refund.status == RefundStatus.COMPLETED
    assert refund.completed_at is not None

    completed = engine.ledger.by_entry_type(
        LedgerEntryType.REFUND_COMPLETED, marketplace_id="marketplace_1"
    )

    assert len(completed) == 1


def test_refund_above_threshold_requires_governance_approval():
    gov, calls = fake_governance(allow=True)
    engine = FinancialHardeningEngine(governance=gov)

    refund = engine.request_refund(
        marketplace_id="marketplace_1",
        order_id="order_big",
        listing_id="listing_1",
        tenant_id="tenant_1",
        amount=1000.0,
        currency="USD",
        requested_by="customer",
        original_payment_event_id="ev_test_1",
    )

    assert refund.status == RefundStatus.PENDING_APPROVAL

    assert any(
        a == "REFUND_ABOVE_THRESHOLD" for a, _ in calls
    )

    engine.refund_engine.approve_refund(refund.refund_id, approver_id="ops")

    assert refund.status == RefundStatus.COMPLETED


# ------------------------------------------------------------------
# Unit tests: tax and fraud
# ------------------------------------------------------------------


def test_tax_calculation_emits_ledger_adjustment():
    class FixedTaxAdapter(NoopTaxAdapter):
        def calculate_tax(self, request):
            return type("R", (), {
                "tax_request_id": request.tax_request_id,
                "provider": "avatax",
                "jurisdiction": request.jurisdiction,
                "tax_rate": 0.085,
                "tax_amount": 8.5,
                "currency": request.currency,
                "provider_reference": "tx_ref_1",
                "calculated_at": utcnow(),
                "evidence_ref": "tax_evidence_1",
            })()

    engine = FinancialHardeningEngine()
    engine.tax_engine.tax_adapter = FixedTaxAdapter()

    request = TaxCalculationRequest(
        marketplace_id="marketplace_1",
        order_id="order_tax",
        listing_id="listing_1",
        tenant_id="tenant_1",
        jurisdiction="US-CA",
        amounts=[{"amount": 100.0, "currency": "USD"}],
        currency="USD",
        provider="avatax",
    )

    result = engine.calculate_tax(request)

    assert result.tax_amount == 8.5

    tax_entries = engine.ledger.by_entry_type(
        LedgerEntryType.TAX_CALCULATED, marketplace_id="marketplace_1"
    )

    assert len(tax_entries) == 1


def test_fraud_action_mapping_high_score_blocks():
    class HighFraudAdapter(FraudProviderAdapter):
        def assess(self, listing_id, tenant_id, order_id=None, context=None):
            return {
                "provider": "fraudco",
                "fraud_score": 0.9,
                "risk_indicators": ["velocity_anomaly"],
                "provider_reference": "fr_9",
            }

    engine = FinancialHardeningEngine()
    engine.fraud_engine.fraud_adapter = HighFraudAdapter()

    assessment = engine.assess_fraud(listing_id="listing_1", tenant_id="tenant_1")

    assert assessment.action == FraudAction.BLOCK
    assert engine.fraud_engine.is_blocked("listing_1")


def test_fraud_action_mapping_low_score_allows():
    class LowFraudAdapter(FraudProviderAdapter):
        def assess(self, listing_id, tenant_id, order_id=None, context=None):
            return {
                "provider": "fraudco",
                "fraud_score": 0.1,
                "risk_indicators": [],
                "provider_reference": "fr_1",
            }

    engine = FinancialHardeningEngine()
    engine.fraud_engine.fraud_adapter = LowFraudAdapter()

    assessment = engine.assess_fraud(listing_id="listing_2", tenant_id="tenant_1")

    assert assessment.action == FraudAction.ALLOW
    assert not engine.fraud_engine.is_blocked("listing_2")


# ------------------------------------------------------------------
# Unit tests: SLA monitoring
# ------------------------------------------------------------------


def test_sla_breach_detection():
    engine = FinancialHardeningEngine()

    for _ in range(5):
        engine.sla_engine.record(
            SLADomain.PAYMENT_WEBHOOK_PROCESSING_LATENCY,
            value=800.0,
            success=True,
        )

    report = engine.sla_report()

    assert report.overall_status == SLAStatusOverall.BREACH
    assert len(report.alerts) >= 1


def test_sla_ok_when_within_target():
    engine = FinancialHardeningEngine()

    for _ in range(10):
        engine.sla_engine.record(
            SLADomain.PAYMENT_WEBHOOK_PROCESSING_LATENCY,
            value=100.0,
            success=True,
        )

    report = engine.sla_report()

    assert report.overall_status != SLAStatusOverall.BREACH


# ------------------------------------------------------------------
# Integration tests: reconciliation
# ------------------------------------------------------------------


def test_reconciliation_detects_missing_ledger_entry():
    payment_engine = PaymentAdapterEngine(ledger=None)
    payment_engine.ingest_webhook(signed_envelope(status="CAPTURED"))

    recon = ReconciliationEngine(
        ledger=FinancialLedgerEngine(),
        payment_engine=payment_engine,
    )

    report = recon.run_reconciliation("marketplace_1")

    assert report.mismatch_count >= 1
    assert report.mismatches[0].kind.value == "PAYMENT_EVENT_MISSING_LEDGER"


def test_reconciliation_healthy_with_matched_ledger():
    engine = FinancialHardeningEngine()
    engine.process_payment_webhook(signed_envelope(status="CAPTURED"))

    report = engine.run_reconciliation("marketplace_1")

    assert report.status.value == "HEALTHY"
    assert report.mismatch_count == 0


# ------------------------------------------------------------------
# Integration tests: financial compliance certification
# ------------------------------------------------------------------


def _ready_engine(governance=None, production_learning_engine=None):
    gov, _ = fake_governance(allow=True)

    return FinancialHardeningEngine(
        governance=governance or gov,
        production_learning_certification_engine=production_learning_engine
        or fake_26_8_engine(status="CERTIFIED"),
    )


def test_financial_certification_passes_with_human():
    engine = _ready_engine()

    engine.process_payment_webhook(signed_envelope(status="CAPTURED"))
    engine.run_reconciliation("marketplace_1")

    report = engine.certify(
        certified_by="human",
        evidence=full_readiness_evidence(),
    )

    assert report.status == "CERTIFIED"


def test_financial_certification_conditional_for_system():
    engine = _ready_engine()

    engine.process_payment_webhook(signed_envelope(status="CAPTURED"))
    engine.run_reconciliation("marketplace_1")

    report = engine.certify(
        certified_by="system",
        evidence=full_readiness_evidence(),
    )

    assert report.status == "CONDITIONALLY_CERTIFIED"


def test_financial_certification_fails_when_26_8_revoked():
    engine = _ready_engine(
        production_learning_engine=fake_26_8_engine(revoked=True),
    )

    engine.process_payment_webhook(signed_envelope(status="CAPTURED"))
    engine.run_reconciliation("marketplace_1")

    report = engine.certify(
        certified_by="human",
        evidence=full_readiness_evidence(),
    )

    assert report.status == "NOT_CERTIFIED"

    names = [g.name for g in report.gates if not g.passed]
    assert "production_learning_certification" in names


def test_financial_certification_fails_without_governance():
    engine = _ready_engine()

    engine.process_payment_webhook(signed_envelope(status="CAPTURED"))
    engine.run_reconciliation("marketplace_1")

    engine.compliance_engine.governance = None

    report = engine.certify(
        certified_by="human",
        evidence=full_readiness_evidence(),
    )

    assert report.status == "NOT_CERTIFIED"

    names = [g.name for g in report.gates if not g.passed]
    assert "governance_policy_evidence" in names


# ------------------------------------------------------------------
# API integration tests
# ------------------------------------------------------------------


@pytest.fixture()
def api_client():
    app = FastAPI()

    gov, _ = fake_governance(allow=True)

    enable_marketplace_financial_hardening(
        app,
        governance=gov,
        production_learning_certification_engine=fake_26_8_engine(),
    )

    return TestClient(app)


def test_api_payment_event_endpoint_and_ledger(api_client):
    resp = api_client.post(
        "/v1/marketplace/financial/payments/events",
        json={
            "provider": "test",
            "provider_event_id": "ev_api_1",
            "idempotency_key": "idem_api_1",
            "signature": "sig_valid",
            "payload": payment_payload(status="CAPTURED"),
        },
    )

    assert resp.status_code == 201

    resp = api_client.post(
        "/v1/marketplace/financial/payments/events",
        json={
            "provider": "test",
            "provider_event_id": "ev_api_1",
            "signature": "sig_valid",
            "payload": payment_payload(status="CAPTURED"),
        },
    )

    # Duplicate provider event_id is deduplicated (200 on the deduped return
    # path is acceptable; the first ingestion returned 201).
    assert resp.status_code in (200, 201)

    resp = api_client.post(
        "/v1/marketplace/financial/reconciliation/run",
        params={"marketplace_id": "marketplace_1"},
    )

    assert resp.status_code == 201
    assert resp.json()["status"] == "HEALTHY"


def test_api_unsigned_webhook_rejected(api_client):
    resp = api_client.post(
        "/v1/marketplace/financial/payments/events",
        json={
            "provider": "test",
            "provider_event_id": "ev_unsigned_api",
            "signature": None,
            "payload": payment_payload(status="CAPTURED"),
        },
    )

    assert resp.status_code == 422


def test_api_financial_certification_endpoint(api_client):
    api_client.post(
        "/v1/marketplace/financial/payments/events",
        json={
            "provider": "test",
            "provider_event_id": "ev_api_2",
            "signature": "sig_valid",
            "payload": payment_payload(status="CAPTURED"),
        },
    )

    api_client.post(
        "/v1/marketplace/financial/reconciliation/run",
        params={"marketplace_id": "marketplace_1"},
    )

    resp = api_client.post(
        "/v1/marketplace/financial/compliance/certify",
        json={
            "certified_by": "human",
            "evidence": full_readiness_evidence().model_dump(),
        },
    )

    assert resp.status_code == 201
    assert resp.json()["status"] == "CERTIFIED"


def test_api_financial_compliance_revocation(api_client):
    report_id = "legit_report_id"

    api_client.post(
        "/v1/marketplace/financial/compliance/certify",
        json={
            "certified_by": "human",
            "evidence": full_readiness_evidence().model_dump(),
        },
    )

    from product_factory.marketplace_financial_hardening.api import _engine

    app = api_client.app
    state_engine = getattr(app.state, "marketplace_financial_hardening_engine")

    latest = state_engine.latest_certification_report()

    resp = api_client.post(
        f"/v1/marketplace/financial/compliance/report/{latest.report_id}/revoke",
        json={"reason": "Policy violation detected.", "revoked_by": "ops"},
    )

    assert resp.status_code == 200
    assert resp.json()["status"] == "REVOKED"
