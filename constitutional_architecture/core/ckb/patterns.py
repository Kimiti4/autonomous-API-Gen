from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from constitutional_architecture.core.models.genome import (
    APIDesign, ApplicationArchitecture, ArchitectureGenome, DataArchitecture,
    DeploymentTopology, IntegrationArchitecture, ObservabilityStrategy,
    SecurityArchitecture, StateManagement,
)
from constitutional_architecture.core.models.intent import (
    BusinessArchetype, QualityAttribute,
)


class ArchetypeProfile:
    def __init__(self, archetype: BusinessArchetype, genome: ArchitectureGenome,
                 quality_profile: Dict[str, float],
                 conflicting_patterns: Optional[List[str]] = None) -> None:
        self.archetype = archetype
        self.genome = genome
        self.quality_profile = quality_profile
        self.conflicting_patterns = conflicting_patterns or []


QUALITY_MODIFIERS: Dict[QualityAttribute, Dict[str, Any]] = {
    QualityAttribute.SCALABILITY: {
        "app_arch": ApplicationArchitecture.MICROSERVICES,
        "data_arch": DataArchitecture.DATABASE_PER_SERVICE,
        "deployment_topology": DeploymentTopology.MULTI_REGION,
        "consistency_level": 0.3,
        "latency_tolerance_ms": 500.0,
    },
    QualityAttribute.SECURITY: {
        "security_arch": SecurityArchitecture.ZERO_TRUST,
        "data_durability": 0.999999,
    },
    QualityAttribute.PERFORMANCE: {
        "app_arch": ApplicationArchitecture.MODULAR_MONOLITH,
        "api_design": APIDesign.GRPC,
        "latency_tolerance_ms": 50.0,
        "fault_tolerance": 0.999,
    },
    QualityAttribute.MAINTAINABILITY: {
        "app_arch": ApplicationArchitecture.MODULAR_MONOLITH,
        "integration_arch": IntegrationArchitecture.API_GATEWAY,
        "state_management": StateManagement.STATELESS,
    },
    QualityAttribute.OBSERVABILITY: {
        "observability_strategy": ObservabilityStrategy.FULL_OBSERVABILITY,
        "integration_arch": IntegrationArchitecture.SERVICE_MESH,
    },
    QualityAttribute.RELIABILITY: {
        "data_durability": 0.99999,
        "fault_tolerance": 0.9999,
        "deployment_topology": DeploymentTopology.MULTI_REGION,
    },
    QualityAttribute.COST_EFFICIENCY: {
        "app_arch": ApplicationArchitecture.MONOLITHIC,
        "deployment_topology": DeploymentTopology.SINGLE_REGION,
        "observability_strategy": ObservabilityStrategy.METRICS_AND_LOGS,
    },
    QualityAttribute.AI_READINESS: {
        "data_arch": DataArchitecture.DATA_LAKE,
        "integration_arch": IntegrationArchitecture.EVENT_STORE,
        "observability_strategy": ObservabilityStrategy.DDA,
    },
}


ARCHETYPE_DEFAULTS: Dict[BusinessArchetype, ArchetypeProfile] = {}


def _base_genome(
    app_arch: ApplicationArchitecture = ApplicationArchitecture.MODULAR_MONOLITH,
    data_arch: DataArchitecture = DataArchitecture.SINGLE_DATABASE,
    integration: IntegrationArchitecture = IntegrationArchitecture.API_GATEWAY,
    security: SecurityArchitecture = SecurityArchitecture.DEFENSE_IN_DEPTH,
    deployment: DeploymentTopology = DeploymentTopology.SINGLE_REGION,
    observability: ObservabilityStrategy = ObservabilityStrategy.METRICS_AND_LOGS,
    api: APIDesign = APIDesign.REST,
    state: StateManagement = StateManagement.EVENTUAL_CONSISTENCY,
    consistency: float = 0.7,
    latency: float = 200.0,
    durability: float = 0.999,
    fault: float = 0.99,
) -> ArchitectureGenome:
    g = ArchitectureGenome()
    g.set_gene("app_arch", app_arch)
    g.set_gene("data_arch", data_arch)
    g.set_gene("integration_arch", integration)
    g.set_gene("security_arch", security)
    g.set_gene("deployment_topology", deployment)
    g.set_gene("observability_strategy", observability)
    g.set_gene("api_design", api)
    g.set_gene("state_management", state)
    g.set_gene("consistency_level", consistency)
    g.set_gene("latency_tolerance_ms", latency)
    g.set_gene("data_durability", durability)
    g.set_gene("fault_tolerance", fault)
    return g


