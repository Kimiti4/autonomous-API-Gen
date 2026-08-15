from __future__ import annotations

import time
from typing import Any

from constitutional_architecture.deployment.deployment_context import DeploymentContext
from constitutional_architecture.deployment.deployment_pipeline import DeploymentPipeline
from constitutional_architecture.deployment.deployment_result import DeploymentResult, DeploymentStatus
from constitutional_architecture.deployment.deployment_events import DeploymentEvent, DeploymentEventType, DeploymentErrorEvent
from constitutional_architecture.deployment.deployment_metrics import DeploymentMetricsCollector
from constitutional_architecture.deployment.deployment_registry import DeploymentRegistry
from constitutional_architecture.deployment.environment_manager import EnvironmentManager
from constitutional_architecture.deployment.rollout.rollout_manager import RolloutConfig, RolloutManager, RolloutStrategy
from constitutional_architecture.deployment.rollout.rollback_manager import RollbackConfig, RollbackManager
from constitutional_architecture.deployment.rollout.promotion_manager import PromotionConfig, PromotionManager
from constitutional_architecture.deployment.health.health_monitor import HealthCheckConfig, HealthMonitor


class DeploymentEngine:
    CONSTITUTIONAL_BOUNDARY = (
        "The Deployment Engine operates only on verified "
        "artifacts and never accesses engine internals."
    )

    def __init__(
        self,
        pipeline: DeploymentPipeline | None = None,
        env_manager: EnvironmentManager | None = None,
        rollout_manager: RolloutManager | None = None,
        rollback_manager: RollbackManager | None = None,
        promotion_manager: PromotionManager | None = None,
        health_monitor: HealthMonitor | None = None,
        metrics_collector: DeploymentMetricsCollector | None = None,
    ) -> None:
        self._pipeline = pipeline or DeploymentPipeline()
        self._env_manager = env_manager or EnvironmentManager()
        self._rollout = rollout_manager or RolloutManager()
        self._rollback = rollback_manager or RollbackManager()
        self._promotion = promotion_manager or PromotionManager()
        self._health = health_monitor or HealthMonitor()
        self._metrics = metrics_collector or DeploymentMetricsCollector()

    @property
    def pipeline(self) -> DeploymentPipeline:
        return self._pipeline

    @property
    def env_manager(self) -> EnvironmentManager:
        return self._env_manager

    @property
    def rollout(self) -> RolloutManager:
        return self._rollout

    @property
    def rollback(self) -> RollbackManager:
        return self._rollback

    @property
    def promotion(self) -> PromotionManager:
        return self._promotion

    @property
    def health(self) -> HealthMonitor:
        return self._health

    def deploy(
        self,
        ctx: DeploymentContext,
        strategy: RolloutStrategy = RolloutStrategy.IMMEDIATE,
    ) -> DeploymentResult:
        overall_start = time.perf_counter()
        DeploymentEvent.emit(DeploymentEventType.DEPLOYMENT_STARTED, {
            "system": ctx.isr.system.name,
            "strategy": strategy.value,
        })

        pipeline_result = self._pipeline.execute(ctx)
        if pipeline_result.status != DeploymentStatus.RUNNING:
            DeploymentEvent.emit(DeploymentEventType.DEPLOYMENT_FAILED, {
                "error": "Pipeline execution failed",
            })
            self._metrics.record("deployment_success", 0.0)
            return pipeline_result

        rollout_config = RolloutConfig(strategy=strategy)
        rollout_plan = self._rollout.create_plan(ctx, rollout_config)
        rollout_result = self._rollout.execute_plan(rollout_plan, ctx)

        self._metrics.record("deployment_success", 1.0)
        self._metrics.record("deployment_duration", time.perf_counter() - overall_start)

        overall_duration = time.perf_counter() - overall_start

        if rollout_result.status != DeploymentStatus.RUNNING:
            DeploymentEvent.emit(DeploymentEventType.DEPLOYMENT_FAILED, {
                "error": "Rollout execution failed",
            })
            return rollout_result

        DeploymentEvent.emit(DeploymentEventType.DEPLOYMENT_COMPLETED, {
            "duration_seconds": overall_duration,
        })

        ctx.deployment_history.append(pipeline_result)

        return DeploymentResult(
            status=DeploymentStatus.RUNNING,
            duration_seconds=overall_duration,
            version=ctx.isr.system.name,
            metadata={"message": f"Deployment of {ctx.isr.system.name} completed ({strategy.value})"},
        )
