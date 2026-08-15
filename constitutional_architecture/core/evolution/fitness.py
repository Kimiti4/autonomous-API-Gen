from __future__ import annotations

from typing import Any, Dict, List, Optional

from constitutional_architecture.core.models.genome import (
    APIDesign, ApplicationArchitecture, ArchitectureGenome, DataArchitecture,
    DeploymentTopology, IntegrationArchitecture, ObservabilityStrategy,
    SecurityArchitecture, StateManagement,
)
from constitutional_architecture.core.models.intent import QualityAttribute


SCORING_MAP: Dict[QualityAttribute, Dict[str, Any]] = {
    QualityAttribute.SCALABILITY: {
        "weights": {
            ApplicationArchitecture.MICROSERVICES: 1.0,
            ApplicationArchitecture.EVENT_DRIVEN: 0.9,
            ApplicationArchitecture.CQRS: 0.8,
            ApplicationArchitecture.SOA: 0.7,
            ApplicationArchitecture.MODULAR_MONOLITH: 0.5,
            ApplicationArchitecture.LAMBDA: 0.9,
            ApplicationArchitecture.MONOLITHIC: 0.1,
            ApplicationArchitecture.P2P: 0.6,
        },
        "data_weights": {
            DataArchitecture.DATABASE_PER_SERVICE: 1.0,
            DataArchitecture.DATA_MESH: 0.9,
            DataArchitecture.POLYGLOT_PERSISTENCE: 0.8,
            DataArchitecture.EVENT_SOURCING: 0.7,
            DataArchitecture.CQRS_SEGREGATION: 0.7,
            DataArchitecture.DATA_LAKE: 0.5,
            DataArchitecture.SINGLE_DATABASE: 0.2,
        },
        "deployment_weights": {
            DeploymentTopology.MULTI_REGION: 1.0,
            DeploymentTopology.EDGE: 0.9,
            DeploymentTopology.HYBRID: 0.8,
            DeploymentTopology.SINGLE_REGION: 0.3,
            DeploymentTopology.ON_PREM: 0.2,
        },
        "consistency_penalty": True,
    },
    QualityAttribute.SECURITY: {
        "weights": {
            SecurityArchitecture.ZERO_TRUST: 1.0,
            SecurityArchitecture.DEFENSE_IN_DEPTH: 0.9,
            SecurityArchitecture.JIT_ACCESS: 0.8,
            SecurityArchitecture.PERIMETER: 0.3,
        },
        "durability_target": 0.999,
    },
    QualityAttribute.PERFORMANCE: {
        "weights": {
            APIDesign.GRPC: 1.0,
            APIDesign.REST: 0.6,
            APIDesign.GRAPHQL: 0.5,
            APIDesign.EVENT_STREAM: 0.7,
            APIDesign.HYBRID: 0.8,
        },
        "latency_target": 100.0,
    },
    QualityAttribute.MAINTAINABILITY: {
        "weights": {
            ApplicationArchitecture.MODULAR_MONOLITH: 1.0,
            ApplicationArchitecture.MONOLITHIC: 0.9,
            ApplicationArchitecture.SOA: 0.7,
            ApplicationArchitecture.MICROSERVICES: 0.5,
            ApplicationArchitecture.EVENT_DRIVEN: 0.4,
            ApplicationArchitecture.CQRS: 0.3,
            ApplicationArchitecture.LAMBDA: 0.3,
            ApplicationArchitecture.P2P: 0.2,
        },
        "integration_weights": {
            IntegrationArchitecture.API_GATEWAY: 1.0,
            IntegrationArchitecture.POINT_TO_POINT: 0.7,
            IntegrationArchitecture.MESSAGE_BUS: 0.6,
            IntegrationArchitecture.EVENT_STORE: 0.4,
            IntegrationArchitecture.SERVICE_MESH: 0.5,
            IntegrationArchitecture.WEBHOOKS: 0.6,
        },
        "state_weights": {
            StateManagement.STATELESS: 1.0,
            StateManagement.EVENTUAL_CONSISTENCY: 0.7,
            StateManagement.DISTRIBUTED_CACHE: 0.6,
            StateManagement.SESSION_BASED: 0.4,
            StateManagement.STRONG_CONSISTENCY: 0.3,
        },
    },
    QualityAttribute.COST_EFFICIENCY: {
        "weights": {
            ApplicationArchitecture.MONOLITHIC: 1.0,
            ApplicationArchitecture.MODULAR_MONOLITH: 0.8,
            ApplicationArchitecture.SOA: 0.5,
            ApplicationArchitecture.MICROSERVICES: 0.3,
            ApplicationArchitecture.EVENT_DRIVEN: 0.3,
            ApplicationArchitecture.CQRS: 0.2,
            ApplicationArchitecture.LAMBDA: 0.7,
            ApplicationArchitecture.P2P: 0.4,
        },
        "deployment_weights": {
            DeploymentTopology.SINGLE_REGION: 1.0,
            DeploymentTopology.ON_PREM: 0.7,
            DeploymentTopology.HYBRID: 0.5,
            DeploymentTopology.MULTI_REGION: 0.3,
            DeploymentTopology.EDGE: 0.4,
        },
    },
    QualityAttribute.OBSERVABILITY: {
        "weights": {
            ObservabilityStrategy.FULL_OBSERVABILITY: 1.0,
            ObservabilityStrategy.DDA: 0.95,
            ObservabilityStrategy.METRICS_AND_LOGS: 0.6,
            ObservabilityStrategy.LOGS_ONLY: 0.2,
        },
    },
    QualityAttribute.RELIABILITY: {
        "durability_target": 0.9999,
        "fault_target": 0.999,
        "deployment_weights": {
            DeploymentTopology.MULTI_REGION: 1.0,
            DeploymentTopology.HYBRID: 0.8,
            DeploymentTopology.EDGE: 0.5,
            DeploymentTopology.SINGLE_REGION: 0.4,
            DeploymentTopology.ON_PREM: 0.6,
        },
    },
    QualityAttribute.AI_READINESS: {
        "weights": {
            DataArchitecture.DATA_LAKE: 1.0,
            DataArchitecture.DATA_MESH: 0.9,
            DataArchitecture.POLYGLOT_PERSISTENCE: 0.6,
            DataArchitecture.EVENT_SOURCING: 0.7,
            DataArchitecture.CQRS_SEGREGATION: 0.5,
            DataArchitecture.DATABASE_PER_SERVICE: 0.4,
            DataArchitecture.SINGLE_DATABASE: 0.2,
        },
        "observability_weights": {
            ObservabilityStrategy.DDA: 1.0,
            ObservabilityStrategy.FULL_OBSERVABILITY: 0.8,
            ObservabilityStrategy.METRICS_AND_LOGS: 0.4,
            ObservabilityStrategy.LOGS_ONLY: 0.1,
        },
    },
}