ARCHETYPE_DEFAULTS[BusinessArchetype.B2B_SAAS] = ArchetypeProfile(
    archetype=BusinessArchetype.B2B_SAAS,
    genome=_base_genome(
        app_arch=ApplicationArchitecture.MODULAR_MONOLITH,
        api=APIDesign.REST,
        security=SecurityArchitecture.DEFENSE_IN_DEPTH,
        observability=ObservabilityStrategy.FULL_OBSERVABILITY,
    ),
    quality_profile={"maintainability": 0.8, "security": 0.8, "scalability": 0.6, "cost_efficiency": 0.7},
    conflicting_patterns=["p2p_architecture", "event_sourcing"],
)

ARCHETYPE_DEFAULTS[BusinessArchetype.MARKETPLACE] = ArchetypeProfile(
    archetype=BusinessArchetype.MARKETPLACE,
    genome=_base_genome(
        app_arch=ApplicationArchitecture.EVENT_DRIVEN,
        data_arch=DataArchitecture.DATABASE_PER_SERVICE,
        integration=IntegrationArchitecture.MESSAGE_BUS,
        api=APIDesign.GRAPHQL,
        state=StateManagement.STRONG_CONSISTENCY,
        consistency=0.95,
        latency=100.0,
    ),
    quality_profile={"scalability": 0.9, "performance": 0.7, "reliability": 0.8, "cost_efficiency": 0.5},
    conflicting_patterns=["monolithic"],
)

ARCHETYPE_DEFAULTS[BusinessArchetype.E_COMMERCE] = ArchetypeProfile(
    archetype=BusinessArchetype.E_COMMERCE,
    genome=_base_genome(
        app_arch=ApplicationArchitecture.CQRS,
        data_arch=DataArchitecture.CQRS_SEGREGATION,
        api=APIDesign.REST,
        state=StateManagement.STRONG_CONSISTENCY,
        consistency=0.9,
        latency=50.0,
        deployment=DeploymentTopology.MULTI_REGION,
        durability=0.99999,
    ),
    quality_profile={"scalability": 0.8, "reliability": 0.9, "performance": 0.8, "security": 0.7},
    conflicting_patterns=["peer_to_peer", "logs_only"],
)

ARCHETYPE_DEFAULTS[BusinessArchetype.B2C_SAAS] = ArchetypeProfile(
    archetype=BusinessArchetype.B2C_SAAS,
    genome=_base_genome(
        app_arch=ApplicationArchitecture.MODULAR_MONOLITH,
        api=APIDesign.REST,
        deployment=DeploymentTopology.MULTI_REGION,
        latency=150.0,
        durability=0.999,
    ),
    quality_profile={"scalability": 0.8, "performance": 0.7, "cost_efficiency": 0.6, "observability": 0.7},
    conflicting_patterns=["event_sourcing"],
)

ARCHETYPE_DEFAULTS[BusinessArchetype.DATA_PLATFORM] = ArchetypeProfile(
    archetype=BusinessArchetype.DATA_PLATFORM,
    genome=_base_genome(
        app_arch=ApplicationArchitecture.EVENT_DRIVEN,
        data_arch=DataArchitecture.DATA_LAKE,
        integration=IntegrationArchitecture.EVENT_STORE,
        observability=ObservabilityStrategy.FULL_OBSERVABILITY,
        state=StateManagement.EVENTUAL_CONSISTENCY,
        consistency=0.4,
        latency=500.0,
        durability=0.9999,
    ),
    quality_profile={"scalability": 0.9, "ai_readiness": 0.8, "observability": 0.8, "cost_efficiency": 0.5},
    conflicting_patterns=["strong_consistency", "single_database"],
)

