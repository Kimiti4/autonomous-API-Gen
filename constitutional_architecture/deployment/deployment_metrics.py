from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


class DeploymentMetricsCollector:
    def __init__(self) -> None:
        self._metrics: dict[str, Any] = {}

    def record(self, key: str, value: Any) -> None:
        self._metrics[key] = value

    def get_metric(self, key: str) -> Any:
        return self._metrics.get(key)

    def get_all(self) -> dict[str, Any]:
        return dict(self._metrics)

    def clear(self) -> None:
        self._metrics.clear()


@dataclass
class DeploymentMetrics:
    total_deployments: int = 0
    successful_deployments: int = 0
    failed_deployments: int = 0
    rollbacks_executed: int = 0
    rollbacks_failed: int = 0
    total_duration_seconds: float = 0.0
    average_duration_seconds: float = 0.0
    environment_deployments: dict[str, int] = field(default_factory=dict)
    target_deployments: dict[str, int] = field(default_factory=dict)
    rollback_success_rate: float = 0.0

    @property
    def success_rate(self) -> float:
        if self.total_deployments == 0:
            return 0.0
        return self.successful_deployments / self.total_deployments

    @property
    def rollback_rate(self) -> float:
        if self.total_deployments == 0:
            return 0.0
        return self.rollbacks_executed / self.total_deployments

    def record_deployment(
        self,
        success: bool,
        duration_seconds: float,
        environment: str = "",
        target: str = "",
        rollback: bool = False,
        rollback_success: bool = False,
    ) -> None:
        self.total_deployments += 1
        if success:
            self.successful_deployments += 1
        else:
            self.failed_deployments += 1

        self.total_duration_seconds += duration_seconds
        n = self.total_deployments
        self.average_duration_seconds = (
            self.average_duration_seconds * (n - 1) + duration_seconds
        ) / n

        if environment:
            self.environment_deployments[environment] = (
                self.environment_deployments.get(environment, 0) + 1
            )
        if target:
            self.target_deployments[target] = (
                self.target_deployments.get(target, 0) + 1
            )

        if rollback:
            self.rollbacks_executed += 1
            if rollback_success:
                self.rollback_success_rate = (
                    (self.rollback_success_rate * (self.rollbacks_executed - 1) + 1.0)
                    / self.rollbacks_executed
                )
            else:
                self.rollbacks_failed += 1
                self.rollback_success_rate = (
                    (self.rollback_success_rate * (self.rollbacks_executed - 1) + 0.0)
                    / self.rollbacks_executed
                )
