"""
Signal correlation and incident clustering.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List, Set, Tuple

from ..models import LearningSignal, LearningSignalType, Severity, severity_rank
from ..utils import deterministic_id, utcnow
from .models import (
    AnomalyDetectionPolicy,
    AnomalyRecord,
    IncidentCluster,
    RootCauseCandidate,
    SignalCorrelation,
)


SIGNAL_TYPE_OBJECTIVES = {
    LearningSignalType.PERFORMANCE: ["performance_efficiency"],
    LearningSignalType.INCIDENT: [
        "reliability",
        "operational_resilience",
    ],
    LearningSignalType.RELIABILITY: ["reliability"],
    LearningSignalType.SECURITY: ["security_posture"],
    LearningSignalType.COST: ["cost_efficiency"],
    LearningSignalType.CUSTOMER_FEEDBACK: ["user_satisfaction"],
    LearningSignalType.USAGE: ["user_satisfaction"],
    LearningSignalType.LOG: ["operational_resilience"],
    LearningSignalType.TRACE: ["performance_efficiency"],
}


SIGNAL_TYPE_ROOT_CAUSE_WEIGHT = {
    LearningSignalType.INCIDENT: 1.0,
    LearningSignalType.SECURITY: 0.95,
    LearningSignalType.RELIABILITY: 0.90,
    LearningSignalType.PERFORMANCE: 0.70,
    LearningSignalType.COST: 0.60,
    LearningSignalType.CUSTOMER_FEEDBACK: 0.50,
    LearningSignalType.LOG: 0.55,
    LearningSignalType.TRACE: 0.55,
    LearningSignalType.USAGE: 0.35,
}


def parse_timestamp(value: str) -> datetime:
    """Parse ISO timestamp safely."""

    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return utcnow()

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)

    return parsed


class UnionFind:
    """Simple union-find structure for clustering."""

    def __init__(self, items: List[str]) -> None:
        self.parent = {item: item for item in items}

    def find(self, item: str) -> str:
        while self.parent[item] != item:
            self.parent[item] = self.parent[self.parent[item]]
            item = self.parent[item]

        return item

    def union(self, left: str, right: str) -> None:
        left_root = self.find(left)
        right_root = self.find(right)

        if left_root != right_root:
            self.parent[right_root] = left_root


class SignalCorrelationEngine:
    """Correlates signals and builds incident clusters."""

    def __init__(self, policy: AnomalyDetectionPolicy) -> None:
        self.policy = policy

    def correlate(
        self,
        signals: List[LearningSignal],
        anomalies: List[AnomalyRecord],
    ) -> Tuple[List[IncidentCluster], List[SignalCorrelation]]:
        anomaly_signal_ids = {
            anomaly.signal_id
            for anomaly in anomalies
        }

        candidate_signals = [
            signal
            for signal in signals
            if signal.id in anomaly_signal_ids
            or severity_rank(signal.severity)
            >= severity_rank(Severity.MEDIUM)
        ]

        if len(candidate_signals) < self.policy.min_cluster_signals:
            return [], []

        signal_by_id: Dict[str, LearningSignal] = {
            signal.id or "": signal
            for signal in candidate_signals
            if signal.id
        }

        signal_ids = list(signal_by_id.keys())

        union = UnionFind(signal_ids)

        correlations: List[SignalCorrelation] = []

        for index, left_id in enumerate(signal_ids):
            left = signal_by_id[left_id]

            for right_id in signal_ids[index + 1 :]:
                right = signal_by_id[right_id]

                score, reasons = self._correlation_score(left, right)

                if score < self.policy.correlation_threshold:
                    continue

                correlation_id = deterministic_id(
                    "signal_correlation",
                    {
                        "source_signal_id": left_id,
                        "target_signal_id": right_id,
                    },
                )

                correlations.append(
                    SignalCorrelation(
                        id=correlation_id,
                        source_signal_id=left_id,
                        target_signal_id=right_id,
                        score=round(score, 4),
                        reasons=reasons,
                    )
                )

                union.union(left_id, right_id)

        groups: Dict[str, List[str]] = {}

        for signal_id in signal_ids:
            root = union.find(signal_id)

            groups.setdefault(root, []).append(signal_id)

        clusters: List[IncidentCluster] = []

        for group_signal_ids in groups.values():
            if len(group_signal_ids) < self.policy.min_cluster_signals:
                continue

            cluster = self._build_cluster(
                group_signal_ids,
                signal_by_id,
                anomalies,
                correlations,
            )

            if cluster:
                clusters.append(cluster)

        return clusters, correlations

    def _correlation_score(
        self,
        left: LearningSignal,
        right: LearningSignal,
    ) -> Tuple[float, List[str]]:
        reasons: List[str] = []

        left_time = parse_timestamp(left.timestamp)
        right_time = parse_timestamp(right.timestamp)

        delta_minutes = abs((left_time - right_time).total_seconds()) / 60.0

        if delta_minutes > self.policy.cluster_window_minutes:
            return 0.0, []

        time_score = max(
            0.0,
            1.0 - (delta_minutes / self.policy.cluster_window_minutes),
        )

        subject_score, subject_reasons = self._subject_score(left, right)

        reasons.extend(subject_reasons)

        severity_similarity = (
            1.0
            - abs(severity_rank(left.severity) - severity_rank(right.severity)) / 4.0
        )

        type_bonus = 0.05 if left.signal_type == right.signal_type else 0.0

        score = (
            (0.50 * time_score)
            + (0.35 * subject_score)
            + (0.10 * severity_similarity)
            + type_bonus
        )

        if time_score > 0.75:
            reasons.append("Temporal proximity")

        if severity_similarity > 0.75:
            reasons.append("Similar severity")

        return min(1.0, score), reasons

    def _subject_score(
        self,
        left: LearningSignal,
        right: LearningSignal,
    ) -> Tuple[float, List[str]]:
        reasons: List[str] = []

        if left.subject_ref and left.subject_ref == right.subject_ref:
            reasons.append(f"Same subject: {left.subject_ref}")
            return 0.70, reasons

        left_service = left.labels.get("service")
        right_service = right.labels.get("service")

        if left_service and left_service == right_service:
            reasons.append(f"Same service label: {left_service}")
            return 0.55, reasons

        left_tokens = self._subject_tokens(left)
        right_tokens = self._subject_tokens(right)

        shared = left_tokens.intersection(right_tokens)

        if shared:
            reasons.append(f"Shared subject tokens: {', '.join(sorted(shared))}")
            return 0.35, reasons

        return 0.0, reasons

    def _subject_tokens(self, signal: LearningSignal) -> Set[str]:
        tokens: Set[str] = set()

        if signal.subject_ref:
            tokens.add(signal.subject_ref.lower())

        service = signal.labels.get("service")

        if service:
            tokens.add(str(service).lower())

        namespace = signal.labels.get("namespace")

        if namespace:
            tokens.add(str(namespace).lower())

        domain = signal.labels.get("domain")

        if domain:
            tokens.add(str(domain).lower())

        return tokens

    def _build_cluster(
        self,
        signal_ids: List[str],
        signal_by_id: Dict[str, LearningSignal],
        anomalies: List[AnomalyRecord],
        correlations: List[SignalCorrelation],
    ) -> IncidentCluster | None:
        signals = [
            signal_by_id[signal_id]
            for signal_id in signal_ids
            if signal_id in signal_by_id
        ]

        if len(signals) < self.policy.min_cluster_signals:
            return None

        anomaly_by_signal = {
            anomaly.signal_id: anomaly
            for anomaly in anomalies
        }

        cluster_anomaly_ids = [
            anomaly.id
            for signal_id in signal_ids
            if (anomaly := anomaly_by_signal.get(signal_id))
        ]

        affected_subjects = sorted(
            {
                signal.subject_ref
                for signal in signals
                if signal.subject_ref
            }
        )

        objectives: Set[str] = set()

        for signal in signals:
            objectives.update(
                SIGNAL_TYPE_OBJECTIVES.get(signal.signal_type, [])
            )

        max_severity = Severity.INFO

        for signal in signals:
            if severity_rank(signal.severity) > severity_rank(max_severity):
                max_severity = signal.severity

        relevant_correlations = [
            correlation
            for correlation in correlations
            if correlation.source_signal_id in signal_ids
            and correlation.target_signal_id in signal_ids
        ]

        if relevant_correlations:
            average_correlation = sum(
                correlation.score
                for correlation in relevant_correlations
            ) / len(relevant_correlations)
        else:
            average_correlation = 0.5

        density_bonus = min(0.2, (len(signals) - 2) * 0.05)

        confidence = min(1.0, average_correlation + density_bonus)

        cluster_id = deterministic_id(
            "incident_cluster",
            {
                "signal_ids": sorted(signal_ids),
            },
        )

        root_cause_candidates = self._root_cause_candidates(signals)

        return IncidentCluster(
            id=cluster_id,
            signal_ids=sorted(signal_ids),
            anomaly_ids=cluster_anomaly_ids,
            affected_subjects=affected_subjects,
            objectives=sorted(objectives),
            severity=max_severity,
            confidence=round(confidence, 4),
            root_cause_candidates=root_cause_candidates,
            created_at=utcnow().isoformat(),
        )

    def _root_cause_candidates(
        self,
        signals: List[LearningSignal],
    ) -> List[RootCauseCandidate]:
        if not signals:
            return []

        times = [parse_timestamp(signal.timestamp) for signal in signals]

        min_time = min(times)
        max_time = max(times)

        duration = (max_time - min_time).total_seconds()

        candidates: List[RootCauseCandidate] = []

        for signal in signals:
            signal_time = parse_timestamp(signal.timestamp)

            if duration <= 0:
                earliness = 1.0
            else:
                earliness = 1.0 - (
                    (signal_time - min_time).total_seconds() / duration
                )

            severity_score = severity_rank(signal.severity) / 4.0

            type_weight = SIGNAL_TYPE_ROOT_CAUSE_WEIGHT.get(
                signal.signal_type,
                0.35,
            )

            score = (
                (0.40 * severity_score)
                + (0.35 * type_weight)
                + (0.25 * earliness)
            )

            rationale = (
                f"{signal.signal_type.value} signal with severity "
                f"{signal.severity.value} at {signal.timestamp}."
            )

            candidates.append(
                RootCauseCandidate(
                    signal_id=signal.id or "",
                    subject_ref=signal.subject_ref,
                    signal_type=signal.signal_type.value,
                    severity=signal.severity,
                    score=round(score, 4),
                    rationale=rationale,
                )
            )

        candidates.sort(key=lambda candidate: candidate.score, reverse=True)

        return candidates[:3]
