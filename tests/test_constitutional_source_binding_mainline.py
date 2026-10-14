import hashlib

from constitutional_architecture.compiler.compilation_config import CompilationConfig
from constitutional_architecture.compiler.pipeline import CompilerPipeline
from constitutional_architecture.compiler.source_binding import (
    ConstitutionalSourceBinding,
    verify_constitutional_source_binding,
)
from constitutional_architecture.isr.model.isr import ISR
from constitutional_architecture.isr.model.system import System
from constitutional_architecture.isr.semantics.requirement import Requirement
from tiannara.domain.models.requirement_graph import (
    GraphProvenance,
    RequirementGraph,
    RequirementKind,
    RequirementNode,
)
from tiannara.domain.models.system_model import Priority


def _binding(source: bytes, mapped=None):
    graph = RequirementGraph(
        graph_id="binding-graph",
        nodes=[
            RequirementNode(
                id="REQ-A",
                kind=RequirementKind.CONSTRAINT,
                statement="Workspace access is isolated.",
                priority=Priority.MUST,
            ),
            RequirementNode(
                id="REQ-B",
                kind=RequirementKind.QUALITY,
                statement="Readiness is observable.",
                priority=Priority.SHOULD,
            ),
        ],
        provenance=GraphProvenance(
            source_statement_hash=hashlib.sha256(source).hexdigest()
        ),
    )
    requirements = (
        Requirement(
            requirement_id="ISR-REQ-A",
            statement="Workspace access is isolated.",
            target_refs=("CAP-WORKSPACE",),
        ),
        Requirement(
            requirement_id="ISR-REQ-B",
            statement="Readiness is observable.",
            target_refs=("CAP-READINESS",),
        ),
    )
    isr = ISR(system=System(
        id="system-binding-test",
        name="Binding test",
        requirements=requirements,
    ))
    binding = ConstitutionalSourceBinding(
        source_bytes=source,
        expected_source_sha256=hashlib.sha256(source).hexdigest(),
        graph=graph,
        graph_to_isr_requirement_ids=mapped or {"REQ-A": "ISR-REQ-A"},
    )
    return isr, binding


def test_binding_recomputes_exact_source_and_maps_mandatory_requirements():
    source = b"Workspace isolation is mandatory."
    isr, binding = _binding(source)

    report = verify_constitutional_source_binding(binding=binding, isr=isr)

    assert report.complete
    assert report.bound_graph_requirement_ids == ("REQ-A",)
    assert report.source_sha256 == hashlib.sha256(source).hexdigest()
    assert report.graph_sha256 == binding.graph.content_hash()
    assert report.isr_sha256 == isr.content_hash


def test_binding_rejects_stale_source_snapshot():
    source = b"Workspace isolation is mandatory."
    isr, binding = _binding(source)
    stale = ConstitutionalSourceBinding(
        source_bytes=b"Different source snapshot.",
        expected_source_sha256=binding.expected_source_sha256,
        graph=binding.graph,
        graph_to_isr_requirement_ids=binding.graph_to_isr_requirement_ids,
    )

    report = verify_constitutional_source_binding(binding=stale, isr=isr)

    assert not report.complete
    assert any("source bytes" in blocker for blocker in report.blockers)


def test_binding_rejects_unknown_ids_and_unbound_mandatory_requirement():
    source = b"Workspace isolation is mandatory."
    isr, binding = _binding(source, mapped={"REQ-UNKNOWN": "ISR-UNKNOWN"})

    report = verify_constitutional_source_binding(binding=binding, isr=isr)

    assert not report.complete
    assert report.unbound_mandatory_graph_requirement_ids == ("REQ-A",)
    assert report.unknown_graph_requirement_ids == ("REQ-UNKNOWN",)
    assert report.unknown_isr_requirement_ids == ("ISR-UNKNOWN",)


def test_compile_blocks_when_binding_is_required_but_missing():
    isr = ISR(system=System(id="missing-binding", name="Missing binding"))
    result = CompilerPipeline().compile(
        isr,
        CompilationConfig(
            project_name="missing-binding",
            require_source_binding=True,
        ),
    )

    assert not result.success
    assert result.artifact_count == 0
    assert result.diagnostics[0].code == "COMP-SOURCE-BINDING-001"


def test_source_bound_entrypoint_forces_gate_even_with_compatibility_config():
    isr = ISR(system=System(id="source-bound", name="Source bound"))
    result = CompilerPipeline().compile_source_bound(
        isr,
        CompilationConfig(project_name="source-bound"),
    )

    assert not result.success
    assert result.artifact_count == 0
    assert result.diagnostics[0].code == "COMP-SOURCE-BINDING-001"


def test_compile_blocks_invalid_binding_before_artifact_generation():
    source = b"Workspace isolation is mandatory."
    isr, binding = _binding(source, mapped={"REQ-UNKNOWN": "ISR-UNKNOWN"})

    result = CompilerPipeline().compile_source_bound(
        isr,
        CompilationConfig(project_name="invalid-binding"),
        source_binding=binding,
    )

    assert not result.success
    assert result.artifact_count == 0
    assert any(
        diagnostic.code == "COMP-SOURCE-BINDING-003"
        for diagnostic in result.diagnostics
    )


def test_supplied_binding_is_validated_even_without_opt_in_flag():
    source = b"Workspace isolation is mandatory."
    isr, binding = _binding(source, mapped={"REQ-UNKNOWN": "ISR-UNKNOWN"})

    result = CompilerPipeline().compile(
        isr,
        CompilationConfig(project_name="supplied-invalid-binding"),
        source_binding=binding,
    )

    assert not result.success
    assert result.artifact_count == 0
    assert any(
        diagnostic.code == "COMP-SOURCE-BINDING-003"
        for diagnostic in result.diagnostics
    )
