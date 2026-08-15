"""
Backend artifact output builder.

This builder helps backends produce safe, deterministic compilation output.
"""

from __future__ import annotations

import json
from typing import Any

from ..errors import ArtifactPackagingError
from ..models import CompilationOutput, GeneratedArtifact


RESERVED_ARTIFACT_PATHS = {
    "artifact-manifest.json",
}


def validate_artifact_path(path: str) -> None:
    """Validate artifact path safety."""

    if not path or not path.strip():
        raise ArtifactPackagingError("Artifact path must not be empty.")

    normalized = path.replace("\\", "/").strip()

    if normalized.startswith("/"):
        raise ArtifactPackagingError(
            "Artifact path must not be absolute."
        )

    if normalized in RESERVED_ARTIFACT_PATHS:
        raise ArtifactPackagingError(
            f"Artifact path is reserved: {normalized}"
        )

    parts = normalized.split("/")

    if any(part == ".." for part in parts):
        raise ArtifactPackagingError(
            "Artifact path must not contain parent traversal."
        )


class CompilationOutputBuilder:
    """Builds safe compilation output for backends."""

    def __init__(self) -> None:
        self._artifacts: list[GeneratedArtifact] = []
        self._logs: list[str] = []

    def add_artifact(
        self,
        path: str,
        content: str,
        content_type: str = "text/plain",
    ) -> "CompilationOutputBuilder":
        """Add a text artifact."""

        validate_artifact_path(path)

        self._artifacts.append(
            GeneratedArtifact(
                path=path,
                content=content,
                content_type=content_type,
            )
        )

        return self

    def add_json_artifact(
        self,
        path: str,
        payload: Any,
    ) -> "CompilationOutputBuilder":
        """Add a deterministic JSON artifact."""

        content = json.dumps(
            payload,
            indent=2,
            sort_keys=True,
        )

        return self.add_artifact(
            path=path,
            content=content,
            content_type="application/json",
        )

    def add_markdown_artifact(
        self,
        path: str,
        content: str,
    ) -> "CompilationOutputBuilder":
        """Add a Markdown artifact."""

        return self.add_artifact(
            path=path,
            content=content,
            content_type="text/markdown",
        )

    def add_log(self, message: str) -> "CompilationOutputBuilder":
        """Add a compilation log message."""

        self._logs.append(str(message))
        return self

    def build(self, sort_artifacts: bool = True) -> CompilationOutput:
        """Build compilation output."""

        artifacts = list(self._artifacts)

        if sort_artifacts:
            artifacts.sort(key=lambda artifact: artifact.path)

        return CompilationOutput(
            artifacts=artifacts,
            logs=list(self._logs),
        )