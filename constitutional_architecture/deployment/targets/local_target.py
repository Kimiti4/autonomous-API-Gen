from __future__ import annotations

from constitutional_architecture.deployment.deployment_result import DeploymentArtifact, HealthCheckResult
from constitutional_architecture.deployment.targets.target_interface import (
    DeploymentTarget, TargetExecutor, TargetResult,
)


class LocalTarget(DeploymentTarget):
    """Local process target; requires an injected runtime adapter.

    Without an executor this target fails closed instead of reporting a
    synthetic endpoint and a fabricated healthy status.
    """

    def __init__(self, executor: TargetExecutor | None = None) -> None:
        self._executor = executor

    @property
    def name(self) -> str:
        return "local"

    def deploy(self, artifact: DeploymentArtifact) -> TargetResult:
        if artifact.artifact_type != "build":
            return TargetResult(success=False, error=f"Cannot deploy {artifact.artifact_type} to local")

        if self._executor is None:
            return TargetResult(
                success=False,
                error=(
                    "LocalTarget requires an injected TargetExecutor; "
                    "refusing to report a synthetic deployment."
                ),
                diagnostics=("No local runtime adapter configured; deployment was not attempted.",),
            )

        result = self._executor.deploy(artifact)
        if result.success and not result.endpoint.strip():
            return TargetResult(
                success=False,
                error="Local executor reported success without an endpoint.",
            )
        return result

    def health_check(self) -> HealthCheckResult:
        if self._executor is None:
            return HealthCheckResult(
                endpoint="",
                status="unknown",
                details="No local executor configured; health is unknown, not healthy.",
            )
        return self._executor.health_check()

    def cleanup(self) -> None:
        if self._executor is not None:
            self._executor.cleanup()
