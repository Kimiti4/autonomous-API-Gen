from __future__ import annotations

import pytest

from product_factory.hardening.compilation import CompilationExecutor, DryRunCompilerGateway
from product_factory.hardening.models import CompilationTarget


class _Gateway:
    def __init__(self, output):
        self.output = output

    def compile_isr(self, isr, backend_id, environment):
        return self.output


def _target():
    return [CompilationTarget(backend_id="python.fastapi.foundation")]


def _reported_execution():
    return {
        "mode": "executed",
        "artifacts": ["app/main.py", "app/manifest.json"],
        "execution_evidence": {
            "exit_code": 0,
            "artifact_manifest_sha256": "a" * 64,
        },
        "logs": ["gateway reports compiler exit code 0"],
    }


def test_gateway_reported_execution_is_distinguished_from_independent_attestation():
    report = CompilationExecutor(gateway=_Gateway(_reported_execution())).execute(
        product_id="p1", isr={"name": "demo"}, targets=_target()
    )

    # A gateway's self-reported success is recorded, but cannot satisfy the
    # required-backend gate without independent verification.
    assert report.success is False
    assert report.artifact_count == 2
    assert report.missing_required_backends == ["python.fastapi.foundation"]
    job = report.jobs[0]
    assert job.status == "SUCCEEDED"
    assert job.execution_mode == "executed"
    assert job.evidence_status == "REPORTED"
    assert job.artifacts == ["app/main.py", "app/manifest.json"]
    assert job.planned_artifacts == []
    assert job.evidence_status not in {"VERIFIED", "CERTIFIED"}


@pytest.mark.parametrize(
    "output",
    [
        {"artifacts": ["fake.py"]},
        {"mode": "executed", "artifacts": ["fake.py"]},
        {
            "mode": "executed",
            "artifacts": ["fake.py"],
            "execution_evidence": {
                "exit_code": True,
                "artifact_manifest_sha256": "a" * 64,
            },
        },
        {
            "mode": "executed",
            "artifacts": ["fake.py"],
            "execution_evidence": {
                "exit_code": 0,
                "artifact_manifest_sha256": "not-a-digest",
            },
        },
        {
            "mode": "executed",
            "artifacts": [],
            "execution_evidence": {
                "exit_code": 0,
                "artifact_manifest_sha256": "a" * 64,
            },
        },
        {
            "mode": "executed",
            "artifacts": ["   "],
            "execution_evidence": {
                "exit_code": 0,
                "artifact_manifest_sha256": "a" * 64,
            },
        },
    ],
)
def test_untrusted_or_malformed_execution_output_cannot_count_as_success(output):
    report = CompilationExecutor(gateway=_Gateway(output)).execute(
        product_id="p1", isr={"name": "demo"}, targets=_target()
    )

    assert report.success is False
    assert report.artifact_count == 0
    assert report.missing_required_backends == ["python.fastapi.foundation"]
    job = report.jobs[0]
    assert job.status == "UNKNOWN"
    assert job.evidence_status in {"MISSING", "INVALID"}
    assert job.artifacts == []


def test_dry_run_keeps_planned_paths_separate_from_artifacts():
    report = CompilationExecutor(gateway=DryRunCompilerGateway()).execute(
        product_id="p1", isr={"name": "demo"}, targets=_target()
    )

    job = report.jobs[0]
    assert report.success is False
    assert report.artifact_count == 0
    assert job.status == "DRY_RUN"
    assert job.evidence_status == "NOT_EXECUTED"
    assert job.artifacts == []
    assert job.planned_artifacts
