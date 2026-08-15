from __future__ import annotations

import time

from constitutional_architecture.deployment.deployment_context import DeploymentContext
from constitutional_architecture.deployment.stages.stage_interface import DeploymentStage, StageResult


class DeployStage(DeploymentStage):
    @property
    def name(self) -> str:
        return "deploy"

    @property
    def description(self) -> str:
        return "Deploy application to provisioned infrastructure"

    @property
    def dependencies(self) -> list[str]:
        return ["provision", "containerize"]

    def execute(self, ctx: DeploymentContext) -> StageResult:
        start = time.perf_counter()

        provision_result = ctx.get_stage_result("provision")
        container_result = ctx.get_stage_result("containerize")

        if provision_result is None or not provision_result.success:
            return StageResult(
                stage_name=self.name,
                success=False,
                duration_seconds=time.perf_counter() - start,
                error="Provision stage did not complete successfully",
            )

        if container_result is None or not container_result.success:
            return StageResult(
                stage_name=self.name,
                success=False,
                duration_seconds=time.perf_counter() - start,
                error="Container stage did not complete successfully",
            )

        duration = time.perf_counter() - start
        return StageResult(
            stage_name=self.name,
            success=True,
            duration_seconds=duration,
            metrics={"deployed": True},
        )
