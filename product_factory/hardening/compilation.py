"""
Phase 24.3 — Product Compilation Execution with Phase 25 Backends.
"""

from __future__ import annotations

from typing import Any, Dict, List, Protocol
import re

from ..utils import deterministic_id, utcnow
from .models import CompilationJob, CompilationReport, CompilationTarget


class CompilerGateway(Protocol):
    """Abstract compiler gateway."""

    def compile_isr(
        self,
        isr: Dict[str, Any],
        backend_id: str,
        environment: str,
    ) -> Dict[str, Any]:
        ...


class DryRunCompilerGateway:
    """Deterministic dry-run compiler gateway."""

    def compile_isr(
        self,
        isr: Dict[str, Any],
        backend_id: str,
        environment: str,
    ) -> Dict[str, Any]:
        artifacts = [
            f"{backend_id}/README.md",
            f"{backend_id}/artifact-manifest.json",
        ]

        if "openapi" in backend_id:
            artifacts.append(f"{backend_id}/openapi.json")

        if "fastapi" in backend_id:
            artifacts.append(f"{backend_id}/app/main.py")

        if "postgres" in backend_id:
            artifacts.append(f"{backend_id}/migrations/0001_initial.sql")

        if "docker" in backend_id:
            artifacts.append(f"{backend_id}/Dockerfile")

        if "github_actions" in backend_id:
            artifacts.append(f"{backend_id}/.github/workflows/ci.yml")

        return {
            "mode": "dry_run",
            "artifacts": [],
            "planned_artifacts": artifacts,
            "evidence_status": "NOT_EXECUTED",
            "logs": [
                f"Dry-run compilation for backend {backend_id}; no files were generated.",
                f"Environment: {environment}.",
            ],
        }


def default_compilation_targets() -> List[CompilationTarget]:
    return [
        CompilationTarget(backend_id="openapi.spec"),
        CompilationTarget(backend_id="python.fastapi.foundation"),
        CompilationTarget(backend_id="postgres.schema"),
        CompilationTarget(backend_id="deployment.docker"),
        CompilationTarget(backend_id="cicd.github_actions"),
    ]


class CompilationExecutor:
    """Executes product compilation through compiler backends."""

    def __init__(
        self,
        gateway: CompilerGateway | None = None,
    ) -> None:
        self.gateway = gateway or DryRunCompilerGateway()

    def execute(
        self,
        product_id: str,
        isr: Dict[str, Any],
        targets: List[CompilationTarget] | None = None,
        environment: str = "development",
    ) -> CompilationReport:
        targets = targets or default_compilation_targets()

        jobs: List[CompilationJob] = []

        missing_required_backends: List[str] = []

        artifact_count = 0

        created_at = utcnow().isoformat()

        for target in targets:
            job_id = deterministic_id(
                "compilation_job",
                {
                    "product_id": product_id,
                    "backend_id": target.backend_id,
                    "environment": environment,
                    "created_at": created_at,
                },
            )

            job = CompilationJob(
                id=job_id,
                product_id=product_id,
                backend_id=target.backend_id,
                status="RUNNING",
                created_at=created_at,
            )

            try:
                output = self.gateway.compile_isr(
                    isr=isr,
                    backend_id=target.backend_id,
                    environment=environment,
                )

                mode = output.get("mode", "unknown")
                artifacts = output.get("artifacts", [])
                planned_artifacts = output.get("planned_artifacts", [])
                logs = output.get("logs", [])

                job.execution_mode = mode
                job.planned_artifacts = planned_artifacts
                job.logs = logs

                if mode == "executed" and output.get("execution_evidence"):
                    evidence = output["execution_evidence"]
                    if (
                        isinstance(evidence, dict)
                        and type(evidence.get("exit_code")) is int
                        and evidence.get("exit_code") == 0
                        and isinstance(evidence.get("artifact_manifest_sha256"), str)
                        and re.fullmatch(r"[0-9a-f]{64}", evidence["artifact_manifest_sha256"])
                        and isinstance(artifacts, list)
                        and bool(artifacts)
                        and all(isinstance(path, str) and path.strip() for path in artifacts)
                    ):
                        job.status = "SUCCEEDED"
                        job.evidence_status = "REPORTED"
                        job.artifacts = artifacts
                        artifact_count += len(artifacts)
                    else:
                        job.status = "UNKNOWN"
                        job.evidence_status = "INVALID"
                        job.logs.append(
                            "Execution output lacked valid exit-code and artifact-manifest evidence."
                        )
                        if target.required:
                            missing_required_backends.append(target.backend_id)
                elif mode == "dry_run":
                    job.status = "DRY_RUN"
                    job.evidence_status = "NOT_EXECUTED"
                    job.artifacts = []
                    job.logs.append(
                        "Dry-run output is planning evidence only; it cannot satisfy a required compilation target."
                    )
                    if target.required:
                        missing_required_backends.append(target.backend_id)
                else:
                    job.status = "UNKNOWN"
                    job.evidence_status = "MISSING"
                    job.artifacts = []
                    job.logs.append(
                        "Backend did not provide recognized execution evidence; success is not inferred."
                    )
                    if target.required:
                        missing_required_backends.append(target.backend_id)

            except Exception as exc:
                job.status = "FAILED"
                job.logs = [str(exc)]

                if target.required:
                    missing_required_backends.append(target.backend_id)

            jobs.append(job)

        success = (
            all(job.status == "SUCCEEDED" for job in jobs)
            and not missing_required_backends
        )

        return CompilationReport(
            product_id=product_id,
            success=success,
            jobs=jobs,
            missing_required_backends=missing_required_backends,
            artifact_count=artifact_count,
            created_at=created_at,
        )
