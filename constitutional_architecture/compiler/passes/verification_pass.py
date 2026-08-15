from __future__ import annotations

import time
from typing import Any

from constitutional_architecture.compiler.artifacts.artifact_model import Artifact, ArtifactType
from constitutional_architecture.compiler.compiler_context import CompilerContext
from constitutional_architecture.compiler.pass_interface import CompilerPass, PassResult
from constitutional_architecture.compiler.quality.diagnostics import Diagnostic, DiagnosticSeverity


class VerificationPass(CompilerPass):
    @property
    def identifier(self) -> str:
        return "verification"

    @property
    def description(self) -> str:
        return "Verify generated artifacts for completeness and consistency"

    @property
    def dependencies(self) -> list[str]:
        return ["code_generation"]

    @property
    def input_requirements(self) -> set[str]:
        return {"artifacts_generated"}

    @property
    def output_guarantees(self) -> set[str]:
        return {"artifacts_verified"}

    def execute(self, ctx: CompilerContext) -> PassResult:
        start = time.perf_counter()
        metrics: dict[str, Any] = {}

        compiler_checks = self._run_compiler_checks(ctx)
        metrics["compiler_checks"] = len(compiler_checks)
        metrics["compiler_checks_passed"] = sum(1 for c in compiler_checks if c[0])

        compiler_failures = [c for c in compiler_checks if not c[0]]
        if compiler_failures:
            for check_name, message, severity in compiler_failures:
                ctx.diagnostics.add(Diagnostic(code=f"COMP-VERIFY-{check_name}", message=message, severity=severity))

            fatal = [c for c in compiler_failures if c[2] == DiagnosticSeverity.FATAL]
            if fatal:
                return PassResult(success=False,
                    description=f"Verification failed: {len(fatal)} fatal error(s)", metrics=metrics)

        try:
            from constitutional_architecture.verification.verification_context import ArtifactReference
            from constitutional_architecture.verification.verification_engine import VerificationEngine
            from constitutional_architecture.verification.verification_result import VerificationLevel

            engine = VerificationEngine()
            artifact_refs = []
            for artifact in ctx.artifacts:
                if isinstance(artifact, Artifact):
                    artifact_refs.append(ArtifactReference(
                        path=artifact.path, content=artifact.content,
                        artifact_type=artifact.artifact_type.value, backend=artifact.backend,
                        checksum=artifact.checksum,
                        isr_node_id=artifact.source_mapping.isr_node_id if artifact.source_mapping else "",
                    ))

            report = engine.verify(isr=ctx.original_isr, artifacts=artifact_refs, max_level=VerificationLevel.L3_SECURITY)
            metrics["verification_checks"] = report.total_checks
            metrics["verification_passed"] = report.passed_checks
            metrics["verification_failed"] = report.failed_checks
            metrics["verification_warnings"] = report.warning_checks
            metrics["approved_for_deployment"] = report.approved_for_deployment

            for failure in report.blocking_failures:
                ctx.diagnostics.error(f"COMP-VERIFY-BLOCK-{failure.check_id}", f"Blocking failure: {failure.message}")

        except Exception as e:
            ctx.diagnostics.warning("COMP-VERIFY-001", f"Verification Engine failed: {e}")
            metrics["verification_error"] = str(e)

        duration = (time.perf_counter() - start) * 1000
        metrics["duration_ms"] = duration

        return PassResult(
            success=not ctx.diagnostics.has_errors,
            description=f"Verification: {metrics.get('verification_passed', 0)}/{metrics.get('verification_checks', 0)} passed",
            metrics=metrics,
        )

    def _run_compiler_checks(self, ctx: CompilerContext) -> list[tuple[bool, str, Any]]:
        checks: list[tuple[bool, str, Any]] = []

        checks.append((len(ctx.artifacts) > 0,
                       f"{len(ctx.artifacts)} artifact(s) generated",
                       DiagnosticSeverity.FATAL if len(ctx.artifacts) == 0 else DiagnosticSeverity.INFO))

        paths = [a.path for a in ctx.artifacts if isinstance(a, Artifact)]
        duplicates = [p for p in paths if paths.count(p) > 1]
        checks.append((len(duplicates) == 0,
                       f"Duplicate artifact paths: {set(duplicates)}" if duplicates else "No duplicate paths",
                       DiagnosticSeverity.ERROR if duplicates else DiagnosticSeverity.INFO))

        source_artifacts = [a for a in ctx.artifacts if isinstance(a, Artifact) and a.artifact_type == ArtifactType.SOURCE]
        checks.append((len(source_artifacts) > 0,
                       f"{len(source_artifacts)} source artifact(s)",
                       DiagnosticSeverity.ERROR if len(source_artifacts) == 0 else DiagnosticSeverity.INFO))

        config_artifacts = [a for a in ctx.artifacts if isinstance(a, Artifact) and a.artifact_type == ArtifactType.CONFIG]
        checks.append((len(config_artifacts) > 0,
                       f"{len(config_artifacts)} config artifact(s)",
                       DiagnosticSeverity.WARNING if len(config_artifacts) == 0 else DiagnosticSeverity.INFO))

        empty_sources = [a.path for a in source_artifacts if not a.content.strip()]
        checks.append((len(empty_sources) == 0,
                       f"Empty source files: {empty_sources}" if empty_sources else "No empty source files",
                       DiagnosticSeverity.WARNING if empty_sources else DiagnosticSeverity.INFO))

        backends_used = {a.backend for a in ctx.artifacts if isinstance(a, Artifact) and a.backend}
        expected_backends = set(ctx.config.target_backends)
        missing_backends = expected_backends - backends_used
        checks.append((len(missing_backends) == 0,
                       f"Backends with no artifacts: {missing_backends}" if missing_backends else "All backends produced artifacts",
                       DiagnosticSeverity.WARNING if missing_backends else DiagnosticSeverity.INFO))

        if ctx.config.source_maps:
            mapped = [a for a in ctx.artifacts if isinstance(a, Artifact) and a.source_mapping]
            unmapped = len(ctx.artifacts) - len(mapped)
            checks.append((unmapped == 0,
                           f"{unmapped} artifact(s) without source mappings",
                           DiagnosticSeverity.WARNING if unmapped > 0 else DiagnosticSeverity.INFO))

        return checks
