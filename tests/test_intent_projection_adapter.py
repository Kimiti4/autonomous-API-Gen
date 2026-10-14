import hashlib
from dataclasses import replace

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
    assert any("services" in blocker for blocker in result.blockers)


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
        graph_to_isr_requirement_ids={node.id: node.id for node in graph.nodes},
    )

    report = verify_constitutional_source_binding(
        binding=binding, isr=result.candidate_isr
    )

    assert not report.complete
    assert any("projection incomplete" in blocker for blocker in report.blockers)
