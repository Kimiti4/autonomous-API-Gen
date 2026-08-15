"""
Artifact packaging system.

The packager writes backend-produced artifacts to disk and creates a
verifiable artifact manifest.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from .errors import ArtifactPackagingError
from .ids import deterministic_id
from .models import (
    ArtifactFile,
    ArtifactManifest,
    CompilationOutput,
    utcnow,
)


class ArtifactPackager:
    """Packages compilation artifacts."""

    def package(
        self,
        output: CompilationOutput,
        job_id: str,
        backend_id: str,
        backend_version: str,
        output_root: Path,
    ) -> ArtifactManifest:
        """Write artifacts and produce an artifact manifest."""

        output_root = output_root.resolve()
        output_root.mkdir(parents=True, exist_ok=True)

        files: list[ArtifactFile] = []

        for artifact in output.artifacts:
            target_path = self._safe_path(output_root, artifact.path)

            target_path.parent.mkdir(parents=True, exist_ok=True)

            content_bytes = artifact.content.encode("utf-8")

            target_path.write_bytes(content_bytes)

            content_hash = hashlib.sha256(content_bytes).hexdigest()

            files.append(
                ArtifactFile(
                    path=str(target_path.relative_to(output_root)),
                    content_hash=f"sha256:{content_hash}",
                    size_bytes=len(content_bytes),
                    content_type=artifact.content_type,
                )
            )

        manifest = ArtifactManifest(
            manifest_id=deterministic_id(
                "artifact_manifest",
                {
                    "job_id": job_id,
                    "backend_id": backend_id,
                    "backend_version": backend_version,
                    "files": [file.model_dump(mode="json") for file in files],
                },
            ),
            compilation_job_id=job_id,
            backend_id=backend_id,
            backend_version=backend_version,
            created_at=utcnow().isoformat(),
            files=files,
        )

        manifest_path = output_root / "artifact-manifest.json"

        manifest_path.write_text(
            manifest.model_dump_json(indent=2),
            encoding="utf-8",
        )

        return manifest

    def _safe_path(self, output_root: Path, artifact_path: str) -> Path:
        candidate = (output_root / artifact_path).resolve()

        if not str(candidate).startswith(str(output_root)):
            raise ArtifactPackagingError(
                f"Artifact path escapes output root: {artifact_path}"
            )

        return candidate