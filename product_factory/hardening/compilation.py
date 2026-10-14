"""
Phase 24.3 — Product Compilation Execution with Phase 25 Backends.
"""

from __future__ import annotations

from typing import Any, Dict, List, Protocol

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


class CompilerGatewayNotConfigured(RuntimeError):
    """Raised when no real compiler gateway has been configured."""


class UnconfiguredCompilerGateway:
    """Fail-closed default: no generation is claimed without a real gateway."""

    def compile_isr(
        self,
        isr: Dict[str, Any],
        backend_id: str,
        environment: str,
    ) -> Dict[str, Any]:
        raise CompilerGatewayNotConfigured(
            "No real compiler gateway is configured. Supply a production "
            "CompilerGateway or explicitly select DryRunCompilerGateway."
        )


class DryRunCompilerGateway:
    """Planning-only gateway; it never reports planned paths as emitted artifacts."""

    def compile_isr(
        self,
        isr: Dict[str, Any],
        backend_id: str,
        environment: str,
    ) -> Dict[str, Any]:
        planned_artifacts = [
            f"{backend_id}/README.md",
            f"{backend_id}/artifact-manifest.json",
        ]

        if "openapi" in backend_id:
            planned_artifacts.append(f"{backend_id}/openapi.json")

        if "fastapi" in backend_id:
            planned_artifacts.append(f"{backend_id}/app/main.py")

        if "postgres" in backend_id:
            planned_artifacts.append(f"{backend_id}/migrations/0001_initial.sql")

        if "docker" in backend_id:
            planned_artifacts.append(f"{backend_id}/Dockerfile")

        if "github_actions" in backend_id:
            planned_artifacts.append(f"{backend_id}/.github/workflows/ci.yml")

        return {
            "mode": "dry_run",
            "artifacts": [],
            "planned_artifacts": planned_artifacts,
            "logs": [
                f"Dry-run plan only for backend {backend_id}; no files were emitted.",
                f"Environment: {environment}.",
                "Planned paths are not build artifacts and cannot satisfy a required backend.",
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
        self.gateway = gateway or UnconfiguredCompilerGateway()

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

                artifacts = output.get("artifacts", [])
                logs = output.get("logs", [])

                if output.get("mode") == "dry_run":
                    planned = output.get("planned_artifacts", [])
                    job.status = "DRY_RUN"
                    job.artifacts = []
                    job.logs = list(logs) + [
                        "Planned only: " + ", ".join(str(item) for item in planned)
                    ]
                    if target.required:
                        missing_required_backends.append(target.backend_id)
                else:
                    if not artifacts:
                        raise RuntimeError(
                            "compiler gateway returned no emitted artifacts; "
                            "empty output cannot count as compilation success"
                        )
                    job.status = "SUCCEEDED"
                    job.artifacts = artifacts
                    job.logs = logs
                    artifact_count += len(artifacts)

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
