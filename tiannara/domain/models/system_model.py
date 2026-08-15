"""Typed ISR payload: SystemModel (v1.0).

The ISR envelope itself is an ``IntermediateSoftwareRepresentation``; the
*typed, technology-agnostic* architectural content is carried in
``content["system_model"]`` as a ``SystemModel`` (payload type
``system_model.v1``).

Every concern here maps to a constitutional ISR dimension. The vocabulary
is abstract on purpose:

  * No framework / language / database / cloud / deployment token may
    appear anywhere. The boundary guard ``scan_for_technology_coupling``
    enforces this at envelope creation time
    (``IntermediateSoftwareRepresentation.from_system_model``).

  * Serialization is deterministic (see ``canonical_json``); two builders
    that assemble an identical system produce an identical hash.

  * Unknown concerns go into ``extensions`` rather than crashing the
    pipeline; each such item is a schema-evolution flag for Phase 38
    (Self-Improvement) to consume.
"""

from __future__ import annotations

import enum
import re
from typing import Any

from pydantic import BaseModel, Field, model_validator

from ..services.canonical import canonical_hash, canonical_json


# --------------------------------------------------------------------------
# Abstract vocabulary (no technology tokens anywhere)
# --------------------------------------------------------------------------

class Criticality(str, enum.Enum):
    CORE = "core"
    SUPPORTING = "supporting"
    GENERIC = "generic"


class Priority(str, enum.Enum):
    MUST = "must"
    SHOULD = "should"
    COULD = "could"


class CommunicationStyle(str, enum.Enum):
    SYNCHRONOUS_REQUEST_RESPONSE = "synchronous_request_response"
    ASYNCHRONOUS_EVENT = "asynchronous_event"
    BATCH = "batch"
    STREAMING = "streaming"


class InteractionStyle(str, enum.Enum):
    REQUEST_RESPONSE = "request_response"
    EVENT_DRIVEN = "event_driven"
    BATCH = "batch"
    STREAMING = "streaming"


class OperationSemantics(str, enum.Enum):
    COMMAND = "command"
    QUERY = "query"


class DeliverySemantics(str, enum.Enum):
    AT_MOST_ONCE = "at_most_once"
    AT_LEAST_ONCE = "at_least_once"
    EXACTLY_ONCE = "exactly_once"


class EventOrdering(str, enum.Enum):
    NONE = "none"
    PARTITION_ORDERED = "partition_ordered"
    TOTALLY_ORDERED = "totally_ordered"


class AbstractFieldType(str, enum.Enum):
    """Technology-agnostic field types. Backends map these to concrete types."""

    IDENTIFIER = "identifier"
    TEXT = "text"
    INTEGER = "integer"
    DECIMAL = "decimal"
    BOOLEAN = "boolean"
    TIMESTAMP = "timestamp"
    ENUMERATION = "enumeration"
    REFERENCE = "reference"
    BINARY = "binary"
    DOCUMENT = "document"


class ConsistencyPosture(str, enum.Enum):
    STRONG = "strong"
    EVENTUAL = "eventual"
    CAUSAL = "causal"


class AuthenticationPosture(str, enum.Enum):
    ANONYMOUS = "anonymous"
    CREDENTIAL_BASED = "credential_based"
    TOKEN_BASED = "token_based"
    FEDERATED_IDENTITY = "federated_identity"
    MUTUAL_AUTHENTICATION = "mutual_authentication"


class AuthorizationModel(str, enum.Enum):
    NONE = "none"
    RBAC = "rbac"
    ABAC = "abac"
    POLICY_BASED = "policy_based"


