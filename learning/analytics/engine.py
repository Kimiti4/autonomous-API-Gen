"""
Anomaly detection and signal correlation engine.
"""

from __future__ import annotations

from typing import Dict, List

from ..models import LearningInsight, Severity
from ..utils import deterministic_id, utcnow
from .baseline import BaselineRegistry
from .correlation import SIGNAL_TYPE_OBJECTIVES, SignalCorrelationEngine
from .detection import CompositeAnomalyDetector
from .models import (
    AnomalyDetectionPolicy,
    AnomalyRecord,
    AnomalyReport,
    IncidentCluster,
)


OBJECTIVE_RECOMMENDATIONS = {
    "reliability": [
        "Investigate incident root cause.",
        "Strengthen reliability controls.",
    ],
    "operational_resilience": [
        "Review operational runbooks.",
        "Verify rollback and recovery readiness.",
    ],
    "performance_efficiency": [
        "Profile slow operations.",
        "Evaluate caching and scaling.",
    ],
    "security_posture": [
        "Escalate security findings through governance.",
        "Verify least privilege and secrets hygiene.",
    ],
    "cost_efficiency": [
        "Review infrastructure utilization.",
        "Evaluate autoscaling and scheduling.",
    ],
    "user_satisfaction": [
        "Review onboarding and UX flows.",
        "Correlate feedback with reliability and performance.",
    ],
}


class AnomalyCorrelationEngine:
    """Coordinates anomaly detection, correlation, and insight generation."""

    def __init__(
        self,
        learning_engine=None,
        policy: AnomalyDetectionPolicy | None = None,
    ) -> None:
        self.learning_engine = learning_engine
        self.policy = policy or AnomalyDetectionPolicy()

        self.baselines = BaselineRegistry(self.policy)
        self.detector = CompositeAnomalyDetector()
        self.correlation_engine = SignalCorrelationEngine(self.policy)

        self.anomalies: Dict[str, AnomalyRecord] = {}
        self.clusters: Dict[str, IncidentCluster] = {}
        self.insights: Dict[str, LearningInsight] = {}

        self.processed_signal_ids: set[str] = set()

    def analyze(
        self,
        subject_ref: str | None = None,
    ) -> AnomalyReport:
        signals = []

        if self.learning_engine:
            signals = self.learning_engine.pipeline.query(
                subject_ref=subject_ref
            )

        new_signals = [
            signal
            for signal in signals
            if signal.id and signal.id not in self.processed_signal_ids
        ]

        anomalies: List[AnomalyRecord] = []

        for signal in new_signals:
            self.processed_signal_ids.add(signal.id)

            anomaly = self.detector.detect(
                signal,
                self.baselines,
                self.policy,
            )

            if anomaly:
                self.anomalies[anomaly.id] = anomaly
                anomalies.append(anomaly)

        clusters, correlations = self.correlation_engine.correlate(
            signals,
            list(self.anomalies.values()),
        )

        for cluster in clusters:
            self.clusters[cluster.id] = cluster

        insights = self._clusters_to_insights(clusters)

        for insight in insights:
            self.insights[insight.id] = insight

            if self.learning_engine and hasattr(self.learning_engine, "insights"):
                self.learning_engine.insights[insight.id] = insight

        return AnomalyReport(
            analyzed_signals=len(new_signals),
            anomalies=len(anomalies),
            clusters=len(clusters),
            insights=len(insights),
            generated_at=utcnow().isoformat(),
        )

    def _clusters_to_insights(
        self,
        clusters: List[IncidentCluster],
    ) -> List[LearningInsight]:
        insights: List[LearningInsight] = []

        for cluster in clusters:
            recommendations: List[str] = []

            for objective in cluster.objectives:
                recommendations.extend(
                    OBJECTIVE_RECOMMENDATIONS.get(objective, [])
                )

            if cluster.severity == Severity.CRITICAL:
                recommendations.append(
                    "Escalate through governance before architecture change."
                )

            recommendations = sorted(set(recommendations))

            insight_id = deterministic_id(
                "learning_insight_anomaly_cluster",
                {
                    "cluster_id": cluster.id,
                },
            )

            insight = LearningInsight(
                id=insight_id,
                title="Correlated anomaly cluster detected",
                description=(
                    "Multiple operational signals correlate in time and "
                    "subject scope, indicating a probable incident or "
                    "systemic degradation."
                ),
                affected_subjects=cluster.affected_subjects,
                signal_ids=cluster.signal_ids,
                objectives=cluster.objectives,
                severity=cluster.severity,
                confidence=cluster.confidence,
                recommendations=recommendations,
                created_at=cluster.created_at,
            )

            insights.append(insight)

        return insights
