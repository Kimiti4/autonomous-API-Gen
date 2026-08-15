"""
Learning analyzers.
"""

from __future__ import annotations

from typing import Dict, List, Set

from .models import (
    LearningInsight,
    LearningPolicy,
    LearningSignal,
    LearningSignalType,
    Severity,
    severity_rank,
)
from .utils import deterministic_id, utcnow


def _hour_bucket(timestamp: str) -> str:
    return timestamp[:13]


def _affected_subjects(signals: List[LearningSignal]) -> List[str]:
    subjects: Set[str] = set()

    for signal in signals:
        if signal.subject_ref:
            subjects.add(signal.subject_ref)

        service = signal.labels.get("service")

        if service:
            subjects.add(service)

    return sorted(subjects) or ["platform"]


def _max_severity(signals: List[LearningSignal]) -> Severity:
    max_rank = -1
    result = Severity.INFO

    for signal in signals:
        rank = severity_rank(signal.severity)

        if rank > max_rank:
            max_rank = rank
            result = signal.severity

    return result


class IncidentAnalyzer:
    """Detects reliability incidents."""

    def analyze(
        self,
        signals: List[LearningSignal],
        policy: LearningPolicy,
    ) -> List[LearningInsight]:
        relevant = [
            signal
            for signal in signals
            if signal.signal_type
            in {
                LearningSignalType.INCIDENT,
                LearningSignalType.RELIABILITY,
                LearningSignalType.LOG,
            }
            and severity_rank(signal.severity) >= severity_rank(Severity.MEDIUM)
        ]

        if len(relevant) < policy.min_signals_for_insight:
            return []

        subjects = _affected_subjects(relevant)

        insight_id = deterministic_id(
            "learning_insight_incident",
            {
                "subjects": subjects,
                "hour": _hour_bucket(relevant[0].timestamp),
                "signal_ids": sorted(signal.id or "" for signal in relevant),
            },
        )

        severity = _max_severity(relevant)

        confidence = min(1.0, 0.5 + (0.1 * len(relevant)))

        return [
            LearningInsight(
                id=insight_id,
                title="Reliability incident detected",
                description=(
                    "Operational signals indicate a reliability incident or "
                    "service degradation."
                ),
                affected_subjects=subjects,
                signal_ids=[signal.id or "" for signal in relevant],
                objectives=[
                    "reliability",
                    "operational_resilience",
                ],
                severity=severity,
                confidence=round(confidence, 4),
                recommendations=[
                    "Investigate incident root cause.",
                    "Strengthen reliability controls.",
                    "Verify rollback and recovery readiness.",
                ],
                created_at=utcnow().isoformat(),
            )
        ]


class PerformanceAnalyzer:
    """Detects performance degradation."""

    def analyze(
        self,
        signals: List[LearningSignal],
        policy: LearningPolicy,
    ) -> List[LearningInsight]:
        relevant = [
            signal
            for signal in signals
            if signal.signal_type == LearningSignalType.PERFORMANCE
            and (
                (signal.metric and "latency" in signal.metric.lower())
                or signal.value >= policy.latency_threshold_ms
            )
        ]

        if len(relevant) < policy.min_signals_for_insight:
            return []

        subjects = _affected_subjects(relevant)

        insight_id = deterministic_id(
            "learning_insight_performance",
            {
                "subjects": subjects,
                "hour": _hour_bucket(relevant[0].timestamp),
                "signal_ids": sorted(signal.id or "" for signal in relevant),
            },
        )

        severity = _max_severity(relevant)

        if severity == Severity.INFO:
            severity = Severity.MEDIUM

        confidence = min(1.0, 0.5 + (0.1 * len(relevant)))

        return [
            LearningInsight(
                id=insight_id,
                title="Performance degradation detected",
                description=(
                    "Latency or performance metrics exceed expected thresholds."
                ),
                affected_subjects=subjects,
                signal_ids=[signal.id or "" for signal in relevant],
                objectives=[
                    "performance_efficiency",
                ],
                severity=severity,
                confidence=round(confidence, 4),
                recommendations=[
                    "Profile slow operations.",
                    "Review caching and query efficiency.",
                    "Evaluate scaling and backpressure controls.",
                ],
                created_at=utcnow().isoformat(),
            )
        ]


