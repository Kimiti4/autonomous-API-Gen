"""
Evolutionary fitness feedback integration engine.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from ..models import LearningInsight, Severity, severity_rank
from ..utils import deterministic_id, utcnow
from .gateway import EvolutionGateway, InMemoryEvolutionGateway
from .models import (
    EvolutionFeedbackBundle,
    EvolutionFeedbackPolicy,
    EvolutionSubmissionResult,
    FitnessFeedbackState,
    GenomeHint,
    IntegrationReport,
    ObjectivePressure,
)


OBJECTIVE_TO_GENOME = {
    "reliability": ("Reliability", "strengthen_reliability"),
    "operational_resilience": (
        "Observability",
        "strengthen_operational_resilience",
    ),
    "performance_efficiency": ("Performance", "improve_performance"),
    "security_posture": ("Security", "harden_security"),
    "cost_efficiency": ("Infrastructure", "optimize_cost"),
    "user_satisfaction": ("Frontend", "improve_user_experience"),
}


OBJECTIVE_ACTIONS = {
    "reliability": [
        "Investigate incident root causes.",
        "Strengthen retry, timeout, and circuit-breaker policies.",
    ],
    "operational_resilience": [
        "Improve observability and alerting.",
        "Verify rollback and recovery readiness.",
    ],
    "performance_efficiency": [
        "Profile slow operations.",
        "Evaluate caching, indexing, and scaling.",
    ],
    "security_posture": [
        "Harden authentication and authorization.",
        "Review secrets hygiene and least privilege.",
    ],
    "cost_efficiency": [
        "Review infrastructure utilization.",
        "Evaluate autoscaling and scheduling.",
    ],
    "user_satisfaction": [
        "Improve onboarding and UX flows.",
        "Correlate feedback with reliability and performance.",
    ],
}


class EvolutionFitnessIntegrationEngine:
    """Converts learning insights into evolutionary fitness feedback."""

    def __init__(
        self,
        learning_engine=None,
        analytics_engine=None,
        gateway: Optional[EvolutionGateway] = None,
        policy: Optional[EvolutionFeedbackPolicy] = None,
    ) -> None:
        self.learning_engine = learning_engine
        self.analytics_engine = analytics_engine
        self.gateway = gateway or InMemoryEvolutionGateway()
        self.policy = policy or EvolutionFeedbackPolicy()

        self.bundles: Dict[str, EvolutionFeedbackBundle] = {}
        self.submissions: Dict[str, EvolutionSubmissionResult] = {}

        self.fitness_states: Dict[str, FitnessFeedbackState] = {}

        self.processed_insight_ids: set[str] = set()

        self.last_bundle_id: Optional[str] = None

    # ------------------------------------------------------------------
    # Feedback generation
    # ------------------------------------------------------------------

    def generate_feedback(
        self,
        scope: str = "platform",
    ) -> EvolutionFeedbackBundle:
        insights = self._collect_insights()

        eligible_insights = [
            insight
            for insight in insights
            if insight.confidence >= self.policy.min_confidence
            and insight.id not in self.processed_insight_ids
        ]

        if not eligible_insights:
            bundle_id = deterministic_id(
                "evolution_feedback_bundle",
                {
                    "scope": scope,
                    "insight_ids": [],
                    "generated_at": utcnow().isoformat(),
                },
            )

            bundle = EvolutionFeedbackBundle(
                id=bundle_id,
                scope=scope,
                status="NO_ACTION",
            )

            self.bundles[bundle_id] = bundle
            self.last_bundle_id = bundle_id

            return bundle

        insight_ids = sorted(insight.id for insight in eligible_insights)

        bundle_id = deterministic_id(
            "evolution_feedback_bundle",
            {
                "scope": scope,
                "insight_ids": insight_ids,
            },
        )

        if (
            self.policy.duplicate_suppression
            and bundle_id in self.bundles
        ):
            return self.bundles[bundle_id]

        objective_pressures = self._objective_pressures(eligible_insights)

        filtered_pressures = {
            objective: pressure
            for objective, pressure in objective_pressures.items()
            if pressure.pressure >= self.policy.pressure_threshold
        }

        sorted_pressures = dict(
            sorted(
                filtered_pressures.items(),
                key=lambda item: item[1].pressure,
                reverse=True,
            )[: self.policy.max_pressures]
        )

        genome_hints = self._genome_hints(sorted_pressures)

        recommended_actions = self._recommended_actions(sorted_pressures)

        requires_governance = self._requires_governance(sorted_pressures)

        priority = self._priority(sorted_pressures)

        bundle = EvolutionFeedbackBundle(
            id=bundle_id,
            scope=scope,
            source_insight_ids=insight_ids,
            objective_pressures=sorted_pressures,
            genome_hints=genome_hints,
            recommended_actions=recommended_actions,
            priority=priority,
            requires_governance=requires_governance,
            status="GENERATED",
        )

        self.bundles[bundle_id] = bundle
        self.last_bundle_id = bundle_id

        self.fitness_states[scope] = FitnessFeedbackState(
            scope=scope,
            pressures=sorted_pressures,
            last_updated=utcnow().isoformat(),
        )

        # NOTE: insight ids are intentionally not marked as processed here.
        # Duplicate suppression is handled via the deterministic bundle-id
        # cache above, so re-running generation on the same insights returns
        # the existing bundle (see test_duplicate_suppression).

        return bundle

    # ------------------------------------------------------------------
    # Submission
    # ------------------------------------------------------------------

    def submit_feedback(
        self,
        bundle_id: Optional[str] = None,
    ) -> EvolutionSubmissionResult:
        bundle = self._get_bundle(bundle_id)

        if bundle.id in self.submissions:
            return self.submissions[bundle.id]

        result = self.gateway.submit_feedback(bundle)

        self.submissions[bundle.id] = result

        if result.status in {"ACCEPTED", "PENDING_GOVERNANCE"}:
            bundle.status = "SUBMITTED"
        else:
            bundle.status = "REJECTED"

        return result

    def sync(self, scope: str = "platform") -> IntegrationReport:
        bundle = self.generate_feedback(scope=scope)

        if bundle.status == "NO_ACTION":
            return IntegrationReport(
                generated_bundle_id=bundle.id,
                submission_id=None,
                status="NO_ACTION",
            )

        submission = self.submit_feedback(bundle.id)

        return IntegrationReport(
            generated_bundle_id=bundle.id,
            submission_id=submission.submission_id,
            status=submission.status,
        )

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_bundle(
        self,
        bundle_id: Optional[str] = None,
    ) -> EvolutionFeedbackBundle:
        return self._get_bundle(bundle_id)

    def get_submission(
        self,
        bundle_id: Optional[str] = None,
    ) -> Optional[EvolutionSubmissionResult]:
        bundle = self._get_bundle(bundle_id)

        return self.submissions.get(bundle.id)

    def fitness_state(self, scope: str = "platform") -> FitnessFeedbackState:
        return self.fitness_states.get(
            scope,
            FitnessFeedbackState(scope=scope),
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_bundle(
        self,
        bundle_id: Optional[str] = None,
    ) -> EvolutionFeedbackBundle:
        if bundle_id:
            bundle = self.bundles.get(bundle_id)

            if not bundle:
                raise KeyError(f"Feedback bundle not found: {bundle_id}")

            return bundle

        if self.last_bundle_id:
            bundle = self.bundles.get(self.last_bundle_id)

            if bundle:
                return bundle

        raise KeyError("No feedback bundle available.")

    def _collect_insights(self) -> List[LearningInsight]:
        insights: Dict[str, LearningInsight] = {}

        if self.analytics_engine and hasattr(self.analytics_engine, "insights"):
            for insight in self.analytics_engine.insights.values():
                insights[insight.id] = insight

        if self.learning_engine and hasattr(self.learning_engine, "insights"):
            for insight in self.learning_engine.insights.values():
                insights[insight.id] = insight

        return list(insights.values())

    def _objective_pressures(
        self,
        insights: List[LearningInsight],
    ) -> Dict[str, ObjectivePressure]:
        pressures: Dict[str, ObjectivePressure] = {}

        for insight in insights:
            severity_weight = severity_rank(insight.severity) / 4.0

            base_pressure = round(
                min(1.0, severity_weight * insight.confidence),
                4,
            )

            for objective in insight.objectives:
                existing = pressures.get(objective)

                evidence_refs = sorted(
                    set(insight.signal_ids)
                )

                if existing:
                    new_pressure = round(
                        min(
                            1.0,
                            existing.pressure + (base_pressure * 0.25),
                        ),
                        4,
                    )

                    severity = (
                        insight.severity.value
                        if severity_rank(insight.severity)
                        > severity_rank(Severity(existing.severity))
                        else existing.severity
                    )

                    pressures[objective] = ObjectivePressure(
                        objective=objective,
                        pressure=new_pressure,
                        severity=severity,
                        confidence=max(
                            existing.confidence,
                            insight.confidence,
                        ),
                        evidence_refs=sorted(
                            set(existing.evidence_refs + evidence_refs)
                        ),
                        updated_at=utcnow().isoformat(),
                    )
                else:
                    pressures[objective] = ObjectivePressure(
                        objective=objective,
                        pressure=base_pressure,
                        severity=insight.severity.value,
                        confidence=insight.confidence,
                        evidence_refs=evidence_refs,
                        updated_at=utcnow().isoformat(),
                    )

        return pressures

    def _genome_hints(
        self,
        pressures: Dict[str, ObjectivePressure],
    ) -> List[GenomeHint]:
        hints: List[GenomeHint] = []

        for objective, pressure in pressures.items():
            hint = OBJECTIVE_TO_GENOME.get(objective)

            if not hint:
                continue

            chromosome_family, gene_id = hint

            priority = self._pressure_priority(pressure.pressure)

            hints.append(
                GenomeHint(
                    chromosome_family=chromosome_family,
                    gene_id=gene_id,
                    action=gene_id,
                    priority=priority,
                    rationale=(
                        f"Operational learning indicates pressure on "
                        f"{objective} with pressure {pressure.pressure}."
                    ),
                    evidence_refs=pressure.evidence_refs,
                )
            )

        return hints

    def _recommended_actions(
        self,
        pressures: Dict[str, ObjectivePressure],
    ) -> List[str]:
        actions: List[str] = []

        for objective in pressures.keys():
            actions.extend(OBJECTIVE_ACTIONS.get(objective, []))

        return sorted(set(actions))

    def _requires_governance(
        self,
        pressures: Dict[str, ObjectivePressure],
    ) -> bool:
        for pressure in pressures.values():
            if (
                pressure.objective == "security_posture"
                and pressure.severity == "CRITICAL"
                and self.policy.critical_security_requires_governance
            ):
                return True

            if (
                pressure.pressure >= self.policy.high_pressure_threshold
                and self.policy.high_pressure_requires_governance
            ):
                return True

        return False

    def _priority(self, pressures: Dict[str, ObjectivePressure]) -> str:
        max_pressure = max(
            (pressure.pressure for pressure in pressures.values()),
            default=0.0,
        )

        return self._pressure_priority(max_pressure)

    def _pressure_priority(self, pressure: float) -> str:
        if pressure >= self.policy.high_pressure_threshold:
            return "HIGH"

        if pressure >= self.policy.pressure_threshold * 2:
            return "MEDIUM"

        return "LOW"
