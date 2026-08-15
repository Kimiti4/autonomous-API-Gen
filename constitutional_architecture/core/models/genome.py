from __future__ import annotations

import copy
import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ApplicationArchitecture(str, Enum):
    MONOLITHIC = "monolithic"
    MODULAR_MONOLITH = "modular_monolith"
    SOA = "soa"
    MICROSERVICES = "microservices"
    EVENT_DRIVEN = "event_driven"
    CQRS = "cqrs"
    LAMBDA = "lambda"
    P2P = "peer_to_peer"


class DataArchitecture(str, Enum):
    SINGLE_DATABASE = "single_database"
    POLYGLOT_PERSISTENCE = "polyglot_persistence"
    EVENT_SOURCING = "event_sourcing"
    CQRS_SEGREGATION = "cqrs_segregation"
    DATA_LAKE = "data_lake"
    DATA_MESH = "data_mesh"
    DATABASE_PER_SERVICE = "database_per_service"


class IntegrationArchitecture(str, Enum):
    POINT_TO_POINT = "point_to_point"
    API_GATEWAY = "api_gateway"
    MESSAGE_BUS = "message_bus"
    EVENT_STORE = "event_store"
    SERVICE_MESH = "service_mesh"
    WEBHOOKS = "webhooks"


class SecurityArchitecture(str, Enum):
    PERIMETER = "perimeter"
    ZERO_TRUST = "zero_trust"
    DEFENSE_IN_DEPTH = "defense_in_depth"
    JIT_ACCESS = "jit_access"


class DeploymentTopology(str, Enum):
    SINGLE_REGION = "single_region"
    MULTI_REGION = "multi_region"
    EDGE = "edge"
    HYBRID = "hybrid"
    ON_PREM = "on_prem"
    CONTAINERIZED = "containerized"


class ObservabilityStrategy(str, Enum):
    LOGS_ONLY = "logs_only"
    METRICS_AND_LOGS = "metrics_and_logs"
    FULL_OBSERVABILITY = "full_observability"
    DDA = "distributed_debugging_agent"


class APIDesign(str, Enum):
    REST = "rest"
    GRAPHQL = "graphql"
    GRPC = "grpc"
    EVENT_STREAM = "event_stream"
    HYBRID = "hybrid"


class StateManagement(str, Enum):
    STATELESS = "stateless"
    SESSION_BASED = "session_based"
    DISTRIBUTED_CACHE = "distributed_cache"
    EVENTUAL_CONSISTENCY = "eventual_consistency"
    STRONG_CONSISTENCY = "strong_consistency"


class SecurityModel(str, Enum):
    ZERO_TRUST = "zero_trust"
    RBAC = "rbac"
    JWT = "jwt"


class PersistenceModel(str, Enum):
    RELATIONAL = "relational"
    DOCUMENT = "document"
    KEY_VALUE = "key_value"
    POLYGLOT = "polyglot"


class MessagingTopology(str, Enum):
    ASYNC_EVENT_BUS = "async_event_bus"
    POINT_TO_POINT = "point_to_point"
    NONE = "none"


class TenancyStrategy(str, Enum):
    SINGLE_TENANT = "single_tenant"
    MULTI_TENANT_SHARED = "multi_tenant_shared"
    MULTI_TENANT_ISOLATED = "multi_tenant_isolated"


class ResiliencePosture(str, Enum):
    FAIL_FAST = "fail_fast"
    RETRY_WITH_BACKOFF = "retry_with_backoff"
    CIRCUIT_BREAKER = "circuit_breaker"
    BULKHEAD_ISOLATION = "bulkhead_isolation"


class AuditLevel(str, Enum):
    MINIMAL = "minimal"
    STANDARD = "standard"
    STRICT_COMPLIANCE = "strict_compliance"


@dataclass
class CategoricalGene:
    id: str
    name: str
    value: Enum
    allowed_values: tuple[Enum, ...]

    def mutate(self, rate: float, rng: Optional[random.Random] = None) -> bool:
        rng = rng or random.Random()
        if rng.random() < rate:
            old = self.value
            candidates = [v for v in self.allowed_values if v != old]
            self.value = rng.choice(candidates) if candidates else old
            return True
        return False

    def serialize(self) -> Dict[str, Any]:
        raw = self.value.value if isinstance(self.value, Enum) else self.value
        return {"id": self.id, "name": self.name, "value": raw, "type": "categorical"}


@dataclass
class ContinuousGene:
    id: str
    name: str
    value: float
    min_value: float
    max_value: float

    def mutate(self, rate: float, rng: Optional[random.Random] = None) -> bool:
        rng = rng or random.Random()
        if rng.random() < rate:
            self.value = max(self.min_value, min(self.max_value, self.value + rng.gauss(0, 0.1)))
            return True
        return False

    def serialize(self) -> Dict[str, Any]:
        return {"id": self.id, "name": self.name, "value": self.value, "type": "continuous"}


