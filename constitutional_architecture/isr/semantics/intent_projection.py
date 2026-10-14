"""Loss-aware projection from the intent graph into constitutional ISR semantics.

The adapter deliberately separates a candidate projection from authorization to
compile it. Requirement graph identity, node metadata, and graph relations are
projected into first-class ISR records. Typed architectural fields not yet
translated into constitutional genes are reported as blockers; a candidate
with blockers must never be passed to source-bound compilation.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass

from constitutional_architecture.isr.model.component import Component
from constitutional_architecture.isr.model.api_contract import ApiContract, ApiOperationContract
from constitutional_architecture.isr.model.entity import Entity
from constitutional_architecture.isr.model.event import Event, EventGuarantee
from constitutional_architecture.isr.model.fields import Field, FieldCardinality, FieldType
from constitutional_architecture.isr.model.isr import ISR
from constitutional_architecture.isr.model.module import Module
from constitutional_architecture.isr.model.service import Service
from constitutional_architecture.isr.model.system import System, SystemMetadata
from constitutional_architecture.isr.semantics.capability import BusinessCapability
from constitutional_architecture.isr.semantics.intent_architecture import IntentArchitectureReference
from constitutional_architecture.isr.semantics.security_posture import SecurityPosture
from constitutional_architecture.isr.semantics.policy_postures import (
    DeploymentPosture,
    DocumentationPosture,
    InfrastructurePosture,
    OperationalPosture,
    OperationalSLO,
    TestingPosture,
)
from constitutional_architecture.isr.semantics.requirement import (
    Requirement,
    RequirementGraphReference,
    RequirementRelation,
    RequirementSourceMetadata,
)
from tiannara.domain.models.requirement_graph import RequirementGraph
from tiannara.domain.models.system_model import SystemModel


@dataclass(frozen=True)
class IntentProjectionResult:
    candidate_isr: ISR | None
    source_sha256: str
    graph_sha256: str
    system_model_sha256: str
    requirement_id_map: tuple[tuple[str, str], ...]
    blockers: tuple[str, ...]

    @property
    def ready_for_compilation(self) -> bool:
        return self.candidate_isr is not None and not self.blockers


def _stable_capability_id(requirement_id: str) -> str:
    digest = hashlib.sha256(requirement_id.encode("utf-8")).hexdigest()[:16]
    return f"cap-req-{digest}"


def project_intent_to_constitutional_isr(
    *,
    source_bytes: bytes,
    graph: RequirementGraph,
    system_model: SystemModel,
    system_id: str,
) -> IntentProjectionResult:
    """Create a traceable candidate ISR, refusing unverified/lossy projections.

    Requirement graph semantics are preserved in first-class records.
    Domains, services, components, events, and representable data models are
    lowered into native ISR genes. APIs and policy sections whose contracts
    are not faithfully representable remain explicit blockers.
    """
    source_hash = hashlib.sha256(source_bytes).hexdigest()
    graph_hash = graph.content_hash()
    model_hash = system_model.content_hash()
    blockers: list[str] = []

    if not source_bytes:
        blockers.append("source snapshot is empty")
    if graph.provenance.source_statement_hash != source_hash:
        blockers.append("graph provenance does not match exact source bytes")
    if system_model.requirements_ref.graph_id != graph.graph_id:
        blockers.append("SystemModel references a different requirement graph ID")
    if system_model.requirements_ref.graph_hash != graph_hash:
        blockers.append("SystemModel references a stale requirement graph hash")
    if not graph.nodes:
        blockers.append("requirement graph has no nodes")

    nodes = {node.id: node for node in graph.nodes}
    capabilities: list[BusinessCapability] = []
    requirements: list[Requirement] = []
    metadata: list[RequirementSourceMetadata] = []
    id_map: list[tuple[str, str]] = []

    for node in graph.nodes:
        cap_id = _stable_capability_id(node.id)
        capabilities.append(
            BusinessCapability(
                capability_id=cap_id,
                intent=node.statement,
                requirement_refs=(node.id,),
            )
        )
        acceptance_text = tuple(node.acceptance_criteria)
        requirements.append(
            Requirement(
                requirement_id=node.id,
                statement=node.statement,
                target_refs=(cap_id,),
            )
        )
        metadata.append(
            RequirementSourceMetadata(
                requirement_id=node.id,
                source_kind=node.kind.value,
                priority=node.priority.value,
                acceptance_criteria=acceptance_text,
                verification_method=node.verification_method.value,
                rationale=node.rationale,
                provenance_source=node.provenance.source,
                taxonomy_version=node.provenance.taxonomy_version,
                stratum=node.provenance.stratum,
                seed=node.provenance.seed,
                created_by=node.provenance.created_by,
            )
        )
        id_map.append((node.id, node.id))

    relations = tuple(
        RequirementRelation(
            source_requirement_id=edge.source_id,
            target_requirement_id=edge.target_id,
            kind=edge.kind.value,
            rationale=edge.rationale,
        )
        for edge in graph.edges
    )

    typed_capability_ids = {capability.id for capability in system_model.capabilities}
    for capability in system_model.capabilities:
        if capability.id in {item.capability_id for item in capabilities}:
            blockers.append(f"typed capability ID '{capability.id}' collides with a requirement-derived capability")
            continue
        unknown_requirements = set(capability.traced_requirement_ids) - set(nodes)
        if unknown_requirements:
            blockers.append(
                f"typed capability '{capability.id}' traces unknown requirements: "
                + ", ".join(sorted(unknown_requirements))
            )
        capabilities.append(
            BusinessCapability(
                capability_id=capability.id,
                intent=capability.description or capability.name,
                requirement_refs=tuple(capability.traced_requirement_ids),
                name=capability.name,
                description=capability.description,
                criticality=capability.criticality.value,
                priority=capability.priority.value,
            )
        )

    # Lower the explicitly representable architecture sections into native ISR
    # genes. A source field is never assigned a guessed default to make it fit.
    domain_by_id = {domain.id: domain for domain in system_model.domains}
    if not system_model.domains:
        blockers.append("typed SystemModel has no domains to lower into constitutional modules")
    service_by_id = {service.id: service for service in system_model.services}
    model_by_id = {model.id: model for model in system_model.data_models}
    module_services: dict[str, list[Service]] = {domain_id: [] for domain_id in domain_by_id}
    module_components: dict[str, list[Component]] = {domain_id: [] for domain_id in domain_by_id}
    module_entities: dict[str, list[Entity]] = {domain_id: [] for domain_id in domain_by_id}
    module_events: dict[str, list[Event]] = {domain_id: [] for domain_id in domain_by_id}
    module_api_contracts: dict[str, list[ApiContract]] = {domain_id: [] for domain_id in domain_by_id}
    service_domain: dict[str, str] = {}

    declared_capability_ids = typed_capability_ids
    for domain in system_model.domains:
        unknown_ids = set(domain.capability_ids) - declared_capability_ids
        if unknown_ids:
            blockers.append(
                f"domain '{domain.id}' references capability IDs that are not declared: "
                + ", ".join(sorted(unknown_ids))
            )

    for service in system_model.services:
        domain = domain_by_id.get(service.domain_id)
        if domain is None:
            blockers.append(
                f"service '{service.id}' references unknown domain '{service.domain_id}'"
            )
            continue
        service_domain[service.id] = service.domain_id
        module_services[service.domain_id].append(
            Service(
                id=service.id,
                name=service.name,
                description="; ".join(service.responsibilities),
                domain_id=service.domain_id,
                responsibility_refs=tuple(service.responsibilities),
                exposed_capability_refs=tuple(service.exposed_capability_ids),
                is_stateless=None,
            )
        )
        unknown_capabilities = set(service.exposed_capability_ids) - {
            capability.id for capability in system_model.capabilities
        }
        if unknown_capabilities:
            blockers.append(
                f"service '{service.id}' exposes unknown capability IDs: "
                + ", ".join(sorted(unknown_capabilities))
            )

    for api in system_model.apis:
        provider_domain = service_domain.get(api.provider_service_id)
        if provider_domain is None:
            blockers.append(
                f"API '{api.id}' references unknown or unprojected provider service "
                f"'{api.provider_service_id}'"
            )
            continue
        unknown_consumers = set(api.consumer_service_ids) - set(service_by_id)
        if unknown_consumers:
            blockers.append(
                f"API '{api.id}' references unknown consumer services: "
                + ", ".join(sorted(unknown_consumers))
            )
        module_api_contracts[provider_domain].append(
            ApiContract(
                api_id=api.id,
                name=api.name,
                provider_service_id=api.provider_service_id,
                consumer_service_ids=tuple(api.consumer_service_ids),
                interaction_style=api.interaction_style.value,
                operations=tuple(
                    ApiOperationContract(
                        name=operation.name,
                        description=operation.description,
                        semantics=operation.semantics.value,
                        idempotent=operation.idempotent,
                    )
                    for operation in api.operations
                ),
            )
        )

    for component in system_model.components:
        domain_id = service_domain.get(component.service_id)
        if domain_id is None:
            blockers.append(
                f"component '{component.id}' references unknown or unprojected service "
                f"'{component.service_id}'"
            )
            continue
        module_components[domain_id].append(
            Component(
                component_id=component.id,
                service_id=component.service_id,
                name=component.name,
                responsibility=component.responsibility,
                kind=component.kind.value,
            )
        )

    field_type_map = {
        "identifier": FieldType.IDENTIFIER,
        "text": FieldType.TEXT,
        "integer": FieldType.INTEGER,
        "decimal": FieldType.DECIMAL,
        "boolean": FieldType.BOOLEAN,
        "timestamp": FieldType.DATETIME,
        "enumeration": FieldType.ENUM,
        "binary": FieldType.BINARY,
        "document": FieldType.JSON,
    }
    for data_model in system_model.data_models:
        domain_id = service_domain.get(data_model.owning_service_id)
        if domain_id is None:
            blockers.append(
                f"data model '{data_model.id}' references unknown or unprojected owning service "
                f"'{data_model.owning_service_id}'"
            )
            continue
        projected_fields: list[Field] = []
        for source_field in data_model.fields:
            target_type = field_type_map.get(source_field.type.value)
            if source_field.type.value == "reference":
                blockers.append(
                    f"field '{data_model.id}.{source_field.name}' is a reference without "
                    "a declared target model"
                )
                continue
            if target_type is None:
                blockers.append(
                    f"field '{data_model.id}.{source_field.name}' has unsupported type "
                    f"'{source_field.type.value}'"
                )
                continue
            projected_fields.append(
                Field(
                    name=source_field.name,
                    field_type=target_type,
                    cardinality=(
                        FieldCardinality.REQUIRED
                        if source_field.required
                        else FieldCardinality.OPTIONAL
                    ),
                    description=source_field.description,
                    enum_values=tuple(source_field.enumeration_values),
                    abstract_source_type=source_field.type.value,
                )
            )
        module_entities[domain_id].append(
            Entity(
                id=data_model.id,
                name=data_model.name,
                description=f"Data model owned by service {data_model.owning_service_id}",
                fields=tuple(projected_fields),
                owning_service_id=data_model.owning_service_id,
                invariants=tuple(data_model.invariants),
                consistency_posture=data_model.consistency.value,
            )
        )

    for event_spec in system_model.events:
        producer_domain = service_domain.get(event_spec.producer_service_id)
        if producer_domain is None:
            blockers.append(
                f"event '{event_spec.id}' references unknown or unprojected producer service "
                f"'{event_spec.producer_service_id}'"
            )
            continue
        unknown_consumers = set(event_spec.consumer_service_ids) - set(service_by_id)
        if unknown_consumers:
            blockers.append(
                f"event '{event_spec.id}' references unknown consumer services: "
                + ", ".join(sorted(unknown_consumers))
            )
        if event_spec.payload_model_id and event_spec.payload_model_id not in model_by_id:
            blockers.append(
                f"event '{event_spec.id}' references unknown payload model "
                f"'{event_spec.payload_model_id}'"
            )
        guarantee = {
            "at_most_once": EventGuarantee.AT_MOST_ONCE,
            "at_least_once": EventGuarantee.AT_LEAST_ONCE,
            "exactly_once": EventGuarantee.EXACTLY_ONCE,
        }[event_spec.delivery_semantics.value]
        module_events[producer_domain].append(
            Event(
                id=event_spec.id,
                name=event_spec.name,
                description="",
                pattern=None,
                guarantee=guarantee,
                ordering_required=event_spec.ordering.value != "none",
                ordering_semantics=event_spec.ordering.value,
                producer_service_id=event_spec.producer_service_id,
                consumer_service_ids=tuple(event_spec.consumer_service_ids),
                payload_model_id=event_spec.payload_model_id,
            )
        )

    # These sections need additional native semantic carriers before they can
    # be declared complete. They are intentionally not copied into extensions.
    if system_model.extensions:
        blockers.append("typed SystemModel contains extensions with no declared lowering")

    modules = tuple(
        Module(
            id=domain.id,
            name=domain.name,
            description=domain.description,
            services=tuple(module_services[domain.id]),
            components=tuple(module_components[domain.id]),
            entities=tuple(module_entities[domain.id]),
            events=tuple(module_events[domain.id]),
            capability_refs=tuple(domain.capability_ids),
            api_contracts=tuple(module_api_contracts[domain.id]),
        )
        for domain in system_model.domains
    )
    # Detect accidental dangling relations even though RequirementGraph itself
    # validates this invariant at construction; retain the check at the boundary.
    for edge in graph.edges:
        if edge.source_id not in nodes or edge.target_id not in nodes:
            blockers.append(
                f"relation {edge.source_id}->{edge.target_id} references an unknown node"
            )

    candidate = ISR(
        system=System(
            id=system_id,
            name=system_model.system_name,
            description=system_model.problem_statement,
            metadata=SystemMetadata(description=system_model.problem_statement),
            modules=modules,
            business_capabilities=tuple(capabilities),
            requirements=tuple(requirements),
            requirement_graph_ref=RequirementGraphReference(
                graph_id=graph.graph_id,
                graph_sha256=graph_hash,
                source_sha256=source_hash,
                projection_complete=not blockers,
                projection_blockers=tuple(blockers),
            ),
            requirement_source_metadata=tuple(metadata),
            requirement_relations=relations,
            infrastructure_posture=InfrastructurePosture(
                topology=system_model.infrastructure.topology.value,
                stateful=system_model.infrastructure.stateful,
                scaling_unit=system_model.infrastructure.scaling_unit.value,
                availability=system_model.infrastructure.availability.value,
            ),
            deployment_posture=DeploymentPosture(
                rollout_strategy=system_model.deployment.rollout_strategy.value,
                environment_names=tuple(system_model.deployment.environment_names),
                scaling_policy=system_model.deployment.scaling_policy.value,
                zero_downtime_required=system_model.deployment.zero_downtime_required,
            ),
            testing_posture=TestingPosture(
                required_levels=tuple(level.value for level in system_model.testing.required_levels),
                coverage_posture=system_model.testing.coverage_posture.value,
                performance_required=system_model.testing.performance_required,
                security_required=system_model.testing.security_required,
            ),
            documentation_posture=DocumentationPosture(
                required_artifacts=tuple(system_model.documentation.required_artifacts),
                adr_required=system_model.documentation.adr_required,
            ),
            operational_posture=OperationalPosture(
                service_level_objectives=tuple(
                    OperationalSLO(name=slo.name, metric=slo.metric, target=slo.target)
                    for slo in system_model.operational_policies.service_level_objectives
                ),
                observability_requirements=tuple(
                    requirement.value
                    for requirement in system_model.operational_policies.observability_requirements
                ),
                backup_posture=system_model.operational_policies.backup_posture,
                disaster_recovery_posture=system_model.operational_policies.disaster_recovery_posture,
                incident_response_required=system_model.operational_policies.incident_response_required,
            ),
            security_posture=SecurityPosture(
                authentication=system_model.security.authentication.value,
                authorization=system_model.security.authorization.value,
                data_classification=system_model.security.data_classification.value,
                encryption_in_transit_required=system_model.security.encryption_in_transit_required,
                encryption_at_rest_required=system_model.security.encryption_at_rest_required,
                audit_logging_required=system_model.security.audit_logging_required,
                secrets_management_required=system_model.security.secrets_management_required,
            ),
            intent_architecture_ref=IntentArchitectureReference(
                system_model_sha256=model_hash,
                projection_complete=not blockers,
                projection_blockers=tuple(blockers),
            ),
        )
    ) if not any(
        blocker in {
            "source snapshot is empty",
            "graph provenance does not match exact source bytes",
            "SystemModel references a different requirement graph ID",
            "SystemModel references a stale requirement graph hash",
            "requirement graph has no nodes",
        }
        for blocker in blockers
    ) else None

    return IntentProjectionResult(
        candidate_isr=candidate,
        source_sha256=source_hash,
        graph_sha256=graph_hash,
        system_model_sha256=model_hash,
        requirement_id_map=tuple(id_map),
        blockers=tuple(blockers),
    )
