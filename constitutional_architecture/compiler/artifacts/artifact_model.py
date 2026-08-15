from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class ArtifactType(str, Enum):
    SOURCE = "source"
    CONFIG = "config"
    TEST = "test"
    DOCKER = "docker"
    CI = "ci"
    DOCUMENTATION = "documentation"


@dataclass(frozen=True)
class SourceMapping:
    isr_node_id: str
    artifact_path: str = ""
    bir_node_id: str = ""


@dataclass(frozen=True)
class Artifact:
    path: str
    content: str = ""
    artifact_type: ArtifactType = ArtifactType.SOURCE
    backend: str = ""
    source_mapping: Optional[SourceMapping] = None
    checksum: str = ""
    language: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
