"""
Platform Fitness.

Evaluates how well the PLATFORM is performing (not user software).
Platform fitness is measured across multiple dimensions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass(frozen=True)
class PlatformFitness:
    evolution_success_rate: float = 0.0
    mutation_efficiency: float = 0.0
    diversity_maintenance: float = 0.0
    convergence_speed: float = 0.0
    compilation_success_rate: float = 0.0
    compilation_speed: float = 0.0
    artifact_quality: float = 0.0
    verification_accuracy: float = 0.0
    false_positive_rate: float = 0.0
    false_negative_rate: float = 0.0
    deployment_success_rate: float = 0.0
    rollback_rate: float = 0.0
    mean_time_to_deploy: float = 0.0
    system_availability: float = 0.0
    incident_rate: float = 0.0
    mean_time_to_recovery: float = 0.0
    knowledge_utilization: float = 0.0
    recommendation_accuracy: float = 0.0
    pattern_discovery_rate: float = 0.0
    consensus_rate: float = 0.0
    arbitration_rate: float = 0.0
    proposal_quality: float = 0.0
    throughput: float = 0.0
    resource_efficiency: float = 0.0
    end_to_latency: float = 0.0

    @property
    def composite_score(self) -> float:
        weights = {
            "evolution": 0.20, "compilation": 0.10, "verification": 0.10,
            "deployment": 0.15, "operational": 0.15, "knowledge": 0.10,
            "agent": 0.10, "performance": 0.10,
        }
        evolution = (
            self.evolution_success_rate * 0.3 + self.mutation_efficiency * 0.3
            + self.diversity_maintenance * 0.2 + self.convergence_speed * 0.2
        )
        compilation = (
            self.compilation_success_rate * 0.5 + self.compilation_speed * 0.2
            + self.artifact_quality * 0.3
        )
        verification = (
            self.verification_accuracy * 0.6
            + (1.0 - self.false_positive_rate) * 0.2
            + (1.0 - self.false_negative_rate) * 0.2
        )
        deployment = (
            self.deployment_success_rate * 0.5
            + (1.0 - self.rollback_rate) * 0.3 + self.mean_time_to_deploy * 0.2
        )
        operational = (
            self.system_availability * 0.4
            + (1.0 - self.incident_rate) * 0.3 + self.mean_time_to_recovery * 0.3
        )
        knowledge = (
            self.knowledge_utilization * 0.3
            + self.recommendation_accuracy * 0.4 + self.pattern_discovery_rate * 0.3
        )
        agent = (
            self.consensus_rate * 0.4
            + (1.0 - self.arbitration_rate) * 0.3 + self.proposal_quality * 0.3
        )
        performance = (
            self.throughput * 0.3 + self.resource_efficiency * 0.4
            + self.end_to_latency * 0.3
        )
        return (
            evolution * weights["evolution"] + compilation * weights["compilation"]
            + verification * weights["verification"] + deployment * weights["deployment"]
            + operational * weights["operational"] + knowledge * weights["knowledge"]
            + agent * weights["agent"] + performance * weights["performance"]
        )

    def to_dict(self) -> dict[str, float]:
        return {
            "evolution_success_rate": self.evolution_success_rate,
            "mutation_efficiency": self.mutation_efficiency,
            "diversity_maintenance": self.diversity_maintenance,
            "convergence_speed": self.convergence_speed,
            "compilation_success_rate": self.compilation_success_rate,
            "compilation_speed": self.compilation_speed,
            "artifact_quality": self.artifact_quality,
            "verification_accuracy": self.verification_accuracy,
            "false_positive_rate": self.false_positive_rate,
            "false_negative_rate": self.false_negative_rate,
            "deployment_success_rate": self.deployment_success_rate,
            "rollback_rate": self.rollback_rate,
            "mean_time_to_deploy": self.mean_time_to_deploy,
            "system_availability": self.system_availability,
            "incident_rate": self.incident_rate,
            "mean_time_to_recovery": self.mean_time_to_recovery,
            "knowledge_utilization": self.knowledge_utilization,
            "recommendation_accuracy": self.recommendation_accuracy,
            "pattern_discovery_rate": self.pattern_discovery_rate,
            "consensus_rate": self.consensus_rate,
            "arbitration_rate": self.arbitration_rate,
            "proposal_quality": self.proposal_quality,
            "throughput": self.throughput,
            "resource_efficiency": self.resource_efficiency,
            "end_to_latency": self.end_to_latency,
            "composite_score": self.composite_score,
        }


class PlatformFitnessEvaluator:
    def __init__(self) -> None:
        self._history: list[PlatformFitness] = []

    def evaluate(self, metrics: dict[str, Any]) -> PlatformFitness:
        fitness = PlatformFitness(
            evolution_success_rate=metrics.get("evolution_success_rate", 0.0),
            mutation_efficiency=metrics.get("mutation_efficiency", 0.0),
            diversity_maintenance=metrics.get("diversity_maintenance", 0.0),
            convergence_speed=metrics.get("convergence_speed", 0.0),
            compilation_success_rate=metrics.get("compilation_success_rate", 0.0),
            compilation_speed=metrics.get("compilation_speed", 0.0),
            artifact_quality=metrics.get("artifact_quality", 0.0),
            verification_accuracy=metrics.get("verification_accuracy", 0.0),
            false_positive_rate=metrics.get("false_positive_rate", 0.0),
            false_negative_rate=metrics.get("false_negative_rate", 0.0),
            deployment_success_rate=metrics.get("deployment_success_rate", 0.0),
            rollback_rate=metrics.get("rollback_rate", 0.0),
            mean_time_to_deploy=metrics.get("mean_time_to_deploy", 0.0),
            system_availability=metrics.get("system_availability", 0.0),
            incident_rate=metrics.get("incident_rate", 0.0),
            mean_time_to_recovery=metrics.get("mean_time_to_recovery", 0.0),
            knowledge_utilization=metrics.get("knowledge_utilization", 0.0),
            recommendation_accuracy=metrics.get("recommendation_accuracy", 0.0),
            pattern_discovery_rate=metrics.get("pattern_discovery_rate", 0.0),
            consensus_rate=metrics.get("consensus_rate", 0.0),
            arbitration_rate=metrics.get("arbitration_rate", 0.0),
            proposal_quality=metrics.get("proposal_quality", 0.0),
            throughput=metrics.get("throughput", 0.0),
            resource_efficiency=metrics.get("resource_efficiency", 0.0),
            end_to_latency=metrics.get("end_to_latency", 0.0),
        )
        self._history.append(fitness)
        return fitness

    @property
    def history(self) -> list[PlatformFitness]:
        return list(self._history)

    @property
    def latest(self) -> Optional[PlatformFitness]:
        return self._history[-1] if self._history else None

    def compute_trend(self, dimension: str, window: int = 10) -> float:
        if len(self._history) < 2:
            return 0.0
        recent = self._history[-window:]
        values = [getattr(f, dimension, 0.0) for f in recent]
        if len(values) < 2:
            return 0.0
        n = len(values)
        x_mean = (n - 1) / 2.0
        y_mean = sum(values) / n
        numerator = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
        denominator = sum((i - x_mean) ** 2 for i in range(n))
        return numerator / denominator if denominator != 0 else 0.0
