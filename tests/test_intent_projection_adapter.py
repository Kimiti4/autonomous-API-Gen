import hashlib
from dataclasses import replace

from constitutional_architecture.compiler.compilation_config import CompilationConfig
from constitutional_architecture.compiler.pipeline import CompilerPipeline
from constitutional_architecture.compiler.source_binding import (
    ConstitutionalSourceBinding,
    verify_constitutional_source_binding,
)

from constitutional_architecture.isr.semantics.intent_projection import (
    project_intent_to_constitutional_isr,
)
from tiannara.domain.models.requirement_graph import (
    EdgeKind,
    GraphProvenance,
    RequirementEdge,
    RequirementGraph,
    RequirementKind,
    RequirementNode,
    NodeProvenance,
    VerificationMethod,
)
from tiannara.domain.models.system_model import (
    Priority,
    RequirementsReference,
    ServiceSpec,
    SystemModel,
)


def _inputs(*, with_architecture=False, priority=Priority.MUST):
    source = b"Workspace members must be isolated."
    graph = RequirementGraph(
        graph_id="graph-projection-test",
        nodes=[
            RequirementNode(
                id="REQ-WORKSPACE-ISOLATION",
                kind=RequirementKind.CONSTRAINT,
                statement="Workspace members must be isolated.",
                priority=priority,
                acceptance_criteria=["A member cannot read another workspace's data."],
                verification_method=VerificationMethod.TEST,
                rationale="Prevent cross-tenant disclosure.",
                provenance=NodeProvenance(
                    source="extracted",
                    taxonomy_version="v1",
                    stratum="security",
                    seed=17,
                    created_by="intent-compiler",
                ),
            ),
            RequirementNode(
                id="REQ-AUDIT",
                kind=RequirementKind.QUALITY,
                statement="Access decisions must be auditable.",
                priority=Priority.SHOULD,
            ),
        ],
        edges=[
            RequirementEdge(
                source_id="REQ-WORKSPACE-ISOLATION",
                target_id="REQ-AUDIT",
                kind=EdgeKind.CONSTRAINS,
                rationale="Audit coverage applies to access decisions.",
            )
        ],
        provenance=GraphProvenance(
            source_statement_hash=hashlib.sha256(source).hexdigest()
        ),
    )
    model = SystemModel(
        system_name="workspace-service",
        problem_statement="Provide isolated workspaces.",
        requirements_ref=RequirementsReference(
            graph_id=graph.graph_id,
            graph_hash=graph.content_hash(),
        ),
        domains=[
            {"id": "domain-core", "name": "Core domain", "description": "Core domain"}
        ],
        services=(
            [
                ServiceSpec(
                    id="workspace-service",
                    name="workspace-service",
                    domain_id="domain-core",
                )
            ]
            if with_architecture
            else []
        ),
        apis=(
            [
                {
                    "id": "workspace-api",
                    "name": "Workspace API",
                    "provider_service_id": "workspace-service",
                }
            ]
            if with_architecture
            else []
        ),
        extensions=({"unmapped": {"meaning": "must not be dropped"}} if with_architecture else {}),
    )
    return source, graph, model


def test_projection_preserves_graph_identity_nodes_metadata_and_relations():
    source, graph, model = _inputs()

    result = project_intent_to_constitutional_isr(
        source_bytes=source,
        graph=graph,
        system_model=model,
        system_id="workspace-system",
    )

    assert result.ready_for_compilation
    assert result.blockers == ()
    assert result.candidate_isr is not None
    system = result.candidate_isr.system
    assert system.requirement_graph_ref.graph_id == graph.graph_id
    assert system.requirement_graph_ref.graph_sha256 == graph.content_hash()
    assert system.requirement_graph_ref.source_sha256 == hashlib.sha256(source).hexdigest()
    assert {r.requirement_id for r in system.requirements} == {
        node.id for node in graph.nodes
    }
    first = next(
        item for item in system.requirement_source_metadata
        if item.requirement_id == "REQ-WORKSPACE-ISOLATION"
    )
    assert first.source_kind == "constraint"
    assert first.priority == "must"
    assert first.acceptance_criteria == (
        "A member cannot read another workspace's data.",
    )
    assert first.verification_method == "test"
    assert first.rationale == "Prevent cross-tenant disclosure."
    assert first.provenance_source == "extracted"
    assert first.taxonomy_version == "v1"
    assert first.stratum == "security"
    assert first.seed == 17
    assert first.created_by == "intent-compiler"
    assert len(system.requirement_relations) == 1
    assert system.requirement_relations[0].kind == "constrains"
    assert system.requirement_relations[0].source_requirement_id == "REQ-WORKSPACE-ISOLATION"
    assert system.requirement_relations[0].target_requirement_id == "REQ-AUDIT"


