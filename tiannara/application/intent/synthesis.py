"""Deterministic, rule-based synthesis of a SystemModel from a validated
RequirementGraph plus elicitation context.

Intentionally heuristic and abstract: maps requirement structure onto ISR
sections using only technology-agnostic vocabulary. This is the extension
point where Domain-Expert / Software-Architect agents will later refine
domains, services, and policies. Every rule is documented inline.
"""

from __future__ import annotations

import re

from tiannara.domain.models.requirement_graph import RequirementGraph, RequirementKind
from tiannara.domain.models.system_model import (
    AbstractFieldType,
    AuthenticationPosture,
    AuthorizationModel,
    BusinessCapability,
    CommunicationStyle,
    DataClassification,
    DataModelSpec,
    DomainSpec,
    FieldSpec,
    InfrastructureModel,
    OperationalPolicies,
    RequirementsReference,
    SecurityModel,
    ServiceLevelObjective,
    ServiceSpec,
    SystemModel,
    TestingPolicy,
    TopologyStyle,
)

from .schemas import DataSeed, ElicitationOutput, NormalizedIntent


def _slug(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or "node"


def _synthesize_data_models(
    data_seeds: list[DataSeed] | None,
    services: list[ServiceSpec],
) -> list[DataModelSpec]:
    """Deterministically type the extraction's entity seeds.

    Rules (each is a schema-evolution flag, not a heuristic):
      * field ``type`` must already be a validated abstract vocabulary value;
      * an identifier field is synthesized when the seed omits one (every
        backend keys entities by an id);
      * the owning service is ``svc-<slug(owning_service_ref)>`` when that
        service exists, otherwise the first service (or an empty owner for
        service-less models -- derivation never plans a database artifact
        without a service, so a dangling owner cannot reach a bundle).
    """
    if not data_seeds:
        return []
    service_ids = {service.id for service in services}
    models: list[DataModelSpec] = []
    for seed in data_seeds:
        fields: list[FieldSpec] = []
        for field in seed.fields:
            try:
                field_type = AbstractFieldType(field.type)
            except ValueError as exc:
                raise ValueError(
                    f"data model '{seed.ref}' field '{field.name}': "
                    f"unknown abstract field type '{field.type}'"
                ) from exc
            fields.append(
                FieldSpec(
                    name=field.name,
                    type=field_type,
                    required=field.required,
                    description=field.description,
                    enumeration_values=list(field.enumeration_values),
                )
            )
        has_identifier = any(
            f.type is AbstractFieldType.IDENTIFIER or f.name == "id"
            for f in fields
        )
        if not has_identifier:
            fields.insert(0, FieldSpec(name="id", type=AbstractFieldType.IDENTIFIER))
        owner = ""
        if seed.owning_service_ref:
            candidate = f"svc-{_slug(seed.owning_service_ref)}"
            owner = candidate if candidate in service_ids else owner
        if not owner and services:
            owner = services[0].id
        models.append(
            DataModelSpec(
                id=f"dm-{_slug(seed.ref)}",
                name=seed.name,
                owning_service_id=owner,
                fields=fields,
                invariants=list(seed.invariants),
            )
        )
    return models


def synthesize_system_model(
    graph: RequirementGraph,
    elicitation: ElicitationOutput,
    normalized: NormalizedIntent,
    data_seeds: list[DataSeed] | None = None,
) -> SystemModel:
    functional = [n for n in graph.nodes if n.kind is RequirementKind.FUNCTIONAL]
    integration_present = any(
        n.kind is RequirementKind.INTEGRATION for n in graph.nodes
    )

    statement_text = " ".join(n.statement.lower() for n in graph.nodes)
    confidential = any(
        token in statement_text
        for token in ("confidential", "privacy", "gdpr", "hipaa", "restricted")
    )
    performance_focus = any(
        token in statement_text for token in ("performance", "latency", "throughput")
    )
    availability_focus = "availability" in statement_text

    # Capabilities: one per functional requirement, traced; plus inferred ones.
    capabilities: list[BusinessCapability] = []
    for node in functional:
        capabilities.append(
            BusinessCapability(
                id=f"cap-{_slug(node.id)}",
                name=node.statement,
                criticality="core",
                priority=node.priority,
                traced_requirement_ids=[node.id],
            )
        )
    for name in elicitation.inferred_capabilities:
        capabilities.append(
            BusinessCapability(
                id=f"cap-inf-{_slug(name)}",
                name=name,
                criticality="supporting",
                priority="should",
                traced_requirement_ids=[],
            )
        )

    capability_ids = [c.id for c in capabilities]
    domains = [
        DomainSpec(
            id="domain-core",
            name="Core Domain",
            capability_ids=capability_ids,
        )
    ]

    # Services: one per functional capability; communication style from integration.
    comm_style = (
        CommunicationStyle.ASYNCHRONOUS_EVENT
        if integration_present
        else CommunicationStyle.SYNCHRONOUS_REQUEST_RESPONSE
    )
    services = [
        ServiceSpec(
            id=f"svc-{_slug(node.id)}",
            name=_slug(node.id),
            domain_id="domain-core",
            responsibilities=[node.statement],
            exposed_capability_ids=[f"cap-{_slug(node.id)}"],
            communication_styles=[comm_style],
        )
        for node in functional
    ]

    compliance_present = any(
        n.kind is RequirementKind.COMPLIANCE for n in graph.nodes
    )
    security = SecurityModel(
        authentication=AuthenticationPosture.TOKEN_BASED,
        authorization=(
            AuthorizationModel.RBAC if compliance_present else AuthorizationModel.NONE
        ),
        data_classification=(
            DataClassification.CONFIDENTIAL
            if (confidential or compliance_present)
            else DataClassification.INTERNAL
        ),
        encryption_in_transit_required=True,
        encryption_at_rest_required=True,
        audit_logging_required=True,
        secrets_management_required=True,
    )

    testing = TestingPolicy(performance_required=performance_focus)

    slos: list[ServiceLevelObjective] = []
    if availability_focus:
        slos.append(
            ServiceLevelObjective(
                name="availability", metric="availability", target="99.9%"
            )
        )
    if performance_focus:
        slos.append(
            ServiceLevelObjective(name="latency", metric="latency_p95", target="< 300 ms")
        )
    operational = OperationalPolicies(service_level_objectives=slos)

    service_count = len(services)
    if service_count <= 1:
        topology = TopologyStyle.SINGLE_SERVICE
    elif integration_present:
        topology = TopologyStyle.DISTRIBUTED_SERVICES
    else:
        topology = TopologyStyle.MODULAR_MONOLITH
    data_present = any(n.kind is RequirementKind.DATA for n in graph.nodes)
    infrastructure = InfrastructureModel(topology=topology, stateful=data_present)

    return SystemModel(
        system_name=_slug(normalized.normalized_statement)[:40] or "system",
        problem_statement=normalized.original_statement,
        requirements_ref=RequirementsReference(
            graph_id=graph.graph_id, graph_hash=graph.content_hash()
        ),
        capabilities=capabilities,
        domains=domains,
        services=services,
        components=[],
        apis=[],
        events=[],
        data_models=_synthesize_data_models(data_seeds, services),
        security=security,
        infrastructure=infrastructure,
        operational_policies=operational,
        testing=testing,
    )
