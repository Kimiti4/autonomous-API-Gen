"""Tests for universal graph-to-obligation projection and anti-tampering checks."""
import pytest

from tiannara.application.compiler.obligation_projection import (
    project_requirement_graph,
    verify_obligation_projection,
)
from tiannara.domain.models.requirement_graph import (
    GraphProvenance,
    RequirementGraph,
    RequirementKind,
    RequirementNode,
)
from tiannara.domain.models.system_model import Priority


def graph():
    return RequirementGraph(
        graph_id="sample-app-requirements-v1",
        nodes=[
            RequirementNode(
                id="auth.scope",
                kind=RequirementKind.CONSTRAINT,
                statement="Every read is scoped to the active tenant.",
                priority=Priority.MUST,
                acceptance_criteria=["Foreign tenant data is never returned."],
                rationale="Tenant isolation is a mandatory invariant.",
            ),
            RequirementNode(
                id="ui.shortcuts",
                kind=RequirementKind.QUALITY,
                statement="Frequently used actions have keyboard shortcuts.",
                priority=Priority.SHOULD,
                acceptance_criteria=["Shortcut behavior is documented."],
            ),
            RequirementNode(
                id="ui.theme",
                kind=RequirementKind.FUNCTIONAL,
                statement="Users may choose a display theme.",
                priority=Priority.COULD,
            ),
        ],
        provenance=GraphProvenance(origin="reviewed_specification"),
    )


def test_projection_covers_every_requirement_and_keeps_unknowns_unresolved():
    source = graph()
    projected = project_requirement_graph(source)
    assert projected.source_graph_id == source.graph_id
    assert projected.source_graph_hash == source.content_hash()
    assert len(projected.records) == len(source.nodes)
    assert projected.required_obligation_ids == ("requirement.auth.scope",)
    assert all(record.disposition.value == "UNKNOWN" for record in projected.records)
    assert all(not record.consumer_binding for record in projected.records)
    assert all(not record.enforcement_points for record in projected.records)
    verify_obligation_projection(source, projected)


def test_projection_binds_acceptance_criteria_and_rationale_into_obligation_hash():
    original = project_requirement_graph(graph())
    changed_graph = graph()
    changed_node = changed_graph.nodes[0].model_copy(
        update={"acceptance_criteria": ["Foreign data is always returned."]}
    )
    changed_graph.nodes[0] = changed_node
    changed = project_requirement_graph(changed_graph)
    original_record = next(r for r in original.records if r.obligation_id == "requirement.auth.scope")
    changed_record = next(r for r in changed.records if r.obligation_id == "requirement.auth.scope")
    assert original_record.obligation_hash != changed_record.obligation_hash
    assert original.source_graph_hash != changed.source_graph_hash


def test_projection_rejects_manifest_from_another_source_graph():
    first = graph()
    second = graph()
    second.graph_id = "different-app-requirements"
    projection = project_requirement_graph(first)
    with pytest.raises(ValueError, match="does not match the active requirement graph"):
        verify_obligation_projection(second, projection)


def test_projection_recomputes_records_instead_of_trusting_manifest_hash():
    source = graph()
    projection = project_requirement_graph(source)
    forged_record = projection.records[0].model_copy(
        update={"statement": "Forged weaker requirement."}
    )
    forged = type(projection)(
        schema=projection.schema,
        source_graph_id=projection.source_graph_id,
        source_graph_hash=projection.source_graph_hash,
        records=(forged_record, *projection.records[1:]),
        projection_hash=projection.projection_hash,
    )
    with pytest.raises(ValueError, match="records differ from the canonical source projection"):
        verify_obligation_projection(source, forged)


def test_projection_hash_is_stable_for_equivalent_graph_node_order():
    source = graph()
    reordered = source.model_copy(update={"nodes": list(reversed(source.nodes))})
    first = project_requirement_graph(source)
    second = project_requirement_graph(reordered)
    assert first.projection_hash == second.projection_hash