def test_projection_blocks_stale_graph_reference():
    source, graph, model = _inputs()
    model = model.model_copy(
        update={
            "requirements_ref": model.requirements_ref.model_copy(
                update={"graph_hash": "stale-hash"}
            )
        }
    )

    result = project_intent_to_constitutional_isr(
        source_bytes=source,
        graph=graph,
        system_model=model,
        system_id="workspace-system",
    )

    assert not result.ready_for_compilation
    assert result.candidate_isr is None
    assert any("stale requirement graph hash" in blocker for blocker in result.blockers)


def test_projection_blocks_unlowered_typed_architecture_instead_of_dropping_it():
    source, graph, model = _inputs(with_architecture=True)

    result = project_intent_to_constitutional_isr(
        source_bytes=source,
        graph=graph,
        system_model=model,
        system_id="workspace-system",
    )

    assert result.candidate_isr is not None
    assert not result.ready_for_compilation
    assert any("extensions" in blocker for blocker in result.blockers)


def test_priority_mutation_is_preserved_in_constitutional_projection():
    source, graph, model = _inputs(priority=Priority.MUST)
    must = project_intent_to_constitutional_isr(
        source_bytes=source, graph=graph, system_model=model, system_id="workspace-system"
    )
    changed_graph = graph.model_copy(
        update={
            "nodes": [
                node.model_copy(update={"priority": Priority.COULD})
                if node.id == "REQ-WORKSPACE-ISOLATION"
                else node
                for node in graph.nodes
            ]
        }
    )
    changed_model = model.model_copy(
        update={
            "requirements_ref": model.requirements_ref.model_copy(
                update={"graph_hash": changed_graph.content_hash()}
            )
        }
    )
    could = project_intent_to_constitutional_isr(
        source_bytes=source,
        graph=changed_graph,
        system_model=changed_model,
        system_id="workspace-system",
    )

    assert must.ready_for_compilation and could.ready_for_compilation
    assert must.candidate_isr.system.requirement_source_metadata[0].priority == "must"
    assert next(
        item.priority for item in could.candidate_isr.system.requirement_source_metadata
        if item.requirement_id == "REQ-WORKSPACE-ISOLATION"
    ) == "could"
    assert must.candidate_isr.content_hash != could.candidate_isr.content_hash


def test_source_binding_accepts_only_complete_projection_metadata():
    source, graph, model = _inputs()
    result = project_intent_to_constitutional_isr(
        source_bytes=source, graph=graph, system_model=model, system_id="workspace-system"
    )
    assert result.ready_for_compilation
    isr = result.candidate_isr
    binding = ConstitutionalSourceBinding(
        source_bytes=source,
        expected_source_sha256=hashlib.sha256(source).hexdigest(),
        graph=graph,
        system_model=model,
        graph_to_isr_requirement_ids={node.id: node.id for node in graph.nodes},
    )

    report = verify_constitutional_source_binding(binding=binding, isr=isr)

    assert report.complete


def test_source_binding_rejects_mutated_projected_priority():
    source, graph, model = _inputs()
    result = project_intent_to_constitutional_isr(
        source_bytes=source, graph=graph, system_model=model, system_id="workspace-system"
    )
    isr = result.candidate_isr
    metadata = list(isr.system.requirement_source_metadata)
    index = next(
        i for i, item in enumerate(metadata)
        if item.requirement_id == "REQ-WORKSPACE-ISOLATION"
    )
    metadata[index] = replace(metadata[index], priority="could")
    changed_system = replace(isr.system, requirement_source_metadata=tuple(metadata))
    changed_isr = replace(isr, system=changed_system)
    binding = ConstitutionalSourceBinding(
        source_bytes=source,
        expected_source_sha256=hashlib.sha256(source).hexdigest(),
        graph=graph,
        system_model=model,
        graph_to_isr_requirement_ids={node.id: node.id for node in graph.nodes},
    )

    report = verify_constitutional_source_binding(binding=binding, isr=changed_isr)

    assert not report.complete
    assert any("metadata differs" in blocker for blocker in report.blockers)


