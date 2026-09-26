from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable

from constitutional_architecture.deployment.deployment_context import DeploymentContext
from constitutional_architecture.deployment.deployment_result import (
    DeploymentArtifact,
    DeploymentResult,
    DeploymentStatus,
)
from constitutional_architecture.deployment.deployment_events import (
    DeploymentEvent,
    DeploymentEventType,
)


class RollbackReason:
    HEALTH_CHECK_FAILURE = "health_check_failure"
    MANUAL_INTERVENTION = "manual_intervention"
    DEPLOYMENT_ERROR = "deployment_error"
    TIMEOUT = "timeout"


@dataclass(frozen=True)
class RollbackExecution:
    """Result returned by the concrete deployment rollback adapter.

    The manager owns authorization, target binding, replay protection and
    post-action health verification. The adapter owns the actual platform
    actuation (for example restoring a cached artifact through a deployment
    target). A successful manager result is therefore impossible without a
    successful concrete execution result.
    """

    success: bool
    health_verified: bool
    target: str = ""
    restored_version: str = ""
    diagnostics: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


RollbackExecutor = Callable[[dict[str, Any]], RollbackExecution]
RollbackAuthorizer = Callable[[DeploymentContext, DeploymentResult, str], bool]


@dataclass
class RollbackConfig:
    auto_rollback: bool = True
    max_rollback_attempts: int = 2
    preserve_artifacts: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)
    executor: RollbackExecutor | None = None
    authorizer: RollbackAuthorizer | None = None


class RollbackManager:
    """Fail-closed rollback coordinator.

    Before this boundary was remediated, rollback was only a history append.
    This manager now requires an explicit authorization and a concrete
    executor. It binds the execution request to one previously successful
    deployment snapshot, rejects authorization replay, serializes concurrent
    attempts, and only reports ROLLED_BACK after the executor confirms both
    actuation and post-action health.

    The manager deliberately does not invent infrastructure commands. The
    configured executor is the actuation port for the deployment environment.
    """

    def __init__(self, config: RollbackConfig | None = None) -> None:
        self._config = config or RollbackConfig()
        self._rollback_history: list[dict[str, Any]] = []
        self._used_authorizations: set[str] = set()
        self._lock = threading.Lock()
        if self._config.max_rollback_attempts < 1:
            raise ValueError("max_rollback_attempts must be positive")

    def rollback(
        self,
        ctx: DeploymentContext,
        reason: str = RollbackReason.MANUAL_INTERVENTION,
        *,
        authorization_id: str | None = None,
    ) -> DeploymentResult:
        operation_id = f"rollback-{uuid.uuid4().hex}"
        DeploymentEvent.emit(
            DeploymentEventType.ROLLBACK_INITIATED,
            {
                "operation_id": operation_id,
                "reason": reason,
            },
        )

        if not self._config.auto_rollback:
            return self._failed(operation_id, reason, "Auto-rollback is disabled")

        if self._config.executor is None:
            return self._failed(
                operation_id,
                reason,
                "Rollback executor is not configured; actuation is unavailable",
            )

        if not authorization_id:
            return self._failed(
                operation_id,
                reason,
                "Rollback authorization is required",
            )

        with self._lock:
            if authorization_id in self._used_authorizations:
                return self._failed(
                    operation_id,
                    reason,
                    "Rollback authorization has already been consumed",
                )

            snapshot = self._find_last_snapshot(ctx)
            if snapshot is None:
                return self._failed(
                    operation_id,
                    reason,
                    "No verified rollback snapshot available",
                )

            if self._config.authorizer is None:
                return self._failed(
                    operation_id,
                    reason,
                    "Rollback authorizer is not configured",
                )

            if not self._config.authorizer(ctx, snapshot, authorization_id):
                return self._failed(
                    operation_id,
                    reason,
                    "Rollback authorization denied",
                )

            target = self._rollback_target(snapshot)
            if target is None:
                return self._failed(
                    operation_id,
                    reason,
                    "Rollback snapshot has no bounded target artifact",
                )

            request = {
                "operation_id": operation_id,
                "authorization_id": authorization_id,
                "reason": reason,
                "deployment_id": snapshot.deployment_id,
                "version": snapshot.version,
                "artifact": target,
            }

            try:
                execution = self._config.executor(request)
            except Exception as exc:
                return self._failed(
                    operation_id,
                    reason,
                    f"Rollback executor failed: {exc}",
                )

            if not execution.success or not execution.health_verified:
                diagnostics = "; ".join(execution.diagnostics)
                detail = (
                    "Rollback execution did not reach a verified healthy state"
                    + (f": {diagnostics}" if diagnostics else "")
                )
                return self._failed(operation_id, reason, detail)

            self._used_authorizations.add(authorization_id)
            record = {
                "operation_id": operation_id,
                "authorization_id": authorization_id,
                "reason": reason,
                "deployment_id": snapshot.deployment_id,
                "version": snapshot.version,
                "target": execution.target,
                "restored_version": execution.restored_version or snapshot.version,
                "status": DeploymentStatus.ROLLED_BACK.value,
                "metadata": dict(execution.metadata),
            }
            self._rollback_history.append(record)

            DeploymentEvent.emit(
                DeploymentEventType.ROLLBACK_COMPLETED,
                {
                    **record,
                    "diagnostics": list(execution.diagnostics),
                },
            )
            return DeploymentResult(
                deployment_id=operation_id,
                status=DeploymentStatus.ROLLED_BACK,
                rollback_executed=True,
                rollback_reason=reason,
                version=execution.restored_version or snapshot.version,
                metadata={
                    "operation_id": operation_id,
                    "authorization_id": authorization_id,
                    "target": execution.target,
                    "diagnostics": list(execution.diagnostics),
                },
            )

    def _failed(
        self,
        operation_id: str,
        reason: str,
        error: str,
    ) -> DeploymentResult:
        DeploymentEvent.emit(
            DeploymentEventType.ROLLBACK_FAILED,
            {
                "operation_id": operation_id,
                "reason": reason,
                "error": error,
            },
        )
        return DeploymentResult(
            deployment_id=operation_id,
            status=DeploymentStatus.FAILED,
            rollback_executed=False,
            rollback_reason=reason,
            metadata={"operation_id": operation_id, "error": error},
        )

    @staticmethod
    def _rollback_target(
        snapshot: DeploymentResult,
    ) -> DeploymentArtifact | None:
        artifacts = (
            snapshot.container_images
            or snapshot.build_artifacts
            or snapshot.infrastructure_artifacts
        )
        if not artifacts:
            return None
        artifact = artifacts[0]
        if not artifact.location or not artifact.name:
            return None
        return artifact

    @staticmethod
    def _find_last_snapshot(
        ctx: DeploymentContext,
    ) -> DeploymentResult | None:
        for result in reversed(ctx.deployment_history):
            if not isinstance(result, DeploymentResult):
                continue
            if result.status != DeploymentStatus.RUNNING:
                continue
            if not result.build_artifacts and not result.container_images:
                continue
            return result
        return None

    def get_history(self) -> list[dict[str, Any]]:
        return list(self._rollback_history)
