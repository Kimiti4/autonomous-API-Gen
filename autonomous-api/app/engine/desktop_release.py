"""Production release boundary for Windows/macOS artifacts.

Build and verification can be autonomous under bounded execution. Signing,
notarization, distribution, and marketplace publication are consequential
release actions and therefore require explicit human authorization.
"""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
import hashlib, json

from .desktop_build import DesktopBuildEvidence, DesktopBuildRequest, validate_desktop_build_evidence
from .desktop_target import DesktopTarget

class DesktopReleaseAction(str, Enum):
    SIGN="sign"
    NOTARIZE="notarize"
    DISTRIBUTE="distribute"

@dataclass(frozen=True)
class DesktopReleaseAuthorization:
    authorization_id: str
    authorized_by: str
    target: DesktopTarget
    artifact_digest: str
    actions: tuple[DesktopReleaseAction,...]

    def __post_init__(self):
        if not self.authorization_id.strip() or not self.authorized_by.strip():
            raise ValueError("desktop-release-human-authorization-required")
        if len(self.artifact_digest)!=64: raise ValueError("desktop-release-invalid-artifact-digest")
        if not self.actions: raise ValueError("desktop-release-no-authorized-actions")

@dataclass(frozen=True)
class DesktopReleaseReadiness:
    target: DesktopTarget
    artifact_digest: str
    build_verified: bool
    authorized_actions: tuple[DesktopReleaseAction,...]
    production_ready: bool
    reasons: tuple[str,...]
    digest: str

def assess_desktop_release(
    request: DesktopBuildRequest,
    evidence: DesktopBuildEvidence,
    *,
    artifact_digest: str,
    authorization: DesktopReleaseAuthorization | None = None,
    required_actions: tuple[DesktopReleaseAction,...] = (),
) -> DesktopReleaseReadiness:
    validate_desktop_build_evidence(request,evidence)
    if evidence.target != request.target or evidence.artifact_digest != artifact_digest:
        raise ValueError("desktop-release-artifact-binding-mismatch")
    reasons=[]
    if authorization is None and required_actions:
        reasons.append("human-release-authorization-required")
    elif authorization is not None:
        if authorization.target != request.target or authorization.artifact_digest != artifact_digest:
            reasons.append("human-release-authorization-binding-mismatch")
        missing=tuple(a for a in required_actions if a not in authorization.actions)
        if missing: reasons.append("required-release-actions-not-authorized")
    ready=not reasons
    payload={"target":request.target.value,"artifact_digest":artifact_digest,"build_verified":True,
             "authorized_actions":[a.value for a in (authorization.actions if authorization else ())],
             "production_ready":ready,"reasons":reasons}
    digest=hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    return DesktopReleaseReadiness(request.target,artifact_digest,True,
        tuple(authorization.actions if authorization else ()),ready,tuple(reasons),digest)