def test_source_binding_rejects_candidate_with_unlowered_architecture():
    source, graph, model = _inputs(with_architecture=True)
    result = project_intent_to_constitutional_isr(
        source_bytes=source, graph=graph, system_model=model, system_id="workspace-system"
    )
    assert result.candidate_isr is not None
    assert not result.ready_for_compilation
    binding = ConstitutionalSourceBinding(
        source_bytes=source,
        expected_source_sha256=hashlib.sha256(source).hexdigest(),
        graph=graph,
        system_model=model,
        graph_to_isr_requirement_ids={node.id: node.id for node in graph.nodes},
    )

    report = verify_constitutional_source_binding(
        binding=binding, isr=result.candidate_isr
    )

    assert not report.complete
    assert any("projection incomplete" in blocker for blocker in report.blockers)


def test_projected_isr_cannot_bypass_source_binding_via_compatibility_compile():
    source, graph, model = _inputs()
    result = project_intent_to_constitutional_isr(
        source_bytes=source, graph=graph, system_model=model, system_id="workspace-system"
    )
    assert result.ready_for_compilation

    compiled = CompilerPipeline().compile(
        result.candidate_isr,
        CompilationConfig(project_name="workspace-system"),
    )

    assert not compiled.success
    assert compiled.artifact_count == 0
    assert compiled.diagnostics[0].code == "COMP-SOURCE-BINDING-001"


def test_incomplete_projection_is_blocked_even_if_caller_uses_compatibility_compile():
    source, graph, model = _inputs(with_architecture=True)
    result = project_intent_to_constitutional_isr(
        source_bytes=source, graph=graph, system_model=model, system_id="workspace-system"
    )
    assert result.candidate_isr is not None
    assert not result.ready_for_compilation

    compiled = CompilerPipeline().compile(
        result.candidate_isr,
        CompilationConfig(project_name="workspace-system"),
    )

    assert not compiled.success
    assert compiled.artifact_count == 0
    assert compiled.diagnostics[0].code in {
        "COMP-SOURCE-BINDING-001",
        "COMP-SOURCE-BINDING-004",
    }


def test_source_binding_rejects_mutated_projected_architecture_gene():
    source = b"Workspace members must be isolated."
    graph = RequirementGraph(
        graph_id="architecture-graph",
        nodes=[
            RequirementNode(
                id="REQ-A",
                kind=RequirementKind.CONSTRAINT,
                statement="Workspace access is isolated.",
                priority=Priority.MUST,
            )
        ],
        provenance=GraphProvenance(
            source_statement_hash=hashlib.sha256(source).hexdigest()
        ),
    )
    model = SystemModel(
        system_name="workspace-service",
        problem_statement="Provide isolated workspaces.",
        requirements_ref=RequirementsReference(
            graph_id=graph.graph_id, graph_hash=graph.content_hash()
        ),
        domains=[
            {"id": "domain-core", "name": "Core domain", "description": "Core domain"}
        ],
        services=[
            {
                "id": "workspace-service",
                "name": "Workspace service",
                "domain_id": "domain-core",
                "responsibilities": ["isolate workspace access"],
            }
        ],
    )
    result = project_intent_to_constitutional_isr(
        source_bytes=source, graph=graph, system_model=model, system_id="workspace-system"
    )
    assert result.ready_for_compilation
    isr = result.candidate_isr
    original_module = isr.system.modules[0]
    mutated_service = replace(
        original_module.services[0],
        responsibility_refs=("ignore workspace isolation",),
    )
    mutated_module = replace(
        original_module, services=(mutated_service,)
    )
    mutated_isr = replace(
        isr,
        system=replace(isr.system, modules=(mutated_module,)),
    )
    binding = ConstitutionalSourceBinding(
        source_bytes=source,
        expected_source_sha256=hashlib.sha256(source).hexdigest(),
        graph=graph,
        system_model=model,
        graph_to_isr_requirement_ids={node.id: node.id for node in graph.nodes},
    )

    report = verify_constitutional_source_binding(binding=binding, isr=mutated_isr)

    assert not report.complete
    assert any("modules differ from deterministic" in blocker for blocker in report.blockers)


