from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from constitutional_architecture.deployment.deployment_result import DeploymentArtifact, HealthCheckResult


@dataclass(frozen=True)
class TargetResult:
    success: bool = True
    endpoint: str = ""
    deployed_artifacts: tuple[DeploymentArtifact, ...] = ()
    health: HealthCheckResult | None = None
    diagnostics: tuple[str, ...] = ()
    error: str = ""


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
