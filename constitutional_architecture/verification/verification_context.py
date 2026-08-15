from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from constitutional_architecture.isr.model.isr import ISR


@dataclass(frozen=True)
class ArtifactReference:
    path: str
    content: str
    artifact_type: str = ""
    backend: str = ""
    checksum: str = ""
    isr_node_id: str = ""


@dataclass
class VerificationContext:
    _isr: ISR
    _artifacts: tuple[ArtifactReference, ...] = ()
    _config: dict[str, Any] = field(default_factory=dict)
    _checks: list[Any] = field(default_factory=list)
    _metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def isr(self) -> ISR:
        return self._isr

    @property
    def artifacts(self) -> tuple[ArtifactReference, ...]:
        return self._artifacts

    @property
    def config(self) -> dict[str, Any]:
        return dict(self._config)

    @property
    def isr_hash(self) -> str:
        return self._isr.content_hash

    def get_artifacts_by_type(self, artifact_type: str) -> list[ArtifactReference]:
        return [a for a in self._artifacts if a.artifact_type == artifact_type]

    def get_artifacts_by_backend(self, backend: str) -> list[ArtifactReference]:
        return [a for a in self._artifacts if a.backend == backend]

    def get_artifact(self, path: str) -> Optional[ArtifactReference]:
        for a in self._artifacts:
            if a.path == path:
                return a
        return None

    def get_config_value(self, key: str, default: Any = None) -> Any:
        return self._config.get(key, default)

    @property
    def has_artifacts(self) -> bool:
        return len(self._artifacts) > 0

    @property
    def artifact_count(self) -> int:
        return len(self._artifacts)