def test_projection_lowers_domain_service_component_data_and_event_semantics():
    source = b"Workspace members must be isolated."
    graph = RequirementGraph(
        graph_id="architecture-map-graph",
        nodes=[
            RequirementNode(
                id="REQ-A",
                kind=RequirementKind.CONSTRAINT,
                statement="Workspace access is isolated.",
                priority=Priority.MUST,
            )
        ],
        provenance=GraphProvenance(
            source_statement_hash=hashlib.sha256(source).hexdigest()
        ),
    )
    model = SystemModel(
        system_name="workspace-service",
        problem_statement="Provide isolated workspaces.",
        requirements_ref=RequirementsReference(
            graph_id=graph.graph_id, graph_hash=graph.content_hash()
        ),
        capabilities=[
            {
                "id": "cap-workspace",
                "name": "Workspace isolation",
                "description": "Keep workspace data isolated.",
                "criticality": "core",
                "priority": "must",
                "traced_requirement_ids": ["REQ-A"],
            }
        ],
        domains=[
            {
                "id": "domain-core",
                "name": "Core domain",
                "description": "Core domain",
                "capability_ids": ["cap-workspace"],
            }
        ],
        services=[
            {
                "id": "workspace-service",
                "name": "Workspace service",
                "domain_id": "domain-core",
                "responsibilities": ["isolate workspace access"],
                "exposed_capability_ids": ["cap-workspace"],
            },
            {
                "id": "audit-service",
                "name": "Audit service",
                "domain_id": "domain-core",
                "responsibilities": ["record access decisions"],
            },
        ],
        apis=[
            {
                "id": "workspace-api",
                "name": "Workspace API",
                "provider_service_id": "workspace-service",
                "consumer_service_ids": ["audit-service"],
                "interaction_style": "request_response",
                "operations": [
                    {
                        "name": "create_workspace",
                        "description": "Create a workspace.",
                        "semantics": "command",
                        "idempotent": True,
                    }
                ],
            }
        ],
        components=[
            {
                "id": "workspace-policy",
                "service_id": "workspace-service",
                "name": "Workspace policy",
                "responsibility": "enforce workspace isolation",
                "kind": "policy",
            }
        ],
        data_models=[
            {
                "id": "workspace-record",
                "name": "Workspace record",
                "owning_service_id": "workspace-service",
                "fields": [
                    {"name": "name", "type": "text", "required": True},
                    {
                        "name": "status",
                        "type": "enumeration",
                        "required": True,
                        "enumeration_values": ["active", "archived"],
                    },
                    {
                        "name": "parent_workspace",
                        "type": "reference",
                        "required": False,
                        "reference_target_model_id": "workspace-record",
                    },
                ],
                "invariants": ["workspace identity is immutable"],
                "consistency": "strong",
            }
        ],
        events=[
            {
                "id": "workspace-audited",
                "name": "Workspace audited",
                "producer_service_id": "audit-service",
                "consumer_service_ids": ["workspace-service"],
                "payload_model_id": "workspace-record",
                "delivery_semantics": "at_least_once",
                "ordering": "partition_ordered",
            }
        ],
    )
    result = project_intent_to_constitutional_isr(
        source_bytes=source, graph=graph, system_model=model, system_id="workspace-system"
    )

    assert result.ready_for_compilation
    assert result.candidate_isr.validate_structure()
    from constitutional_architecture.isr.semantics.intent_architecture import validate_system_architecture_projection
    assert validate_system_architecture_projection(result.candidate_isr.system) == ()
    assert result.candidate_isr.system.security_posture.authorization == "none"
    assert result.candidate_isr.system.security_posture.encryption_in_transit_required is True
    assert result.candidate_isr.system.infrastructure_posture.topology == "modular_monolith"
    assert result.candidate_isr.system.deployment_posture.rollout_strategy == "rolling"
    assert result.candidate_isr.system.testing_posture.coverage_posture == "enforced"
    assert result.candidate_isr.system.documentation_posture.adr_required is True
    assert result.candidate_isr.system.operational_posture.incident_response_required is True
    module = result.candidate_isr.system.modules[0]
    assert module.id == "domain-core"
    assert {service.id for service in module.services} == {
        "workspace-service", "audit-service"
    }
    assert module.services[0].domain_id == "domain-core"
    assert module.services[0].exposed_capability_refs == ("cap-workspace",)
    capability = next(
        item for item in result.candidate_isr.system.business_capabilities
        if item.capability_id == "cap-workspace"
    )
    assert capability.name == "Workspace isolation"
    assert capability.priority == "must"
    assert capability.requirement_refs == ("REQ-A",)
    api = module.api_contracts[0]
    assert api.api_id == "workspace-api"
    assert api.provider_service_id == "workspace-service"
    assert api.consumer_service_ids == ("audit-service",)
    assert api.operations[0].name == "create_workspace"
    assert api.operations[0].semantics == "command"
    assert api.operations[0].idempotent is True
    assert module.components[0].component_id == "workspace-policy"
    entity = module.entities[0]
    assert entity.owning_service_id == "workspace-service"
    assert entity.invariants == ("workspace identity is immutable",)
    assert [field.field_type.value for field in entity.fields] == ["text", "enum", "reference"]
    assert [field.abstract_source_type for field in entity.fields] == ["text", "enumeration", "reference"]
    assert entity.fields[2].reference_target == "workspace-record"
    assert entity.relationships[0].target_entity_id == "workspace-record"
    assert entity.relationships[0].field_name == "parent_workspace"
    event = module.events[0]
    assert event.producer_service_id == "audit-service"
    assert event.consumer_service_ids == ("workspace-service",)
    assert event.payload_model_id == "workspace-record"
    assert event.ordering_semantics == "partition_ordered"
    assert event.ordering_required is True


