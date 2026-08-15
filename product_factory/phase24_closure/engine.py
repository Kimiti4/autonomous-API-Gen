"""
Phase 24 closure engine.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Dict, List

from pydantic import BaseModel, Field

from .models import (
    ClosureDomain,
    ClosureGateResult,
    ClosureStatus,
    GateStatus,
    Phase24Evidence,
    Phase24ClosureReport,
    utcnow,
)


class Phase24ClosurePolicy(BaseModel):
    """Policy controlling Phase 24 closure certification."""

    require_all_domains: bool = True

    require_product_factory_core: bool = True
    require_monetization_ops: bool = True
    require_marketplace_foundation: bool = True
    require_product_certification_publishing: bool = True
    require_marketplace_design_economics: bool = True
    require_financial_hardening: bool = True
    require_reconciliation_settlement: bool = True
    require_marketplace_compliance: bool = True
    require_learning_certification: bool = True
    require_governance_integration: bool = True
    require_observability: bool = True
    require_documentation: bool = True
    require_test_suite: bool = True

    require_human_signoff: bool = True

    allow_conditional_certification: bool = True

    certification_ttl_days: int = Field(default=180, ge=1)


class Phase24ClosureEngine:
    """Certifies Phase 24 closure."""

    def __init__(
        self,
        policy: Phase24ClosurePolicy | None = None,
    ) -> None:
        self.policy = policy or Phase24ClosurePolicy()
        self.reports: Dict[str, Phase24ClosureReport] = {}

    # ------------------------------------------------------------------
    # Certification
    # ------------------------------------------------------------------

    def certify(
        self,
        certified_by: str = "system",
        evidence: Phase24Evidence | None = None,
    ) -> Phase24ClosureReport:
        evidence = evidence or Phase24Evidence()

        gates: List[ClosureGateResult] = []

        for domain, refs, required, message in self._domain_requirements(evidence):
            gates.append(
                self._evidence_gate(
                    domain=domain,
                    refs=refs,
                    required=required,
                    missing_reason=message,
                )
            )

        failures = [gate for gate in gates if gate.status == GateStatus.FAIL]
        warnings = [gate for gate in gates if gate.status == GateStatus.WARNING]

        reasons: List[str] = []

        if failures:
            status = ClosureStatus.NOT_CERTIFIED
            reasons.extend([gate.reason for gate in failures if gate.reason])
        elif warnings and self.policy.allow_conditional_certification:
            status = ClosureStatus.CONDITIONALLY_CERTIFIED
            reasons.extend([gate.reason for gate in warnings if gate.reason])
        else:
            status = ClosureStatus.CERTIFIED

        if (
            self.policy.require_human_signoff
            and certified_by != "human"
            and status == ClosureStatus.CERTIFIED
        ):
            status = ClosureStatus.CONDITIONALLY_CERTIFIED
            reasons.append("Human sign-off is required to close Phase 24.")

        expires_at = utcnow() + timedelta(
            days=self.policy.certification_ttl_days
        )

        evidence_refs: List[str] = []

        evidence_refs.extend(evidence.product_factory_core_refs)
        evidence_refs.extend(evidence.monetization_ops_refs)
        evidence_refs.extend(evidence.marketplace_foundation_refs)
        evidence_refs.extend(evidence.product_certification_publishing_refs)
        evidence_refs.extend(evidence.marketplace_design_economics_refs)
        evidence_refs.extend(evidence.financial_hardening_refs)
        evidence_refs.extend(evidence.reconciliation_settlement_refs)
        evidence_refs.extend(evidence.marketplace_compliance_refs)
        evidence_refs.extend(evidence.learning_certification_refs)
        evidence_refs.extend(evidence.governance_integration_refs)
        evidence_refs.extend(evidence.observability_refs)
        evidence_refs.extend(evidence.documentation_refs)
        evidence_refs.extend(evidence.test_suite_refs)

        report = Phase24ClosureReport(
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
    ) -> Phase24ClosureReport:
        report = self.reports.get(report_id)

        if not report:
            raise KeyError(f"Phase 24 closure report not found: {report_id}")

        report.status = ClosureStatus.REVOKED
        report.revoked_at = utcnow()
        report.revocation_reason = reason
        report.certified_by = revoked_by

        return report

    def latest_report(self) -> Phase24ClosureReport | None:
        if not self.reports:
            return None

        return list(self.reports.values())[-1]

    def report(self, report_id: str) -> Phase24ClosureReport:
        report = self.reports.get(report_id)

        if not report:
            raise KeyError(f"Phase 24 closure report not found: {report_id}")

        return report

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _domain_requirements(self, evidence: Phase24Evidence):
        return [
            (
                ClosureDomain.PRODUCT_FACTORY_CORE,
                evidence.product_factory_core_refs,
                self.policy.require_all_domains
                or self.policy.require_product_factory_core,
                "Product factory core evidence missing.",
            ),
            (
                ClosureDomain.MONETIZATION_OPS,
                evidence.monetization_ops_refs,
                self.policy.require_all_domains
                or self.policy.require_monetization_ops,
                "Monetization operations evidence missing.",
            ),
            (
                ClosureDomain.MARKETPLACE_FOUNDATION,
                evidence.marketplace_foundation_refs,
                self.policy.require_all_domains
                or self.policy.require_marketplace_foundation,
                "Marketplace foundation evidence missing.",
            ),
            (
                ClosureDomain.PRODUCT_CERTIFICATION_PUBLISHING,
                evidence.product_certification_publishing_refs,
                self.policy.require_all_domains
                or self.policy.require_product_certification_publishing,
                "Product certification and publishing evidence missing.",
            ),
            (
                ClosureDomain.MARKETPLACE_DESIGN_ECONOMICS,
                evidence.marketplace_design_economics_refs,
                self.policy.require_all_domains
                or self.policy.require_marketplace_design_economics,
                "Marketplace design and economics evidence missing.",
            ),
            (
                ClosureDomain.FINANCIAL_HARDENING,
                evidence.financial_hardening_refs,
                self.policy.require_all_domains
                or self.policy.require_financial_hardening,
                "Financial hardening evidence missing.",
            ),
            (
                ClosureDomain.RECONCILIATION_SETTLEMENT,
                evidence.reconciliation_settlement_refs,
                self.policy.require_all_domains
                or self.policy.require_reconciliation_settlement,
                "Reconciliation and settlement evidence missing.",
            ),
            (
                ClosureDomain.MARKETPLACE_COMPLIANCE,
                evidence.marketplace_compliance_refs,
                self.policy.require_all_domains
                or self.policy.require_marketplace_compliance,
                "Marketplace compliance evidence missing.",
            ),
            (
                ClosureDomain.LEARNING_CERTIFICATION,
                evidence.learning_certification_refs,
                self.policy.require_all_domains
                or self.policy.require_learning_certification,
                "Learning certification evidence missing.",
            ),
            (
                ClosureDomain.GOVERNANCE_INTEGRATION,
                evidence.governance_integration_refs,
                self.policy.require_all_domains
                or self.policy.require_governance_integration,
                "Governance integration evidence missing.",
            ),
            (
                ClosureDomain.OBSERVABILITY,
                evidence.observability_refs,
                self.policy.require_all_domains
                or self.policy.require_observability,
                "Observability evidence missing.",
            ),
            (
                ClosureDomain.DOCUMENTATION,
                evidence.documentation_refs,
                self.policy.require_all_domains
                or self.policy.require_documentation,
                "Documentation evidence missing.",
            ),
            (
                ClosureDomain.TEST_SUITE,
                evidence.test_suite_refs,
                self.policy.require_all_domains
                or self.policy.require_test_suite,
                "Test suite evidence missing.",
            ),
        ]

    def _evidence_gate(
        self,
        domain: ClosureDomain,
        refs: List[str],
        required: bool,
        missing_reason: str,
    ) -> ClosureGateResult:
        if required and not refs:
            return ClosureGateResult(
                domain=domain,
                status=GateStatus.FAIL,
                reason=missing_reason,
                evidence_refs=refs,
            )

        if refs:
            return ClosureGateResult(
                domain=domain,
                status=GateStatus.PASS,
                reason="Evidence present.",
                evidence_refs=refs,
            )

        return ClosureGateResult(
            domain=domain,
            status=GateStatus.PASS,
            reason="Optional evidence not provided.",
            evidence_refs=refs,
        )
