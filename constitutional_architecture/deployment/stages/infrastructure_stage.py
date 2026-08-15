from __future__ import annotations

import time

from constitutional_architecture.deployment.deployment_context import DeploymentContext
from constitutional_architecture.deployment.deployment_result import DeploymentArtifact
from constitutional_architecture.deployment.stages.stage_interface import DeploymentStage, StageResult


class InfrastructureStage(DeploymentStage):
    @property
    def name(self) -> str:
        return "infrastructure"

    @property
    def description(self) -> str:
        return "Generate Infrastructure as Code from ISR deployment nodes"

    def execute(self, ctx: DeploymentContext) -> StageResult:
        start = time.perf_counter()

        isr = ctx.isr
        deployment = isr.system.deployment

        if deployment is None:
            infra_artifact = DeploymentArtifact(
                artifact_type="iac",
                name="docker-compose.yml",
                location="./infra/docker-compose.yml",
                metadata={"type": "docker-compose", "auto_generated": "true"},
            )
        else:
            infra_artifact = DeploymentArtifact(
                artifact_type="iac",
                name="infrastructure.tf",
                location="./infra/infrastructure.tf",
                metadata={
                    "type": "terraform",
                    "environment": deployment.environment.value,
                    "scaling": deployment.scaling.strategy.value,
                },
            )

        duration = time.perf_counter() - start
        return StageResult(
            stage_name=self.name,
            success=True,
            duration_seconds=duration,
            artifacts=(infra_artifact,),
        )
