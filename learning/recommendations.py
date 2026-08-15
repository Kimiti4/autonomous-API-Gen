"""
Learning recommendation and fitness update engine.
"""

from __future__ import annotations

from typing import Dict, List

from .models import (
    FitnessUpdate,
    LearningInsight,
    LearningPolicy,
    LearningRecommendation,
    Severity,
    severity_rank,
)
from .utils import deterministic_id, utcnow


OBJECTIVE_TO_HINT = {
    "reliability": ("Reliability", "strengthen_reliability"),
    "operational_resilience": ("Observability", "strengthen_operational_resilience"),
    "performance_efficiency": ("Performance", "improve_performance"),
    "security_posture": ("Security", "harden_security"),
    "cost_efficiency": ("Infrastructure", "optimize_cost"),
    "user_satisfaction": ("Frontend", "improve_user_experience"),
}


SEVERITY_PRESSURE = {
    Severity.INFO: 0.0,
    Severity.LOW: 0.05,
    Severity.MEDIUM: 0.10,
    Severity.HIGH: 0.20,
    Severity.CRITICAL: 0.35,
}


def _priority_from_severity(severity: Severity) -> str:
    rank = severity_rank(severity)

    if rank >= severity_rank(Severity.HIGH):
        return "HIGH"

    if rank == severity_rank(Severity.MEDIUM):
        return "MEDIUM"

    return "LOW"


class LearningRecommendationEngine:
    """Generates governed recommendations from insights."""

    def __init__(self, policy: LearningPolicy | None = None) -> None:
        self.policy = policy or LearningPolicy()

    def from_insights(
        self,
        insights: List[LearningInsight],
    ) -> List[LearningRecommendation]:
        recommendations: Dict[str, LearningRecommendation] = {}

        for insight in insights:
            subject = (
                insight.affected_subjects[0]
                if insight.affected_subjects
                else "platform"
            )

            for objective in insight.objectives:
                hint = OBJECTIVE_TO_HINT.get(objective)

                if not hint:
                    continue

                chromosome_family, gene_id = hint

                key = f"{subject}:{objective}"

                if key in recommendations:
                    continue

                requires_governance = False

                if (
                    objective == "security_posture"
                    and self.policy.critical_security_requires_governance
                    and insight.severity == Severity.CRITICAL
                ):
                    requires_governance = True

                if (
                    self.policy.high_severity_requires_governance
                    and severity_rank(insight.severity)
                    >= severity_rank(Severity.HIGH)
                ):
                    requires_governance = True

                recommendations[key] = LearningRecommendation(
                    id=deterministic_id(
                        "learning_recommendation",
                        {
                            "subject_ref": subject,
                            "objective": objective,
                            "action": gene_id,
                        },
                    ),
                    subject_ref=subject,
                    action=gene_id,
                    chromosome_family=chromosome_family,
                    gene_id=gene_id,
                    priority=_priority_from_severity(insight.severity),
                    rationale=insight.description,
                    evidence_refs=insight.signal_ids,
                    requires_governance=requires_governance,
                )

        return list(recommendations.values())


class FitnessUpdater:
    """Generates fitness pressure updates from insights."""

    def from_insights(
        self,
        insights: List[LearningInsight],
    ) -> List[FitnessUpdate]:
        updates_by_subject: Dict[str, FitnessUpdate] = {}

        for insight in insights:
            subject = (
                insight.affected_subjects[0]
                if insight.affected_subjects
                else "platform"
            )

            if subject not in updates_by_subject:
                updates_by_subject[subject] = FitnessUpdate(
                    id=deterministic_id(
                        "fitness_update",
                        {
                            "subject_ref": subject,
                        },
                    ),
                    subject_ref=subject,
                    objective_pressures={},
                    constraints={},
                    rationale="Operational learning evidence.",
                    evidence_refs=[],
                    created_at=utcnow().isoformat(),
                )

            update = updates_by_subject[subject]

            pressure = SEVERITY_PRESSURE.get(insight.severity, 0.0)
            pressure = round(pressure * insight.confidence, 4)

            for objective in insight.objectives:
                existing = update.objective_pressures.get(objective, 0.0)

                update.objective_pressures[objective] = max(existing, pressure)

            update.evidence_refs.extend(insight.signal_ids)

            if "security_posture" in insight.objectives:
                update.constraints["security_review_required"] = True

            if "reliability" in insight.objectives:
                update.constraints["reliability_regression_risk"] = True

            if "cost_efficiency" in insight.objectives:
                update.constraints["cost_review_required"] = True

        return list(updates_by_subject.values())
