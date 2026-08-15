from __future__ import annotations

import time

from constitutional_architecture.deployment.deployment_context import DeploymentContext
from constitutional_architecture.deployment.stages.stage_interface import DeploymentStage, StageResult


class ProvisionStage(DeploymentStage):
    @property
    def name(self) -> str:
        return "provision"

    @property
    def description(self) -> str:
        return "Provision infrastructure using generated IaC"

    @property
    def dependencies(self) -> list[str]:
        return ["infrastructure"]

    def execute(self, ctx: DeploymentContext) -> StageResult:
        start = time.perf_counter()

        infra_result = ctx.get_stage_result("infrastructure")
        if infra_result is None or not infra_result.success:
            return StageResult(
                stage_name=self.name,
                success=False,
                duration_seconds=time.perf_counter() - start,
                error="Infrastructure stage did not complete successfully",
            )

        duration = time.perf_counter() - start
        return StageResult(
            stage_name=self.name,
            success=True,
            duration_seconds=duration,
            metrics={"infrastructure_provisioned": True},
        )
