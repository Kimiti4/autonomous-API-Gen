from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, unique
from typing import Any, Callable


@unique
class DeploymentEventType(str, Enum):
    DEPLOYMENT_STARTED = "deployment_started"
    BUILD_STARTED = "build_started"
    BUILD_COMPLETED = "build_completed"
    PACKAGE_COMPLETED = "package_completed"
    CONTAINER_BUILT = "container_built"
    INFRASTRUCTURE_PROVISIONED = "infrastructure_provisioned"
    DEPLOYMENT_IN_PROGRESS = "deployment_in_progress"
    HEALTH_CHECK_PASSED = "health_check_passed"
    HEALTH_CHECK_FAILED = "health_check_failed"
    DEPLOYMENT_COMPLETED = "deployment_completed"
    DEPLOYMENT_FAILED = "deployment_failed"
    ROLLBACK_INITIATED = "rollback_initiated"
    ROLLBACK_COMPLETED = "rollback_completed"
    ROLLBACK_FAILED = "rollback_failed"
    ENVIRONMENT_PROMOTED = "environment_promoted"
    DEPLOYMENT_ROLLOUT = "deployment_rollout"
    PIPELINE_STARTED = "pipeline_started"
    PIPELINE_FAILED = "pipeline_failed"
    PIPELINE_COMPLETED = "pipeline_completed"
    ROLLOUT_STARTED = "rollout_started"
    ROLLOUT_COMPLETED = "rollout_completed"
    PROMOTION_BLOCKED = "promotion_blocked"
    PROMOTION_COMPLETED = "promotion_completed"


@dataclass(frozen=True)
class DeploymentEvent:
    event_type: DeploymentEventType
    deployment_id: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    data: dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def emit(event_type: DeploymentEventType, data: dict[str, Any] | None = None) -> None:
        bus = _get_global_bus()
        event = DeploymentEvent(event_type=event_type, data=data or {})
        bus.publish(event)


@dataclass(frozen=True)
class DeploymentErrorEvent:
    rollout_id: str = ""
    error: str = ""
    stage: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    data: dict[str, Any] = field(default_factory=dict)

    def emit(self) -> None:
        event = DeploymentEvent(
            event_type=DeploymentEventType.DEPLOYMENT_FAILED,
            data={
                "rollout_id": self.rollout_id,
                "error": self.error,
                "stage": self.stage,
                **(self.data or {}),
            },
        )
        _get_global_bus().publish(event)


class DeploymentEventBus:
    def __init__(self) -> None:
        self._handlers: dict[DeploymentEventType, list[Callable]] = {}
        self._global_handlers: list[Callable] = []
        self._history: list[DeploymentEvent] = []

    def subscribe(self, event_type: DeploymentEventType, handler: Callable) -> None:
        self._handlers.setdefault(event_type, []).append(handler)

    def subscribe_all(self, handler: Callable) -> None:
        self._global_handlers.append(handler)

    def publish(self, event: DeploymentEvent) -> None:
        self._history.append(event)
        for handler in self._handlers.get(event.event_type, []):
            handler(event)
        for handler in self._global_handlers:
            handler(event)

    @property
    def history(self) -> list[DeploymentEvent]:
        return list(self._history)

    def get_events(self, event_type: DeploymentEventType) -> list[DeploymentEvent]:
        return [e for e in self._history if e.event_type == event_type]


_global_bus: DeploymentEventBus | None = None


def _get_global_bus() -> DeploymentEventBus:
    global _global_bus
    if _global_bus is None:
        _global_bus = DeploymentEventBus()
    return _global_bus
