from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Protocol

from constitutional_architecture.deployment.deployment_result import DeploymentArtifact, HealthCheckResult


@dataclass(frozen=True)
class TargetResult:
    success: bool = True
    endpoint: str = ""
    deployed_artifacts: tuple[DeploymentArtifact, ...] = ()
    health: HealthCheckResult | None = None
    diagnostics: tuple[str, ...] = ()
    error: str = ""


class TargetExecutor(Protocol):
    """Injected adapter that performs a real deployment against a target runtime.

    Targets never fabricate deployment success: without an executor they fail
    closed, and an executor that reports success without an endpoint is rejected.
    """

    def deploy(self, artifact: DeploymentArtifact) -> TargetResult:
        ...

    def health_check(self) -> HealthCheckResult:
        ...

    def cleanup(self) -> None:
        ...


class DeploymentTarget(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @abstractmethod
    def deploy(self, artifact: DeploymentArtifact) -> TargetResult:
        ...

    @abstractmethod
    def health_check(self) -> HealthCheckResult:
        ...

    @abstractmethod
    def cleanup(self) -> None:
        ...
