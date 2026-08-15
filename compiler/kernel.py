"""
Universal Compiler kernel.

The kernel coordinates:
- ISR validation
- backend resolution
- compilation planning
- optimization passes
- backend compilation
- output validation
- artifact packaging
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from .errors import (
    CompilationOutputValidationError,
    CompilerError,
    ISRValidationError,
)
from .ids import deterministic_id
from .models import (
    CompilationPlan,
    CompilationRequest,
    CompilationResult,
    CompilationContext,
    utcnow,
)
from .optimization import OptimizationPipeline
from .packaging import ArtifactPackager
from .registry import BackendRegistry
from .validation import (
    validate_compilation_output,
    validate_isr_payload,
)


class UniversalCompiler:
    """Universal Software Compiler kernel."""

    def __init__(
        self,
        registry: BackendRegistry,
        output_root: str | Path,
    ) -> None:
        self.registry = registry
        self.output_root = Path(output_root)
        self.jobs: dict[str, CompilationResult] = {}

    def compile(self, request: CompilationRequest) -> CompilationResult:
        """Compile an ISR payload using the requested backend."""

        started_at = utcnow().isoformat()

        job_id = deterministic_id(
            "compilation_job",
            {
                "request": request.model_dump(mode="json"),
                "started_at": started_at,
            },
        )

        logs: list[str] = []

        isr_report = validate_isr_payload(request.isr)

        if not isr_report.valid:
            self._store_failed_job(
                job_id=job_id,
                started_at=started_at,
                error="ISR validation failed.",
                logs=logs,
                validation_report=isr_report,
            )

            raise ISRValidationError("ISR validation failed.", isr_report)

        backend = self.registry.get_backend(
            request.target.backend_id,
            request.target.backend_version,
        )

        manifest = backend.manifest

        plan = self._build_plan(
            request=request,
            manifest=manifest,
            job_id=job_id,
        )

        pipeline = OptimizationPipeline()

        executed_passes = pipeline.run(
            plan=plan,
            isr=request.isr,
            logs=logs,
        )

        plan.passes = executed_passes

        output_directory = self.output_root / job_id

        context = CompilationContext(
            plan=plan,
            isr=request.isr,
            output_directory=str(output_directory),
        )

        try:
            output = backend.compile(context)
        except Exception as exc:
            self._store_failed_job(
                job_id=job_id,
                started_at=started_at,
                error=f"Backend compilation failed: {exc}",
                logs=logs,
            )

            raise CompilerError(f"Backend compilation failed: {exc}") from exc

        logs.extend(output.logs)

        output_report = validate_compilation_output(output)

        if not output_report.valid:
            self._store_failed_job(
                job_id=job_id,
                started_at=started_at,
                error="Backend output validation failed.",
                logs=logs,
                validation_report=output_report,
            )

            raise CompilationOutputValidationError(
                "Backend output validation failed.",
                output_report,
            )

        packager = ArtifactPackager()

        artifact_manifest = packager.package(
            output=output,
            job_id=job_id,
            backend_id=manifest.backend_id,
            backend_version=manifest.version,
            output_root=output_directory,
        )

        result = CompilationResult(
            job_id=job_id,
            status="SUCCEEDED",
            plan=plan,
            started_at=started_at,
            completed_at=utcnow().isoformat(),
            artifact_manifest=artifact_manifest,
            validation_report=output_report,
            logs=logs,
        )

        self.jobs[job_id] = result

        return result

    def get_job(self, job_id: str) -> Optional[CompilationResult]:
        """Get a compilation job by ID."""
        return self.jobs.get(job_id)

    def _build_plan(
        self,
        request: CompilationRequest,
        manifest,
        job_id: str,
    ) -> CompilationPlan:
        plan_id = deterministic_id(
            "compilation_plan",
            {
                "job_id": job_id,
                "backend_id": manifest.backend_id,
                "backend_version": manifest.version,
                "isr_id": request.isr.get("isr_id"),
                "isr_version": request.isr.get("version"),
            },
        )

        return CompilationPlan(
            plan_id=plan_id,
            isr_id=str(request.isr.get("isr_id")),
            isr_version=str(request.isr.get("version")),
            backend_id=manifest.backend_id,
            backend_version=manifest.version,
            environment=request.environment,
            parameters=request.target.parameters,
            passes=[],
            validation_level="standard",
            created_at=utcnow().isoformat(),
        )

    def _store_failed_job(
        self,
        job_id: str,
        started_at: str,
        error: str,
        logs: list[str],
        validation_report=None,
    ) -> None:
        result = CompilationResult(
            job_id=job_id,
            status="FAILED",
            plan=None,
            started_at=started_at,
            completed_at=utcnow().isoformat(),
            artifact_manifest=None,
            validation_report=validation_report,
            logs=logs,
            error=error,
        )

        self.jobs[job_id] = result