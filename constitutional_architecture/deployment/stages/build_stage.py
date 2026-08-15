from __future__ import annotations

import time

from constitutional_architecture.deployment.deployment_context import DeploymentContext
from constitutional_architecture.deployment.deployment_result import DeploymentArtifact
from constitutional_architecture.deployment.stages.stage_interface import DeploymentStage, StageResult


class BuildStage(DeploymentStage):
    @property
    def name(self) -> str:
        return "build"

    @property
    def description(self) -> str:
        return "Compile source code and resolve dependencies"

    def execute(self, ctx: DeploymentContext) -> StageResult:
        start = time.perf_counter()

        modules = ctx.isr.system.modules
        source_count = len(modules) if modules else 0
        if source_count == 0:
            return StageResult(
                stage_name=self.name,
                success=False,
                duration_seconds=time.perf_counter() - start,
                error="No source artifacts found to build",
            )

        build_artifact = DeploymentArtifact(
            artifact_type="build",
            name="build-output",
            location="./build/",
            metadata={"source_files": str(source_count)},
        )

        duration = time.perf_counter() - start
        return StageResult(
            stage_name=self.name,
            success=True,
            duration_seconds=duration,
            artifacts=(build_artifact,),
            metrics={"source_files": source_count},
        )
