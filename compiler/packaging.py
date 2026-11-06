"""
Artifact packaging system.

The packager writes backend-produced artifacts to disk and creates a
verifiable artifact manifest. Backend paths are untrusted input.
"""
from __future__ import annotations

import hashlib
from pathlib import Path, PurePosixPath, PureWindowsPath

from .errors import ArtifactPackagingError
from .ids import deterministic_id
from .models import (
    ArtifactFile,
    ArtifactManifest,
    CompilationOutput,
    utcnow,
)


class ArtifactPackager:
    """Packages compilation artifacts into an isolated output directory."""

    def package(
        self,
        output: CompilationOutput,
        job_id: str,
        backend_id: str,
        backend_version: str,
        output_root: Path,
    ) -> ArtifactManifest:
        """Preflight all paths, then write files and produce a manifest."""
        output_root = Path(output_root)
        output_root.mkdir(parents=True, exist_ok=True)
        output_root = output_root.resolve()
        if any(output_root.iterdir()):
            raise ArtifactPackagingError(
                "Artifact output directory must be empty; use a fresh job workspace."
            )

        planned: list[tuple[object, Path]] = []
        seen: set[str] = set()
        for artifact in output.artifacts:
            target_path = self._safe_path(output_root, artifact.path)
            normalized = "/".join(
                part.casefold() for part in target_path.relative_to(output_root).parts
            )
            if normalized in seen:
                raise ArtifactPackagingError(
                    f"Duplicate artifact path after normalization: {artifact.path!r}"
                )
            seen.add(normalized)
            planned.append((artifact, target_path))

        files: list[ArtifactFile] = []
        for artifact, target_path in planned:
            target_path.parent.mkdir(parents=True, exist_ok=True)
            # Re-check after directory creation to reject symlink redirection.
            resolved_parent = target_path.parent.resolve()
            if not resolved_parent.is_relative_to(output_root) or target_path.is_symlink():
                raise ArtifactPackagingError(
                    f"Artifact path changed or escaped during packaging: {artifact.path!r}"
                )

            content_bytes = artifact.content.encode("utf-8")
            target_path.write_bytes(content_bytes)
            content_hash = hashlib.sha256(content_bytes).hexdigest()
            files.append(
                ArtifactFile(
                    path=target_path.relative_to(output_root).as_posix(),
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
        if manifest_path.exists() or manifest_path.is_symlink():
            raise ArtifactPackagingError("artifact-manifest.json is reserved for the packager.")
        manifest_path.write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
        return manifest

    def _safe_path(self, output_root: Path, artifact_path: str) -> Path:
        if (
            not isinstance(artifact_path, str)
            or not artifact_path
            or "\x00" in artifact_path
        ):
            raise ArtifactPackagingError(f"Unsafe artifact path: {artifact_path!r}")

        normalized_input = artifact_path.replace("\\", "/")
        raw_parts = normalized_input.split("/")
        posix = PurePosixPath(normalized_input)
        windows = PureWindowsPath(artifact_path)
        if (
            posix.is_absolute()
            or windows.is_absolute()
            or bool(windows.drive)
            or bool(windows.root)
            or any(part in ("", ".", "..") for part in raw_parts)
            or any(part.casefold() in {".git", ".tiannara"} for part in raw_parts)
            or "/".join(part.casefold() for part in posix.parts) == "artifact-manifest.json"
        ):
            raise ArtifactPackagingError(f"Unsafe or reserved artifact path: {artifact_path!r}")

        root = output_root.resolve()
        target = root.joinpath(*posix.parts)
        current = root
        for part in posix.parts[:-1]:
            current = current / part
            if current.is_symlink():
                raise ArtifactPackagingError(
                    f"Artifact path traverses a symlink: {artifact_path!r}"
                )
        if target.is_symlink():
            raise ArtifactPackagingError(
                f"Artifact path targets a symlink: {artifact_path!r}"
            )

        resolved = target.resolve(strict=False)
        if not resolved.is_relative_to(root):
            raise ArtifactPackagingError(
                f"Artifact path escapes output root: {artifact_path!r}"
            )
        return target
