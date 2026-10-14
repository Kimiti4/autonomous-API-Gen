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


def _binding(source: bytes, graph_ids=("REQ-A",), mapped=None):
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
    return isr, ConstitutionalSourceBinding(
        source_bytes=source,
        expected_source_sha256=hashlib.sha256(source).hexdigest(),
        graph=graph,
        graph_to_isr_requirement_ids=mapped or {"REQ-A": "ISR-REQ-A"},
    )


def test_constitutional_binding_recomputes_source_and_maps_mandatory_requirements():
    source = b"Workspace isolation is mandatory."
    isr, binding = _binding(source)
    report = verify_constitutional_source_binding(binding=binding, isr=isr)
    assert report.complete
    assert report.bound_graph_requirement_ids == ("REQ-A",)
    assert report.source_sha256 == hashlib.sha256(source).hexdigest()
    assert report.graph_sha256 == binding.graph.content_hash()
    assert report.isr_sha256 == isr.content_hash


def test_constitutional_binding_blocks_missing_mandatory_and_unknown_ids():
    source = b"Workspace isolation is mandatory."
    isr, binding = _binding(
        source,
        mapped={"REQ-NOT-REAL": "ISR-NOT-REAL"},
    )
    report = verify_constitutional_source_binding(binding=binding, isr=isr)
    assert not report.complete
    assert report.unbound_mandatory_graph_requirement_ids == ("REQ-A",)
    assert report.unknown_graph_requirement_ids == ("REQ-NOT-REAL",)
    assert report.unknown_isr_requirement_ids == ("ISR-NOT-REAL",)


def test_constitutional_binding_blocks_stale_source_bytes():
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


def test_pipeline_fails_closed_when_source_binding_is_required_but_absent():
    isr = ISR(system=System(id="system-gate-test", name="Gate test"))
    result = CompilerPipeline().compile(
        isr,
        CompilationConfig(project_name="gate-test", require_source_binding=True),
    )
    assert not result.success
    assert result.error_count == 1
    assert result.diagnostics[0].code == "COMP-SOURCE-BINDING-001"
