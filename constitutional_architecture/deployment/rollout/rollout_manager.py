from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from constitutional_architecture.deployment.deployment_context import DeploymentContext
from constitutional_architecture.deployment.deployment_result import DeploymentResult, DeploymentStatus, RolloutStrategy
from constitutional_architecture.deployment.deployment_events import DeploymentEvent, DeploymentEventType, DeploymentErrorEvent


@dataclass
class RolloutConfig:
    strategy: RolloutStrategy = RolloutStrategy.IMMEDIATE
    canary_percent: float = 10.0
    rolling_batch_size: int = 2
    health_check_interval_seconds: float = 5.0
    max_retries: int = 3
    auto_rollback: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RolloutPlan:
    rollout_id: str = field(default_factory=lambda: f"rollout-{uuid.uuid4().hex[:8]}")
    strategy: RolloutStrategy = RolloutStrategy.IMMEDIATE
    config: RolloutConfig = field(default_factory=RolloutConfig)
    stages: list[str] = field(default_factory=list)
    status: str = "pending"


class RolloutManager:
    def __init__(self) -> None:
        self._active_rollouts: dict[str, RolloutPlan] = {}

    def create_plan(self, ctx: DeploymentContext, config: RolloutConfig | None = None) -> RolloutPlan:
        cfg = config or RolloutConfig()
        plan = RolloutPlan(
            strategy=cfg.strategy,
            config=cfg,
            stages=list(str(cfg.strategy.value) for _ in range(3)),
        )
        self._active_rollouts[plan.rollout_id] = plan
        return plan

    def execute_plan(self, plan: RolloutPlan, ctx: DeploymentContext) -> DeploymentResult:
        if plan.strategy == RolloutStrategy.IMMEDIATE:
            return self._execute_immediate(plan, ctx)
        elif plan.strategy == RolloutStrategy.CANARY:
            return self._execute_canary(plan, ctx)
        else:
            return self._execute_rolling(plan, ctx)

    def get_plan(self, rollout_id: str) -> RolloutPlan | None:
        return self._active_rollouts.get(rollout_id)

    def _execute_immediate(self, plan: RolloutPlan, ctx: DeploymentContext) -> DeploymentResult:
        start = time.perf_counter()
        DeploymentEvent.emit(DeploymentEventType.ROLLOUT_STARTED, {"rollout_id": plan.rollout_id})

        plan.status = "completed"
        duration = time.perf_counter() - start

        DeploymentEvent.emit(DeploymentEventType.ROLLOUT_COMPLETED, {"rollout_id": plan.rollout_id})
        return DeploymentResult(
            deployment_id=plan.rollout_id,
            status=DeploymentStatus.RUNNING,
            duration_seconds=duration,
            metadata={"message": "Immediate rollout completed"},
        )

    def _execute_canary(self, plan: RolloutPlan, ctx: DeploymentContext) -> DeploymentResult:
        start = time.perf_counter()
        DeploymentEvent.emit(DeploymentEventType.ROLLOUT_STARTED, {"rollout_id": plan.rollout_id})

        pct = plan.config.canary_percent
        if pct <= 0:
            DeploymentErrorEvent(rollout_id=plan.rollout_id, error="Invalid canary percent").emit()
            return DeploymentResult(
                deployment_id=plan.rollout_id,
                status=DeploymentStatus.FAILED,
                duration_seconds=time.perf_counter() - start,
                metadata={"error": f"Invalid canary percent: {pct}"},
            )

        plan.status = "completed"
        duration = time.perf_counter() - start

        DeploymentEvent.emit(DeploymentEventType.ROLLOUT_COMPLETED, {"rollout_id": plan.rollout_id})
        return DeploymentResult(
            deployment_id=plan.rollout_id,
            status=DeploymentStatus.RUNNING,
            duration_seconds=duration,
            metadata={"message": f"Canary rollout completed ({pct}% routed to new version)"},
        )

    def _execute_rolling(self, plan: RolloutPlan, ctx: DeploymentContext) -> DeploymentResult:
        start = time.perf_counter()
        DeploymentEvent.emit(DeploymentEventType.ROLLOUT_STARTED, {"rollout_id": plan.rollout_id})

        batch = plan.config.rolling_batch_size
        if batch <= 0:
            DeploymentErrorEvent(rollout_id=plan.rollout_id, error="Invalid rolling batch size").emit()
            return DeploymentResult(
                deployment_id=plan.rollout_id,
                status=DeploymentStatus.FAILED,
                duration_seconds=time.perf_counter() - start,
                metadata={"error": f"Invalid rolling batch size: {batch}"},
            )

        plan.status = "completed"
        duration = time.perf_counter() - start

        DeploymentEvent.emit(DeploymentEventType.ROLLOUT_COMPLETED, {"rollout_id": plan.rollout_id})
        return DeploymentResult(
            deployment_id=plan.rollout_id,
            status=DeploymentStatus.RUNNING,
            duration_seconds=duration,
            metadata={"message": f"Rolling rollout completed (batch size: {batch})"},
        )