class SystemFitnessEvaluator:
    def evaluate(self, genome: ArchitectureGenome) -> Dict[QualityAttribute, float]:
        scores: Dict[QualityAttribute, float] = {}
        for qa in QualityAttribute:
            scores[qa] = self._score_quality(genome, qa)
        return scores

    def evaluate_weighted(self, genome: ArchitectureGenome,
                          weights: Dict[QualityAttribute, float]) -> float:
        scores = self.evaluate(genome)
        total = 0.0
        weight_sum = 0.0
        for qa, weight in weights.items():
            total += scores.get(qa, 0.0) * weight
            weight_sum += weight
        return total / weight_sum if weight_sum > 0 else 0.0

    def _score_quality(self, genome: ArchitectureGenome, qa: QualityAttribute) -> float:
        config = SCORING_MAP.get(qa)
        if config is None:
            return 0.5

        score = 0.0
        components = 0

        if "weights" in config:
            gene = genome.get_gene("app_arch")
            if gene is not None and gene in config["weights"]:
                score += config["weights"][gene]
                components += 1

        if "data_weights" in config:
            gene = genome.get_gene("data_arch")
            if gene is not None and gene in config["data_weights"]:
                score += config["data_weights"][gene]
                components += 1

        if "deployment_weights" in config:
            gene = genome.get_gene("deployment_topology")
            if gene is not None and gene in config["deployment_weights"]:
                score += config["deployment_weights"][gene]
                components += 1

        if "integration_weights" in config:
            gene = genome.get_gene("integration_arch")
            if gene is not None and gene in config["integration_weights"]:
                score += config["integration_weights"][gene]
                components += 1

        if "state_weights" in config:
            gene = genome.get_gene("state_management")
            if gene is not None and gene in config["state_weights"]:
                score += config["state_weights"][gene]
                components += 1

        if "observability_weights" in config:
            gene = genome.get_gene("observability_strategy")
            if gene is not None and gene in config["observability_weights"]:
                score += config["observability_weights"][gene]
                components += 1

        if "durability_target" in config:
            durability = genome.get_gene("data_durability")
            if durability is not None:
                target = config["durability_target"]
                durability_score = min(1.0, durability / target)
                score += durability_score
                components += 1

        if "fault_target" in config:
            fault = genome.get_gene("fault_tolerance")
            if fault is not None:
                target = config["fault_target"]
                fault_score = min(1.0, fault / target)
                score += fault_score
                components += 1

        if "latency_target" in config:
            latency = genome.get_gene("latency_tolerance_ms")
            if latency is not None:
                target = config["latency_target"]
                latency_score = max(0.0, 1.0 - (latency / target) * 0.5)
                score += latency_score
                components += 1

        app_arch = genome.get_gene("app_arch")
        if qa == QualityAttribute.SCALABILITY and config.get("consistency_penalty"):
            consistency = genome.get_gene("consistency_level")
            if consistency is not None and app_arch in (ApplicationArchitecture.MICROSERVICES, ApplicationArchitecture.EVENT_DRIVEN):
                score -= consistency * 0.3
                components += 1

        return max(0.0, min(1.0, score / max(1, components)))
