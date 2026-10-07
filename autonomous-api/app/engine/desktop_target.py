"""Governed desktop target contract for Bucket 4.4."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class DesktopTarget(str, Enum):
    WINDOWS = "windows"
    MACOS = "macos"


class DesktopArtifact(str, Enum):
    WINDOWS_INSTALLER = "windows_installer"
    WINDOWS_PORTABLE = "windows_portable"
    MACOS_APP = "macos_app"
    MACOS_DMG = "macos_dmg"


@dataclass(frozen=True)
class DesktopTargetContract:
    target: DesktopTarget
    allowed_artifacts: tuple[DesktopArtifact, ...]
    requires_human_release_authorization: bool = True
    allows_marketplace_publication: bool = False

    @classmethod
    def for_target(cls, target: DesktopTarget) -> "DesktopTargetContract":
        if not isinstance(target, DesktopTarget):
            raise ValueError("invalid-desktop-target")
        artifacts = {
            DesktopTarget.WINDOWS: (DesktopArtifact.WINDOWS_INSTALLER, DesktopArtifact.WINDOWS_PORTABLE),
            DesktopTarget.MACOS: (DesktopArtifact.MACOS_APP, DesktopArtifact.MACOS_DMG),
        }
        return cls(target=target, allowed_artifacts=artifacts[target])

    def allows_artifact(self, artifact: DesktopArtifact) -> bool:
        if not isinstance(artifact, DesktopArtifact):
            raise ValueError("invalid-desktop-artifact")
        return artifact in self.allowed_artifacts

    def validate_release_authorization(self, authorized: bool) -> None:
        if not authorized:
            raise ValueError("desktop-release-authorization-required")
