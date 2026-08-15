"""
Architecture Feedback Compiler.

This compiler converts learning insights into an ISR-compatible feedback
bundle for the Evolution Engine.

It does not mutate the ISR directly.
"""

from __future__ import annotations

from typing import List

from .models import (
    ArchitectureFeedbackBundle,
    FitnessUpdate,
    GenomeRefinementHint,
    LearningInsight,
    LearningRecommendation,
    Severity,
)
from .utils import deterministic_id, utcnow


class ArchitectureFeedbackCompiler:
    """Compiles learning output into governed architecture feedback."""

    def compile(
        self,
        scope: str,
        insights: List[LearningInsight],
        recommendations: List[LearningRecommendation],
        fitness_updates: List[FitnessUpdate],
    ) -> ArchitectureFeedbackBundle:
        signal_ids: List[str] = []

        for insight in insights:
            signal_ids.extend(insight.signal_ids)

        genome_hints: List[GenomeRefinementHint] = []

        for recommendation in recommendations:
            genome_hints.append(
                GenomeRefinementHint(
                    chromosome_family=recommendation.chromosome_family,
                    gene_id=recommendation.gene_id,
                    action=recommendation.action,
                    priority=recommendation.priority,
                    rationale=recommendation.rationale,
                    evidence_refs=recommendation.evidence_refs,
                )
            )

        governance_required = any(
            recommendation.requires_governance
            for recommendation in recommendations
        ) or any(
            insight.severity == Severity.CRITICAL
            for insight in insights
        )

        bundle_id = deterministic_id(
            "architecture_feedback_bundle",
            {
                "scope": scope,
                "insight_ids": sorted(insight.id for insight in insights),
                "generated_at": utcnow().isoformat(),
            },
        )

        return ArchitectureFeedbackBundle(
            id=bundle_id,
            scope=scope,
            generated_at=utcnow().isoformat(),
            signal_ids=sorted(set(signal_ids)),
            insight_ids=[insight.id for insight in insights],
            fitness_updates=fitness_updates,
            genome_hints=genome_hints,
            recommendations=recommendations,
            governance_required=governance_required,
            status="DRAFT",
        )
