"""
Production feedback fitness integration.

This module converts production signals into evolutionary fitness evidence.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field

from .models import CandidateArchitecture, FitnessEvaluation, utcnow
from .utils import deterministic_id, iter_services


class FeedbackSignalType(str, Enum):
    """Type of production feedback signal."""

    INCIDENT = "INCIDENT"
    PERFORMANCE_OBSERVATION = "PERFORMANCE_OBSERVATION"
    COST_OBSERVATION = "COST_OBSERVATION"
    CUSTOMER_FEEDBACK = "CUSTOMER_FEEDBACK"
    SECURITY_FINDING = "SECURITY_FINDING"
    TELEMETRY_SIGNAL = "TELEMETRY_SIGNAL"
    USAGE_METRIC = "USAGE_METRIC"
    OPERATIONAL_POLICY_VIOLATION = "OPERATIONAL_POLICY_VIOLATION"


class FeedbackSeverity(str, Enum):
    """Severity of a production feedback signal."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


FEEDBACK_OBJECTIVES = (
    "reliability",
    "security_posture",
    "performance_efficiency",
    "cost_efficiency",
    "user_satisfaction",
    "operational_stability",
)


SEVERITY_WEIGHTS = {
    FeedbackSeverity.LOW: 0.25,
    FeedbackSeverity.MEDIUM: 0.50,
    FeedbackSeverity.HIGH: 0.80,
    FeedbackSeverity.CRITICAL: 1.00,
}


SIGNAL_TYPE_WEIGHTS = {
    FeedbackSignalType.INCIDENT: 1.00,
    FeedbackSignalType.SECURITY_FINDING: 0.95,
    FeedbackSignalType.OPERATIONAL_POLICY_VIOLATION: 0.85,
    FeedbackSignalType.PERFORMANCE_OBSERVATION: 0.75,
    FeedbackSignalType.CUSTOMER_FEEDBACK: 0.70,
    FeedbackSignalType.COST_OBSERVATION: 0.65,
    FeedbackSignalType.TELEMETRY_SIGNAL: 0.55,
    FeedbackSignalType.USAGE_METRIC: 0.40,
}


class ProductionSignal(BaseModel):
    """A production feedback signal."""

    id: Optional[str] = None

    signal_type: FeedbackSignalType
    severity: FeedbackSeverity = FeedbackSeverity.LOW

    source_id: str
    source_system: str = ""

    subject_refs: list[str] = Field(default_factory=list)
    domain_refs: list[str] = Field(default_factory=list)
    service_refs: list[str] = Field(default_factory=list)

    metric_name: Optional[str] = None
    value: Optional[float] = None
    unit: Optional[str] = None

    description: str = ""

    labels: dict[str, str] = Field(default_factory=dict)
    evidence_refs: list[str] = Field(default_factory=list)

    occurred_at: Optional[str] = None
    received_at: str = Field(
        default_factory=lambda: utcnow().isoformat()
    )


class FeedbackEvaluationContext(BaseModel):
    """Context used to correlate signals with a candidate architecture."""

    target_ref: Optional[str] = None
    extra_subject_refs: list[str] = Field(default_factory=list)


class GenomeRefinementRecommendation(BaseModel):
    """Recommendation to refine the architectural genome."""

    id: str

    objective: str
    chromosome_family: str
    gene_id: str

    action: str
    rationale: str

    target_refs: list[str] = Field(default_factory=list)
    signal_ids: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)


class FeedbackFitnessPolicy(BaseModel):
    """Policy for production feedback fitness evaluation."""

    enabled_signal_types: list[FeedbackSignalType] = Field(default_factory=list)

    lookback_days: Optional[int] = Field(default=90, ge=1)

    pressure_normalization: float = Field(default=3.0, gt=0.0)

    default_objective_value: float = Field(default=0.70, ge=0.0, le=1.0)

    min_objective_value: float = Field(default=0.20, ge=0.0, le=1.0)

    required_objectives: list[str] = Field(default_factory=list)

    require_feedback_evidence: bool = False
    min_feedback_signals: int = Field(default=1, ge=0)

    recommendation_threshold: float = Field(default=0.60, ge=0.0, le=1.0)


class FeedbackFitnessReport(BaseModel):
    """Fitness report derived from production feedback."""

    candidate_id: str

    matched_signal_count: int = 0
    signal_ids: list[str] = Field(default_factory=list)

    objectives: dict[str, float] = Field(default_factory=dict)
    constraints: dict[str, bool] = Field(default_factory=dict)

    passed: bool = False

    issues: list[str] = Field(default_factory=list)

    recommendations: list[GenomeRefinementRecommendation] = Field(
        default_factory=list
    )

    created_at: str


def _parse_timestamp(value: Optional[str]) -> Optional[datetime]:
    """Parse ISO-8601 timestamp safely."""

    if not value:
        return None

    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)

    return parsed


