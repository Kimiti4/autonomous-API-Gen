from __future__ import annotations

from constitutional_architecture.deployment.deployment_result import DeploymentArtifact, HealthCheckResult
from constitutional_architecture.deployment.targets.target_interface import DeploymentTarget, TargetResult


class LocalTarget(DeploymentTarget):
    @property
    def name(self) -> str:
        return "local"

    def deploy(self, artifact: DeploymentArtifact) -> TargetResult:
        if artifact.artifact_type != "build":
            return TargetResult(success=False, error=f"Cannot deploy {artifact.artifact_type} to local")

        return TargetResult(
            success=True,
            endpoint="http://localhost:5000",
            deployed_artifacts=(artifact,),
            health=HealthCheckResult(
                endpoint="http://localhost:5000/health",
                status="healthy",
                response_time_ms=2.0,
                details="Local deployment healthy",
            ),
        )

    def health_check(self) -> HealthCheckResult:
        return HealthCheckResult(
            endpoint="http://localhost:5000/health",
            status="healthy",
            response_time_ms=2.0,
            details="Local process healthy",
        )

    def cleanup(self) -> None:
        pass
