from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from constitutional_architecture.deployment.deployment_context import DeploymentContext
from constitutional_architecture.deployment.deployment_result import DeploymentResult, DeploymentStatus
from constitutional_architecture.deployment.deployment_events import DeploymentEvent, DeploymentEventType


class RollbackReason:
    HEALTH_CHECK_FAILURE = "health_check_failure"
    MANUAL_INTERVENTION = "manual_intervention"
    DEPLOYMENT_ERROR = "deployment_error"
    TIMEOUT = "timeout"


@dataclass
class RollbackConfig:
    auto_rollback: bool = True
    max_rollback_attempts: int = 2
    preserve_artifacts: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


class RollbackManager:
    def __init__(self, config: RollbackConfig | None = None) -> None:
        self._config = config or RollbackConfig()
        self._rollback_history: list[dict[str, Any]] = []

    def rollback(
        self,
        ctx: DeploymentContext,
        reason: str = RollbackReason.MANUAL_INTERVENTION,
    ) -> DeploymentResult:
        DeploymentEvent.emit(DeploymentEventType.ROLLBACK_INITIATED, {"reason": reason})

        if self._config.auto_rollback:
            snapshot = self._find_last_snapshot(ctx)
            if snapshot is None:
                return DeploymentResult(
                    status=DeploymentStatus.FAILED,
                    metadata={"error": "No rollback snapshot available"},
                )

            self._rollback_history.append({
                "reason": reason,
                "snapshot": snapshot,
            })

            DeploymentEvent.emit(DeploymentEventType.ROLLBACK_COMPLETED, {"reason": reason})
            return DeploymentResult(
                status=DeploymentStatus.RUNNING,
                metadata={"message": f"Rollback completed: {reason}"},
            )

        return DeploymentResult(
            status=DeploymentStatus.FAILED,
            metadata={"error": "Auto-rollback is disabled"},
        )

    def _find_last_snapshot(self, ctx: DeploymentContext) -> dict[str, Any] | None:
        for r in reversed(ctx.deployment_history):
            if r.status == DeploymentStatus.RUNNING:
                return {"version": r.metadata.get("message", ""), "status": "stable"}
        return None

    def get_history(self) -> list[dict[str, Any]]:
        return list(self._rollback_history)