class InMemorySignalStore:
    """In-memory production signal store."""

    def __init__(self) -> None:
        self._signals: dict[str, ProductionSignal] = {}

    def add_signal(self, signal: ProductionSignal) -> ProductionSignal:
        """Add a signal to the store."""

        if not signal.id:
            signal.id = deterministic_id(
                "production_signal",
                signal.model_dump(mode="json"),
            )

        self._signals[signal.id] = signal

        return signal

    def list_signals(self, limit: int = 100) -> list[ProductionSignal]:
        """List stored signals."""

        return list(self._signals.values())[:limit]

    def query(
        self,
        service_names: Optional[set[str]] = None,
        domain_names: Optional[set[str]] = None,
        subject_refs: Optional[set[str]] = None,
        signal_types: Optional[set[FeedbackSignalType]] = None,
        since: Optional[datetime] = None,
        limit: int = 1000,
    ) -> list[ProductionSignal]:
        """Query signals correlated with services, domains, or subjects."""

        service_set = {
            str(service).lower()
            for service in service_names or set()
        }

        domain_set = {
            str(domain).lower()
            for domain in domain_names or set()
        }

        subject_set = {
            str(subject).lower()
            for subject in subject_refs or set()
        }

        type_set = signal_types or set()

        results: list[ProductionSignal] = []

        for signal in self._signals.values():
            if type_set and signal.signal_type not in type_set:
                continue

            if since:
                timestamp = _parse_timestamp(
                    signal.occurred_at or signal.received_at
                )

                if timestamp and timestamp < since:
                    continue

            matched = False

            if not service_set and not domain_set and not subject_set:
                matched = True

            if service_set and any(
                str(ref).lower() in service_set
                for ref in signal.service_refs
            ):
                matched = True

            if domain_set and any(
                str(ref).lower() in domain_set
                for ref in signal.domain_refs
            ):
                matched = True

            if subject_set and any(
                str(ref).lower() in subject_set
                for ref in signal.subject_refs
            ):
                matched = True

            if matched:
                results.append(signal)

            if len(results) >= limit:
                break

        return results


class GenomeRefinementAdvisor:
    """Advises genome refinement based on feedback fitness weaknesses."""

    OBJECTIVE_TO_CHROMOSOME_FAMILY = {
        "reliability": "Reliability",
        "security_posture": "Security",
        "performance_efficiency": "Performance",
        "cost_efficiency": "Infrastructure",
        "user_satisfaction": "Frontend",
        "operational_stability": "Observability",
    }

    def advise(
        self,
        report: FeedbackFitnessReport,
        candidate: CandidateArchitecture,
        context: FeedbackEvaluationContext,
        threshold: float,
    ) -> list[GenomeRefinementRecommendation]:
        recommendations: list[GenomeRefinementRecommendation] = []

        target_refs = [candidate.id]

        if context.target_ref:
            target_refs.append(context.target_ref)

        for objective, value in report.objectives.items():
            if value >= threshold:
                continue

            chromosome_family = self.OBJECTIVE_TO_CHROMOSOME_FAMILY.get(
                objective,
                "Governance",
            )

            recommendation_id = deterministic_id(
                "genome_refinement_recommendation",
                {
                    "candidate_id": candidate.id,
                    "objective": objective,
                    "chromosome_family": chromosome_family,
                    "value": value,
                },
            )

            recommendations.append(
                GenomeRefinementRecommendation(
                    id=recommendation_id,
                    objective=objective,
                    chromosome_family=chromosome_family,
                    gene_id=f"{objective}_gene",
                    action="STRENGTHEN",
                    rationale=(
                        f"Production feedback indicates weak {objective} "
                        f"with score {value:.2f}."
                    ),
                    target_refs=target_refs,
                    signal_ids=report.signal_ids,
                    evidence_refs=report.signal_ids,
                )
            )

        return recommendations


