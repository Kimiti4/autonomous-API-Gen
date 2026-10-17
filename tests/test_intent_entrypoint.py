import hashlib
from types import SimpleNamespace

from constitutional_architecture.compiler.intent_entrypoint import (
    compile_intent_to_constitutional_isr,
)
from tiannara.application.intent.schemas import IntentCompilationResult
from tiannara.domain.models.isr import IntermediateSoftwareRepresentation
from tiannara.domain.models.requirement_graph import (
    GraphProvenance,
    RequirementGraph,
    RequirementKind,
    RequirementNode,
)
from tiannara.domain.models.system_model import RequirementsReference, SystemModel


SOURCE = "Provide isolated workspaces."


def _intent_result(*, unmapped_extension=False):
    source_bytes = SOURCE.encode("utf-8")
    graph = RequirementGraph(
        graph_id="entrypoint-graph",
        nodes=[
            RequirementNode(
                id="REQ-ISOLATION",
                kind=RequirementKind.CONSTRAINT,
                statement="Workspace data must be isolated.",
            )
        ],
        provenance=GraphProvenance(
            source_statement_hash=hashlib.sha256(source_bytes).hexdigest()
        ),
    )
    model = SystemModel(
        system_name="workspace-service",
        problem_statement=SOURCE,
        requirements_ref=RequirementsReference(
            graph_id=graph.graph_id,
            graph_hash=graph.content_hash(),
        ),
        domains=[
            {"id": "domain-core", "name": "Core", "description": "Core domain"}
        ],
        extensions={"unknown_semantics": {"must_preserve": True}}
        if unmapped_extension
        else {},
    )
    isr = IntermediateSoftwareRepresentation.from_system_model(
        "workspace-service", model
    )
    return IntentCompilationResult(
        system_id="workspace-service",
        isr=isr,
        requirement_graph=graph,
        call_records=[],
        repair_iterations=0,
        assumption_ids=[],
    )


class _FakeIntentCompiler:
    def __init__(self, result):
        self.result = result

    def compile_full(self, statement, system_id, *, taskflow_semantic_gate=False):
        assert statement == SOURCE
        assert system_id == "workspace-service"
        return self.result


class _FakePipeline:
    def __init__(self, success=True):
        self.calls = []
        self.success = success

    def compile_source_bound(self, isr, config, *, source_binding):
        self.calls.append((isr, config, source_binding))
        return SimpleNamespace(success=self.success)


def test_entrypoint_blocks_unmapped_source_semantics_before_compiler_call():
    intent = _FakeIntentCompiler(_intent_result(unmapped_extension=True))
    pipeline = _FakePipeline()

    result = compile_intent_to_constitutional_isr(
        intent_compiler=intent,
        source_statement=SOURCE,
        system_id="workspace-service",
        compiler_pipeline=pipeline,
    )

    assert result.status == "projection_blocked"
    assert result.compilation is None
    assert result.projection.blockers
    assert pipeline.calls == []


def test_entrypoint_verifies_binding_before_calling_source_bound_compiler():
    intent = _FakeIntentCompiler(_intent_result())
    pipeline = _FakePipeline(success=True)

    result = compile_intent_to_constitutional_isr(
        intent_compiler=intent,
        source_statement=SOURCE,
        system_id="workspace-service",
        compiler_pipeline=pipeline,
    )

    assert result.status == "compiled"
    assert result.binding_report is not None and result.binding_report.complete
    assert result.compilation is not None and result.compilation.success
    assert len(pipeline.calls) == 1
    candidate_isr, config, binding = pipeline.calls[0]
    assert candidate_isr is result.projection.candidate_isr
    assert binding.source_bytes == SOURCE.encode("utf-8")
    assert binding.graph.graph_id == result.intent.requirement_graph.graph_id
    assert binding.system_model.content_hash() == result.projection.system_model_sha256


def test_entrypoint_does_not_equate_compiler_failure_with_success():
    intent = _FakeIntentCompiler(_intent_result())
    pipeline = _FakePipeline(success=False)

    result = compile_intent_to_constitutional_isr(
        intent_compiler=intent,
        source_statement=SOURCE,
        system_id="workspace-service",
        compiler_pipeline=pipeline,
    )

    assert result.status == "compilation_failed"
    assert not result.ready_for_downstream_verification