ARCHITECTURE_GENES = (
    CategoricalGene("app_arch", "Application Architecture", ApplicationArchitecture.MODULAR_MONOLITH,
                    tuple(ApplicationArchitecture)),
    CategoricalGene("data_arch", "Data Architecture", DataArchitecture.SINGLE_DATABASE,
                    tuple(DataArchitecture)),
    CategoricalGene("integration_arch", "Integration Architecture", IntegrationArchitecture.API_GATEWAY,
                    tuple(IntegrationArchitecture)),
    CategoricalGene("security_arch", "Security Architecture", SecurityArchitecture.DEFENSE_IN_DEPTH,
                    tuple(SecurityArchitecture)),
    CategoricalGene("deployment_topology", "Deployment Topology", DeploymentTopology.SINGLE_REGION,
                    tuple(DeploymentTopology)),
    CategoricalGene("observability_strategy", "Observability Strategy", ObservabilityStrategy.METRICS_AND_LOGS,
                    tuple(ObservabilityStrategy)),
    CategoricalGene("api_design", "API Design", APIDesign.REST, tuple(APIDesign)),
    CategoricalGene("state_management", "State Management", StateManagement.EVENTUAL_CONSISTENCY,
                    tuple(StateManagement)),
    CategoricalGene("security_model", "Security Model", SecurityModel.RBAC,
                    tuple(SecurityModel)),
    CategoricalGene("persistence_model", "Persistence Model", PersistenceModel.RELATIONAL,
                    tuple(PersistenceModel)),
    CategoricalGene("messaging_topology", "Messaging Topology", MessagingTopology.NONE,
                    tuple(MessagingTopology)),
    CategoricalGene("tenancy_strategy", "Tenancy Strategy", TenancyStrategy.SINGLE_TENANT,
                    tuple(TenancyStrategy)),
    CategoricalGene("resilience_posture", "Resilience Posture", ResiliencePosture.CIRCUIT_BREAKER,
                    tuple(ResiliencePosture)),
    CategoricalGene("auditability_level", "Auditability Level", AuditLevel.STANDARD,
                    tuple(AuditLevel)),
)

CONTINUOUS_GENES = (
    ContinuousGene("consistency_level", "Consistency Level", 0.7, 0.0, 1.0),
    ContinuousGene("latency_tolerance_ms", "Latency Tolerance (ms)", 200.0, 1.0, 5000.0),
    ContinuousGene("data_durability", "Data Durability", 0.999, 0.9, 0.999999),
    ContinuousGene("fault_tolerance", "Fault Tolerance", 0.99, 0.9, 0.999999),
    ContinuousGene("observability_depth", "Observability Depth", 0.5, 0.0, 1.0),
    ContinuousGene("reliability_target", "Reliability Target", 0.99, 0.9, 0.9999),
    ContinuousGene("cost_monitoring_intensity", "Cost Monitoring Intensity", 0.5, 0.0, 1.0),
)


@dataclass
class ArchitectureGenome:
    categorical_genes: dict[str, CategoricalGene] = field(default_factory=lambda: {g.id: copy.deepcopy(g) for g in ARCHITECTURE_GENES})
    continuous_genes: dict[str, ContinuousGene] = field(default_factory=lambda: {g.id: copy.deepcopy(g) for g in CONTINUOUS_GENES})
    genome_id: str = ""
    intent_hash: str = ""

    @property
    def architecture_style(self) -> Optional[Any]:
        return self.get_gene("app_arch")

    @property
    def deployment_topology(self) -> Optional[Any]:
        return self.get_gene("deployment_topology")

    @property
    def persistence_model(self) -> Optional[Any]:
        return self.get_gene("persistence_model")

    @property
    def messaging_topology(self) -> Optional[Any]:
        return self.get_gene("messaging_topology")

    @property
    def tenancy_strategy(self) -> Optional[Any]:
        return self.get_gene("tenancy_strategy")

    @property
    def observability_depth(self) -> Optional[Any]:
        return self.get_gene("observability_depth")

    @property
    def security_model(self) -> Optional[Any]:
        return self.get_gene("security_model")

    @property
    def resilience_posture(self) -> Optional[Any]:
        return self.get_gene("resilience_posture")

    @property
    def auditability_level(self) -> Optional[Any]:
        return self.get_gene("auditability_level")

    @property
    def reliability_target(self) -> Optional[Any]:
        return self.get_gene("reliability_target")

    @property
    def cost_monitoring_intensity(self) -> Optional[Any]:
        return self.get_gene("cost_monitoring_intensity")

    def get_gene(self, gene_id: str) -> Optional[Any]:
        if gene_id in self.categorical_genes:
            return self.categorical_genes[gene_id].value
        if gene_id in self.continuous_genes:
            return self.continuous_genes[gene_id].value
        return None

    def set_gene(self, gene_id: str, value: Any) -> None:
        if gene_id in self.categorical_genes:
            self.categorical_genes[gene_id].value = value
        elif gene_id in self.continuous_genes:
            self.continuous_genes[gene_id].value = value

    def clone(self) -> ArchitectureGenome:
        import copy
        return copy.deepcopy(self)

    def mutate(self, rate: float = 0.1, rng: Optional[random.Random] = None) -> int:
        rng = rng or random.Random()
        mutations = 0
        for gene in list(self.categorical_genes.values()) + list(self.continuous_genes.values()):
            if gene.mutate(rate, rng):
                mutations += 1
        return mutations

    def serialize(self) -> Dict[str, Any]:
        categorical = {g_id: g.serialize() for g_id, g in self.categorical_genes.items()}
        continuous = {g_id: g.serialize() for g_id, g in self.continuous_genes.items()}
        return {"categorical": categorical, "continuous": continuous}
