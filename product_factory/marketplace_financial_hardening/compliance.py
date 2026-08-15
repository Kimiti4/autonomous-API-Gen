"""
Financial compliance certification engine.

Evaluates multi-gate certification that marketplace financial operations are
production-ready, enforcing the Phase 26.8 production learning certification
prerequisite, human certification, and expiry/revocation.
"""

from __future__ import annotations

from datetime import timedelta
from typing import List, Optional

from .models import (
    FinancialComplianceGate,
    FinancialComplianceReport,
    MarketplaceFinancialPolicy,
    MarketplaceFinancialReadinessEvidence,
    utcnow,
)


class FinancialComplianceEngine:
    """Certifies marketplace financial production readiness."""

    def __init__(
        self,
        payment_engine=None,
        refund_engine=None,
        ledger=None,
        tax_engine=None,
        fraud_engine=None,
        sla_engine=None,
        reconciliation_engine=None,
        production_learning_certification_engine=None,
        policy: Optional[MarketplaceFinancialPolicy] = None,
        governance=None,
    ) -> None:
        self.payment_engine = payment_engine
        self.refund_engine = refund_engine
        self.ledger = ledger
        self.tax_engine = tax_engine
        self.fraud_engine = fraud_engine
        self.sla_engine = sla_engine
        self.reconciliation_engine = reconciliation_engine
        self.production_learning_certification_engine = (
            production_learning_certification_engine
        )
        self.policy = policy or MarketplaceFinancialPolicy()
        self.governance = governance

        self.reports: dict = {}

    def certify(
        self,
        marketplace_id: str,
        certified_by: str = "system",
        evidence: Optional[MarketplaceFinancialReadinessEvidence] = None,
        prerequisite_26_8_report_id: Optional[str] = None,
    ) -> FinancialComplianceReport:
        gates: List[FinancialComplianceGate] = []

        gates.append(self._gate_payment_adapter_health())
        gates.append(self._gate_refund_governance_evidence())
        gates.append(self._gate_ledger_integrity())
        gates.append(self._gate_reconciliation_health())
        gates.append(self._gate_tax_adapter_evidence())
        gates.append(self._gate_fraud_control_evidence())
        gates.append(self._gate_sla_monitoring_evidence())
        gates.append(self._gate_audit_trail_integrity())
        gates.append(self._gate_governance_policy_evidence())
        gates.append(
            self._gate_production_learning_certification(
                prerequisite_26_8_report_id
            )
        )

        failures = [
            g
            for g in gates
            if not g.passed and g.severity in ("HIGH", "CRITICAL")
        ]
        warnings = [
            g
            for g in gates
            if not g.passed and g.severity in ("MEDIUM", "INFO")
        ]

        reasons: List[str] = []

        if failures:
            status = "NOT_CERTIFIED"
            reasons.extend([g.reason for g in failures if g.reason])
        elif warnings and self.policy.allow_conditional_financial_certification:
            status = "CONDITIONALLY_CERTIFIED"
            reasons.extend([g.reason for g in warnings if g.reason])
        else:
            status = "CERTIFIED"

        if (
            self.policy.require_human_financial_certification
            and certified_by != "human"
            and status == "CERTIFIED"
        ):
            status = "CONDITIONALLY_CERTIFIED"
            reasons.append(
                "Human certification is required for financial certification."
            )

        expires_at = utcnow() + timedelta(
            days=self.policy.financial_certification_ttl_days
        )

        evidence_refs: List[str] = []

        if evidence:
            evidence_refs.extend(evidence.slo_definitions)
            evidence_refs.extend(evidence.runbooks)
            evidence_refs.extend(evidence.incident_response_plans)
            evidence_refs.extend(evidence.backup_restore_evidence)
            evidence_refs.extend(evidence.observability_evidence)
            evidence_refs.extend(evidence.dashboard_refs)
            evidence_refs.extend(evidence.marketplace_metrics_refs)
            evidence_refs.extend(evidence.payment_adapter_evidence)
            evidence_refs.extend(evidence.fraud_evidence)
            evidence_refs.extend(evidence.tax_evidence)
            evidence_refs.extend(evidence.audit_evidence)

        report = FinancialComplianceReport(
            marketplace_id=marketplace_id,
            status=status,
            gates=gates,
            reasons=reasons,
            evidence_refs=evidence_refs,
            prerequisite_26_8_report_id=prerequisite_26_8_report_id,
            certified_by=certified_by,
            expires_at=expires_at,
        )

        self.reports[report.report_id] = report

        return report

    def revoke(
        self,
        report_id: str,
        reason: str,
        revoked_by: str = "system",
    ) -> FinancialComplianceReport:
        report = self.reports.get(report_id)

        if not report:
            raise KeyError(
                f"Financial compliance report not found: {report_id}"
            )

        report.status = "REVOKED"
        report.revoked_at = utcnow()
        report.revocation_reason = reason
        report.certified_by = revoked_by

        return report

    def latest_report(self) -> Optional[FinancialComplianceReport]:
        if not self.reports:
            return None

        return list(self.reports.values())[-1]

    def report(self, report_id: str) -> FinancialComplianceReport:
        report = self.reports.get(report_id)

        if not report:
            raise KeyError(
                f"Financial compliance report not found: {report_id}"
            )

        return report

    # ------------------------------------------------------------------
    # Certification gates
    # ------------------------------------------------------------------

    def _gate_payment_adapter_health(self) -> FinancialComplianceGate:
        if self.payment_engine and hasattr(
            self.payment_engine, "ingest_webhook"
        ):
            return FinancialComplianceGate(
                name="payment_adapter_health",
                passed=True,
                reason="Payment adapter engine is present.",
            )

        return FinancialComplianceGate(
            name="payment_adapter_health",
            passed=False,
            severity="HIGH",
            reason="Payment adapter engine is missing.",
        )

    def _gate_refund_governance_evidence(self) -> FinancialComplianceGate:
        if self.refund_engine:
            return FinancialComplianceGate(
                name="refund_governance_evidence",
                passed=True,
                reason="Refund governance engine is present.",
            )

        return FinancialComplianceGate(
            name="refund_governance_evidence",
            passed=False,
            severity="HIGH",
            reason="Refund governance engine is missing.",
        )

    def _gate_ledger_integrity(self) -> FinancialComplianceGate:
        if not self.ledger:
            return FinancialComplianceGate(
                name="ledger_integrity",
                passed=False,
                severity="HIGH",
                reason="Financial ledger is missing.",
            )

        duplicates = self.ledger.duplicate_idempotency_keys()

        if duplicates:
            return FinancialComplianceGate(
                name="ledger_integrity",
                passed=False,
                severity="HIGH",
                reason=(
                    "Ledger contains duplicate idempotency keys: "
                    + ", ".join(duplicates)
                ),
            )

        return FinancialComplianceGate(
            name="ledger_integrity",
            passed=True,
            reason="Ledger idempotency integrity verified.",
        )

    def _gate_reconciliation_health(self) -> FinancialComplianceGate:
        if not self.reconciliation_engine:
            return FinancialComplianceGate(
                name="reconciliation_health",
                passed=False,
                severity="MEDIUM",
                reason="Reconciliation engine is not configured.",
            )

        report = self.reconciliation_engine.latest_report()

        if report is None:
            return FinancialComplianceGate(
                name="reconciliation_health",
                passed=False,
                severity="MEDIUM",
                reason="No reconciliation has been run.",
            )

        if report.status.value == "HEALTHY":
            return FinancialComplianceGate(
                name="reconciliation_health",
                passed=True,
                reason="Latest reconciliation is healthy.",
                evidence_refs=[report.report_id],
            )

        severe = any(
            m.severity in ("HIGH", "CRITICAL") for m in report.mismatches
        )

        if severe or report.status.value == "FAILED":
            return FinancialComplianceGate(
                name="reconciliation_health",
                passed=False,
                severity="HIGH",
                reason="Reconciliation detected severe mismatches.",
                evidence_refs=[report.report_id],
            )

        return FinancialComplianceGate(
            name="reconciliation_health",
            passed=False,
            severity="MEDIUM",
            reason="Reconciliation has minor mismatches.",
            evidence_refs=[report.report_id],
        )

    def _gate_tax_adapter_evidence(self) -> FinancialComplianceGate:
        if self.tax_engine:
            return FinancialComplianceGate(
                name="tax_adapter_evidence",
                passed=True,
                reason="Tax adapter engine is present.",
            )

        return FinancialComplianceGate(
            name="tax_adapter_evidence",
            passed=False,
            severity="MEDIUM",
            reason="Tax adapter engine is not configured.",
        )

    def _gate_fraud_control_evidence(self) -> FinancialComplianceGate:
        if self.fraud_engine:
            return FinancialComplianceGate(
                name="fraud_control_evidence",
                passed=True,
                reason="Fraud control engine is present.",
            )

        return FinancialComplianceGate(
            name="fraud_control_evidence",
            passed=False,
            severity="HIGH",
            reason="Fraud control engine is missing.",
        )

    def _gate_sla_monitoring_evidence(self) -> FinancialComplianceGate:
        if self.sla_engine:
            return FinancialComplianceGate(
                name="sla_monitoring_evidence",
                passed=True,
                reason="SLA monitoring engine is present.",
            )

        return FinancialComplianceGate(
            name="sla_monitoring_evidence",
            passed=False,
            severity="MEDIUM",
            reason="SLA monitoring engine is not configured.",
        )

    def _gate_audit_trail_integrity(self) -> FinancialComplianceGate:
        if not self.ledger:
            return FinancialComplianceGate(
                name="audit_trail_integrity",
                passed=False,
                severity="MEDIUM",
                reason="Ledger is not configured; no audit trail available.",
            )

        if self.ledger.audit_events:
            return FinancialComplianceGate(
                name="audit_trail_integrity",
                passed=True,
                reason="Financial audit trail is present.",
                evidence_refs=[str(len(self.ledger.audit_events))],
            )

        return FinancialComplianceGate(
            name="audit_trail_integrity",
            passed=False,
            severity="MEDIUM",
            reason="Financial audit trail is empty.",
        )

    def _gate_governance_policy_evidence(self) -> FinancialComplianceGate:
        if self.governance is not None:
            return FinancialComplianceGate(
                name="governance_policy_evidence",
                passed=True,
                reason="Governance controls are configured.",
            )

        return FinancialComplianceGate(
            name="governance_policy_evidence",
            passed=False,
            severity="HIGH",
            reason="Governance controls are not configured.",
        )

    def _gate_production_learning_certification(
        self,
        prerequisite_26_8_report_id: Optional[str],
    ) -> FinancialComplianceGate:
        from .models import utcnow

        engine = self.production_learning_certification_engine

        if not engine:
            return FinancialComplianceGate(
                name="production_learning_certification",
                passed=False,
                severity="MEDIUM",
                reason="Phase 26.8 production learning certification engine is not wired.",
            )

        report = getattr(engine, "latest_report", lambda: None)()

        if not report:
            return FinancialComplianceGate(
                name="production_learning_certification",
                passed=False,
                severity="MEDIUM",
                reason="No Phase 26.8 production learning certification report found.",
            )

        if getattr(report, "revoked_at", None):
            return FinancialComplianceGate(
                name="production_learning_certification",
                passed=False,
                severity="HIGH",
                reason="Phase 26.8 certification has been revoked.",
            )

        expires_at = getattr(report, "expires_at", None)

        if expires_at and expires_at < utcnow():
            return FinancialComplianceGate(
                name="production_learning_certification",
                passed=False,
                severity="HIGH",
                reason="Phase 26.8 certification has expired.",
            )

        status_value = getattr(
            getattr(report, "status", None), "value", str(getattr(report, "status", None))
        )

        if status_value in ("CERTIFIED", "CONDITIONALLY_CERTIFIED"):
            return FinancialComplianceGate(
                name="production_learning_certification",
                passed=True,
                reason="Phase 26.8 production learning certification is valid.",
                evidence_refs=[getattr(report, "id", "unknown")],
            )

        return FinancialComplianceGate(
            name="production_learning_certification",
            passed=False,
            severity="HIGH",
            reason="Phase 26.8 production learning certification is not valid.",
        )