class FeedbackFitnessEvaluator:
    """Evaluates candidate architectures using production feedback."""

    def __init__(
        self,
        signal_store: InMemorySignalStore,
        policy: FeedbackFitnessPolicy,
    ) -> None:
        self.signal_store = signal_store
        self.policy = policy
        self.advisor = GenomeRefinementAdvisor()

    def evaluate_candidate(
        self,
        candidate: CandidateArchitecture,
        context: Optional[FeedbackEvaluationContext] = None,
    ) -> FeedbackFitnessReport:
        context = context or FeedbackEvaluationContext()

        service_names: set[str] = set()

        for service in iter_services(candidate.isr):
            service_name = service.get("name")

            if service_name:
                service_names.add(str(service_name))

        domain_names: set[str] = set()

        domains = candidate.isr.get("domains", []) or []

        for domain in domains:
            if isinstance(domain, dict):
                domain_name = domain.get("name")

                if domain_name:
                    domain_names.add(str(domain_name))

        subject_refs: set[str] = {
            candidate.id,
            candidate.proposal_id,
        }

        if context.target_ref:
            subject_refs.add(context.target_ref)

        subject_refs.update(context.extra_subject_refs)

        since: Optional[datetime] = None

        if self.policy.lookback_days:
            since = utcnow() - timedelta(days=self.policy.lookback_days)

        enabled_signal_types = (
            set(self.policy.enabled_signal_types)
            if self.policy.enabled_signal_types
            else None
        )

        signals = self.signal_store.query(
            service_names=service_names,
            domain_names=domain_names,
            subject_refs=subject_refs,
            signal_types=enabled_signal_types,
            since=since,
        )

        objective_pressures = {
            objective: 0.0
            for objective in FEEDBACK_OBJECTIVES
        }

        objective_counts = {
            objective: 0
            for objective in FEEDBACK_OBJECTIVES
        }

        critical_incident = False
        critical_security = False
        positive_customer_feedback = 0

        for signal in signals:
            severity_weight = SEVERITY_WEIGHTS.get(signal.severity, 0.5)
            signal_weight = SIGNAL_TYPE_WEIGHTS.get(signal.signal_type, 0.5)

            pressure = severity_weight * signal_weight

            if signal.signal_type == FeedbackSignalType.INCIDENT:
                objective_pressures["reliability"] += pressure
                objective_counts["reliability"] += 1

                objective_pressures["operational_stability"] += pressure * 0.8
                objective_counts["operational_stability"] += 1

                if signal.severity == FeedbackSeverity.CRITICAL:
                    critical_incident = True

            elif signal.signal_type == FeedbackSignalType.SECURITY_FINDING:
                objective_pressures["security_posture"] += pressure
                objective_counts["security_posture"] += 1

                if signal.severity == FeedbackSeverity.CRITICAL:
                    critical_security = True

            elif signal.signal_type == FeedbackSignalType.PERFORMANCE_OBSERVATION:
                objective_pressures["performance_efficiency"] += pressure
                objective_counts["performance_efficiency"] += 1

                objective_pressures["operational_stability"] += pressure * 0.5
                objective_counts["operational_stability"] += 1

            elif signal.signal_type == FeedbackSignalType.TELEMETRY_SIGNAL:
                objective_pressures["performance_efficiency"] += pressure * 0.6
                objective_counts["performance_efficiency"] += 1

                objective_pressures["operational_stability"] += pressure * 0.4
                objective_counts["operational_stability"] += 1

            elif signal.signal_type == FeedbackSignalType.COST_OBSERVATION:
                objective_pressures["cost_efficiency"] += pressure
                objective_counts["cost_efficiency"] += 1

            elif signal.signal_type == FeedbackSignalType.CUSTOMER_FEEDBACK:
                objective_counts["user_satisfaction"] += 1

                sentiment = str(signal.labels.get("sentiment", "")).lower()

                if sentiment == "positive":
                    positive_customer_feedback += 1
                else:
                    objective_pressures["user_satisfaction"] += pressure

            elif signal.signal_type == FeedbackSignalType.OPERATIONAL_POLICY_VIOLATION:
                objective_pressures["reliability"] += pressure * 0.8
                objective_counts["reliability"] += 1

                objective_pressures["operational_stability"] += pressure * 0.8
                objective_counts["operational_stability"] += 1

        objectives: dict[str, float] = {}

        for objective in FEEDBACK_OBJECTIVES:
            if objective_counts[objective] == 0:
                objectives[objective] = self.policy.default_objective_value
                continue

            value = max(
                0.0,
                1.0
                - (
                    objective_pressures[objective]
                    / self.policy.pressure_normalization
                ),
            )

            if objective == "user_satisfaction":
                value = min(1.0, value + (positive_customer_feedback * 0.05))

            objectives[objective] = round(value, 4)

        constraints: dict[str, bool] = {
            "feedback_configuration_valid": True,
            "no_critical_incidents": not critical_incident,
            "no_critical_security_findings": not critical_security,
        }

        if self.policy.require_feedback_evidence:
            constraints["sufficient_feedback_evidence"] = (
                len(signals) >= self.policy.min_feedback_signals
            )

        issues: list[str] = []

        if critical_incident:
            issues.append("Critical production incident detected.")

        if critical_security:
            issues.append("Critical security finding detected.")

        for objective, value in objectives.items():
            if value < self.policy.min_objective_value:
                issues.append(
                    f"Feedback objective below minimum threshold: {objective}"
                )

        required_objective_passed = all(
            objectives.get(objective_name, 0.0)
            >= self.policy.min_objective_value
            for objective_name in self.policy.required_objectives
            if objective_name in objectives
        )

        passed = all(constraints.values()) and required_objective_passed

        report = FeedbackFitnessReport(
            candidate_id=candidate.id,
            matched_signal_count=len(signals),
            signal_ids=[signal.id for signal in signals if signal.id],
            objectives=objectives,
            constraints=constraints,
            passed=passed,
            issues=issues,
            recommendations=[],
            created_at=utcnow().isoformat(),
        )

        report.recommendations = self.advisor.advise(
            report=report,
            candidate=candidate,
            context=context,
            threshold=self.policy.recommendation_threshold,
        )

        return report
