"""Phase 16 — ProjectCompiler end-to-end (hermetic, stub front-end)."""

import hashlib

import pytest

from tiannara.application.compiler.fastapi_hexagonal_backend import FastAPIHexagonalBackend
from tiannara.application.compiler.project_compiler import (
    ProjectCompilationError,
    ProjectCompilationReport,
    ProjectCompiler,
)
from tiannara.application.compiler.registry import CompilerRegistry
from tiannara.domain.models.backend_declaration import (
    ArtifactKind,
    BackendCapabilityDeclaration,
)
from tiannara.domain.models.capability_manifest import BundleCapability
from tiannara.domain.models.isr import (
    IntentSpecification,
    IntermediateSoftwareRepresentation,
)
from tiannara.domain.models.semantic_resolution import UnresolvedSemanticsError
from tiannara.domain.models.system_model import (
    AbstractFieldType,
    DataModelSpec,
    FieldSpec,
    RequirementsReference,
    ServiceSpec,
    SystemModel,
)


def _clean_model() -> SystemModel:
    return SystemModel(
        system_name="Order Service",
        requirements_ref=RequirementsReference(graph_id="g", graph_hash="h"),
        services=[
            ServiceSpec(
                id="svc-1",
                name="order",
                domain_id="general",
                responsibilities=["serve orders"],
            )
        ],
        data_models=[
            DataModelSpec(
                id="dm-order",
                name="Order",
                owning_service_id="svc-1",
                fields=[
                    FieldSpec(name="id", type=AbstractFieldType.IDENTIFIER),
                    FieldSpec(name="customer", type=AbstractFieldType.TEXT),
                ],
            )
        ],
    )


class _StubIntentCompiler:
    """Implements the IntentCompiler port without an LLM.

    Returns a *typed* (SystemModel-carrying) ISR envelope, which is what the
    pure Cap-C pipeline requires.
    """

    def __init__(self, model: SystemModel) -> None:
        self._model = model

    def compile(self, statement: str, hints: dict) -> IntermediateSoftwareRepresentation:
        return IntermediateSoftwareRepresentation.from_system_model(
            hints.get("system_id") or "sys-stub", self._model
        )


def _registry_with_fastapi() -> CompilerRegistry:
    reg = CompilerRegistry()
    reg.register(
        FastAPIHexagonalBackend(),
        BackendCapabilityDeclaration(
            backend_id="fastapi_hexagonal",
            artifact_kinds=[ArtifactKind.BACKEND_SERVICE],
            capabilities=list(BundleCapability),
            quality_profile=0.8,
            metadata={"language": "python", "framework": "fastapi"},
        ),
    )
    return reg


def test_compile_intent_produces_verified_report():
    compiler = ProjectCompiler(_StubIntentCompiler(_clean_model()), _registry_with_fastapi())
    report = compiler.compile_intent("Build an order management service", {})
    assert isinstance(report, ProjectCompilationReport)
    assert report.ok is True
    assert len(report.outcomes) == 1
    outcome = report.outcomes[0]
    assert outcome.status == "success"
    assert outcome.verification_reason == ""
    assert outcome.verification_report is not None
    assert outcome.verification_report.ok is True
    assert report.plan_id
    assert report.isr_hash


def test_compile_intent_provenance_hashes_match_inputs():
    stub = _StubIntentCompiler(_clean_model())
    compiler = ProjectCompiler(stub, _registry_with_fastapi())
    statement = "Build an order management service"
    report = compiler.compile_intent(statement, {"system_id": "sys-1"})
    expected_isr = stub.compile(statement, {"system_id": "sys-1"})
    assert report.statement_hash == hashlib.sha256(
        statement.encode("utf-8")
    ).hexdigest()
    assert report.isr_hash == expected_isr.content_hash()


def test_compile_intent_raises_on_unsatisfiable_requirement():
    compiler = ProjectCompiler(_StubIntentCompiler(_clean_model()), CompilerRegistry())
    with pytest.raises(ProjectCompilationError):
        compiler.compile_intent("Build an order management service", {})


def test_compile_intent_raises_when_backend_execution_fails():
    class _FailingBackend:
        def generate(self, system_model):
            raise RuntimeError("kaboom")

    reg = CompilerRegistry()
    reg.register(
        _FailingBackend(),
        BackendCapabilityDeclaration(
            backend_id="broken",
            artifact_kinds=[ArtifactKind.BACKEND_SERVICE],
            capabilities=[
                BundleCapability.TEST,
                BundleCapability.HEALTH_CHECK,
                BundleCapability.CONTAINERIZE,
            ],
            quality_profile=0.9,
        ),
    )
    compiler = ProjectCompiler(_StubIntentCompiler(_clean_model()), reg)
    with pytest.raises(ProjectCompilationError) as exc:
        compiler.compile_intent("x", {})
    assert "kaboom" in str(exc.value)


