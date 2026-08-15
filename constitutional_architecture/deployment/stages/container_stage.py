from __future__ import annotations

import time

from constitutional_architecture.deployment.deployment_context import DeploymentContext
from constitutional_architecture.deployment.deployment_result import DeploymentArtifact
from constitutional_architecture.deployment.stages.stage_interface import DeploymentStage, StageResult


class ContainerStage(DeploymentStage):
    @property
    def name(self) -> str:
        return "containerize"

    @property
    def description(self) -> str:
        return "Build container images from packaged artifacts"

    @property
    def dependencies(self) -> list[str]:
        return ["package"]

    def execute(self, ctx: DeploymentContext) -> StageResult:
        start = time.perf_counter()

        package_result = ctx.get_stage_result("package")
        if package_result is None or not package_result.success:
            return StageResult(
                stage_name=self.name,
                success=False,
                duration_seconds=time.perf_counter() - start,
                error="Package stage did not complete successfully",
            )

        isr = ctx.isr
        image_name = f"{isr.system.name.lower()}:latest"

        container_artifact = DeploymentArtifact(
            artifact_type="container_image",
            name=image_name,
            location=f"registry.local/{image_name}",
            metadata={"tag": "latest", "base_image": "python:3.11-slim"},
        )

        duration = time.perf_counter() - start
        return StageResult(
            stage_name=self.name,
            success=True,
            duration_seconds=duration,
            artifacts=(container_artifact,),
            metrics={"image_name": image_name},
        )
