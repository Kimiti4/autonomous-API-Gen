from types import SimpleNamespace

import pytest

from constitutional_architecture.compiler.artifacts.artifact_model import Artifact, ArtifactType
from constitutional_architecture.compiler.passes.verification_pass import VerificationPass
from constitutional_architecture.compiler.quality.diagnostics import DiagnosticsCollector, DiagnosticSeverity
from constitutional_architecture.verification import verification_engine


def _context():
    return SimpleNamespace(
        artifacts=[Artifact(path="src/app.py", content="print('ok')", artifact_type=ArtifactType.SOURCE, backend="fastapi")],
        config=SimpleNamespace(target_backends=["fastapi"], source_maps=False),
        diagnostics=DiagnosticsCollector(),
        original_isr=object(),
    )


def test_verification_engine_exception_is_fatal_and_indeterminate(monkeypatch):
    class BrokenEngine:
        def verify(self, **kwargs):
            raise RuntimeError("engine unavailable")

    monkeypatch.setattr(verification_engine, "VerificationEngine", BrokenEngine)
    ctx = _context()

    result = VerificationPass().execute(ctx)

    assert result.success is False
    assert result.metrics["verification_status"] == "INDETERMINATE"
    assert result.metrics["approved_for_deployment"] is False
    diagnostic = next(
        d for d in ctx.diagnostics.diagnostics
        if d.code == "COMP-VERIFY-INDETERMINATE"
    )
    assert diagnostic.severity is DiagnosticSeverity.FATAL


@pytest.mark.parametrize(
    ("approved", "failed_checks"),
    [(False, 0), (True, 1)],
)
def test_non_approving_or_failed_verification_report_blocks_success(
    monkeypatch, approved, failed_checks
):
    class ReportingEngine:
        def verify(self, **kwargs):
            return SimpleNamespace(
                total_checks=3,
                passed_checks=3 - failed_checks,
                failed_checks=failed_checks,
                warning_checks=0,
                approved_for_deployment=approved,
                blocking_failures=(),
            )

    monkeypatch.setattr(verification_engine, "VerificationEngine", ReportingEngine)
    ctx = _context()

    result = VerificationPass().execute(ctx)

    assert result.success is False
    codes = {d.code for d in ctx.diagnostics.diagnostics}
    if not approved:
        assert "COMP-VERIFY-NOT-APPROVED" in codes
    if failed_checks:
        assert "COMP-VERIFY-CHECKS-FAILED" in codes
