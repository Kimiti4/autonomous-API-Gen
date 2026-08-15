"""
Production Learning Certification engine.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Dict, List, Optional

from .models import (
    CertificationGateResult,
    CertificationStatus,
    GateStatus,
    OperationalReadinessEvidence,
    ProductionLearningCertificationPolicy,
    ProductionLearningCertificationReport,
    ProductionLearningDomain,
    utcnow,
)


class ProductionLearningCertificationEngine:
    """Certifies production learning readiness."""

    def __init__(
        self,
        learning_pipeline_certification_engine=None,
        telemetry_engine=None,
        anomaly_engine=None,
        knowledge_sync_engine=None,
        evolution_feedback_engine=None,
        learning_governance_engine=None,
        observability_engine=None,
        marketplace_autonomy_engine=None,
        policy: ProductionLearningCertificationPolicy | None = None,
    ) -> None:
        self.learning_pipeline_certification_engine = (
            learning_pipeline_certification_engine
        )
        self.telemetry_engine = telemetry_engine
        self.anomaly_engine = anomaly_engine
        self.knowledge_sync_engine = knowledge_sync_engine
        self.evolution_feedback_engine = evolution_feedback_engine
        self.learning_governance_engine = learning_governance_engine
        self.observability_engine = observability_engine
        self.marketplace_autonomy_engine = marketplace_autonomy_engine

        self.policy = policy or ProductionLearningCertificationPolicy()

        self.reports: Dict[str, ProductionLearningCertificationReport] = {}

    # ------------------------------------------------------------------
    # Certification
    # ------------------------------------------------------------------

    def certify(
        self,
        scope: str = "production_learning",
        certified_by: str = "system",
        evidence: OperationalReadinessEvidence | None = None,
        prerequisite_26_7_report_id: Optional[str] = None,
    ) -> ProductionLearningCertificationReport:
        gates: List[CertificationGateResult] = []

        gates.append(
            self._gate_learning_pipeline_certification(
                prerequisite_26_7_report_id
            )
        )

        gates.append(
            self._gate_engine(
                domain=ProductionLearningDomain.TELEMETRY_ADAPTERS,
                engine=self.telemetry_engine,
                required=self.policy.require_telemetry_adapters,
                engine_name="Telemetry adapter engine",
            )
        )

        gates.append(
            self._gate_engine(
                domain=ProductionLearningDomain.ANOMALY_DETECTION,
                engine=self.anomaly_engine,
                required=self.policy.require_anomaly_detection,
                engine_name="Anomaly detection engine",
            )
        )

        gates.append(
            self._gate_engine(
                domain=ProductionLearningDomain.KNOWLEDGE_SYNC,
                engine=self.knowledge_sync_engine,
                required=self.policy.require_knowledge_sync,
                engine_name="Knowledge Graph learning sync engine",
            )
        )

        gates.append(
            self._gate_engine(
                domain=ProductionLearningDomain.EVOLUTION_FEEDBACK,
                engine=self.evolution_feedback_engine,
                required=self.policy.require_evolution_feedback,
                engine_name="Evolutionary fitness feedback engine",
            )
        )

        gates.append(
            self._gate_engine(
                domain=ProductionLearningDomain.LEARNING_GOVERNANCE,
                engine=self.learning_governance_engine,
                required=self.policy.require_learning_governance,
                engine_name="Learning governance engine",
            )
        )

        gates.append(
            self._gate_engine(
                domain=ProductionLearningDomain.OBSERVABILITY,
                engine=self.observability_engine,
                required=self.policy.require_observability,
                engine_name="Learning observability engine",
            )
        )

        gates.append(
            self._gate_marketplace_learning(evidence)
        )

        gates.append(
            self._gate_production_readiness(evidence)
        )

        failures = [gate for gate in gates if gate.status == GateStatus.FAIL]

        warnings = [gate for gate in gates if gate.status == GateStatus.WARNING]

        reasons: List[str] = []

        if failures:
            status = CertificationStatus.NOT_CERTIFIED
            reasons.extend([gate.reason for gate in failures if gate.reason])
        elif warnings and self.policy.allow_conditional_certification:
            status = CertificationStatus.CONDITIONALLY_CERTIFIED
            reasons.extend([gate.reason for gate in warnings if gate.reason])
        else:
            status = CertificationStatus.CERTIFIED

        if (
            self.policy.require_human_certification
            and certified_by != "human"
            and status == CertificationStatus.CERTIFIED
        ):
            status = CertificationStatus.CONDITIONALLY_CERTIFIED
            reasons.append(
                "Human certification is required for production learning certification."
            )

        expires_at = utcnow() + timedelta(
            days=self.policy.certification_ttl_days
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
            evidence_refs.extend(evidence.fraud_learning_evidence)
            evidence_refs.extend(evidence.pricing_learning_evidence)
            evidence_refs.extend(evidence.conversion_learning_evidence)
            evidence_refs.extend(evidence.refund_support_learning_evidence)
            evidence_refs.extend(evidence.revenue_ops_learning_evidence)

        report = ProductionLearningCertificationReport(
            scope=scope,
            status=status,
            gates=gates,
            reasons=reasons,
            evidence_refs=evidence_refs,
            prerequisite_26_7_report_id=prerequisite_26_7_report_id,
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
    ) -> ProductionLearningCertificationReport:
        report = self.reports.get(report_id)

        if not report:
            raise KeyError(
                f"Production learning certification report not found: {report_id}"
            )

        report.status = CertificationStatus.REVOKED
        report.revoked_at = utcnow()
        report.revocation_reason = reason
        report.certified_by = revoked_by

        return report

    def latest_report(self) -> Optional[ProductionLearningCertificationReport]:
        if not self.reports:
            return None

        return list(self.reports.values())[-1]

    def report(self, report_id: str) -> ProductionLearningCertificationReport:
        report = self.reports.get(report_id)

        if not report:
            raise KeyError(
                f"Production learning certification report not found: {report_id}"
            )

        return report

    # ------------------------------------------------------------------
    # Certification gates
    # ------------------------------------------------------------------

    def _gate_learning_pipeline_certification(
        self,
        prerequisite_report_id: Optional[str],
    ) -> CertificationGateResult:
        domain = ProductionLearningDomain.LEARNING_PIPELINE_CERTIFICATION

        if not self.policy.require_learning_pipeline_certification:
            return CertificationGateResult(
                domain=domain,
                status=GateStatus.PASS,
                reason="Learning pipeline certification is optional.",
            )

        engine = self.learning_pipeline_certification_engine

        if not engine:
            return CertificationGateResult(
                domain=domain,
                status=GateStatus.FAIL,
                reason="Learning pipeline certification engine is missing.",
            )

        report = None

        if prerequisite_report_id:
            report = getattr(engine, "reports", {}).get(
                prerequisite_report_id
            )
        else:
            report = engine.latest_report()

        if not report:
            return CertificationGateResult(
                domain=domain,
                status=GateStatus.FAIL,
                reason="Phase 26.7 learning pipeline certification report is missing.",
            )

        status_value = getattr(report.status, "value", str(report.status))

        revoked_at = getattr(report, "revoked_at", None)

        expires_at = getattr(report, "expires_at", None)

        if revoked_at:
            return CertificationGateResult(
                domain=domain,
                status=GateStatus.FAIL,
                reason="Phase 26.7 learning pipeline certification has been revoked.",
            )

        if expires_at and expires_at < utcnow():
            return CertificationGateResult(
                domain=domain,
                status=GateStatus.FAIL,
                reason="Phase 26.7 learning pipeline certification has expired.",
            )

        if status_value == "CERTIFIED":
            return CertificationGateResult(
                domain=domain,
                status=GateStatus.PASS,
                reason="Phase 26.7 learning pipeline certification is valid.",
                evidence_refs=[getattr(report, "id", "unknown")],
            )

        if status_value == "CONDITIONALLY_CERTIFIED":
            return CertificationGateResult(
                domain=domain,
                status=GateStatus.WARNING,
                reason="Phase 26.7 learning pipeline certification is conditional.",
                evidence_refs=[getattr(report, "id", "unknown")],
            )

        return CertificationGateResult(
            domain=domain,
            status=GateStatus.FAIL,
            reason="Phase 26.7 learning pipeline certification is not valid.",
        )

    def _gate_engine(
        self,
        domain: ProductionLearningDomain,
        engine,
        required: bool,
        engine_name: str,
    ) -> CertificationGateResult:
        if engine:
            return CertificationGateResult(
                domain=domain,
                status=GateStatus.PASS,
                reason=f"{engine_name} is present.",
            )

        if required:
            return CertificationGateResult(
                domain=domain,
                status=GateStatus.FAIL,
                reason=f"{engine_name} is missing.",
            )

        return CertificationGateResult(
            domain=domain,
            status=GateStatus.PASS,
            reason=f"{engine_name} is optional and not present.",
        )

    def _gate_marketplace_learning(
        self,
        evidence: OperationalReadinessEvidence | None,
    ) -> CertificationGateResult:
        domain = ProductionLearningDomain.MARKETPLACE_LEARNING

        if not self.policy.require_marketplace_learning:
            return CertificationGateResult(
                domain=domain,
                status=GateStatus.PASS,
                reason="Marketplace learning certification is optional.",
            )

        if not self.marketplace_autonomy_engine:
            return CertificationGateResult(
                domain=domain,
                status=GateStatus.FAIL,
                reason="Marketplace autonomy/learning engine is missing.",
            )

        missing_marketplace_evidence: List[str] = []

        if evidence:
            if self.policy.require_fraud_learning and not evidence.fraud_learning_evidence:
                missing_marketplace_evidence.append("fraud_learning_evidence")

            if self.policy.require_pricing_learning and not evidence.pricing_learning_evidence:
                missing_marketplace_evidence.append("pricing_learning_evidence")

            if self.policy.require_conversion_learning and not evidence.conversion_learning_evidence:
                missing_marketplace_evidence.append("conversion_learning_evidence")

            if self.policy.require_refund_support_learning and not evidence.refund_support_learning_evidence:
                missing_marketplace_evidence.append("refund_support_learning_evidence")

            if self.policy.require_revenue_ops_learning and not evidence.revenue_ops_learning_evidence:
                missing_marketplace_evidence.append("revenue_ops_learning_evidence")

            if self.policy.require_marketplace_metrics and not evidence.marketplace_metrics_refs:
                missing_marketplace_evidence.append("marketplace_metrics_refs")
        else:
            missing_marketplace_evidence.append("marketplace_learning_evidence")

        if missing_marketplace_evidence:
            return CertificationGateResult(
                domain=domain,
                status=GateStatus.FAIL,
                reason=(
                    "Marketplace learning evidence missing: "
                    + ", ".join(missing_marketplace_evidence)
                ),
            )

        return CertificationGateResult(
            domain=domain,
            status=GateStatus.PASS,
            reason="Marketplace learning evidence is present.",
        )

    def _gate_production_readiness(
        self,
        evidence: OperationalReadinessEvidence | None,
    ) -> CertificationGateResult:
        domain = ProductionLearningDomain.PRODUCTION_OPERATIONS

        if not self.policy.require_production_readiness:
            return CertificationGateResult(
                domain=domain,
                status=GateStatus.PASS,
                reason="Production readiness evidence is optional.",
            )

        if not evidence:
            return CertificationGateResult(
                domain=domain,
                status=GateStatus.FAIL,
                reason="Production readiness evidence is missing.",
            )

        missing: List[str] = []

        if self.policy.require_slos and not evidence.slo_definitions:
            missing.append("slo_definitions")

        if self.policy.require_runbooks and not evidence.runbooks:
            missing.append("runbooks")

        if self.policy.require_incident_response and not evidence.incident_response_plans:
            missing.append("incident_response_plans")

        if self.policy.require_backup_restore and not evidence.backup_restore_evidence:
            missing.append("backup_restore_evidence")

        if self.policy.require_observability_evidence and not evidence.observability_evidence:
            missing.append("observability_evidence")

        if self.policy.require_dashboard_evidence and not evidence.dashboard_refs:
            missing.append("dashboard_refs")

        if missing:
            return CertificationGateResult(
                domain=domain,
                status=GateStatus.FAIL,
                reason="Production readiness evidence missing: " + ", ".join(missing),
            )

        return CertificationGateResult(
            domain=domain,
            status=GateStatus.PASS,
            reason="Production readiness evidence is present.",
        )