class CostAnalyzer:
    """Detects cost pressure or anomalies."""

    def analyze(
        self,
        signals: List[LearningSignal],
        policy: LearningPolicy,
    ) -> List[LearningInsight]:
        relevant = [
            signal
            for signal in signals
            if signal.signal_type == LearningSignalType.COST
            and (
                signal.value >= policy.monthly_cost_threshold
                or severity_rank(signal.severity)
                >= severity_rank(Severity.HIGH)
                or signal.labels.get("cost_anomaly") == "true"
            )
        ]

        if len(relevant) < policy.min_signals_for_insight:
            return []

        subjects = _affected_subjects(relevant)

        insight_id = deterministic_id(
            "learning_insight_cost",
            {
                "subjects": subjects,
                "hour": _hour_bucket(relevant[0].timestamp),
                "signal_ids": sorted(signal.id or "" for signal in relevant),
            },
        )

        severity = _max_severity(relevant)

        if severity == Severity.INFO:
            severity = Severity.MEDIUM

        confidence = min(1.0, 0.5 + (0.1 * len(relevant)))

        return [
            LearningInsight(
                id=insight_id,
                title="Cost pressure detected",
                description=(
                    "Cost signals indicate abnormal spend or inefficiency."
                ),
                affected_subjects=subjects,
                signal_ids=[signal.id or "" for signal in relevant],
                objectives=[
                    "cost_efficiency",
                ],
                severity=severity,
                confidence=round(confidence, 4),
                recommendations=[
                    "Review infrastructure utilization.",
                    "Evaluate autoscaling and scheduling.",
                    "Identify unused or overprovisioned resources.",
                ],
                created_at=utcnow().isoformat(),
            )
        ]


class SecurityLearningAnalyzer:
    """Detects security learning signals."""

    def analyze(
        self,
        signals: List[LearningSignal],
        policy: LearningPolicy,
    ) -> List[LearningInsight]:
        relevant = [
            signal
            for signal in signals
            if signal.signal_type == LearningSignalType.SECURITY
            and severity_rank(signal.severity)
            >= severity_rank(Severity.MEDIUM)
        ]

        if len(relevant) < policy.min_signals_for_insight:
            return []

        subjects = _affected_subjects(relevant)

        insight_id = deterministic_id(
            "learning_insight_security",
            {
                "subjects": subjects,
                "hour": _hour_bucket(relevant[0].timestamp),
                "signal_ids": sorted(signal.id or "" for signal in relevant),
            },
        )

        severity = _max_severity(relevant)

        confidence = min(1.0, 0.6 + (0.1 * len(relevant)))

        return [
            LearningInsight(
                id=insight_id,
                title="Security concern detected",
                description=(
                    "Security findings or threat indicators require attention."
                ),
                affected_subjects=subjects,
                signal_ids=[signal.id or "" for signal in relevant],
                objectives=[
                    "security_posture",
                ],
                severity=severity,
                confidence=round(confidence, 4),
                recommendations=[
                    "Review security controls.",
                    "Verify least privilege and secrets hygiene.",
                    "Escalate critical findings through governance.",
                ],
                created_at=utcnow().isoformat(),
            )
        ]


class CustomerFeedbackAnalyzer:
    """Detects customer experience signals."""

    def analyze(
        self,
        signals: List[LearningSignal],
        policy: LearningPolicy,
    ) -> List[LearningInsight]:
        relevant = [
            signal
            for signal in signals
            if signal.signal_type == LearningSignalType.CUSTOMER_FEEDBACK
            and (
                signal.labels.get("sentiment") == "negative"
                or severity_rank(signal.severity)
                >= severity_rank(Severity.MEDIUM)
            )
        ]

        if len(relevant) < policy.min_signals_for_insight:
            return []

        subjects = _affected_subjects(relevant)

        insight_id = deterministic_id(
            "learning_insight_customer_feedback",
            {
                "subjects": subjects,
                "hour": _hour_bucket(relevant[0].timestamp),
                "signal_ids": sorted(signal.id or "" for signal in relevant),
            },
        )

        severity = _max_severity(relevant)

        if severity == Severity.INFO:
            severity = Severity.MEDIUM

        confidence = min(1.0, 0.4 + (0.1 * len(relevant)))

        return [
            LearningInsight(
                id=insight_id,
                title="Negative customer feedback detected",
                description=(
                    "Customer feedback indicates friction or unmet expectations."
                ),
                affected_subjects=subjects,
                signal_ids=[signal.id or "" for signal in relevant],
                objectives=[
                    "user_satisfaction",
                ],
                severity=severity,
                confidence=round(confidence, 4),
                recommendations=[
                    "Review onboarding and UX flows.",
                    "Correlate feedback with performance and reliability.",
                    "Prioritize product improvements.",
                ],
                created_at=utcnow().isoformat(),
            )
        ]
