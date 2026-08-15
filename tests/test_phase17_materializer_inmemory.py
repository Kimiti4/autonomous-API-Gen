"""Phase 17 -- RepositoryMaterializer against the in-memory SourceControlBackend."""
from __future__ import annotations

import pytest

from tiannara.application.compiler.project_compiler import (
    ProjectOutcome,
    ProjectCompilationReport,
)
from tiannara.application.compiler.verification import BundleVerificationReport
from tiannara.application.materializer.materializer import (
    MaterializationError,
    RepositoryMaterializer,
)
from tiannara.domain.models.backend_declaration import (
    ArtifactKind,
    BackendCapabilityDeclaration,
)
from tiannara.domain.models.capability_manifest import (
    BundleCapability,
    CapabilityManifest,
)
from tiannara.domain.models.compilation import CompilationResult
from tiannara.infrastructure.source_control.in_memory import InMemorySourceControlBackend

STATEMENT = "Order Management"
_SYSTEM = "order-management"


def _capability_manifest() -> CapabilityManifest:
    return CapabilityManifest(
        backend_id="fastapi_hexagonal",
        capabilities=[
            BundleCapability.BUILD,
            BundleCapability.TEST,
            BundleCapability.HEALTH_CHECK,
            BundleCapability.CONTAINERIZE,
        ],
        metadata={"language": "python"},
    )


def _result(system_name: str = _SYSTEM, files: dict | None = None) -> CompilationResult:
    return CompilationResult(
        backend_id="fastapi_hexagonal",
        system_name=system_name,
        files=files or {f"{_SYSTEM}/main.py": "x = 1"},
        capability_manifest=_capability_manifest(),
    )


def _outcome(
    result: CompilationResult | None = None,
    ok: bool = True,
    verification_ok: bool = True,
) -> ProjectOutcome:
    from tiannara.domain.models.backend_declaration import CompilationRequirement
    from tiannara.domain.models.backend_declaration import PlannedCompilation

    requirement = CompilationRequirement(
        artifact_kind=ArtifactKind.BACKEND_SERVICE,
        required_capabilities=[BundleCapability.TEST],
    )
    declaration = BackendCapabilityDeclaration(
        backend_id="fastapi_hexagonal",
        artifact_kinds=[ArtifactKind.BACKEND_SERVICE],
        capabilities=[BundleCapability.TEST, BundleCapability.HEALTH_CHECK],
    )
    planned = PlannedCompilation(
        requirement=requirement, backend_id="fastapi_hexagonal", declaration=declaration
    )
    vr = (
        BundleVerificationReport(ok=verification_ok)
        if verification_ok
        else BundleVerificationReport(ok=False, syntax_errors=["boom"])
    )
    return ProjectOutcome(
        planned=planned,
        status="success" if ok else "failed",
        result=result or _result(),
        error=None,
        verification_report=vr,
        verification_reason="" if verification_ok else "verification failed",
    )


def _report(*outcomes: ProjectOutcome) -> ProjectCompilationReport:
    import hashlib
    return ProjectCompilationReport(
        statement_hash=hashlib.sha256(STATEMENT.encode()).hexdigest(),
        isr_hash="isr-hash-1",
        plan_id="plan-1",
        outcomes=list(outcomes),
        ok=True,
    )


def test_materializes_verified_bundle_with_vcs_and_manifest(tmp_path):
    outcome = _outcome()
    report = _report(outcome)
    backend = InMemorySourceControlBackend()
    materializer = RepositoryMaterializer(backend)

    result = materializer.materialize(report, tmp_path, build_id="b-1")

    assert result.commit is not None
    assert result.commit.commit_id.startswith("sha-")
    assert result.commit.branch == "main"
    assert (tmp_path / "provenance" / "manifest.json").exists()
    assert (tmp_path / _SYSTEM / "main.py").read_text() == "x = 1"
    manifest_text = (tmp_path / "provenance" / "manifest.json").read_text()
    assert "isr-hash-1" in manifest_text
    assert '"forced": false' in manifest_text
    assert '"ok": true' in manifest_text
    method_names = [call[0] for call in backend.calls]
    assert method_names == ["init", "add", "commit", "branch"]
    add_call = backend.calls[1]
    assert "provenance/manifest.json" in add_call[1]["paths"]


def test_materializer_refuses_unverified_bundle_without_force(tmp_path):
    outcome = _outcome(verification_ok=False)
    report = _report(outcome)
    materializer = RepositoryMaterializer(InMemorySourceControlBackend())
    with pytest.raises(MaterializationError, match="verification failed"):
        materializer.materialize(report, tmp_path)
    assert not (tmp_path / "provenance" / "manifest.json").exists()


def test_force_records_verification_override_in_manifest(tmp_path):
    outcome = _outcome(verification_ok=False)
    report = _report(outcome)
    backend = InMemorySourceControlBackend()
    materializer = RepositoryMaterializer(backend)

    result = materializer.materialize(report, tmp_path, force=True, build_id="b-2")

    assert result.commit is not None
    manifest = (tmp_path / "provenance" / "manifest.json").read_text()
    assert '"forced": true' in manifest
    assert "forced_reason" in manifest


def test_materializer_without_sc_backend_still_writes_tree_and_manifest(tmp_path):
    report = _report(_outcome())
    materializer = RepositoryMaterializer(sc_backend=None)
    result = materializer.materialize(report, tmp_path, build_id="b-3")
    assert result.commit is None
    assert (tmp_path / "provenance" / "manifest.json").exists()
    assert (tmp_path / _SYSTEM / "main.py").exists()


def test_materializer_rejects_report_with_no_successful_bundles(tmp_path):
    failed = ProjectOutcome(
        planned=_outcome().planned,
        status="failed",
        result=None,
        error="kaboom",
        verification_report=None,
        verification_reason="backend execution failed",
    )
    report = ProjectCompilationReport(
        statement_hash="s", isr_hash="i", plan_id="p", outcomes=[failed], ok=False
    )
    with pytest.raises(MaterializationError, match="no successful"):
        RepositoryMaterializer(None).materialize(report, tmp_path)
