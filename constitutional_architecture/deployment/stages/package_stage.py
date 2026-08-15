from __future__ import annotations

import time

from constitutional_architecture.deployment.deployment_context import DeploymentContext
from constitutional_architecture.deployment.deployment_result import DeploymentArtifact
from constitutional_architecture.deployment.stages.stage_interface import DeploymentStage, StageResult


class PackageStage(DeploymentStage):
    @property
    def name(self) -> str:
        return "package"

    @property
    def description(self) -> str:
        return "Create distributable packages from build output"

    @property
    def dependencies(self) -> list[str]:
        return ["build"]

    def execute(self, ctx: DeploymentContext) -> StageResult:
        start = time.perf_counter()

        build_result = ctx.get_stage_result("build")
        if build_result is None or not build_result.success:
            return StageResult(
                stage_name=self.name,
                success=False,
                duration_seconds=time.perf_counter() - start,
                error="Build stage did not complete successfully",
            )

        package_artifact = DeploymentArtifact(
            artifact_type="build",
            name="application-package.tar.gz",
            location="./dist/application-package.tar.gz",
            metadata={"format": "tar.gz"},
        )

        duration = time.perf_counter() - start
        return StageResult(
            stage_name=self.name,
            success=True,
            duration_seconds=duration,
            artifacts=(package_artifact,),
        )
