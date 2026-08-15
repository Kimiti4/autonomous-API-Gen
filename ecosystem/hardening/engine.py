"""
Ecosystem hardening engine.
"""

from __future__ import annotations

from typing import Dict, List

from ecosystem.models import RoutingRequest

from .models import (
    DependencyHealth,
    DependencyStatus,
    EcosystemAuditBundle,
    EcosystemComplianceEvidence,
    EcosystemComplianceReport,
    EcosystemHardeningPolicy,
    EcosystemObservabilityReport,
    EcosystemResilienceReport,
    GateStatus,
    PartnerTrustAssessment,
    RiskLevel,
    RoutingGuardrailDecision,
    SLAEnforcementReport,
    TreatyRiskAssessment,
    canonical_json,
    new_id,
    sha256_hex,
    utcnow,
)


class EcosystemHardeningEngine:
    """Hardens ecosystem federation, trust, routing, SLA, compliance, and resilience."""

    def __init__(
        self,
        ecosystem_engine,
        governance_gateway=None,
        policy: EcosystemHardeningPolicy | None = None,
    ) -> None:
        self.ecosystem = ecosystem_engine
        self.governance_gateway = governance_gateway
        self.policy = policy or EcosystemHardeningPolicy()

        self.compliance_reports: Dict[str, EcosystemComplianceReport] = {}

        self.dependency_failures: Dict[str, int] = {}
        self.dependency_status: Dict[str, DependencyStatus] = {}

    # ------------------------------------------------------------------
    # Treaty risk
    # ------------------------------------------------------------------

    def assess_treaty(self, treaty_id: str) -> TreatyRiskAssessment:
        treaty = self.ecosystem.federation.get_treaty(treaty_id)

        reasons: List[str] = []
        risk_level = RiskLevel.LOW
        requires_governance = False

        if treaty.status.value == "SUSPENDED":
            risk_level = RiskLevel.HIGH
            reasons.append("Treaty is suspended.")

        if self.ecosystem.federation._is_expired(treaty):
            risk_level = RiskLevel.HIGH
            reasons.append("Treaty is expired.")

        if treaty.revenue_share_pct > self.policy.max_revenue_share_pct:
            risk_level = RiskLevel.HIGH
            reasons.append(
                f"Revenue share {treaty.revenue_share_pct:.2f}% exceeds policy maximum "
                f"{self.policy.max_revenue_share_pct:.2f}%."
            )

        if self.policy.require_treaty_governance and not treaty.governance_ref:
            risk_level = RiskLevel.HIGH
            requires_governance = True
            reasons.append("Treaty has no governance reference.")

        if not treaty.routing_policy:
            if risk_level == RiskLevel.LOW:
                risk_level = RiskLevel.MEDIUM

            reasons.append("Treaty has no explicit routing policy.")

        return TreatyRiskAssessment(
            treaty_id=treaty_id,
            risk_level=risk_level,
            requires_governance=requires_governance,
            reasons=reasons,
        )

    # ------------------------------------------------------------------
    # Partner trust
    # ------------------------------------------------------------------

    def assess_partner(self, partner_id: str) -> PartnerTrustAssessment:
        partner = self.ecosystem.partners.get_partner(partner_id)

        reasons: List[str] = []
        risk_level = RiskLevel.LOW
        recommended_action = "ALLOW"

        evidence_count = len(partner.evidence_refs)

        if partner.status.value in {"SUSPENDED", "BANNED"}:
            risk_level = RiskLevel.HIGH
            recommended_action = "SUSPEND"
            reasons.append("Partner is suspended or banned.")

        if partner.trust_score < self.policy.min_partner_trust:
            risk_level = RiskLevel.HIGH
            recommended_action = "REVIEW"
            reasons.append(
                f"Partner trust score {partner.trust_score:.2f} is below threshold "
                f"{self.policy.min_partner_trust:.2f}."
            )

        if self.policy.require_partner_evidence and evidence_count == 0:
            risk_level = RiskLevel.HIGH
            recommended_action = "REVIEW"
            reasons.append("Partner has no evidence references.")

        if risk_level == RiskLevel.MEDIUM and recommended_action == "ALLOW":
            recommended_action = "REVIEW"

        return PartnerTrustAssessment(
            partner_id=partner_id,
            trust_score=partner.trust_score,
            evidence_count=evidence_count,
            status=partner.status.value,
            risk_level=risk_level,
            recommended_action=recommended_action,
            reasons=reasons,
        )

    # ------------------------------------------------------------------
    # Guarded routing
    # ------------------------------------------------------------------

    def guarded_routing(self, request: RoutingRequest) -> RoutingGuardrailDecision:
        reasons: List[str] = []

        active_treaties = self.ecosystem.federation.active_treaties_for(
            request.source_marketplace_id
        )

        if not active_treaties:
            return RoutingGuardrailDecision(
                allowed=False,
                reasons=["No active federation treaty found."],
            )

        if request.partner_id:
            partner_assessment = self.assess_partner(request.partner_id)

            if partner_assessment.risk_level == RiskLevel.HIGH:
                reasons.append("Partner trust assessment is high risk.")

            if partner_assessment.trust_score < self.policy.min_partner_trust:
                reasons.append("Partner trust score is below routing threshold.")

        try:
            base_decision = self.ecosystem.routing.evaluate(request)
        except ValueError as exc:
            return RoutingGuardrailDecision(
                allowed=False,
                reasons=[str(exc)],
            )

        selected_treaty = next(
            (
                treaty
                for treaty in active_treaties
                if treaty.target_marketplace_id == base_decision.selected_marketplace_id
            ),
            None,
        )

        if not selected_treaty:
            reasons.append("Selected marketplace has no active treaty.")
        else:
            treaty_assessment = self.assess_treaty(selected_treaty.id)

            if treaty_assessment.risk_level == RiskLevel.HIGH:
                reasons.append("Selected treaty is high risk.")

            if (
                treaty_assessment.risk_level == RiskLevel.MEDIUM
                and not self.policy.allow_degraded_routing
            ):
                reasons.append("Medium-risk treaty routing is not allowed by policy.")

        allowed = len(reasons) == 0

        return RoutingGuardrailDecision(
            allowed=allowed,
            reasons=reasons,
            base_decision=base_decision.model_dump(mode="json") if allowed else None,
        )

    # ------------------------------------------------------------------
    # SLA enforcement
    # ------------------------------------------------------------------

    def enforce_sla(
        self,
        contract_id: str,
        metric: str,
        value: float,
    ) -> SLAEnforcementReport:
        breach = self.ecosystem.contracts.ingest_metric(
            contract_id=contract_id,
            metric=metric,
            value=value,
        )

        breaches = self.ecosystem.contracts.breaches_for_contract(contract_id)

        total_breaches = len(breaches)

        escalated = total_breaches >= self.policy.max_sla_breaches_before_escalation

        recommended_action = "MONITOR"

        if escalated:
            recommended_action = "ESCALATE_TO_GOVERNANCE"

            if self.policy.auto_suspend_contract_on_sla_escalation:
                contract = self.ecosystem.contracts.get_contract(contract_id)
                contract.status = "SUSPENDED"

        return SLAEnforcementReport(
            contract_id=contract_id,
            metric=metric,
            value=value,
            breach_detected=breach is not None,
            total_breaches=total_breaches,
            escalated=escalated,
            recommended_action=recommended_action,
        )

    # ------------------------------------------------------------------
    # Compliance certification
    # ------------------------------------------------------------------

    def certify_ecosystem(
        self,
        evidence: EcosystemComplianceEvidence,
        certified_by: str = "system",
        scope: str = "ecosystem",
    ) -> EcosystemComplianceReport:
        gates: List[Dict[str, Any]] = []

        def add_gate(name: str, refs: List[str], required: bool, missing_reason: str):
            if required and not refs:
                gates.append(
                    {
                        "gate": name,
                        "status": GateStatus.FAIL.value,
                        "reason": missing_reason,
                        "evidence_refs": refs,
                    }
                )
            elif refs:
                gates.append(
                    {
                        "gate": name,
                        "status": GateStatus.PASS.value,
                        "reason": "Evidence present.",
                        "evidence_refs": refs,
                    }
                )
            else:
                gates.append(
                    {
                        "gate": name,
                        "status": GateStatus.PASS.value,
                        "reason": "Optional evidence not provided.",
                        "evidence_refs": refs,
                    }
                )

        add_gate(
            "governance",
            evidence.governance_refs,
            True,
            "Governance evidence is missing.",
        )

        add_gate(
            "treaty_risk",
            evidence.treaty_risk_refs,
            True,
            "Treaty risk evidence is missing.",
        )

        add_gate(
            "partner_trust",
            evidence.partner_trust_refs,
            True,
            "Partner trust evidence is missing.",
        )

        add_gate(
            "sla_enforcement",
            evidence.sla_refs,
            True,
            "SLA enforcement evidence is missing.",
        )

        add_gate(
            "financial_controls",
            evidence.financial_refs,
            True,
            "Financial control evidence is missing.",
        )

        add_gate(
            "security_controls",
            evidence.security_refs,
            True,
            "Security control evidence is missing.",
        )

        add_gate(
            "learning_certification",
            evidence.learning_refs,
            True,
            "Learning certification evidence is missing.",
        )

        add_gate(
            "audit_bundle",
            evidence.audit_refs,
            True,
            "Audit bundle evidence is missing.",
        )

        failures = [gate for gate in gates if gate["status"] == GateStatus.FAIL]

        reasons = [gate["reason"] for gate in failures]

        if failures:
            status = "NOT_CERTIFIED"
        else:
            status = "CERTIFIED"

        if (
            self.policy.require_human_compliance_certification
            and certified_by != "human"
            and status == "CERTIFIED"
        ):
            status = "CONDITIONALLY_CERTIFIED"
            reasons.append(
                "Human certification is required for ecosystem compliance."
            )

        evidence_refs: List[str] = []

        evidence_refs.extend(evidence.governance_refs)
        evidence_refs.extend(evidence.treaty_risk_refs)
        evidence_refs.extend(evidence.partner_trust_refs)
        evidence_refs.extend(evidence.sla_refs)
        evidence_refs.extend(evidence.financial_refs)
        evidence_refs.extend(evidence.security_refs)
        evidence_refs.extend(evidence.learning_refs)
        evidence_refs.extend(evidence.audit_refs)

        report = EcosystemComplianceReport(
            scope=scope,
            status=status,
            gates=gates,
            reasons=reasons,
            evidence_refs=evidence_refs,
            certified_by=certified_by,
        )

        self.compliance_reports[report.id] = report

        return report

    def revoke_compliance_report(
        self,
        report_id: str,
        reason: str,
        revoked_by: str = "system",
    ) -> EcosystemComplianceReport:
        report = self.compliance_reports.get(report_id)

        if not report:
            raise KeyError(f"Ecosystem compliance report not found: {report_id}")

        report.status = "REVOKED"
        report.revoked_at = utcnow()
        report.revocation_reason = reason
        report.certified_by = revoked_by

        return report

    # ------------------------------------------------------------------
    # Audit bundle
    # ------------------------------------------------------------------

    def build_audit_bundle(self, scope: str = "ecosystem") -> EcosystemAuditBundle:
        records: List[Dict[str, Any]] = []

        for treaty in self.ecosystem.federation.treaties.values():
            records.append(
                {
                    "record_type": "FEDERATION_TREATY",
                    "payload": treaty.model_dump(mode="json"),
                }
            )

        for partner in self.ecosystem.partners.partners.values():
            records.append(
                {
                    "record_type": "PARTNER_ORGANIZATION",
                    "payload": partner.model_dump(mode="json"),
                }
            )

        for contract in self.ecosystem.contracts.contracts.values():
            records.append(
                {
                    "record_type": "B2B_CONTRACT",
                    "payload": contract.model_dump(mode="json"),
                }
            )

        for contract_id, breaches in self.ecosystem.contracts.breaches.items():
            for breach in breaches:
                records.append(
                    {
                        "record_type": "SLA_BREACH",
                        "contract_id": contract_id,
                        "payload": breach.model_dump(mode="json"),
                    }
                )

        bundle_hash = sha256_hex(canonical_json(records))

        return EcosystemAuditBundle(
            scope=scope,
            records=records,
            bundle_hash=bundle_hash,
        )

    # ------------------------------------------------------------------
    # Observability
    # ------------------------------------------------------------------

    def observability_report(self) -> EcosystemObservabilityReport:
        active_treaties = len(
            [
                treaty
                for treaty in self.ecosystem.federation.treaties.values()
                if self.ecosystem.federation._is_active(treaty)
            ]
        )

        suspended_treaties = len(
            [
                treaty
                for treaty in self.ecosystem.federation.treaties.values()
                if treaty.status.value == "SUSPENDED"
            ]
        )

        active_partners = len(self.ecosystem.partners.active_partners())

        low_trust_partners = len(
            [
                partner
                for partner in self.ecosystem.partners.partners.values()
                if partner.status.value == "ACTIVE"
                and partner.trust_score < self.policy.min_partner_trust
            ]
        )

        active_contracts = len(
            [
                contract
                for contract in self.ecosystem.contracts.contracts.values()
                if contract.status.value == "ACTIVE"
            ]
        )

        sla_breaches = sum(
            len(breaches)
            for breaches in self.ecosystem.contracts.breaches.values()
        )

        alerts: List[str] = []

        if suspended_treaties > 0:
            alerts.append("One or more federation treaties are suspended.")

        if low_trust_partners > 0:
            alerts.append("One or more active partners are below trust threshold.")

        if sla_breaches > 0:
            alerts.append("SLA breaches detected.")

        return EcosystemObservabilityReport(
            active_treaties=active_treaties,
            suspended_treaties=suspended_treaties,
            active_partners=active_partners,
            low_trust_partners=low_trust_partners,
            active_contracts=active_contracts,
            sla_breaches=sla_breaches,
            alerts=alerts,
        )

    # ------------------------------------------------------------------
    # Resilience
    # ------------------------------------------------------------------

    def record_dependency_failure(self, dependency: str) -> DependencyHealth:
        failures = self.dependency_failures.get(dependency, 0) + 1

        self.dependency_failures[dependency] = failures

        if failures >= self.policy.circuit_failure_threshold:
            status = DependencyStatus.OPEN
        elif failures > 0:
            status = DependencyStatus.DEGRADED
        else:
            status = DependencyStatus.HEALTHY

        self.dependency_status[dependency] = status

        return DependencyHealth(
            dependency=dependency,
            status=status,
            failure_count=failures,
        )

    def record_dependency_success(self, dependency: str) -> DependencyHealth:
        self.dependency_failures[dependency] = 0
        self.dependency_status[dependency] = DependencyStatus.HEALTHY

        return DependencyHealth(
            dependency=dependency,
            status=DependencyStatus.HEALTHY,
            failure_count=0,
        )

    def resilience_report(self) -> EcosystemResilienceReport:
        dependencies = [
            DependencyHealth(
                dependency=dependency,
                status=self.dependency_status.get(
                    dependency,
                    DependencyStatus.HEALTHY,
                ),
                failure_count=self.dependency_failures.get(dependency, 0),
            )
            for dependency in self.dependency_failures.keys()
        ]

        return EcosystemResilienceReport(dependencies=dependencies)