class DataClassification(str, enum.Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


class TopologyStyle(str, enum.Enum):
    SINGLE_SERVICE = "single_service"
    MODULAR_MONOLITH = "modular_monolith"
    DISTRIBUTED_SERVICES = "distributed_services"
    EVENT_DRIVEN = "event_driven"
    HYBRID = "hybrid"


class AvailabilityPosture(str, enum.Enum):
    SINGLE_ZONE = "single_zone"
    MULTI_ZONE = "multi_zone"
    MULTI_REGION = "multi_region"


class ScalingUnit(str, enum.Enum):
    SERVICE = "service"
    INSTANCE = "instance"
    PARTITION = "partition"


class RolloutStrategy(str, enum.Enum):
    ALL_AT_ONCE = "all_at_once"
    ROLLING = "rolling"
    BLUE_GREEN = "blue_green"
    CANARY = "canary"


class ScalingPolicy(str, enum.Enum):
    STATIC = "static"
    REACTIVE = "reactive"
    PREDICTIVE = "predictive"


class TestLevel(str, enum.Enum):
    UNIT = "unit"
    INTEGRATION = "integration"
    END_TO_END = "end_to_end"
    PROPERTY_BASED = "property_based"
    PERFORMANCE = "performance"
    SECURITY = "security"
    MUTATION = "mutation"


class CoveragePosture(str, enum.Enum):
    NONE = "none"
    REPORTED = "reported"
    ENFORCED = "enforced"


class ObservabilityRequirement(str, enum.Enum):
    """The constitutional Observability-by-Design set."""

    STRUCTURED_LOGGING = "structured_logging"
    METRICS = "metrics"
    DISTRIBUTED_TRACING = "distributed_tracing"
    HEALTH_CHECKS = "health_checks"
    READINESS_CHECKS = "readiness_checks"
    AUDIT_EVENTS = "audit_events"


class ComponentKind(str, enum.Enum):
    INTERFACE_ADAPTER = "interface_adapter"
    APPLICATION_SERVICE = "application_service"
    DOMAIN_SERVICE = "domain_service"
    REPOSITORY = "repository"
    BACKGROUND_WORKER = "background_worker"
    GATEWAY = "gateway"
    POLICY = "policy"


# --------------------------------------------------------------------------
# ISR sections
# --------------------------------------------------------------------------

class RequirementsReference(BaseModel):
    """Traceability link to the RequirementGraph this model was derived from."""

    graph_id: str
    graph_hash: str


class BusinessCapability(BaseModel):
    id: str
    name: str
    description: str = ""
    criticality: Criticality = Criticality.CORE
    priority: Priority = Priority.MUST
    traced_requirement_ids: list[str] = Field(default_factory=list)


class DomainSpec(BaseModel):
    id: str
    name: str
    description: str = ""
    capability_ids: list[str] = Field(default_factory=list)
    ubiquitous_language: dict[str, str] = Field(default_factory=dict)


class ServiceSpec(BaseModel):
    id: str
    name: str
    domain_id: str
    responsibilities: list[str] = Field(default_factory=list)
    exposed_capability_ids: list[str] = Field(default_factory=list)
    communication_styles: list[CommunicationStyle] = Field(default_factory=list)


class ComponentSpec(BaseModel):
    id: str
    service_id: str
    name: str
    responsibility: str = ""
    kind: ComponentKind = ComponentKind.APPLICATION_SERVICE


class ApiOperation(BaseModel):
    name: str
    description: str = ""
    semantics: OperationSemantics = OperationSemantics.QUERY
    idempotent: bool = False


class ApiSpec(BaseModel):
    id: str
    name: str
    provider_service_id: str
    consumer_service_ids: list[str] = Field(default_factory=list)
    interaction_style: InteractionStyle = InteractionStyle.REQUEST_RESPONSE
    operations: list[ApiOperation] = Field(default_factory=list)


class EventSpec(BaseModel):
    id: str
    name: str
    producer_service_id: str
    consumer_service_ids: list[str] = Field(default_factory=list)
    payload_model_id: str | None = None
    delivery_semantics: DeliverySemantics = DeliverySemantics.AT_LEAST_ONCE
    ordering: EventOrdering = EventOrdering.NONE


class FieldSpec(BaseModel):
    name: str
    type: AbstractFieldType
    required: bool = True
    description: str = ""
    enumeration_values: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _enumeration_needs_values(self) -> "FieldSpec":
        if self.type is AbstractFieldType.ENUMERATION and not self.enumeration_values:
            raise ValueError(f"field '{self.name}': enumeration type requires values")
        return self


class DataModelSpec(BaseModel):
    id: str
    name: str
    owning_service_id: str
    fields: list[FieldSpec] = Field(default_factory=list)
    invariants: list[str] = Field(default_factory=list)
    consistency: ConsistencyPosture = ConsistencyPosture.STRONG


class SecurityModel(BaseModel):
    authentication: AuthenticationPosture = AuthenticationPosture.TOKEN_BASED
    authorization: AuthorizationModel = AuthorizationModel.NONE
    data_classification: DataClassification = DataClassification.INTERNAL
    encryption_in_transit_required: bool = True
    encryption_at_rest_required: bool = True
    audit_logging_required: bool = True
    secrets_management_required: bool = True


class InfrastructureModel(BaseModel):
    topology: TopologyStyle = TopologyStyle.MODULAR_MONOLITH
    stateful: bool = False
    scaling_unit: ScalingUnit = ScalingUnit.INSTANCE
    availability: AvailabilityPosture = AvailabilityPosture.SINGLE_ZONE


class DeploymentModel(BaseModel):
    rollout_strategy: RolloutStrategy = RolloutStrategy.ROLLING
    environment_names: list[str] = Field(
        default_factory=lambda: ["development", "staging", "production"]
    )
    scaling_policy: ScalingPolicy = ScalingPolicy.STATIC
    zero_downtime_required: bool = True


class DocumentationPolicy(BaseModel):
    required_artifacts: list[str] = Field(
        default_factory=lambda: ["README", "ADR", "API_REFERENCE", "RUNBOOK"]
    )
    adr_required: bool = True


class TestingPolicy(BaseModel):
    required_levels: list[TestLevel] = Field(
        default_factory=lambda: [TestLevel.UNIT, TestLevel.INTEGRATION, TestLevel.END_TO_END]
    )
    coverage_posture: CoveragePosture = CoveragePosture.ENFORCED
    performance_required: bool = False
    security_required: bool = True


class ServiceLevelObjective(BaseModel):
    name: str
    metric: str          # abstract metric name, e.g. "availability", "latency_p95"
    target: str          # abstract target, e.g. "99.9%", "< 200 ms"


class OperationalPolicies(BaseModel):
    service_level_objectives: list[ServiceLevelObjective] = Field(default_factory=list)
    observability_requirements: list[ObservabilityRequirement] = Field(
        default_factory=lambda: list(ObservabilityRequirement)
    )
    backup_posture: str = "scheduled"
    disaster_recovery_posture: str = "restore_from_backup"
    incident_response_required: bool = True


# --------------------------------------------------------------------------
# The typed ISR payload
# --------------------------------------------------------------------------

class SystemModel(BaseModel):
    """Canonical, technology-agnostic representation of a software system."""

    schema_version: str = "1.0"
    system_name: str
    problem_statement: str = ""
    requirements_ref: RequirementsReference
    capabilities: list[BusinessCapability] = Field(default_factory=list)
    domains: list[DomainSpec] = Field(default_factory=list)
    services: list[ServiceSpec] = Field(default_factory=list)
    components: list[ComponentSpec] = Field(default_factory=list)
    apis: list[ApiSpec] = Field(default_factory=list)
    events: list[EventSpec] = Field(default_factory=list)
    data_models: list[DataModelSpec] = Field(default_factory=list)
    security: SecurityModel = Field(default_factory=SecurityModel)
    infrastructure: InfrastructureModel = Field(default_factory=InfrastructureModel)
    deployment: DeploymentModel = Field(default_factory=DeploymentModel)
    documentation: DocumentationPolicy = Field(default_factory=DocumentationPolicy)
    testing: TestingPolicy = Field(default_factory=TestingPolicy)
    operational_policies: OperationalPolicies = Field(default_factory=OperationalPolicies)
    extensions: dict[str, Any] = Field(default_factory=dict)

    def canonical_payload(self) -> dict[str, Any]:
        """Return the model serialized to plain JSON-able types deterministically."""
        import json as _json
        return _json.loads(canonical_json(self))

    def canonical_payload_json(self) -> str:
        return canonical_json(self)

    def content_hash(self) -> str:
        return canonical_hash(self)


# --------------------------------------------------------------------------
# Technology-coupling enforcement
# --------------------------------------------------------------------------

class TechnologyCouplingViolation(BaseModel):
    path: str
    token: str
    excerpt: str


class TechnologyCouplingError(ValueError):
    def __init__(self, violations: list[TechnologyCouplingViolation]) -> None:
        self.violations = violations
        detail = "; ".join(f"{v.path}: '{v.token}'" for v in violations[:10])
        super().__init__(f"ISR contains technology tokens: {detail}")


#: Curated denylist. Curation rule: tokens must be unambiguous technology
#: names. Ambiguous natural-language words ("go", "rust", "swift", "lambda",
#: "spring" kept but monitored) are documented trade-offs in the ADR.
TECHNOLOGY_TOKENS: tuple[str, ...] = (
    # languages
    "python", "typescript", "javascript", "java", "kotlin", "csharp", "dotnet",
    "golang", "elixir", "ruby", "php", "scala",
    # frameworks
    "fastapi", "django", "flask", "springboot", "phoenix", "nestjs",
    "laravel", "rails", "express", "axum", "fiber", "quarkus", "micronaut",
    "react", "angular", "vue", "flutter", "nextjs",
    # databases
    "postgresql", "postgres", "mysql", "mariadb", "mongodb", "mongo", "redis",
    "neo4j", "cockroachdb", "sqlite", "elasticsearch", "cassandra", "dynamodb",
    "aurora", "snowflake", "bigquery",
    # infrastructure / cloud
    "docker", "kubernetes", "k8s", "terraform", "pulumi", "nomad", "ansible",
    "aws", "azure", "gcp", "ec2", "s3", "eks", "aks", "fargate",
    # messaging
    "kafka", "rabbitmq", "nats", "activemq", "sqs", "kinesis", "pulsar",
    # auth technologies (ISR must express posture abstractly instead)
    "oauth", "oidc", "jwt", "saml", "mtls",
    # observability stacks
    "prometheus", "grafana", "opentelemetry", "jaeger", "loki", "datadog",
    "newrelic", "splunk",
)
# NOTE: genuinely ambiguous natural-language words (e.g. "go", "rust",
# "swift", "lambda", "spring") are intentionally NOT in the denylist -- they
# are monitored in the ADR rather than silent false-positive blocks. "docker"
# is unambiguous (the canonical runtime token) and is therefore banned. Backends
# map abstract postures to concrete choices.

_TOKEN_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = tuple(
    (token, re.compile(rf"\b{re.escape(token)}\b", re.IGNORECASE))
    for token in TECHNOLOGY_TOKENS
)


def _walk_strings(value: Any, path: str = "$"):
    if isinstance(value, str):
        yield path, value
    elif isinstance(value, dict):
        for key, item in value.items():
            yield from _walk_strings(item, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _walk_strings(item, f"{path}[{index}]")


def scan_for_technology_coupling(
    model: SystemModel,
    extra_tokens: tuple[str, ...] = (),
) -> list[TechnologyCouplingViolation]:
    """Recursively scan all string fields for technology tokens.

    Returns violations rather than raising so callers can report, evolve,
    or (at the envelope boundary) enforce.
    """
    patterns = list(_TOKEN_PATTERNS)
    patterns += [
        (token, re.compile(rf"\b{re.escape(token)}\b", re.IGNORECASE))
        for token in extra_tokens
    ]
    violations: list[TechnologyCouplingViolation] = []
    for path, text in _walk_strings(model.model_dump(mode="json")):
        for token, pattern in patterns:
            if pattern.search(text):
                violations.append(
                    TechnologyCouplingViolation(
                        path=path, token=token, excerpt=text[:120]
                    )
                )
    return violations
