"""Cap-C Stage 2: backend capability declarations.

A compiler backend describes WHAT it can produce (artifact kinds +
capabilities) without the registry caring WHO it is or HOW it executes.
Declarations are passed explicitly at registration time, so existing backends
need no modification. v1 vocabulary.
"""

from __future__ import annotations

import enum

from pydantic import BaseModel, ConfigDict, Field

from .capability_manifest import BundleCapability


class ArtifactKind(str, enum.Enum):
    BACKEND_SERVICE = "backend_service"
    FRONTEND_APPLICATION = "frontend_application"
    DATABASE_MIGRATION = "database_migration"
    INFRASTRUCTURE_PROVISION = "infrastructure_provision"
    DEPLOYMENT = "deployment"
    DOCUMENTATION = "documentation"


class BackendCapabilityDeclaration(BaseModel):
    """Self-description a backend supplies (directly or via a manifest).

    Carried opaquely by the registry; selection is capability-driven and
    never keyed on backend_id beyond provenance.
    """

    model_config = ConfigDict(frozen=True)

    backend_id: str = Field(min_length=1)
    artifact_kinds: list[ArtifactKind] = Field(min_length=1)
    capabilities: list[BundleCapability]
    quality_profile: float = Field(default=0.0, ge=0.0, le=1.0)
    metadata: dict[str, str] = Field(default_factory=dict)

    @property
    def capability_set(self) -> set[BundleCapability]:
        return set(self.capabilities)

    def supports(
        self,
        artifact_kind: ArtifactKind,
        required_capabilities: list[BundleCapability],
    ) -> tuple[bool, list[BundleCapability]]:
        if artifact_kind not in self.artifact_kinds:
            return False, list(required_capabilities)
        missing = [c for c in required_capabilities if c not in self.capabilities]
        return (len(missing) == 0), missing


class CompilationRequirement(BaseModel):
    """A single capability-driven match target."""

    model_config = ConfigDict(frozen=True)

    artifact_kind: ArtifactKind
    required_capabilities: list[BundleCapability]
    subject_ref: str = ""


class PlannedCompilation(BaseModel):
    """One requirement bound to its selected backend's declaration."""

    model_config = ConfigDict(frozen=True)

    requirement: CompilationRequirement
    backend_id: str
    declaration: BackendCapabilityDeclaration


class CompilationPlan(BaseModel):
    """A deterministic, fully-resolved selection result."""

    model_config = ConfigDict(frozen=True)

    plan_id: str
    policy_name: str
    planned: list[PlannedCompilation]


def derive_plan_id(
    requirements: list[CompilationRequirement],
    policy_name: str,
) -> str:
    """Deterministic, content-addressed plan identifier (SHA-256 truncated)."""
    import hashlib
    import json

    payload = json.dumps(
        {
            "policy_name": policy_name,
            "requirements": [r.model_dump(mode="json") for r in requirements],
        },
        sort_keys=True,
    )
    return "plan-" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
