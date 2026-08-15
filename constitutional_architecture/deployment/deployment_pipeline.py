from __future__ import annotations

import time
from typing import Any

from constitutional_architecture.deployment.deployment_context import DeploymentContext
from constitutional_architecture.deployment.deployment_result import DeploymentResult, DeploymentStatus
from constitutional_architecture.deployment.deployment_events import DeploymentEvent, DeploymentEventType, DeploymentErrorEvent
from constitutional_architecture.deployment.deployment_registry import DeploymentRegistry
from constitutional_architecture.deployment.stages.stage_interface import DeploymentStage, StageResult


class DeploymentPipeline:
    def __init__(self, registry: DeploymentRegistry | None = None) -> None:
        self._registry = registry or DeploymentRegistry()
        self._ordered_stages: list[str] = []

    def register_stage(self, stage: DeploymentStage) -> None:
        self._registry.register_stage(stage)
        self._recalculate_order()

    def get_stage(self, name: str) -> DeploymentStage | None:
        return self._registry.get_stage(name)

    def execute(self, ctx: DeploymentContext) -> DeploymentResult:
        if not self._ordered_stages:
            return DeploymentResult(
                status=DeploymentStatus.FAILED,
                metadata={"error": "No stages registered in pipeline"},
            )

        start = time.perf_counter()
        DeploymentEvent.emit(DeploymentEventType.PIPELINE_STARTED, {"stages": list(self._ordered_stages)})

        for stage_name in self._ordered_stages:
            stage = self._registry.get_stage(stage_name)
            if stage is None:
                continue

            if not stage.can_execute(ctx):
                ctx.record_stage_result(StageResult(
                    stage_name=stage_name,
                    success=False,
                    error=f"Stage {stage_name} pre-condition check failed",
                ))
                DeploymentEvent.emit(DeploymentEventType.PIPELINE_FAILED, {"stage": stage_name})
                return DeploymentResult(
                    status=DeploymentStatus.FAILED,
                    duration_seconds=time.perf_counter() - start,
                    metadata={"error": f"Pipeline failed at stage: {stage_name}"},
                )

            result = stage.execute(ctx)
            ctx.record_stage_result(result)

            if not result.success:
                DeploymentErrorEvent(stage=stage_name, error=result.error).emit()
                DeploymentEvent.emit(DeploymentEventType.PIPELINE_FAILED, {"stage": stage_name, "error": result.error})
                return DeploymentResult(
                    status=DeploymentStatus.FAILED,
                    duration_seconds=time.perf_counter() - start,
                    metadata={"error": f"Pipeline failed at stage: {stage_name} - {result.error}"},
                )

        duration = time.perf_counter() - start
        DeploymentEvent.emit(DeploymentEventType.PIPELINE_COMPLETED, {"duration_seconds": duration})
        return DeploymentResult(
            status=DeploymentStatus.RUNNING,
            duration_seconds=duration,
            metadata={"message": "Pipeline completed successfully"},
        )

    def _recalculate_order(self) -> None:
        all_stages = self._registry.list_stages()
        ordered: list[str] = []
        visited: set[str] = set()
        temp: set[str] = set()

        def visit(name: str) -> None:
            if name in temp:
                return
            if name in visited:
                return
            stage = self._registry.get_stage(name)
            if stage is None:
                return
            temp.add(name)
            for dep in stage.dependencies:
                visit(dep)
            temp.discard(name)
            visited.add(name)
            ordered.append(name)

        for name in all_stages:
            if name not in visited:
                visit(name)

        self._ordered_stages = ordered
