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


def test_unsupported_backend_result_skips_verification_but_still_succeeds():
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
    report = compiler.compile_intent("x", {})
    assert report.ok is True
    outcome = report.outcomes[0]
    assert outcome.status == "success"
    assert outcome.verification_report is None
    assert "CompilationResult" in outcome.verification_reason
