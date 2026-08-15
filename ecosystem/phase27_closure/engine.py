"""
Phase 27 closure engine.
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
    Phase27Evidence,
    Phase27ClosureReport,
    utcnow,
)


class Phase27ClosurePolicy(BaseModel):
    """Policy controlling Phase 27 closure certification."""

    require_all_domains: bool = True

    require_ecosystem_core: bool = True
    require_federation_treaties: bool = True
    require_partner_identity_trust: bool = True
    require_cross_marketplace_routing: bool = True
    require_b2b_contract_sla: bool = True

    require_ecosystem_hardening: bool = True
    require_treaty_risk: bool = True
    require_partner_trust_hardening: bool = True
    require_guarded_routing: bool = True
    require_sla_enforcement: bool = True

    require_ecosystem_compliance: bool = True
    require_audit_bundle: bool = True
    require_observability: bool = True
    require_resilience: bool = True

    require_governance_integration: bool = True
    require_learning_certification: bool = True
    require_documentation: bool = True
    require_test_suite: bool = True

    require_human_signoff: bool = True

    allow_conditional_certification: bool = True

    certification_ttl_days: int = Field(default=180, ge=1)


class Phase27ClosureEngine:
    """Certifies Phase 27 closure."""

    def __init__(
        self,
        policy: Phase27ClosurePolicy | None = None,
    ) -> None:
        self.policy = policy or Phase27ClosurePolicy()
        self.reports: Dict[str, Phase27ClosureReport] = {}

    # ------------------------------------------------------------------
    # Certification
    # ------------------------------------------------------------------

    def certify(
        self,
        certified_by: str = "system",
        evidence: Phase27Evidence | None = None,
    ) -> Phase27ClosureReport:
        evidence = evidence or Phase27Evidence()

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
            reasons.append("Human sign-off is required to close Phase 27.")

        expires_at = utcnow() + timedelta(
            days=self.policy.certification_ttl_days
        )

        evidence_refs: List[str] = []

        evidence_refs.extend(evidence.ecosystem_core_refs)
        evidence_refs.extend(evidence.federation_treaty_refs)
        evidence_refs.extend(evidence.partner_identity_trust_refs)
        evidence_refs.extend(evidence.cross_marketplace_routing_refs)
        evidence_refs.extend(evidence.b2b_contract_sla_refs)

        evidence_refs.extend(evidence.ecosystem_hardening_refs)
        evidence_refs.extend(evidence.treaty_risk_refs)
        evidence_refs.extend(evidence.partner_trust_hardening_refs)
        evidence_refs.extend(evidence.guarded_routing_refs)
        evidence_refs.extend(evidence.sla_enforcement_refs)

        evidence_refs.extend(evidence.ecosystem_compliance_refs)
        evidence_refs.extend(evidence.audit_bundle_refs)
        evidence_refs.extend(evidence.observability_refs)
        evidence_refs.extend(evidence.resilience_refs)

        evidence_refs.extend(evidence.governance_integration_refs)
        evidence_refs.extend(evidence.learning_certification_refs)
        evidence_refs.extend(evidence.documentation_refs)
        evidence_refs.extend(evidence.test_suite_refs)

        report = Phase27ClosureReport(
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
    ) -> Phase27ClosureReport:
        report = self.reports.get(report_id)

        if not report:
            raise KeyError(f"Phase 27 closure report not found: {report_id}")

        report.status = ClosureStatus.REVOKED
        report.revoked_at = utcnow()
        report.revocation_reason = reason
        report.certified_by = revoked_by

        return report

    def latest_report(self) -> Phase27ClosureReport | None:
        if not self.reports:
            return None

        return list(self.reports.values())[-1]

    def report(self, report_id: str) -> Phase27ClosureReport:
        report = self.reports.get(report_id)

        if not report:
            raise KeyError(f"Phase 27 closure report not found: {report_id}")

        return report

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _domain_requirements(self, evidence: Phase27Evidence):
        return [
            (
                ClosureDomain.ECOSYSTEM_CORE,
                evidence.ecosystem_core_refs,
                self.policy.require_all_domains
                or self.policy.require_ecosystem_core,
                "Ecosystem core evidence missing.",
            ),
            (
                ClosureDomain.FEDERATION_TREATIES,
                evidence.federation_treaty_refs,
                self.policy.require_all_domains
                or self.policy.require_federation_treaties,
                "Federation treaty evidence missing.",
            ),
            (
                ClosureDomain.PARTNER_IDENTITY_TRUST,
                evidence.partner_identity_trust_refs,
                self.policy.require_all_domains
                or self.policy.require_partner_identity_trust,
                "Partner identity and trust evidence missing.",
            ),
            (
                ClosureDomain.CROSS_MARKETPLACE_ROUTING,
                evidence.cross_marketplace_routing_refs,
                self.policy.require_all_domains
                or self.policy.require_cross_marketplace_routing,
                "Cross-marketplace routing evidence missing.",
            ),
            (
                ClosureDomain.B2B_CONTRACT_SLA,
                evidence.b2b_contract_sla_refs,
                self.policy.require_all_domains
                or self.policy.require_b2b_contract_sla,
                "B2B contract and SLA evidence missing.",
            ),
            (
                ClosureDomain.ECOSYSTEM_HARDENING,
                evidence.ecosystem_hardening_refs,
                self.policy.require_all_domains
                or self.policy.require_ecosystem_hardening,
                "Ecosystem hardening evidence missing.",
            ),
            (
                ClosureDomain.TREATY_RISK,
                evidence.treaty_risk_refs,
                self.policy.require_all_domains
                or self.policy.require_treaty_risk,
                "Treaty risk assessment evidence missing.",
            ),
            (
                ClosureDomain.PARTNER_TRUST_HARDENING,
                evidence.partner_trust_hardening_refs,
                self.policy.require_all_domains
                or self.policy.require_partner_trust_hardening,
                "Partner trust hardening evidence missing.",
            ),
            (
                ClosureDomain.GUARDED_ROUTING,
                evidence.guarded_routing_refs,
                self.policy.require_all_domains
                or self.policy.require_guarded_routing,
                "Guarded routing evidence missing.",
            ),
            (
                ClosureDomain.SLA_ENFORCEMENT,
                evidence.sla_enforcement_refs,
                self.policy.require_all_domains
                or self.policy.require_sla_enforcement,
                "SLA enforcement evidence missing.",
            ),
            (
                ClosureDomain.ECOSYSTEM_COMPLIANCE,
                evidence.ecosystem_compliance_refs,
                self.policy.require_all_domains
                or self.policy.require_ecosystem_compliance,
                "Ecosystem compliance evidence missing.",
            ),
            (
                ClosureDomain.AUDIT_BUNDLE,
                evidence.audit_bundle_refs,
                self.policy.require_all_domains
                or self.policy.require_audit_bundle,
                "Audit bundle evidence missing.",
            ),
            (
                ClosureDomain.OBSERVABILITY,
                evidence.observability_refs,
                self.policy.require_all_domains
                or self.policy.require_observability,
                "Ecosystem observability evidence missing.",
            ),
            (
                ClosureDomain.RESILIENCE,
                evidence.resilience_refs,
                self.policy.require_all_domains
                or self.policy.require_resilience,
                "Ecosystem resilience evidence missing.",
            ),
            (
                ClosureDomain.GOVERNANCE_INTEGRATION,
                evidence.governance_integration_refs,
                self.policy.require_all_domains
                or self.policy.require_governance_integration,
                "Governance integration evidence missing.",
            ),
            (
                ClosureDomain.LEARNING_CERTIFICATION,
                evidence.learning_certification_refs,
                self.policy.require_all_domains
                or self.policy.require_learning_certification,
                "Learning certification evidence missing.",
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
