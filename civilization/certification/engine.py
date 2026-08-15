"""
Production certification engine.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Callable, Dict, List, Optional

from ..utils import deterministic_id, utcnow
from .models import (
    CertificationDomain,
    CertificationEvidence,
    CertificationPolicy,
    CertificationStatus,
    DomainAssessment,
    EvidenceSeverity,
    ManualEvidencePayload,
    ProductionCertificationReport,
)


DOMAIN_REQUIREMENTS: Dict[CertificationDomain, List[str]] = {
    CertificationDomain.ORGANIZATION_GOVERNANCE: [
        "organization_registry",
        "task_lifecycle",
        "organizational_memory",
        "communication_bus",
    ],
    CertificationDomain.FEDERATION_GOVERNANCE: [
        "federation_registry",
        "initiative_delegation",
        "council_decisions",
        "cross_org_conflicts",
    ],
    CertificationDomain.REPUTATION_CERTIFICATION: [
        "reputation_events",
        "trust_scoring",
        "capability_certifications",
    ],
    CertificationDomain.OVERSIGHT_CONTROLS: [
        "oversight_requests",
        "kill_switch",
        "autonomy_controls",
        "human_approval_workflow",
    ],
    CertificationDomain.PERMISSIONED_AUTONOMY: [
        "action_catalog",
        "active_permission_policy",
        "delegation_controls",
        "policy_evaluation",
    ],
    CertificationDomain.MEMORY_KNOWLEDGE_SYNC: [
        "memory_records",
        "consolidation_pipeline",
        "knowledge_graph_gateway",
        "retention_controls",
    ],
    CertificationDomain.OPERATIONAL_RESILIENCE: [
        "circuit_breakers",
        "degradation_modes",
        "retry_budgets",
        "chaos_drills",
        "quorum_controls",
    ],
    CertificationDomain.SECURITY_PRIVACY_AUDIT: [
        "authorization_controls",
        "secret_redaction",
        "audit_chain",
        "security_alerts",
    ],
    CertificationDomain.OBSERVABILITY: [
        "structured_events",
        "metrics_report",
        "health_checks",
        "audit_visibility",
    ],
    CertificationDomain.DOCUMENTATION_ADRS: [
        "architecture_decision_records",
        "subsystem_documentation",
        "extension_documentation",
        "operational_runbooks",
    ],
    CertificationDomain.TESTING_VERIFICATION: [
        "unit_tests",
        "integration_tests",
        "security_tests",
        "resilience_tests",
        "governance_tests",
    ],
    CertificationDomain.PRODUCTION_OPERATIONS: [
        "slo_definitions",
        "backup_restore",
        "incident_response",
        "oncall_process",
        "deployment_controls",
    ],
}


CollectorFunction = Callable[[Dict, Dict], List[CertificationEvidence]]


class CertificationError(Exception):
    """Base error for certification operations."""


def _evidence(
    domain: CertificationDomain,
    requirement: str,
    satisfied: bool,
    severity: EvidenceSeverity,
    source: str,
    details: str = "",
    override_allowed: bool = True,
) -> CertificationEvidence:
    return CertificationEvidence(
        domain=domain,
        requirement=requirement,
        satisfied=satisfied,
        severity=severity,
        source=source,
        details=details,
        override_allowed=override_allowed,
        collected_at=utcnow().isoformat(),
    )


def _ok(
    domain: CertificationDomain,
    requirement: str,
    source: str,
    details: str = "",
) -> CertificationEvidence:
    return _evidence(
        domain=domain,
        requirement=requirement,
        satisfied=True,
        severity=EvidenceSeverity.INFO,
        source=source,
        details=details,
    )


def _blocking(
    domain: CertificationDomain,
    requirement: str,
    source: str,
    details: str = "",
    override_allowed: bool = False,
) -> CertificationEvidence:
    return _evidence(
        domain=domain,
        requirement=requirement,
        satisfied=False,
        severity=EvidenceSeverity.BLOCKING,
        source=source,
        details=details,
        override_allowed=override_allowed,
    )


def _warning(
    domain: CertificationDomain,
    requirement: str,
    source: str,
    details: str = "",
) -> CertificationEvidence:
    return _evidence(
        domain=domain,
        requirement=requirement,
        satisfied=False,
        severity=EvidenceSeverity.WARNING,
        source=source,
        details=details,
        override_allowed=True,
    )


def _missing_all(
    domain: CertificationDomain,
    source: str,
    reason: str,
    override_allowed: bool = False,
) -> List[CertificationEvidence]:
    return [
        _blocking(domain, requirement, source, reason, override_allowed)
        for requirement in DOMAIN_REQUIREMENTS[domain]
    ]


# ----------------------------------------------------------------------
# Default evidence collectors
# ----------------------------------------------------------------------


def collect_organization_governance(
    engines: Dict,
    context: Dict,
) -> List[CertificationEvidence]:
    domain = CertificationDomain.ORGANIZATION_GOVERNANCE
    source = "civilization_engine"

    civilization = engines.get("civilization")

    if not civilization:
        return _missing_all(domain, source, "Civilization engine is missing.")

    evidence: List[CertificationEvidence] = []

    if hasattr(civilization, "organizations"):
        evidence.append(
            _ok(domain, "organization_registry", source)
        )
    else:
        evidence.append(
            _blocking(domain, "organization_registry", source)
        )

    if hasattr(civilization, "tasks") and hasattr(civilization, "create_task"):
        evidence.append(
            _ok(domain, "task_lifecycle", source)
        )
    else:
        evidence.append(
            _blocking(domain, "task_lifecycle", source)
        )

    if hasattr(civilization, "memory"):
        evidence.append(
            _ok(domain, "organizational_memory", source)
        )
    else:
        evidence.append(
            _blocking(domain, "organizational_memory", source)
        )

    if hasattr(civilization, "bus"):
        evidence.append(
            _ok(domain, "communication_bus", source)
        )
    else:
        evidence.append(
            _blocking(domain, "communication_bus", source)
        )

    return evidence


def collect_federation_governance(
    engines: Dict,
    context: Dict,
) -> List[CertificationEvidence]:
    domain = CertificationDomain.FEDERATION_GOVERNANCE
    source = "federation_engine"

    federation = engines.get("federation")

    if not federation:
        return _missing_all(domain, source, "Federation engine is missing.")

    evidence: List[CertificationEvidence] = []

    if hasattr(federation, "federations"):
        evidence.append(_ok(domain, "federation_registry", source))
    else:
        evidence.append(_blocking(domain, "federation_registry", source))

    if hasattr(federation, "initiatives") and hasattr(
        federation,
        "delegate_initiative_tasks",
    ):
        evidence.append(_ok(domain, "initiative_delegation", source))
    else:
        evidence.append(_blocking(domain, "initiative_delegation", source))

    if hasattr(federation, "decisions") and hasattr(federation, "tally_decision"):
        evidence.append(_ok(domain, "council_decisions", source))
    else:
        evidence.append(_blocking(domain, "council_decisions", source))

    if hasattr(federation, "conflicts") and hasattr(federation, "resolve_conflict"):
        evidence.append(_ok(domain, "cross_org_conflicts", source))
    else:
        evidence.append(_blocking(domain, "cross_org_conflicts", source))

    return evidence


def collect_reputation_certification(
    engines: Dict,
    context: Dict,
) -> List[CertificationEvidence]:
    domain = CertificationDomain.REPUTATION_CERTIFICATION
    source = "reputation_engine"

    reputation = engines.get("reputation")

    if not reputation:
        return _missing_all(domain, source, "Reputation engine is missing.")

    evidence: List[CertificationEvidence] = []

    if hasattr(reputation, "events"):
        evidence.append(_ok(domain, "reputation_events", source))
    else:
        evidence.append(_blocking(domain, "reputation_events", source))

    if hasattr(reputation, "trust_report"):
        evidence.append(_ok(domain, "trust_scoring", source))
    else:
        evidence.append(_blocking(domain, "trust_scoring", source))

    if hasattr(reputation, "certifications"):
        evidence.append(_ok(domain, "capability_certifications", source))
    else:
        evidence.append(
            _blocking(domain, "capability_certifications", source)
        )

    return evidence


def collect_oversight_controls(
    engines: Dict,
    context: Dict,
) -> List[CertificationEvidence]:
    domain = CertificationDomain.OVERSIGHT_CONTROLS
    source = "oversight_engine"

    oversight = engines.get("oversight")

    if not oversight:
        return _missing_all(domain, source, "Oversight engine is missing.")

    evidence: List[CertificationEvidence] = []

    if hasattr(oversight, "requests"):
        evidence.append(_ok(domain, "oversight_requests", source))
    else:
        evidence.append(_blocking(domain, "oversight_requests", source))

    if hasattr(oversight, "kill_switch"):
        evidence.append(_ok(domain, "kill_switch", source))
    else:
        evidence.append(_blocking(domain, "kill_switch", source))

    if hasattr(oversight, "autonomy_policies"):
        evidence.append(_ok(domain, "autonomy_controls", source))
    else:
        evidence.append(_blocking(domain, "autonomy_controls", source))

    if hasattr(oversight, "decide_request") and hasattr(
        oversight,
        "execute_request",
    ):
        evidence.append(_ok(domain, "human_approval_workflow", source))
    else:
        evidence.append(
            _blocking(domain, "human_approval_workflow", source)
        )

    return evidence


def collect_permissioned_autonomy(
    engines: Dict,
    context: Dict,
) -> List[CertificationEvidence]:
    domain = CertificationDomain.PERMISSIONED_AUTONOMY
    source = "policy_engine"

    policy_engine = engines.get("policy")

    if not policy_engine:
        return _missing_all(domain, source, "Policy engine is missing.")

    evidence: List[CertificationEvidence] = []

    if hasattr(policy_engine, "action_catalog"):
        evidence.append(_ok(domain, "action_catalog", source))
    else:
        evidence.append(_blocking(domain, "action_catalog", source))

    active_policy = None

    if hasattr(policy_engine, "get_active_policy"):
        active_policy = policy_engine.get_active_policy()

    if active_policy:
        evidence.append(_ok(domain, "active_permission_policy", source))
    else:
        evidence.append(
            _blocking(domain, "active_permission_policy", source)
        )

    if hasattr(policy_engine, "delegations") and hasattr(
        policy_engine,
        "grant_delegation",
    ):
        evidence.append(_ok(domain, "delegation_controls", source))
    else:
        evidence.append(_blocking(domain, "delegation_controls", source))

    if hasattr(policy_engine, "evaluate"):
        evidence.append(_ok(domain, "policy_evaluation", source))
    else:
        evidence.append(_blocking(domain, "policy_evaluation", source))

    return evidence


def collect_memory_knowledge_sync(
    engines: Dict,
    context: Dict,
) -> List[CertificationEvidence]:
    domain = CertificationDomain.MEMORY_KNOWLEDGE_SYNC
    source = "memory_consolidation_engine"

    memory = engines.get("memory")

    if not memory:
        return _missing_all(
            domain,
            source,
            "Memory consolidation engine is missing.",
        )

    evidence: List[CertificationEvidence] = []

    if hasattr(memory, "records"):
        evidence.append(_ok(domain, "memory_records", source))
    else:
        evidence.append(_blocking(domain, "memory_records", source))

    if hasattr(memory, "consolidate_all"):
        evidence.append(_ok(domain, "consolidation_pipeline", source))
    else:
        evidence.append(_blocking(domain, "consolidation_pipeline", source))

    if hasattr(memory, "kg_gateway"):
        evidence.append(_ok(domain, "knowledge_graph_gateway", source))
    else:
        evidence.append(
            _blocking(domain, "knowledge_graph_gateway", source)
        )

    if hasattr(memory, "apply_retention"):
        evidence.append(_ok(domain, "retention_controls", source))
    else:
        evidence.append(_blocking(domain, "retention_controls", source))

    return evidence


def collect_operational_resilience(
    engines: Dict,
    context: Dict,
) -> List[CertificationEvidence]:
    domain = CertificationDomain.OPERATIONAL_RESILIENCE
    source = "resilience_engine"

    resilience = engines.get("resilience")

    if not resilience:
        return _missing_all(domain, source, "Resilience engine is missing.")

    evidence: List[CertificationEvidence] = []

    if hasattr(resilience, "circuits"):
        evidence.append(_ok(domain, "circuit_breakers", source))
    else:
        evidence.append(_blocking(domain, "circuit_breakers", source))

    if hasattr(resilience, "set_degradation_mode"):
        evidence.append(_ok(domain, "degradation_modes", source))
    else:
        evidence.append(_blocking(domain, "degradation_modes", source))

    if hasattr(resilience, "retry_decision"):
        evidence.append(_ok(domain, "retry_budgets", source))
    else:
        evidence.append(_blocking(domain, "retry_budgets", source))

    chaos_drills = getattr(resilience, "chaos_drills", [])

    if len(chaos_drills) > 0:
        evidence.append(_ok(domain, "chaos_drills", source))
    else:
        evidence.append(
            _blocking(
                domain,
                "chaos_drills",
                source,
                "No chaos drills recorded.",
                override_allowed=True,
            )
        )

    if hasattr(resilience, "evaluate_quorum"):
        evidence.append(_ok(domain, "quorum_controls", source))
    else:
        evidence.append(_blocking(domain, "quorum_controls", source))

    return evidence


def collect_security_privacy_audit(
    engines: Dict,
    context: Dict,
) -> List[CertificationEvidence]:
    domain = CertificationDomain.SECURITY_PRIVACY_AUDIT
    source = "security_engine"

    security = engines.get("security")

    if not security:
        return _missing_all(domain, source, "Security engine is missing.")

    evidence: List[CertificationEvidence] = []

    if hasattr(security, "authorize"):
        evidence.append(_ok(domain, "authorization_controls", source))
    else:
        evidence.append(
            _blocking(domain, "authorization_controls", source)
        )

    if hasattr(security, "redact_payload"):
        evidence.append(_ok(domain, "secret_redaction", source))
    else:
        evidence.append(_blocking(domain, "secret_redaction", source))

    if hasattr(security, "verify_audit"):
        verification = security.verify_audit()

        if verification.get("valid") is True:
            evidence.append(
                _ok(domain, "audit_chain", source, "Audit chain valid.")
            )
        else:
            evidence.append(
                _blocking(
                    domain,
                    "audit_chain",
                    source,
                    "Audit chain verification failed.",
                    override_allowed=False,
                )
            )
    else:
        evidence.append(
            _blocking(domain, "audit_chain", source)
        )

    alerts = getattr(security, "alerts", [])

    open_critical_alerts = [
        alert
        for alert in alerts
        if getattr(alert, "status", "OPEN") == "OPEN"
        and getattr(alert, "severity", "") == "CRITICAL"
    ]

    if open_critical_alerts:
        evidence.append(
            _blocking(
                domain,
                "security_alerts",
                source,
                "Open critical security alerts exist.",
                override_allowed=False,
            )
        )
    else:
        evidence.append(_ok(domain, "security_alerts", source))

    return evidence


def collect_observability(
    engines: Dict,
    context: Dict,
) -> List[CertificationEvidence]:
    domain = CertificationDomain.OBSERVABILITY
    source = "observability_collector"

    evidence: List[CertificationEvidence] = []

    civilization = engines.get("civilization")

    if civilization and hasattr(civilization, "bus"):
        evidence.append(_ok(domain, "structured_events", source))
    else:
        evidence.append(
            _blocking(domain, "structured_events", source)
        )

    resilience = engines.get("resilience")

    if resilience and hasattr(resilience, "report"):
        evidence.append(_ok(domain, "metrics_report", source))
    elif context.get("observability_report"):
        evidence.append(
            _ok(domain, "metrics_report", "certification_context")
        )
    else:
        evidence.append(
            _blocking(
                domain,
                "metrics_report",
                source,
                "No observability report evidence found.",
                override_allowed=True,
            )
        )

    if context.get("health_checks"):
        evidence.append(
            _ok(domain, "health_checks", "certification_context")
        )
    else:
        evidence.append(
            _blocking(
                domain,
                "health_checks",
                source,
                "Health check evidence missing.",
                override_allowed=True,
            )
        )

    security = engines.get("security")

    if security and hasattr(security, "audit_events"):
        evidence.append(_ok(domain, "audit_visibility", source))
    elif civilization and hasattr(civilization, "bus"):
        evidence.append(
            _ok(
                domain,
                "audit_visibility",
                source,
                "Audit visibility available through event bus.",
            )
        )
    else:
        evidence.append(
            _blocking(domain, "audit_visibility", source)
        )

    return evidence


def collect_documentation_adrs(
    engines: Dict,
    context: Dict,
) -> List[CertificationEvidence]:
    domain = CertificationDomain.DOCUMENTATION_ADRS
    source = "certification_context"

    evidence: List[CertificationEvidence] = []

    requirements = DOMAIN_REQUIREMENTS[domain]

    for requirement in requirements:
        if context.get(requirement):
            evidence.append(_ok(domain, requirement, source))
        else:
            evidence.append(
                _blocking(
                    domain,
                    requirement,
                    source,
                    "Documentation evidence missing.",
                    override_allowed=True,
                )
            )

    return evidence


def collect_testing_verification(
    engines: Dict,
    context: Dict,
) -> List[CertificationEvidence]:
    domain = CertificationDomain.TESTING_VERIFICATION
    source = "certification_context"

    evidence: List[CertificationEvidence] = []

    requirements = DOMAIN_REQUIREMENTS[domain]

    for requirement in requirements:
        if context.get(requirement):
            evidence.append(_ok(domain, requirement, source))
        else:
            evidence.append(
                _blocking(
                    domain,
                    requirement,
                    source,
                    "Test evidence missing.",
                    override_allowed=True,
                )
            )

    return evidence


def collect_production_operations(
    engines: Dict,
    context: Dict,
) -> List[CertificationEvidence]:
    domain = CertificationDomain.PRODUCTION_OPERATIONS
    source = "certification_context"

    evidence: List[CertificationEvidence] = []

    requirements = DOMAIN_REQUIREMENTS[domain]

    for requirement in requirements:
        if context.get(requirement):
            evidence.append(_ok(domain, requirement, source))
        else:
            evidence.append(
                _blocking(
                    domain,
                    requirement,
                    source,
                    "Operational evidence missing.",
                    override_allowed=True,
                )
            )

    return evidence


DEFAULT_COLLECTORS: Dict[CertificationDomain, List[CollectorFunction]] = {
    CertificationDomain.ORGANIZATION_GOVERNANCE: [
        collect_organization_governance,
    ],
    CertificationDomain.FEDERATION_GOVERNANCE: [
        collect_federation_governance,
    ],
    CertificationDomain.REPUTATION_CERTIFICATION: [
        collect_reputation_certification,
    ],
    CertificationDomain.OVERSIGHT_CONTROLS: [
        collect_oversight_controls,
    ],
    CertificationDomain.PERMISSIONED_AUTONOMY: [
        collect_permissioned_autonomy,
    ],
    CertificationDomain.MEMORY_KNOWLEDGE_SYNC: [
        collect_memory_knowledge_sync,
    ],
    CertificationDomain.OPERATIONAL_RESILIENCE: [
        collect_operational_resilience,
    ],
    CertificationDomain.SECURITY_PRIVACY_AUDIT: [
        collect_security_privacy_audit,
    ],
    CertificationDomain.OBSERVABILITY: [
        collect_observability,
    ],
    CertificationDomain.DOCUMENTATION_ADRS: [
        collect_documentation_adrs,
    ],
    CertificationDomain.TESTING_VERIFICATION: [
        collect_testing_verification,
    ],
    CertificationDomain.PRODUCTION_OPERATIONS: [
        collect_production_operations,
    ],
}


class CertificationEngine:
    """Production certification engine for Phase 22 closure."""

    def __init__(
        self,
        policy: Optional[CertificationPolicy] = None,
        engines: Optional[Dict] = None,
        context: Optional[Dict] = None,
        collectors: Optional[
            Dict[CertificationDomain, List[CollectorFunction]]
        ] = None,
    ) -> None:
        self.policy = policy or CertificationPolicy()

        self.engines = engines or {}
        self.context = context or {}

        self.collectors = collectors or DEFAULT_COLLECTORS

        self.manual_evidence: List[CertificationEvidence] = []

        self.reports: Dict[str, ProductionCertificationReport] = {}

    # ------------------------------------------------------------------
    # Manual evidence
    # ------------------------------------------------------------------

    def add_manual_evidence(
        self,
        payload: ManualEvidencePayload,
    ) -> CertificationEvidence:
        requirements = DOMAIN_REQUIREMENTS.get(payload.domain, [])

        if payload.requirement not in requirements:
            raise CertificationError(
                f"Unknown requirement for domain {payload.domain.value}: "
                f"{payload.requirement}"
            )

        evidence = CertificationEvidence(
            domain=payload.domain,
            requirement=payload.requirement,
            satisfied=payload.satisfied,
            severity=payload.severity,
            source=payload.source,
            details=payload.details,
            override_allowed=True,
            collected_at=utcnow().isoformat(),
        )

        self.manual_evidence.append(evidence)

        return evidence

    # ------------------------------------------------------------------
    # Assessment
    # ------------------------------------------------------------------

    def assess_domain(
        self,
        domain: CertificationDomain,
    ) -> DomainAssessment:
        evidence: List[CertificationEvidence] = []

        collectors = self.collectors.get(domain, [])

        for collector in collectors:
            try:
                evidence.extend(collector(self.engines, self.context))
            except Exception as exc:
                evidence.append(
                    _blocking(
                        domain,
                        "collector_error",
                        "certification_engine",
                        f"Collector failed: {exc}",
                        override_allowed=False,
                    )
                )

        evidence.extend(
            [
                item
                for item in self.manual_evidence
                if item.domain == domain
            ]
        )

        evidence = [self._normalize_evidence(item) for item in evidence]

        required_requirements = DOMAIN_REQUIREMENTS[domain]

        blocking_issues: List[str] = []
        warnings: List[str] = []
        missing_requirements: List[str] = []

        for requirement in required_requirements:
            requirement_evidence = [
                item
                for item in evidence
                if item.requirement == requirement
            ]

            critical_blocks = [
                item
                for item in requirement_evidence
                if not item.satisfied
                and item.severity == EvidenceSeverity.BLOCKING
                and not item.override_allowed
            ]

            satisfied = any(item.satisfied for item in requirement_evidence)

            overrideable_blocks = [
                item
                for item in requirement_evidence
                if not item.satisfied
                and item.severity == EvidenceSeverity.BLOCKING
                and item.override_allowed
            ]

            warning_blocks = [
                item
                for item in requirement_evidence
                if not item.satisfied
                and item.severity == EvidenceSeverity.WARNING
            ]

            if critical_blocks:
                blocking_issues.append(
                    f"{requirement}: critical evidence failed"
                )

            elif not satisfied:
                missing_requirements.append(requirement)
                blocking_issues.append(
                    f"{requirement}: missing evidence"
                )

            else:
                if overrideable_blocks:
                    warnings.append(
                        f"{requirement}: compensating or manual evidence used"
                    )

                for item in warning_blocks:
                    warnings.append(f"{requirement}: {item.details}")

        passed = len(blocking_issues) == 0

        return DomainAssessment(
            domain=domain,
            passed=passed,
            blocking_issues=blocking_issues,
            warnings=warnings,
            missing_requirements=missing_requirements,
            evidence_count=len(evidence),
        )

    # ------------------------------------------------------------------
    # Certification
    # ------------------------------------------------------------------

    def certify(
        self,
        issued_by: str = "certification_engine",
    ) -> ProductionCertificationReport:
        assessments: List[DomainAssessment] = []

        for domain in DOMAIN_REQUIREMENTS.keys():
            assessments.append(self.assess_domain(domain))

        blocking_count = sum(
            len(assessment.blocking_issues)
            for assessment in assessments
        )

        warning_count = sum(
            len(assessment.warnings)
            for assessment in assessments
        )

        if blocking_count > 0:
            status = CertificationStatus.NOT_CERTIFIED
            rationale = (
                "Production certification denied due to blocking evidence "
                "gaps or failed critical controls."
            )
        elif warning_count > 0 and self.policy.allow_conditional_on_warnings:
            status = CertificationStatus.CONDITIONALLY_CERTIFIED
            rationale = (
                "Production certification granted conditionally due to "
                "warnings."
            )
        else:
            status = CertificationStatus.CERTIFIED
            rationale = "All required production certification domains passed."

        created_dt = utcnow()
        created_at = created_dt.isoformat()

        report_id = deterministic_id(
            "production_certification_report",
            {
                "phase": "Phase 22",
                "issued_by": issued_by,
                "created_at": created_at,
            },
        )

        expires_at = (
            created_dt + timedelta(days=self.policy.certification_ttl_days)
        ).isoformat()

        report = ProductionCertificationReport(
            id=report_id,
            phase="Phase 22",
            status=status,
            domains=assessments,
            blocking_count=blocking_count,
            warning_count=warning_count,
            issued_by=issued_by,
            rationale=rationale,
            created_at=created_at,
            expires_at=expires_at,
        )

        self.reports[report_id] = report

        return report

    def revoke_certification(
        self,
        report_id: str,
        revoked_by: str,
        reason: str = "",
    ) -> ProductionCertificationReport:
        report = self.reports.get(report_id)

        if not report:
            raise CertificationError(
                f"Certification report not found: {report_id}"
            )

        report.status = CertificationStatus.REVOKED
        report.revoked_at = utcnow().isoformat()
        report.revocation_reason = reason
        report.issued_by = revoked_by

        return report

    def get_report(self, report_id: str) -> ProductionCertificationReport:
        report = self.reports.get(report_id)

        if not report:
            raise CertificationError(
                f"Certification report not found: {report_id}"
            )

        return report

    def list_reports(self) -> List[ProductionCertificationReport]:
        return list(self.reports.values())

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _normalize_evidence(
        self,
        evidence: CertificationEvidence,
    ) -> CertificationEvidence:
        if evidence.id:
            return evidence

        evidence.id = deterministic_id(
            "certification_evidence",
            {
                "domain": evidence.domain.value,
                "requirement": evidence.requirement,
                "source": evidence.source,
                "collected_at": evidence.collected_at,
                "evidence_count": len(self.manual_evidence)
                + len(self.reports),
            },
        )

        return evidence
