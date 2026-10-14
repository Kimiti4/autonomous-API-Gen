"""Tests for universal source-bound obligation projection."""
import hashlib
import pytest
from pydantic import ValidationError

from tiannara.application.compiler.source_projection import (
    SourceProjectionContext,
    create_source_projection_context,
    project_obligations,
    to_constitutional_source_binding,
    verify_exact_projection,
)
from tiannara.domain.models.compiler_obligation import Applicability, Disposition
from tiannara.application.compiler.obligation_projection import project_requirement_graph
from tiannara.domain.models.requirement_graph import (
    GraphProvenance,
    RequirementGraph,
    RequirementKind,
    RequirementNode,
)
from tiannara.domain.models.semantic_resolution import (
    ResolutionKind,
    SemanticResolution,
    SemanticResolutionRecord,
)
from tiannara.domain.models.system_model import Priority


def graph():
    return RequirementGraph(
        graph_id="graph-project-alpha",
        nodes=[
            RequirementNode(
                id="REQ-auth-scope",
                kind=RequirementKind.CONSTRAINT,
                statement="A user can access only resources in their workspace.",
                priority=Priority.MUST,
                acceptance_criteria=["Cross-workspace read is denied"],
                rationale="Source: requirements.md#L12",
            ),
            RequirementNode(
                id="REQ-health",
                kind=RequirementKind.QUALITY,
                statement="Expose health and readiness endpoints.",
                priority=Priority.SHOULD,
                acceptance_criteria=["Health and readiness are independently observable"],
            ),
        ],
        provenance=GraphProvenance(
            origin="reviewed_source_snapshot",
            taxonomy_version="requirements.v1",
        ),
    )


def resolution_for(g):
    return SemanticResolutionRecord(
        graph_id=g.graph_id,
        graph_hash=g.content_hash(),
        required_fields=("security.authorization_model",),
        resolutions=(
            SemanticResolution(
                field_path="security.authorization_model",
                kind=ResolutionKind.UNRESOLVED,
            ),
        ),
    )


def context():
    g = graph()
    return create_source_projection_context(
        source_id="repo://example/project@source-snapshot-7",
        source_bytes=b"# Requirements\nA user can access only resources in their workspace.",
        graph=g,
        semantic_resolution=resolution_for(g),
    )


def test_projection_is_source_and_graph_bound_and_unknown_by_default():
    result = project_obligations(context())
    assert len(result.records) == 2
    assert result.records[0].source_graph_hash == result.graph_sha256
    assert all(item.disposition is Disposition.UNKNOWN for item in result.records)
    assert result.snapshot_sha256
    assert result.context_sha256
    assert not result.generation_allowed
    assert result.unresolved_semantics == ("security.authorization_model",)
    # Source provenance must not create a second set of obligation semantics.
    canonical = project_requirement_graph(graph())
    assert tuple(item.model_dump(mode="json") for item in result.records) == tuple(
        item.model_dump(mode="json") for item in canonical.records
    )
    assert result.records[1].applicability is Applicability.OPTIONAL


def test_exact_projection_rejects_omission_and_semantic_weakening():
    ctx = context()
    records = project_obligations(ctx, require_resolved_semantics_before_generation=False).records
    assert verify_exact_projection(ctx, records) == ()
    assert any("omitted" in item for item in verify_exact_projection(ctx, records[:1]))
    changed = records[0].model_copy(update={"statement": "Authorization is optional."})
    blockers = verify_exact_projection(ctx, (changed, records[1]))
    assert any("altered" in item for item in blockers)



def test_source_context_uses_domain_hash_contract_for_unicode_graphs():
    g = graph()
    g.nodes[0].statement = "Les utilisateurs accèdent uniquement à leur espace."
    ctx = create_source_projection_context(
        source_id="repo://example/unicode-source",
        source_bytes="Exigences: café ☕".encode("utf-8"),
        graph=g,
        semantic_resolution=resolution_for(g),
    )
    assert ctx.graph_sha256 == g.content_hash()
    assert project_obligations(ctx).records

def test_projection_context_retains_exact_bytes_for_constitutional_binding():
    source_bytes = b"Exact source bytes: berth isolation."
    g = RequirementGraph(
        graph_id="bound-graph",
        nodes=[
            RequirementNode(
                id="REQ-1",
                kind=RequirementKind.CONSTRAINT,
                statement="Workspace access is isolated.",
                priority=Priority.MUST,
            )
        ],
        provenance=GraphProvenance(
            source_statement_hash=hashlib.sha256(source_bytes).hexdigest(),
            origin="trusted_snapshot",
        ),
    )
    ctx = create_source_projection_context(
        source_id="repo://example/exact-source",
        source_bytes=source_bytes,
        graph=g,
        semantic_resolution=resolution_for(g),
    )

    binding = to_constitutional_source_binding(
        ctx,
        graph_to_isr_requirement_ids={"REQ-1": "ISR-REQ-1"},
    )

    assert binding.source_bytes == source_bytes
    assert binding.expected_source_sha256 == hashlib.sha256(source_bytes).hexdigest()
    assert binding.graph.content_hash() == g.content_hash()
    assert binding.graph_to_isr_requirement_ids == {"REQ-1": "ISR-REQ-1"}


def test_projection_context_refuses_constitutional_binding_for_mismatched_graph_provenance():
    ctx = context()
    with pytest.raises(ValueError, match="does not bind the exact source snapshot"):
        to_constitutional_source_binding(
            ctx,
            graph_to_isr_requirement_ids={"REQ-auth-scope": "ISR-REQ-auth-scope"},
        )


def test_projection_context_rejects_source_bytes_hash_mismatch():
    ctx = context()
    with pytest.raises(ValidationError, match="source snapshot bytes do not match"):
        SourceProjectionContext.model_validate(
            {
                **ctx.model_dump(mode="json"),
                "source_bytes_b64": "YXR0YWNrZXItc3VwcGxpZWQtYnl0ZXM=",
            }
        )


def test_projection_context_rejects_tampered_graph_hash():
    ctx = context()
    with pytest.raises(ValidationError, match="graph hash does not match"):
        SourceProjectionContext.model_validate(
            {
                **ctx.model_dump(mode="json"),
                "graph_sha256": "0" * 64,
            }
        )


def test_projection_context_rejects_resolution_for_another_graph():
    g = graph()
    wrong = SemanticResolutionRecord(
        graph_id="another-graph",
        graph_hash="1" * 64,
        required_fields=(),
        resolutions=(),
    )
    with pytest.raises(ValueError, match="does not match the supplied graph"):
        create_source_projection_context(
            source_id="repo://example/project@source-snapshot-7",
            source_bytes=b"requirements",
            graph=g,
            semantic_resolution=wrong,
        )


def test_source_snapshot_bytes_change_snapshot_identity():
    g = graph()
    first = create_source_projection_context(
        source_id="repo://example/project",
        source_bytes=b"requirements version one",
        graph=g,
        semantic_resolution=resolution_for(g),
    )
    second = create_source_projection_context(
        source_id="repo://example/project",
        source_bytes=b"requirements version two",
        graph=g,
        semantic_resolution=resolution_for(g),
    )
    assert first.snapshot_sha256 != second.snapshot_sha256
    assert first.context_sha256 != second.context_sha256
