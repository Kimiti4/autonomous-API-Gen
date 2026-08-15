"""
Marketplace financial hardening engine (coordinator).

Wires the payment adapter, ledger, refund governance, tax, fraud, SLA,
reconciliation, and financial compliance subsystems together, and provides
a unified interface used by the Phase 24.9 API.
"""

from __future__ import annotations

from typing import Optional

from .compliance import FinancialComplianceEngine
from .fraud import FraudControlEngine
from .ledger import FinancialLedgerEngine
from .models import (
    GovernanceAction,
    GovernanceDecision,
    MarketplaceFinancialPolicy,
    MarketplaceFinancialReadinessEvidence,
    PaymentWebhookEnvelope,
    SLADomain,
)
from .payments import PaymentAdapterEngine
from .refunds import RefundGovernanceEngine
from .reconciliation import ReconciliationEngine
from .sla import SLAMonitorEngine
from .tax import TaxAdapterEngine


class DefaultGovernanceAdapter:
    """Default pass-through governance adapter.

    Production deployments should provide a real Phase 28 GovernanceKernel
    instance exposing ``evaluate(action, actor, context, evidence_refs)``.
    """

    def evaluate(
        self,
        action: GovernanceAction,
        actor: str,
        context: dict,
        evidence_refs: list,
    ) -> GovernanceDecision:
        return GovernanceDecision(
            action=action,
            actor=actor,
            allowed=True,
            decision="APPROVED",
            evidence_refs=list(evidence_refs),
        )


class FinancialHardeningEngine:
    """Coordinates all marketplace financial hardening subsystems."""

    def __init__(
        self,
        policy: Optional[MarketplaceFinancialPolicy] = None,
        governance=None,
        production_learning_certification_engine=None,
    ) -> None:
        self.policy = policy or MarketplaceFinancialPolicy()
        self.governance = governance or DefaultGovernanceAdapter()
        self.production_learning_certification_engine = (
            production_learning_certification_engine
        )

        self.ledger = FinancialLedgerEngine()

        self.payment_engine = PaymentAdapterEngine(
            ledger=self.ledger,
            policy=self.policy,
        )

        self.refund_engine = RefundGovernanceEngine(
            ledger=self.ledger,
            policy=self.policy,
            governance=self.governance,
        )

        self.tax_engine = TaxAdapterEngine(
            ledger=self.ledger,
        )

        self.fraud_engine = FraudControlEngine(
            policy=self.policy,
            governance=self.governance,
        )

        self.sla_engine = SLAMonitorEngine(policy=self.policy)

        self.reconciliation_engine = ReconciliationEngine(
            ledger=self.ledger,
            payment_engine=self.payment_engine,
            tax_engine=self.tax_engine,
            policy=self.policy,
            governance=self.governance,
        )

        self.compliance_engine = FinancialComplianceEngine(
            payment_engine=self.payment_engine,
            refund_engine=self.refund_engine,
            ledger=self.ledger,
            tax_engine=self.tax_engine,
            fraud_engine=self.fraud_engine,
            sla_engine=self.sla_engine,
            reconciliation_engine=self.reconciliation_engine,
            production_learning_certification_engine=(
                self.production_learning_certification_engine
            ),
            policy=self.policy,
            governance=self.governance,
        )

    # ------------------------------------------------------------------
    # Payment ingestion
    # ------------------------------------------------------------------

    def process_payment_webhook(
        self,
        envelope: PaymentWebhookEnvelope,
    ):
        event = self.payment_engine.ingest_webhook(envelope)

        self.sla_engine.record(
            SLADomain.PAYMENT_EVENT_INGESTION_SUCCESS_RATE,
            value=0.0 if event.status.value in ("FAILED", "CANCELLED") else 1.0,
            success=event.status.value not in ("FAILED", "CANCELLED"),
        )

        return event

    # ------------------------------------------------------------------
    # Refunds
    # ------------------------------------------------------------------

    def request_refund(self, **kwargs):
        return self.refund_engine.request_refund(**kwargs)

    def approve_refund(self, **kwargs):
        return self.refund_engine.approve_refund(**kwargs)

    def reject_refund(self, **kwargs):
        return self.refund_engine.reject_refund(**kwargs)

    # ------------------------------------------------------------------
    # Tax / fraud
    # ------------------------------------------------------------------

    def calculate_tax(self, request):
        return self.tax_engine.calculate_tax(request)

    def assess_fraud(self, **kwargs):
        return self.fraud_engine.assess(**kwargs)

    # ------------------------------------------------------------------
    # Reconciliation
    # ------------------------------------------------------------------

    def run_reconciliation(self, marketplace_id: Optional[str] = None):
        return self.reconciliation_engine.run_reconciliation(marketplace_id)

    def latest_reconciliation_report(self):
        return self.reconciliation_engine.latest_report()

    # ------------------------------------------------------------------
    # Compliance
    # ------------------------------------------------------------------

    def certify(
        self,
        certified_by: str = "system",
        evidence: Optional[MarketplaceFinancialReadinessEvidence] = None,
        prerequisite_26_8_report_id: Optional[str] = None,
    ):
        return self.compliance_engine.certify(
            marketplace_id=self.policy.marketplace_id,
            certified_by=certified_by,
            evidence=evidence,
            prerequisite_26_8_report_id=prerequisite_26_8_report_id,
        )

    def latest_certification_report(self):
        return self.compliance_engine.latest_report()

    def revoke_certification(self, report_id: str, reason: str, revoked_by: str = "system"):
        return self.compliance_engine.revoke(
            report_id=report_id,
            reason=reason,
            revoked_by=revoked_by,
        )

    # ------------------------------------------------------------------
    # SLA
    # ------------------------------------------------------------------

    def sla_report(self):
        return self.sla_engine.get_sla_report()
