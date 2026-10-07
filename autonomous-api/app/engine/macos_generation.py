"""Governed macOS software-generation boundary for ESAP."""
from __future__ import annotations
from dataclasses import dataclass
import hashlib, json
from .desktop_build import DesktopBuildRequest
from .desktop_target import DesktopArtifact, DesktopTarget

@dataclass(frozen=True)
class MacOSGenerationRequest:
    generation_id: str
    build: DesktopBuildRequest
    host_identity: str
    def canonical_payload(self) -> dict[str, object]:
        return {"generation_id": self.generation_id, "build_digest": self.build.digest(), "host_identity": self.host_identity}
    def digest(self) -> str:
        return hashlib.sha256(json.dumps(self.canonical_payload(), sort_keys=True, separators=(",", ":")).encode()).hexdigest()

def create_macos_generation_request(*, generation_id: str, build: DesktopBuildRequest, host_identity: str) -> MacOSGenerationRequest:
    if not generation_id: raise ValueError("macos-generation-missing-id")
    if not host_identity: raise ValueError("macos-generation-missing-host")
    if build.target is not DesktopTarget.MACOS: raise ValueError("macos-generation-requires-macos-target")
    if build.artifact not in {DesktopArtifact.MACOS_APP, DesktopArtifact.MACOS_DMG}: raise ValueError("macos-generation-invalid-artifact")
    if not host_identity.lower().startswith("macos"): raise ValueError("macos-generation-requires-macos-host")
    return MacOSGenerationRequest(generation_id, build, host_identity)

def validate_macos_generation_result(request: MacOSGenerationRequest, *, generation_id: str, request_digest: str, artifact_digest: str) -> None:
    if generation_id != request.generation_id: raise ValueError("macos-generation-result-id-mismatch")
    if request_digest != request.digest(): raise ValueError("macos-generation-result-request-mismatch")
    if not artifact_digest: raise ValueError("macos-generation-result-missing-artifact")
