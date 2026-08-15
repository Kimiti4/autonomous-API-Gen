from __future__ import annotations

from typing import Any, Optional

from constitutional_architecture.deployment.targets.target_interface import DeploymentTarget


class DeploymentRegistry:
    def __init__(self) -> None:
        self._targets: dict[str, DeploymentTarget] = {}
        self._stages: dict[str, Any] = {}
        self._artifacts: dict[str, Any] = {}

    def register(self, target: DeploymentTarget) -> None:
        if target.name in self._targets:
            raise ValueError(f"Target '{target.name}' already registered")
        self._targets[target.name] = target

    def unregister(self, name: str) -> None:
        if name not in self._targets:
            raise ValueError(f"Target '{name}' not found")
        del self._targets[name]

    def get(self, name: str) -> Optional[DeploymentTarget]:
        return self._targets.get(name)

    def register_stage(self, stage: Any) -> None:
        self._stages[stage.name] = stage

    def get_stage(self, name: str) -> Any | None:
        return self._stages.get(name)

    def list_stages(self) -> list[str]:
        return list(self._stages.keys())

    def clear(self) -> None:
        self._targets.clear()
        self._stages.clear()
        self._artifacts.clear()

    @property
    def all_names(self) -> list[str]:
        return list(self._targets.keys())

    @property
    def count(self) -> int:
        return len(self._targets)

    def __contains__(self, name: str) -> bool:
        return name in self._targets