def test_source_binding_rejects_a_different_typed_system_model_hash():
    source = b"Workspace members must be isolated."
    graph = RequirementGraph(
        graph_id="model-hash-graph",
        nodes=[
            RequirementNode(
                id="REQ-A",
                kind=RequirementKind.CONSTRAINT,
                statement="Workspace access is isolated.",
                priority=Priority.MUST,
            )
        ],
        provenance=GraphProvenance(
            source_statement_hash=hashlib.sha256(source).hexdigest()
        ),
    )
    model = SystemModel(
        system_name="workspace-service",
        problem_statement="Provide isolated workspaces.",
        requirements_ref=RequirementsReference(
            graph_id=graph.graph_id, graph_hash=graph.content_hash()
        ),
        domains=[{"id": "domain-core", "name": "Core domain"}],
    )
    result = project_intent_to_constitutional_isr(
        source_bytes=source, graph=graph, system_model=model, system_id="workspace-system"
    )
    changed_model = model.model_copy(update={"problem_statement": "Different system meaning."})
    binding = ConstitutionalSourceBinding(
        source_bytes=source,
        expected_source_sha256=hashlib.sha256(source).hexdigest(),
        graph=graph,
        system_model=changed_model,
        graph_to_isr_requirement_ids={node.id: node.id for node in graph.nodes},
    )

    report = verify_constitutional_source_binding(
        binding=binding, isr=result.candidate_isr
    )

    assert not report.complete
    assert any("SystemModel hash differs" in blocker for blocker in report.blockers)


def test_source_binding_rejects_mutated_security_posture():
    source = b"Workspace members must be isolated."
    graph = RequirementGraph(
        graph_id="security-posture-graph",
        nodes=[
            RequirementNode(
                id="REQ-A",
                kind=RequirementKind.CONSTRAINT,
                statement="Workspace access is isolated.",
                priority=Priority.MUST,
            )
        ],
        provenance=GraphProvenance(
            source_statement_hash=hashlib.sha256(source).hexdigest()
        ),
    )
    model = SystemModel(
        system_name="workspace-service",
        problem_statement="Provide isolated workspaces.",
        requirements_ref=RequirementsReference(
            graph_id=graph.graph_id, graph_hash=graph.content_hash()
        ),
        domains=[{"id": "domain-core", "name": "Core domain"}],
    )
    result = project_intent_to_constitutional_isr(
        source_bytes=source, graph=graph, system_model=model, system_id="workspace-system"
    )
    isr = result.candidate_isr
    changed_security = replace(isr.system.security_posture, authorization="abac")
    changed_isr = replace(
        isr, system=replace(isr.system, security_posture=changed_security)
    )
    binding = ConstitutionalSourceBinding(
        source_bytes=source,
        expected_source_sha256=hashlib.sha256(source).hexdigest(),
        graph=graph,
        system_model=model,
        graph_to_isr_requirement_ids={node.id: node.id for node in graph.nodes},
    )

    report = verify_constitutional_source_binding(binding=binding, isr=changed_isr)

    assert not report.complete
    assert any("security posture differs" in blocker for blocker in report.blockers)


def test_architecture_validator_rejects_missing_security_posture():
    source, graph, model = _inputs()
    result = project_intent_to_constitutional_isr(
        source_bytes=source, graph=graph, system_model=model, system_id="workspace-system"
    )
    changed_isr = replace(
        result.candidate_isr,
        system=replace(result.candidate_isr.system, security_posture=None),
    )
    from constitutional_architecture.isr.semantics.intent_architecture import (
        validate_system_architecture_projection,
    )

    errors = validate_system_architecture_projection(changed_isr.system)

    assert any("missing first-class security posture" in error for error in errors)


