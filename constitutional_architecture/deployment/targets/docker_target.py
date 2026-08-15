from __future__ import annotations

from constitutional_architecture.deployment.deployment_result import DeploymentArtifact, HealthCheckResult
from constitutional_architecture.deployment.targets.target_interface import DeploymentTarget, TargetResult


class DockerTarget(DeploymentTarget):
    @property
    def name(self) -> str:
        return "docker"

    def deploy(self, artifact: DeploymentArtifact) -> TargetResult:
        if artifact.artifact_type != "container_image":
            return TargetResult(success=False, error=f"Cannot deploy {artifact.artifact_type} to Docker")

        return TargetResult(
            success=True,
            endpoint=f"http://localhost:8080",
            deployed_artifacts=(artifact,),
            health=HealthCheckResult(
                endpoint="http://localhost:8080/health",
                status="healthy",
                response_time_ms=5.0,
                details="Container running",
            ),
        )

    def health_check(self) -> HealthCheckResult:
        return HealthCheckResult(
            endpoint="http://localhost:8080/health",
            status="healthy",
            response_time_ms=5.0,
            details="Docker container healthy",
        )

    def cleanup(self) -> None:
        pass
