"""Governed execution contract for desktop build and packaging work.

This layer deliberately does not choose a desktop framework or release toolchain.
It validates an authorized target/artifact pair and produces a deterministic build
request that an existing bounded executor can execute. Release publication remains
separately human-authorized.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json

from .desktop_target import DesktopArtifact, DesktopTarget, DesktopTargetContract


class DesktopBuildPhase(str, Enum):
    BUILD = "BUILD"
    VERIFY = "VERIFY"
    PACKAGE = "PACKAGE"


@dataclass(frozen=True)
class DesktopBuildRequest:
    build_id: str
    workspace_id: str
    target: DesktopTarget
    artifact: DesktopArtifact
    phase: DesktopBuildPhase
    command: tuple[str, ...]
    expected_artifact_path: str

    def canonical_payload(self) -> dict[str, object]:
        return {
            "build_id": self.build_id,
            "workspace_id": self.workspace_id,
            "target": self.target.value,
            "artifact": self.artifact.value,
            "phase": self.phase.value,
            "command": list(self.command),
            "expected_artifact_path": self.expected_artifact_path,
        }

    def digest(self) -> str:
        payload = json.dumps(
            self.canonical_payload(), sort_keys=True, separators=(",", ":")
        ).encode()
        return hashlib.sha256(payload).hexdigest()


@dataclass(frozen=True)
class DesktopBuildEvidence:
    build_id: str
    request_digest: str
    target: DesktopTarget
    artifact: DesktopArtifact
    platform_identity: str
    artifact_digest: str
    verification_refs: tuple[str, ...]

    @property
    def complete(self) -> bool:
        return bool(
            self.build_id
            and self.request_digest
            and self.platform_identity
            and self.artifact_digest
            and self.verification_refs
        )


def create_desktop_build_request(
    *,
    build_id: str,
    workspace_id: str,
    target: DesktopTarget,
    artifact: DesktopArtifact,
    phase: DesktopBuildPhase,
    command: tuple[str, ...],
    expected_artifact_path: str,
) -> DesktopBuildRequest:
    if not build_id:
        raise ValueError("desktop-build-missing-id")
    if not workspace_id:
        raise ValueError("desktop-build-missing-workspace")
    if not command:
        raise ValueError("desktop-build-missing-command")
    if any(not part for part in command):
        raise ValueError("desktop-build-invalid-command")
    if not expected_artifact_path:
        raise ValueError("desktop-build-missing-artifact-path")

    contract = DesktopTargetContract.for_target(target)
    if not contract.allows_artifact(artifact):
        raise ValueError(
            f"desktop-build-artifact-not-allowed:{target.value}:{artifact.value}"
        )

    return DesktopBuildRequest(
        build_id=build_id,
        workspace_id=workspace_id,
        target=target,
        artifact=artifact,
        phase=phase,
        command=command,
        expected_artifact_path=expected_artifact_path,
    )


def validate_desktop_build_evidence(
    request: DesktopBuildRequest,
    evidence: DesktopBuildEvidence,
) -> DesktopBuildEvidence:
    if evidence.build_id != request.build_id:
        raise ValueError("desktop-build-evidence-id-mismatch")
    if evidence.request_digest != request.digest():
        raise ValueError("desktop-build-evidence-request-mismatch")
    if evidence.target != request.target or evidence.artifact != request.artifact:
        raise ValueError("desktop-build-evidence-target-mismatch")
    if not evidence.complete:
        raise ValueError("desktop-build-evidence-incomplete")
    return evidence
