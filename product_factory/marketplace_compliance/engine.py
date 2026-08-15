"""
Marketplace compliance engine.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Dict, List

from pydantic import BaseModel, Field

from .models import (
    AuditBundle,
    ComplianceDomain,
    ComplianceGateResult,
    ComplianceReport,
    ComplianceStatus,
    GateStatus,
    MarketplaceComplianceEvidence,
    canonical_json,
    sha256_hex,
    utcnow,
)


class MarketplaceCompliancePolicy(BaseModel):
    """Policy controlling marketplace compliance certification."""

    require_financial_reconciliation: bool = True
    require_settlement_governance: bool = True
    require_refund_governance: bool = True
    require_tax_evidence: bool = True
    require_fraud_controls: bool = True
    require_sla_monitoring: bool = True
    require_audit_trail: bool = True
    require_marketplace_certification: bool = True
    require_learning_certification: bool = True
    require_security_controls: bool = True

    require_human_certification: bool = True

    allow_conditional_certification: bool = True

    certification_ttl_days: int = Field(default=90, ge=1)


class MarketplaceComplianceEngine:
    """Certifies marketplace compliance."""

    def __init__(
        self,
        policy: MarketplaceCompliancePolicy | None = None,
    ) -> None:
        self.policy = policy or MarketplaceCompliancePolicy()
        self.reports: Dict[str, ComplianceReport] = {}

    # ------------------------------------------------------------------
    # Certification
    # ------------------------------------------------------------------

    def certify(
        self,
        scope: str = "marketplace",
        certified_by: str = "system",
        evidence: MarketplaceComplianceEvidence | None = None,
    ) -> ComplianceReport:
        evidence = evidence or MarketplaceComplianceEvidence()

        gates: List[ComplianceGateResult] = []

        gates.append(
            self._evidence_gate(
                domain=ComplianceDomain.FINANCIAL_RECONCILIATION,
                refs=evidence.financial_reconciliation_refs,
                required=self.policy.require_financial_reconciliation,
                missing_reason="Financial reconciliation evidence is missing.",
            )
        )

        gates.append(
            self._evidence_gate(
                domain=ComplianceDomain.SETTLEMENT_GOVERNANCE,
                refs=evidence.settlement_governance_refs,
                required=self.policy.require_settlement_governance,
                missing_reason="Settlement governance evidence is missing.",
            )
        )

        gates.append(
            self._evidence_gate(
                domain=ComplianceDomain.REFUND_GOVERNANCE,
                refs=evidence.refund_governance_refs,
                required=self.policy.require_refund_governance,
                missing_reason="Refund governance evidence is missing.",
            )
        )

        gates.append(
            self._evidence_gate(
                domain=ComplianceDomain.TAX_EVIDENCE,
                refs=evidence.tax_evidence_refs,
                required=self.policy.require_tax_evidence,
                missing_reason="Tax evidence is missing.",
            )
        )

        gates.append(
            self._evidence_gate(
                domain=ComplianceDomain.FRAUD_CONTROLS,
                refs=evidence.fraud_controls_refs,
                required=self.policy.require_fraud_controls,
                missing_reason="Fraud control evidence is missing.",
            )
        )

        gates.append(
            self._evidence_gate(
                domain=ComplianceDomain.SLA_MONITORING,
                refs=evidence.sla_monitoring_refs,
                required=self.policy.require_sla_monitoring,
                missing_reason="SLA monitoring evidence is missing.",
            )
        )

        gates.append(
            self._evidence_gate(
                domain=ComplianceDomain.AUDIT_TRAIL,
                refs=evidence.audit_trail_refs,
                required=self.policy.require_audit_trail,
                missing_reason="Audit trail evidence is missing.",
            )
        )

        gates.append(
            self._evidence_gate(
                domain=ComplianceDomain.MARKETPLACE_CERTIFICATION,
                refs=evidence.marketplace_certification_refs,
                required=self.policy.require_marketplace_certification,
                missing_reason="Marketplace certification evidence is missing.",
            )
        )

        gates.append(
            self._evidence_gate(
                domain=ComplianceDomain.LEARNING_CERTIFICATION,
                refs=evidence.learning_certification_refs,
                required=self.policy.require_learning_certification,
                missing_reason="Learning certification evidence is missing.",
            )
        )

        gates.append(
            self._evidence_gate(
                domain=ComplianceDomain.SECURITY_CONTROLS,
                refs=evidence.security_controls_refs,
                required=self.policy.require_security_controls,
                missing_reason="Security control evidence is missing.",
            )
        )

        failures = [gate for gate in gates if gate.status == GateStatus.FAIL]
        warnings = [gate for gate in gates if gate.status == GateStatus.WARNING]

        reasons: List[str] = []

        if failures:
            status = ComplianceStatus.NOT_CERTIFIED
            reasons.extend([gate.reason for gate in failures if gate.reason])
        elif warnings and self.policy.allow_conditional_certification:
            status = ComplianceStatus.CONDITIONALLY_CERTIFIED
            reasons.extend([gate.reason for gate in warnings if gate.reason])
        else:
            status = ComplianceStatus.CERTIFIED

        if (
            self.policy.require_human_certification
            and certified_by != "human"
            and status == ComplianceStatus.CERTIFIED
        ):
            status = ComplianceStatus.CONDITIONALLY_CERTIFIED
            reasons.append(
                "Human certification is required for marketplace compliance."
            )

        expires_at = utcnow() + timedelta(
            days=self.policy.certification_ttl_days
        )

        evidence_refs: List[str] = []

        evidence_refs.extend(evidence.financial_reconciliation_refs)
        evidence_refs.extend(evidence.settlement_governance_refs)
        evidence_refs.extend(evidence.refund_governance_refs)
        evidence_refs.extend(evidence.tax_evidence_refs)
        evidence_refs.extend(evidence.fraud_controls_refs)
        evidence_refs.extend(evidence.sla_monitoring_refs)
        evidence_refs.extend(evidence.audit_trail_refs)
        evidence_refs.extend(evidence.marketplace_certification_refs)
        evidence_refs.extend(evidence.learning_certification_refs)
        evidence_refs.extend(evidence.security_controls_refs)

        report = ComplianceReport(
            scope=scope,
            status=status,
            gates=gates,
            reasons=reasons,
            evidence_refs=evidence_refs,
            certified_by=certified_by,
            expires_at=expires_at,
        )

        self.reports[report.id] = report

        return report

    def revoke(
        self,
        report_id: str,
        reason: str,
        revoked_by: str = "system",
    ) -> ComplianceReport:
        report = self.reports.get(report_id)

        if not report:
            raise KeyError(f"Compliance report not found: {report_id}")

        report.status = ComplianceStatus.REVOKED
        report.revoked_at = utcnow()
        report.revocation_reason = reason
        report.certified_by = revoked_by

        return report

    def latest_report(self) -> ComplianceReport | None:
        if not self.reports:
            return None

        return list(self.reports.values())[-1]

    def report(self, report_id: str) -> ComplianceReport:
        report = self.reports.get(report_id)

        if not report:
            raise KeyError(f"Compliance report not found: {report_id}")

        return report

    # ------------------------------------------------------------------
    # Audit bundle
    # ------------------------------------------------------------------

    def build_audit_bundle(
        self,
        records: List[Dict[str, object]],
        scope: str = "marketplace",
    ) -> AuditBundle:
        bundle_hash = sha256_hex(canonical_json(records))

        return AuditBundle(
            scope=scope,
            records=records,
            bundle_hash=bundle_hash,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _evidence_gate(
        self,
        domain: ComplianceDomain,
        refs: List[str],
        required: bool,
        missing_reason: str,
    ) -> ComplianceGateResult:
        if required and not refs:
            return ComplianceGateResult(
                domain=domain,
                status=GateStatus.FAIL,
                reason=missing_reason,
                evidence_refs=refs,
            )

        if refs:
            return ComplianceGateResult(
                domain=domain,
                status=GateStatus.PASS,
                reason="Evidence present.",
                evidence_refs=refs,
            )

        return ComplianceGateResult(
            domain=domain,
            status=GateStatus.PASS,
            reason="Optional evidence not provided.",
            evidence_refs=refs,
        )
