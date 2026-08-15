"""
Global artifact repository.

Artifacts are content-addressed by SHA-256 hash.
"""

from __future__ import annotations

from typing import Dict, List

from .models import ArtifactLocationISR, ArtifactRecord, new_id, utcnow


class ArtifactRepository:
    """Content-addressed artifact repository."""

    def __init__(self) -> None:
        self.artifacts: Dict[str, ArtifactRecord] = {}

    def put_artifact(
        self,
        content_hash: str,
        size_bytes: int,
        produced_by_job: str | None,
        node_id: str,
        region: str,
        uri: str,
    ) -> ArtifactRecord:
        artifact = self.artifacts.get(content_hash)

        if not artifact:
            artifact = ArtifactRecord(
                artifact_id=new_id("artifact"),
                content_hash=content_hash,
                size_bytes=size_bytes,
                produced_by_job=produced_by_job,
            )

            self.artifacts[content_hash] = artifact

        location = ArtifactLocationISR(
            artifact_hash=content_hash,
            node_id=node_id,
            region=region,
            uri=uri,
        )

        artifact.locations.append(location)

        return artifact

    def get_artifact(self, content_hash: str) -> ArtifactRecord | None:
        return self.artifacts.get(content_hash)

    def verify_artifact(
        self,
        content_hash: str,
        expected_size: int | None = None,
    ) -> bool:
        artifact = self.artifacts.get(content_hash)

        if not artifact:
            return False

        if expected_size is not None and artifact.size_bytes != expected_size:
            return False

        return len(artifact.locations) > 0

    def list_artifacts(self) -> List[ArtifactRecord]:
        return list(self.artifacts.values())