def test_compile_intent_raises_on_legacy_non_typed_isr():
    class _LegacyIntentCompiler:
        def compile(self, statement: str, hints: dict) -> IntermediateSoftwareRepresentation:
            return IntermediateSoftwareRepresentation(
                system_id="legacy",
                system_name="Legacy Service",
                intent=IntentSpecification(statement=statement, domain="general"),
            )

    compiler = ProjectCompiler(_LegacyIntentCompiler(), _registry_with_fastapi())
    with pytest.raises(ProjectCompilationError):
        compiler.compile_intent("anything", {})


def test_unknown_backend_result_blocks_certification():
    class _OpaqueBackend:
        def generate(self, system_model):
            return object()  # not a CompilationResult

    reg = CompilerRegistry()
    reg.register(
        _OpaqueBackend(),
        BackendCapabilityDeclaration(
            backend_id="opaque",
            artifact_kinds=[ArtifactKind.BACKEND_SERVICE],
            capabilities=[
                BundleCapability.TEST,
                BundleCapability.HEALTH_CHECK,
                BundleCapability.CONTAINERIZE,
            ],
            quality_profile=0.9,
        ),
    )
    compiler = ProjectCompiler(_StubIntentCompiler(_clean_model()), reg)
    with pytest.raises(ProjectCompilationError) as exc:
        compiler.compile_intent("x", {})
    assert "UNKNOWN" in str(exc.value)



def _full_compilation_result(statement: str, *, include_context: bool = True):
    from types import SimpleNamespace

    from tiannara.application.compiler.source_projection import (
        create_source_projection_context,
    )
    from tiannara.application.intent.prompts import normalize
    from tiannara.domain.models.requirement_graph import (
        GraphProvenance,
        RequirementGraph,
        RequirementKind,
        RequirementNode,
    )
    from tiannara.domain.models.semantic_resolution import SemanticResolutionRecord

    normalized = normalize(statement)
    graph = RequirementGraph(
        graph_id="phase16-source-bound-graph",
        nodes=[
            RequirementNode(
                id="REQ-order-service",
                kind=RequirementKind.FUNCTIONAL,
                statement="Provide an order management service.",
                acceptance_criteria=["Orders can be created and retrieved."],
            )
        ],
        provenance=GraphProvenance(
            origin="test-fixture",
            source_statement_hash=normalized.source_statement_hash,
        ),
    )
    resolution = SemanticResolutionRecord(
        graph_id=graph.graph_id,
        graph_hash=graph.content_hash(),
        required_fields=(),
        resolutions=(),
    )
    result = {
        "system_id": "phase16-source-bound",
        "isr": IntermediateSoftwareRepresentation.from_system_model(
            "phase16-source-bound", _clean_model()
        ),
        "requirement_graph": graph,
        "call_records": [],
        "semantic_resolution_record": None,
        "authorization_semantic_obligations": None,
    }
    if include_context:
        result["source_projection_context"] = create_source_projection_context(
            source_id="test:phase16-source-bound",
            source_bytes=statement.encode("utf-8"),
            graph=graph,
            semantic_resolution=resolution,
        )
    return SimpleNamespace(**result)


class _FullResultIntentCompiler:
    def __init__(self, *, include_context: bool = True):
        self.include_context = include_context

    def compile_full(self, statement, system_id, *, taskflow_semantic_gate=False):
        return _full_compilation_result(
            statement, include_context=self.include_context
        )


def test_generic_generation_blocks_when_source_context_is_missing():
    compiler = ProjectCompiler(
        _FullResultIntentCompiler(include_context=False),
        _registry_with_fastapi(),
    )
    with pytest.raises(ProjectCompilationError, match="no validated source projection context"):
        compiler.compile_intent("Build an order management service", {})


def test_generic_generation_accepts_matching_source_context_and_graph_identity():
    statement = "Build an order management service"
    compiler = ProjectCompiler(
        _FullResultIntentCompiler(include_context=True),
        _registry_with_fastapi(),
    )
    report = compiler.compile_intent(statement, {})
    assert report.ok is True
    assert report.generation_mode == "no_model_calls"

def test_taskflow_mode_activates_pre_synthesis_gate_before_backend_planning():
    class _GateIntentCompiler:
        def compile_full(self, statement, system_id, *, taskflow_semantic_gate=False):
            assert taskflow_semantic_gate is True
            raise UnresolvedSemanticsError(("authorization.workspace_membership_scope",))

    compiler = ProjectCompiler(
        _GateIntentCompiler(),
        CompilerRegistry(),
        taskflow_semantic_gate=True,
    )
    with pytest.raises(UnresolvedSemanticsError, match="workspace_membership_scope"):
        compiler.compile_intent("Build TaskFlow", {})