def test_source_binding_rejects_mutated_deployment_posture():
    source, graph, model = _inputs()
    result = project_intent_to_constitutional_isr(
        source_bytes=source, graph=graph, system_model=model, system_id="workspace-system"
    )
    isr = result.candidate_isr
    changed_deployment = replace(isr.system.deployment_posture, rollout_strategy="canary")
    changed_isr = replace(
        isr, system=replace(isr.system, deployment_posture=changed_deployment)
    )
    binding = ConstitutionalSourceBinding(
        source_bytes=source,
        expected_source_sha256=hashlib.sha256(source).hexdigest(),
        graph=graph,
        system_model=model,
        graph_to_isr_requirement_ids={node.id: node.id for node in graph.nodes},
    )

    report = verify_constitutional_source_binding(binding=binding, isr=changed_isr)

    assert not report.complete
    assert any("policy postures differ" in blocker for blocker in report.blockers)


def test_source_binding_rejects_mutated_typed_capability_gene():
    source, graph, model = _inputs()
    model = SystemModel.model_validate(
        model.model_dump()
        | {
            "capabilities": [
                {
                    "id": "cap-audit",
                    "name": "Audit access",
                    "description": "Access decisions are auditable.",
                    "criticality": "core",
                    "priority": "must",
                    "traced_requirement_ids": ["REQ-AUDIT"],
                }
            ]
        }
    )
    result = project_intent_to_constitutional_isr(
        source_bytes=source, graph=graph, system_model=model, system_id="workspace-system"
    )
    isr = result.candidate_isr
    capabilities = list(isr.system.business_capabilities)
    index = next(i for i, item in enumerate(capabilities) if item.capability_id == "cap-audit")
    capabilities[index] = replace(capabilities[index], name="Unrelated capability")
    changed_isr = replace(
        isr, system=replace(isr.system, business_capabilities=tuple(capabilities))
    )
    binding = ConstitutionalSourceBinding(
        source_bytes=source,
        expected_source_sha256=hashlib.sha256(source).hexdigest(),
        graph=graph,
        system_model=model,
        graph_to_isr_requirement_ids={node.id: node.id for node in graph.nodes},
    )

    report = verify_constitutional_source_binding(binding=binding, isr=changed_isr)

    assert not report.complete
    assert any("capabilities differ" in blocker for blocker in report.blockers)


def test_projection_blocks_reference_fields_with_unknown_target_models():
    source, graph, model = _inputs()
    model = SystemModel.model_validate(
        model.model_dump()
        | {
            "services": [
                {
                    "id": "workspace-service",
                    "name": "Workspace service",
                    "domain_id": "domain-core",
                }
            ],
            "data_models": [
                {
                    "id": "workspace-record",
                    "name": "Workspace record",
                    "owning_service_id": "workspace-service",
                    "fields": [
                        {
                            "name": "owner",
                            "type": "reference",
                            "reference_target_model_id": "missing-model",
                        }
                    ],
                }
            ],
        }
    )

    result = project_intent_to_constitutional_isr(
        source_bytes=source, graph=graph, system_model=model, system_id="workspace-system"
    )

    assert not result.ready_for_compilation
    assert any("references unknown model 'missing-model'" in blocker for blocker in result.blockers)


def test_architecture_validator_rejects_dangling_entity_relationships():
    from constitutional_architecture.isr.model.entity import Relationship
    from constitutional_architecture.isr.semantics.intent_architecture import (
        validate_system_architecture_projection,
    )

    source, graph, model = _inputs()
    model = SystemModel.model_validate(
        model.model_dump()
        | {
            "services": [
                {
                    "id": "workspace-service",
                    "name": "Workspace service",
                    "domain_id": "domain-core",
                }
            ],
            "data_models": [
                {
                    "id": "workspace-record",
                    "name": "Workspace record",
                    "owning_service_id": "workspace-service",
                }
            ],
        }
    )
    result = project_intent_to_constitutional_isr(
        source_bytes=source, graph=graph, system_model=model, system_id="workspace-system"
    )
    module = result.candidate_isr.system.modules[0]
    entity = replace(
        module.entities[0],
        relationships=(
            Relationship(target_entity_id="missing-entity", relationship_type="reference"),
        ),
    )
    changed_module = replace(module, entities=(entity,))
    changed_system = replace(result.candidate_isr.system, modules=(changed_module,))

    errors = validate_system_architecture_projection(changed_system)

    assert any("references unknown entity 'missing-entity'" in error for error in errors)
