from __future__ import annotations

from constitutional_architecture.deployment.deployment_result import DeploymentArtifact, HealthCheckResult
from constitutional_architecture.deployment.targets.target_interface import (
    DeploymentTarget, TargetExecutor, TargetResult,
)


class KubernetesTarget(DeploymentTarget):
    """Kubernetes target; requires an injected client adapter.

    Without an executor this target fails closed instead of reporting a
    synthetic endpoint and a fabricated healthy status.
    """

    def __init__(self, executor: TargetExecutor | None = None) -> None:
        self._executor = executor

    @property
    def name(self) -> str:
        return "kubernetes"

    def deploy(self, artifact: DeploymentArtifact) -> TargetResult:
        if artifact.artifact_type != "container_image":
            return TargetResult(success=False, error=f"Cannot deploy {artifact.artifact_type} to Kubernetes")

        if self._executor is None:
            return TargetResult(
                success=False,
                error=(
                    "KubernetesTarget requires an injected TargetExecutor; "
                    "refusing to report a synthetic deployment."
                ),
                diagnostics=("No cluster adapter configured; deployment was not attempted.",),
            )

        result = self._executor.deploy(artifact)
        if result.success and not result.endpoint.strip():
            return TargetResult(
                success=False,
                error="Kubernetes executor reported success without an endpoint.",
            )
        return result

    def health_check(self) -> HealthCheckResult:
        if self._executor is None:
            return HealthCheckResult(
                endpoint="",
                status="unknown",
                details="No Kubernetes executor configured; health is unknown, not healthy.",
            )
        return self._executor.health_check()

    def cleanup(self) -> None:
        if self._executor is not None:
            self._executor.cleanup()
