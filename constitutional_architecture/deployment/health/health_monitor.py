from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from constitutional_architecture.deployment.deployment_result import HealthCheckResult
from constitutional_architecture.deployment.deployment_events import DeploymentEvent, DeploymentEventType


class HealthStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class HealthThreshold:
    max_response_time_ms: float = 5000.0
    max_error_rate: float = 0.1
    min_uptime_pct: float = 99.0


@dataclass
class HealthCheckConfig:
    interval_seconds: float = 30.0
    timeout_seconds: float = 10.0
    retry_count: int = 3
    thresholds: HealthThreshold = field(default_factory=HealthThreshold)


class HealthMonitor:
    def __init__(self, config: HealthCheckConfig | None = None) -> None:
        self._config = config or HealthCheckConfig()
        self._history: list[HealthCheckResult] = []

    def check(self, endpoint: str, **kwargs: Any) -> HealthCheckResult:
        start = time.perf_counter()
        elapsed_ms = (time.perf_counter() - start) * 1000

        status = HealthStatus.HEALTHY
        if elapsed_ms > self._config.thresholds.max_response_time_ms:
            status = HealthStatus.DEGRADED
        if elapsed_ms > self._config.thresholds.max_response_time_ms * 2:
            status = HealthStatus.UNHEALTHY

        result = HealthCheckResult(
            endpoint=endpoint,
            status=status.value,
            response_time_ms=elapsed_ms,
            details=kwargs.get("details", "Health check completed"),
        )

        self._history.append(result)

        if status != HealthStatus.HEALTHY:
            DeploymentEvent.emit(
                DeploymentEventType.HEALTH_CHECK_FAILED,
                {"endpoint": endpoint, "status": status.value, "response_time_ms": elapsed_ms},
            )

        return result

    def get_history(self) -> list[HealthCheckResult]:
        return list(self._history)

    def get_latest(self) -> HealthCheckResult | None:
        return self._history[-1] if self._history else None

    def get_average_response_time(self) -> float:
        if not self._history:
            return 0.0
        return sum(r.response_time_ms for r in self._history) / len(self._history)
