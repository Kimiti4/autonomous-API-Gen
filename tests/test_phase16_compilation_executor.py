"""Phase 16 — CompilationExecutor semantics (collect-all, never raises)."""

import pytest

from tiannara.application.compiler.executor import (
    CompilationExecutor,
    ExecutionReport,
)
from tiannara.application.compiler.registry import CompilerRegistry
from tiannara.application.compiler.selector import plan_compilation
from tiannara.domain.models.backend_declaration import (
    ArtifactKind,
    BackendCapabilityDeclaration,
    CompilationPlan,
    CompilationRequirement,
)
from tiannara.domain.models.capability_manifest import (
    BundleCapability,
    CapabilityManifest,
)
from tiannara.domain.models.compilation import CompilationResult


class _StubBackend:
    def __init__(self, result=None, raises=None):
        self._result = result
        self._raises = raises

    def generate(self, system_model):
        if self._raises is not None:
            raise self._raises
        return self._result


def _requirement():
    return CompilationRequirement(
        artifact_kind=ArtifactKind.BACKEND_SERVICE,
        required_capabilities=[
            BundleCapability.TEST,
            BundleCapability.HEALTH_CHECK,
            BundleCapability.CONTAINERIZE,
        ],
    )


def _declaration(backend_id="stub"):
    return BackendCapabilityDeclaration(
        backend_id=backend_id,
        artifact_kinds=[ArtifactKind.BACKEND_SERVICE],
        capabilities=[
            BundleCapability.TEST,
            BundleCapability.HEALTH_CHECK,
            BundleCapability.CONTAINERIZE,
        ],
        quality_profile=0.5,
    )


def _stub_result():
    return CompilationResult(
        backend_id="stub",
        system_name="stub_service",
        files={"stub_service/main.py": "def health():\n    return {'status': 'ok'}\n"},
        capability_manifest=CapabilityManifest(
            backend_id="stub", capabilities=[BundleCapability.TEST]
        ),
    )


def test_execute_records_success_outcome():
    reg = CompilerRegistry()
    reg.register(_StubBackend(result=_stub_result()), _declaration("stub"))
    plan = plan_compilation(reg, [_requirement()])
    report = CompilationExecutor(reg).execute(plan, system_model=None)
    assert report.ok is True
    assert report.plan_id == plan.plan_id
    assert len(report.outcomes) == 1
    outcome = report.outcomes[0]
    assert outcome.status == "success"
    assert isinstance(outcome.result, CompilationResult)
    assert outcome.error is None


def test_execute_does_not_raise_on_backend_failure():
    reg = CompilerRegistry()
    reg.register(_StubBackend(raises=RuntimeError("boom")), _declaration("boom"))
    plan = plan_compilation(reg, [_requirement()])
    report = CompilationExecutor(reg).execute(plan, system_model=None)
    assert report.ok is False
    assert report.outcomes[0].status == "failed"
    assert "boom" in report.outcomes[0].error


def test_execute_collects_all_outcomes_across_multiple_requirements():
    reg = CompilerRegistry()
    reg.register(_StubBackend(raises=RuntimeError("boom")), _declaration("boom"))
    plan = plan_compilation(reg, [_requirement(), _requirement()])
    report = CompilationExecutor(reg).execute(plan, system_model=None)
    # Two planned, both attempted (collect-all), both failed, no raise.
    assert len(report.outcomes) == 2
    assert all(o.status == "failed" for o in report.outcomes)
    assert report.ok is False


def test_execute_empty_plan_is_ok():
    reg = CompilerRegistry()
    plan = CompilationPlan(plan_id="empty", policy_name="default", planned=[])
    report = CompilationExecutor(reg).execute(plan, system_model=None)
    assert report.ok is True
    assert report.outcomes == []
