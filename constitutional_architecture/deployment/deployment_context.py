from __future__ import annotations

from typing import Any

from constitutional_architecture.isr.model.isr import ISR


class VerifiedSystem:
    def __init__(
        self,
        isr: ISR,
        artifacts: tuple[dict[str, Any], ...] = (),
        verification_report: dict[str, Any] | None = None,
        isr_hash: str = "",
        compilation_hash: str = "",
    ) -> None:
        self.isr = isr
        self.artifacts = artifacts
        self.verification_report = verification_report
        self.isr_hash = isr_hash
        self.compilation_hash = compilation_hash

    @property
    def is_verified(self) -> bool:
        if self.verification_report is None:
            return False
        return self.verification_report.get("approved_for_deployment", False)


class DeploymentContext:
    def __init__(
        self,
        _verified_system: VerifiedSystem | None = None,
        *,
        isr: ISR | None = None,
        config: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        if _verified_system is None and isr is None:
            raise TypeError("DeploymentContext requires either _verified_system or isr")
        if _verified_system is None:
            _verified_system = VerifiedSystem(isr=isr)  # type: ignore[arg-type]
        self._verified_system = _verified_system
        self._config = config or {}
        self._stage_results: dict[str, Any] = {}
        self._deployment_artifacts: list[Any] = []
        self._events: list[dict[str, Any]] = []
        self._deployment_history: list[Any] = []
        self.metadata: dict[str, Any] = metadata or {}

    @property
    def isr(self) -> ISR:
        return self._verified_system.isr

    @property
    def verified_system(self) -> VerifiedSystem:
        return self._verified_system

    @property
    def config(self) -> dict[str, Any]:
        return dict(self._config)

    @property
    def isr_hash(self) -> str:
        return self._verified_system.isr_hash or self._verified_system.isr.content_hash

    @property
    def is_verified(self) -> bool:
        return self._verified_system.is_verified

    @property
    def deployment_history(self) -> list[Any]:
        return self._deployment_history

    @deployment_history.setter
    def deployment_history(self, history: list[Any]) -> None:
        self._deployment_history = history

    def record_stage_result(self, result: Any) -> None:
        self._stage_results[result.stage_name] = result

    def get_stage_result(self, stage_name: str) -> Any | None:
        return self._stage_results.get(stage_name)

    def add_deployment_artifact(self, artifact: Any) -> None:
        self._deployment_artifacts.append(artifact)

    @property
    def deployment_artifacts(self) -> list[Any]:
        return list(self._deployment_artifacts)

    def add_event(self, event: dict[str, Any]) -> None:
        self._events.append(event)

    @property
    def events(self) -> list[dict[str, Any]]:
        return list(self._events)

    def get_config_value(self, key: str, default: Any = None) -> Any:
        return self._config.get(key, default)
