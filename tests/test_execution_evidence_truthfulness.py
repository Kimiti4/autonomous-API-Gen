from product_factory.hardening.compilation import (
    CompilationExecutor,
    CompilationTarget,
    DryRunCompilerGateway,
)
from tiannara.application.publication.deployment_handoff import handoff_to_deployment


class _Gateway:
    def __init__(self, output):
        self.output = output

    def compile_isr(self, *, isr, backend_id, environment):
        return self.output


def test_default_dry_run_never_claims_generated_artifacts_or_success():
    report = CompilationExecutor(gateway=DryRunCompilerGateway()).execute(
        product_id="demo",
        isr={"system": "demo"},
        targets=[CompilationTarget(backend_id="python.fastapi.foundation")],
    )

    assert report.success is False
    assert report.artifact_count == 0
    job = report.jobs[0]
    assert job.status == "DRY_RUN"
    assert job.execution_mode == "dry_run"
    assert job.evidence_status == "NOT_EXECUTED"
    assert job.artifacts == []
    assert job.planned_artifacts
    assert "main.py" in " ".join(job.planned_artifacts)
    assert "no files were generated" in " ".join(job.logs)


def test_missing_execution_mode_and_evidence_is_unknown_not_success():
    report = CompilationExecutor(
        gateway=_Gateway({"artifacts": ["app/main.py"], "logs": ["pretend success"]})
    ).execute(
        product_id="demo",
        isr={"system": "demo"},
        targets=[CompilationTarget(backend_id="backend-a")],
    )

    assert report.success is False
    assert report.artifact_count == 0
    assert report.jobs[0].status == "UNKNOWN"
    assert report.jobs[0].evidence_status == "MISSING"
    assert report.jobs[0].artifacts == []
    assert "backend-a" in report.missing_required_backends


def test_execution_claim_requires_zero_exit_and_sha256_manifest_evidence():
    report = CompilationExecutor(
        gateway=_Gateway(
            {
                "mode": "executed",
                "artifacts": ["app/main.py"],
                "execution_evidence": {
                    "exit_code": 0,
                    "artifact_manifest_sha256": "a" * 64,
                },
                "logs": ["compile completed"],
            }
        )
    ).execute(
        product_id="demo",
        isr={"system": "demo"},
        targets=[CompilationTarget(backend_id="backend-a")],
    )

    assert report.success is True
    assert report.artifact_count == 1
    assert report.jobs[0].status == "SUCCEEDED"
    assert report.jobs[0].evidence_status == "REPORTED"


def test_malformed_manifest_evidence_cannot_pass():
    report = CompilationExecutor(
        gateway=_Gateway(
            {
                "mode": "executed",
                "artifacts": ["app/main.py"],
                "execution_evidence": {
                    "exit_code": 0,
                    "artifact_manifest_sha256": "not-a-digest",
                },
            }
        )
    ).execute(
        product_id="demo",
        isr={"system": "demo"},
        targets=[CompilationTarget(backend_id="backend-a")],
    )

    assert report.success is False
    assert report.jobs[0].status == "UNKNOWN"
    assert report.jobs[0].evidence_status == "INVALID"
    assert report.artifact_count == 0


def test_deployment_handoff_does_not_manufacture_ci_deployment_or_health():
    result = handoff_to_deployment("https://example.invalid/repo")

    assert result["repo"] == "https://example.invalid/repo"
    assert result["ci"] == "unknown"
    assert result["deployed"] is False
    assert result["deployment_status"] == "not_attempted"
    assert result["health"] == "unknown"
    assert result["telemetry"] == "unknown"
    assert not result["evidence"]
    assert len(result["blockers"]) == 3


def test_boolean_exit_code_and_non_list_artifacts_are_not_execution_evidence():
    report = CompilationExecutor(
        gateway=_Gateway(
            {
                "mode": "executed",
                "artifacts": "app/main.py",
                "execution_evidence": {
                    "exit_code": False,
                    "artifact_manifest_sha256": "b" * 64,
                },
            }
        )
    ).execute(
        product_id="demo",
        isr={"system": "demo"},
        targets=[CompilationTarget(backend_id="backend-a")],
    )

    assert report.success is False
    assert report.artifact_count == 0
    assert report.jobs[0].status == "UNKNOWN"
    assert report.jobs[0].evidence_status == "INVALID"
