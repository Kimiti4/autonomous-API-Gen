from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from constitutional_architecture.deployment.deployment_context import DeploymentContext


@dataclass(frozen=True)
class StageResult:
    stage_name: str
    success: bool = True
    duration_seconds: float = 0.0
    artifacts: tuple[Any, ...] = ()
    diagnostics: tuple[str, ...] = ()
    metrics: dict[str, Any] = field(default_factory=dict)
    error: str = ""


class DeploymentStage(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        ...

    @property
    def dependencies(self) -> list[str]:
        return []

    @abstractmethod
    def execute(self, ctx: DeploymentContext) -> StageResult:
        ...

    def can_execute(self, ctx: DeploymentContext) -> bool:
        return True