ARCHETYPE_DEFAULTS[BusinessArchetype.FINTECH] = ArchetypeProfile(
    archetype=BusinessArchetype.FINTECH,
    genome=_base_genome(
        app_arch=ApplicationArchitecture.MODULAR_MONOLITH,
        security=SecurityArchitecture.ZERO_TRUST,
        observability=ObservabilityStrategy.FULL_OBSERVABILITY,
        api=APIDesign.REST,
        state=StateManagement.STRONG_CONSISTENCY,
        consistency=0.99,
        latency=50.0,
        durability=0.999999,
        fault=0.9999,
    ),
    quality_profile={"security": 0.95, "reliability": 0.9, "compliance": 0.9, "performance": 0.7},
    conflicting_patterns=["eventual_consistency", "perimeter"],
)

ARCHETYPE_DEFAULTS[BusinessArchetype.HEALTHCARE] = ArchetypeProfile(
    archetype=BusinessArchetype.HEALTHCARE,
    genome=_base_genome(
        app_arch=ApplicationArchitecture.MODULAR_MONOLITH,
        security=SecurityArchitecture.ZERO_TRUST,
        observability=ObservabilityStrategy.FULL_OBSERVABILITY,
        state=StateManagement.STRONG_CONSISTENCY,
        consistency=0.99,
        latency=100.0,
        durability=0.999999,
        fault=0.9999,
    ),
    quality_profile={"security": 0.95, "reliability": 0.95, "compliance": 0.95, "maintainability": 0.6},
    conflicting_patterns=["eventual_consistency", "perimeter", "logs_only"],
)

ARCHETYPE_DEFAULTS[BusinessArchetype.IOT_SYSTEM] = ArchetypeProfile(
    archetype=BusinessArchetype.IOT_SYSTEM,
    genome=_base_genome(
        app_arch=ApplicationArchitecture.EVENT_DRIVEN,
        integration=IntegrationArchitecture.MESSAGE_BUS,
        deployment=DeploymentTopology.EDGE,
        api=APIDesign.EVENT_STREAM,
        state=StateManagement.EVENTUAL_CONSISTENCY,
        consistency=0.3,
        latency=50.0,
        durability=0.995,
    ),
    quality_profile={"performance": 0.9, "scalability": 0.7, "cost_efficiency": 0.6, "reliability": 0.7},
    conflicting_patterns=["monolithic", "strong_consistency"],
)


class CKBPatterns:
    def get_base_genome(self, archetype: BusinessArchetype) -> ArchitectureGenome:
        profile = ARCHETYPE_DEFAULTS.get(archetype)
        if profile is None:
            profile = ARCHETYPE_DEFAULTS.get(BusinessArchetype.B2B_SAAS)
        return profile.genome.clone()

    def apply_quality_modifiers(self, genome: ArchitectureGenome,
                                quality_priorities: Dict[QualityAttribute, float]) -> int:
        modifications = 0
        for qa, priority in quality_priorities.items():
            if priority >= 0.7 and qa in QUALITY_MODIFIERS:
                modifiers = QUALITY_MODIFIERS[qa]
                for gene_id, new_value in modifiers.items():
                    existing = genome.get_gene(gene_id)
                    if existing is not None and existing != new_value:
                        genome.set_gene(gene_id, new_value)
                        modifications += 1
        return modifications

    def get_quality_profile(self, archetype: BusinessArchetype) -> Dict[str, float]:
        profile = ARCHETYPE_DEFAULTS.get(archetype)
        if profile is None:
            profile = ARCHETYPE_DEFAULTS.get(BusinessArchetype.B2B_SAAS)
        return dict(profile.quality_profile)

    def get_conflicting_patterns(self, archetype: BusinessArchetype) -> List[str]:
        profile = ARCHETYPE_DEFAULTS.get(archetype)
        if profile is None:
            return []
        return list(profile.conflicting_patterns)

    def resolve_archetype_profile(self, archetype: BusinessArchetype) -> ArchetypeProfile:
        profile = ARCHETYPE_DEFAULTS.get(archetype)
        if profile is None:
            profile = ARCHETYPE_DEFAULTS.get(BusinessArchetype.B2B_SAAS)
        return profile
