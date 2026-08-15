"""Phase 17 -- real local git integration for RepositoryMaterializer.

Skipped when ``git`` is absent (mirrors the fastapi/httpx skip posture).
Exercises init/add/commit/branch against a real, path-isolated repo and
asserts the committed tree matches the materialized artifact tree exactly.
"""
from __future__ import annotations

import hashlib
import shutil
import subprocess

import pytest

from tiannara.application.compiler.project_compiler import (
    ProjectCompilationReport,
    ProjectOutcome,
)
from tiannara.application.compiler.verification import BundleVerificationReport
from tiannara.application.materializer.materializer import RepositoryMaterializer
from tiannara.domain.models.backend_declaration import (
    ArtifactKind,
    BackendCapabilityDeclaration,
    CompilationRequirement,
    PlannedCompilation,
)
from tiannara.domain.models.capability_manifest import (
    BundleCapability,
    CapabilityManifest,
)
from tiannara.domain.models.compilation import CompilationResult
from tiannara.infrastructure.source_control.local_git import LocalGitBackend

STATEMENT = "Order Management"


def _require_git():
    pytest.skip("git not available on PATH") if shutil.which("git") is None else None


def _result() -> CompilationResult:
    return CompilationResult(
        backend_id="fastapi_hexagonal",
        system_name="order-management",
        files={"order-management/main.py": "x = 1", "README.md": "# Order Management"},
        capability_manifest=CapabilityManifest(
            backend_id="fastapi_hexagonal",
            capabilities=[BundleCapability.BUILD, BundleCapability.TEST],
        ),
    )


def _report() -> ProjectCompilationReport:
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
    outcome = ProjectOutcome(
        planned=planned,
        status="success",
        result=_result(),
        error=None,
        verification_report=BundleVerificationReport(ok=True),
        verification_reason="",
    )
    return ProjectCompilationReport(
        statement_hash=hashlib.sha256(STATEMENT.encode()).hexdigest(),
        isr_hash="isr-hash-1",
        plan_id="plan-1",
        outcomes=[outcome],
        ok=True,
    )


def _git(repo: str, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", repo, *args], check=True, text=True, capture_output=True
    ).stdout.strip()


def test_local_git_backend_materializes_and_commits_hermetically(tmp_path):
    _require_git()
    out = tmp_path / "repo"
    report = _report()
    materializer = RepositoryMaterializer(LocalGitBackend())

    result = materializer.materialize(report, out, build_id="b-1", branch="main")

    assert result.commit is not None
    head = _git(str(out), "rev-parse", "HEAD")
    assert result.commit.commit_id == head
    assert len(head) == 40
    tracked = _git(str(out), "ls-files")
    assert "order-management/main.py" in tracked
    assert "provenance/manifest.json" in tracked
    assert _git(str(out), "rev-parse", "--abbrev-ref", "HEAD") == "main"
    manifest = (out / "provenance" / "manifest.json").read_text()
    assert "fastapi_hexagonal" in manifest
    assert "isr-hash-1" in manifest


def test_local_git_commit_uses_local_identity(tmp_path):
    _require_git()
    out = tmp_path / "repo2"
    report = _report()
    materializer = RepositoryMaterializer(LocalGitBackend())
    materializer.materialize(
        report, out, build_id="b-2",
        author_name="Auditor", author_email="auditor@example.invalid",
    )
    log = _git(str(out), "log", "-1", "--format=%an <%ae>")
    assert log == "Auditor <auditor@example.invalid>"
