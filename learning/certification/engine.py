"""
Learning pipeline certification engine.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Dict, List, Optional

from .models import (
    CertificationGateResult,
    CertificationStatus,
    GateStatus,
    LearningPipelineCertificationPolicy,
    LearningPipelineCertificationReport,
    utcnow,
)


class LearningPipelineCertificationEngine:
    """Certifies the learning pipeline for production use."""

    def __init__(
        self,
        learning_engine=None,
        analytics_engine=None,
        governance_engine=None,
        observability_engine=None,
        knowledge_sync_engine=None,
        policy: LearningPipelineCertificationPolicy | None = None,
    ) -> None:
        self.learning_engine = learning_engine
        self.analytics_engine = analytics_engine
        self.governance_engine = governance_engine
        self.observability_engine = observability_engine
        self.knowledge_sync_engine = knowledge_sync_engine

        self.policy = policy or LearningPipelineCertificationPolicy()

        self.reports: Dict[str, LearningPipelineCertificationReport] = {}

    # ------------------------------------------------------------------
    # Certification
    # ------------------------------------------------------------------

    def certify(
        self,
        scope: str = "learning_pipeline",
        certified_by: str = "system",
        evidence_refs: Optional[List[str]] = None,
    ) -> LearningPipelineCertificationReport:
        gates: List[CertificationGateResult] = []
        reasons: List[str] = []

        metrics = self._metrics_snapshot()
        health = self._operational_health()

        gates.append(self._gate_signal_ingestion(metrics))
        gates.append(self._gate_anomaly_rate(metrics))
        gates.append(self._gate_evidence_quality())
        gates.append(self._gate_safety_controls())
        gates.append(self._gate_governance_backlog(metrics))
        gates.append(self._gate_observability(health))
        gates.append(self._gate_knowledge_sync())
        gates.append(self._gate_production_readiness(evidence_refs or []))

        has_failure = any(gate.status == GateStatus.FAIL for gate in gates)

        warnings = [
            gate
            for gate in gates
            if gate.status == GateStatus.WARNING
        ]

        if has_failure:
            status = CertificationStatus.NOT_CERTIFIED
            reasons.append("One or more certification gates failed.")
        elif warnings and self.policy.allow_conditional_certification:
            status = CertificationStatus.CONDITIONALLY_CERTIFIED
            reasons.append("Certification granted with warnings.")
        else:
            status = CertificationStatus.CERTIFIED

        if (
            self.policy.require_human_certification
            and certified_by != "human"
            and status == CertificationStatus.CERTIFIED
        ):
            status = CertificationStatus.CONDITIONALLY_CERTIFIED
            reasons.append("Human certification is required for production.")

        expires_at = utcnow() + timedelta(days=self.policy.certification_ttl_days)

        report = LearningPipelineCertificationReport(
            scope=scope,
            status=status,
            gates=gates,
            reasons=reasons,
            evidence_refs=evidence_refs or [],
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
    ) -> LearningPipelineCertificationReport:
        report = self.reports.get(report_id)

        if not report:
            raise KeyError(f"Certification report not found: {report_id}")

        report.status = CertificationStatus.REVOKED
        report.revoked_at = utcnow()
        report.revocation_reason = reason
        report.certified_by = revoked_by

        return report

    def latest_report(self) -> Optional[LearningPipelineCertificationReport]:
        if not self.reports:
            return None

        return list(self.reports.values())[-1]

    def report(self, report_id: str) -> LearningPipelineCertificationReport:
        report = self.reports.get(report_id)

        if not report:
            raise KeyError(f"Certification report not found: {report_id}")

        return report

    # ------------------------------------------------------------------
    # Certification gates
    # ------------------------------------------------------------------

    def _gate_signal_ingestion(self, metrics: Dict) -> CertificationGateResult:
        signal_count = metrics.get("signal_count", 0)
        recent_signal_count = metrics.get("recent_signal_count", 0)

        if signal_count >= self.policy.min_signal_count and (
            recent_signal_count >= self.policy.min_recent_signals
        ):
            return CertificationGateResult(
                gate="signal_ingestion",
                status=GateStatus.PASS,
                reason="Signal ingestion is active.",
            )

        if signal_count > 0:
            return CertificationGateResult(
                gate="signal_ingestion",
                status=GateStatus.WARNING,
                reason="Signals exist, but recent signal flow is low.",
            )

        return CertificationGateResult(
            gate="signal_ingestion",
            status=GateStatus.FAIL,
            reason="No signals received by the learning pipeline.",
        )

    def _gate_anomaly_rate(self, metrics: Dict) -> CertificationGateResult:
        signal_count = metrics.get("signal_count", 0)
        anomaly_count = metrics.get("anomaly_count", 0)

        if signal_count <= 0:
            return CertificationGateResult(
                gate="anomaly_rate",
                status=GateStatus.WARNING,
                reason="No signals available for anomaly-rate evaluation.",
            )

        anomaly_rate = anomaly_count / signal_count

        if anomaly_rate > self.policy.max_anomaly_rate:
            return CertificationGateResult(
                gate="anomaly_rate",
                status=GateStatus.FAIL,
                reason=(
                    f"Anomaly rate {anomaly_rate:.2f} exceeds threshold "
                    f"{self.policy.max_anomaly_rate:.2f}."
                ),
            )

        return CertificationGateResult(
            gate="anomaly_rate",
            status=GateStatus.PASS,
            reason=f"Anomaly rate {anomaly_rate:.2f} is within threshold.",
        )

    def _gate_evidence_quality(self) -> CertificationGateResult:
        insights = getattr(self.analytics_engine, "insights", None)

        if not insights:
            return CertificationGateResult(
                gate="evidence_quality",
                status=GateStatus.WARNING,
                reason="No learning insights available.",
            )

        confidences = []

        iterable = insights.values() if isinstance(insights, dict) else insights

        for insight in iterable:
            confidence = getattr(insight, "confidence", None)

            if confidence is not None:
                confidences.append(float(confidence))

        if not confidences:
            return CertificationGateResult(
                gate="evidence_quality",
                status=GateStatus.WARNING,
                reason="Insights exist but confidence data is missing.",
            )

        average_confidence = sum(confidences) / len(confidences)

        if average_confidence < self.policy.min_evidence_confidence:
            return CertificationGateResult(
                gate="evidence_quality",
                status=GateStatus.WARNING,
                reason=(
                    f"Average insight confidence {average_confidence:.2f} "
                    "is below target."
                ),
            )

        return CertificationGateResult(
            gate="evidence_quality",
            status=GateStatus.PASS,
            reason=f"Average insight confidence {average_confidence:.2f}.",
        )

    def _gate_safety_controls(self) -> CertificationGateResult:
        kill_switch = getattr(self.governance_engine, "kill_switch", None)

        kill_switch_enabled = bool(
            getattr(kill_switch, "enabled", False)
        )

        safety_blocker_count = int(
            getattr(self.governance_engine, "safety_blocker_count", 0)
        )

        if kill_switch_enabled and self.policy.require_kill_switch_disabled:
            return CertificationGateResult(
                gate="safety_controls",
                status=GateStatus.FAIL,
                reason="Learning kill switch is active.",
            )

        if safety_blocker_count > 0:
            return CertificationGateResult(
                gate="safety_controls",
                status=GateStatus.FAIL,
                reason="Safety blockers are present.",
            )

        return CertificationGateResult(
            gate="safety_controls",
            status=GateStatus.PASS,
            reason="Safety controls are healthy.",
        )

    def _gate_governance_backlog(self, metrics: Dict) -> CertificationGateResult:
        pending_approval_count = metrics.get("pending_approval_count", 0)

        if pending_approval_count > self.policy.max_pending_approvals:
            return CertificationGateResult(
                gate="governance_backlog",
                status=GateStatus.WARNING,
                reason=(
                    f"Pending approvals {pending_approval_count} exceed target "
                    f"{self.policy.max_pending_approvals}."
                ),
            )

        return CertificationGateResult(
            gate="governance_backlog",
            status=GateStatus.PASS,
            reason="Governance backlog is within target.",
        )

    def _gate_observability(self, health) -> CertificationGateResult:
        if not health:
            return CertificationGateResult(
                gate="observability",
                status=GateStatus.MISSING,
                reason="Observability engine is not configured.",
            )

        status = getattr(health, "status", None)

        status_value = getattr(status, "value", str(status))

        if status_value in {"HEALTHY", "WARNING"}:
            return CertificationGateResult(
                gate="observability",
                status=GateStatus.PASS,
                reason=f"Observability status is {status_value}.",
            )

        if self.policy.require_observability_healthy:
            return CertificationGateResult(
                gate="observability",
                status=GateStatus.FAIL,
                reason=f"Observability status is {status_value}.",
            )

        return CertificationGateResult(
            gate="observability",
            status=GateStatus.WARNING,
            reason=f"Observability status is {status_value}.",
        )

    def _gate_knowledge_sync(self) -> CertificationGateResult:
        if not self.policy.require_knowledge_sync:
            return CertificationGateResult(
                gate="knowledge_sync",
                status=GateStatus.PASS,
                reason="Knowledge sync is optional.",
            )

        registry = getattr(self.knowledge_sync_engine, "registry", None)

        if not registry:
            return CertificationGateResult(
                gate="knowledge_sync",
                status=GateStatus.MISSING,
                reason="Knowledge sync engine is not configured.",
            )

        synced_insights = len(getattr(registry, "synced_insight_ids", set()))

        if synced_insights == 0:
            return CertificationGateResult(
                gate="knowledge_sync",
                status=GateStatus.WARNING,
                reason="No learning insights synced to Knowledge Graph.",
            )

        return CertificationGateResult(
            gate="knowledge_sync",
            status=GateStatus.PASS,
            reason="Learning insights are synced to Knowledge Graph.",
        )

    def _gate_production_readiness(
        self,
        evidence_refs: List[str],
    ) -> CertificationGateResult:
        if not evidence_refs:
            return CertificationGateResult(
                gate="production_readiness",
                status=GateStatus.WARNING,
                reason=(
                    "No production readiness evidence provided. "
                    "Expected SLOs, runbooks, backup evidence, incident "
                    "response evidence, and observability evidence."
                ),
            )

        return CertificationGateResult(
            gate="production_readiness",
            status=GateStatus.PASS,
            reason="Production readiness evidence provided.",
            evidence_refs=evidence_refs,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _metrics_snapshot(self) -> Dict:
        if not self.observability_engine:
            return {}

        snapshot = self.observability_engine.metrics_snapshot()

        return snapshot.model_dump()

    def _operational_health(self):
        if not self.observability_engine:
            return None

        return self.observability_engine.operational_health()
